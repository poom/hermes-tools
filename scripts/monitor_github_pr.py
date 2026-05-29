#!/usr/bin/env python3
"""Portable quiet watcher for a GitHub PR.

Designed for Hermes cron no_agent jobs. It is silent while the PR head SHA is
unchanged, prints once when the PR closes, and can schedule a one-shot Hermes
review job when a new head SHA appears.

Required input: --pr-url or GITHUB_PR_MONITOR_URL.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_tools_common import hermes_home, portable_env, which_executable

PR_URL_RE = re.compile(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", re.I)
ENV = portable_env()


@dataclass(frozen=True)
class MonitorConfig:
    pr_url: str
    owner_repo: str
    pr_number: str
    repo_dir: Path
    state_file: Path
    review_note: Path
    lock_file: Path
    hermes_cmd: str
    delivery_target: str
    skills: list[str]
    review_instruction: str
    schedule_review: bool
    initialize_only: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-_") or "github-pr"


def parse_pr_ref(pr_url: str, owner_repo: str, pr_number: str) -> tuple[str, str]:
    if owner_repo and pr_number:
        return owner_repo, pr_number
    m = PR_URL_RE.search(pr_url)
    if not m:
        raise ValueError("--pr-url must look like https://github.com/OWNER/REPO/pull/NUMBER, or set --repo and --number")
    owner, repo, number = m.groups()
    return owner_repo or f"{owner}/{repo}", pr_number or number


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def build_config(argv: list[str] | None = None) -> MonitorConfig:
    parser = argparse.ArgumentParser(description="Watch a GitHub PR and schedule a Hermes re-review on head changes.")
    parser.add_argument("--pr-url", default=os.getenv("GITHUB_PR_MONITOR_URL", ""))
    parser.add_argument("--repo", default=os.getenv("GITHUB_PR_MONITOR_REPO", ""), help="OWNER/REPO; derived from --pr-url when omitted")
    parser.add_argument("--number", default=os.getenv("GITHUB_PR_MONITOR_NUMBER", ""), help="PR number; derived from --pr-url when omitted")
    parser.add_argument("--repo-dir", default=os.getenv("GITHUB_PR_MONITOR_REPO_DIR", ""))
    parser.add_argument("--state-file", default=os.getenv("GITHUB_PR_MONITOR_STATE_FILE", ""))
    parser.add_argument("--review-note", default=os.getenv("GITHUB_PR_MONITOR_REVIEW_NOTE", ""))
    parser.add_argument("--lock-file", default=os.getenv("GITHUB_PR_MONITOR_LOCK_FILE", ""))
    parser.add_argument("--hermes", default=os.getenv("HERMES_CLI", ""))
    parser.add_argument("--deliver", default=os.getenv("GITHUB_PR_MONITOR_DELIVER", ""))
    parser.add_argument("--skills", default=os.getenv("GITHUB_PR_MONITOR_SKILLS", "pr-review-guardrails,github-code-review,linear"))
    parser.add_argument("--review-instruction", default=os.getenv("GITHUB_PR_MONITOR_REVIEW_INSTRUCTION", "Review the current PR head with the relevant guardrails. Post GitHub review comments only for real blockers; otherwise keep the summary in the delivery channel."))
    parser.add_argument("--no-schedule-review", action="store_true", default=env_bool("GITHUB_PR_MONITOR_NO_SCHEDULE_REVIEW", False))
    parser.add_argument("--initialize-only", action="store_true", default=env_bool("GITHUB_PR_MONITOR_INITIALIZE_ONLY", False), help="Record the current SHA without scheduling a review when no prior SHA exists")
    args = parser.parse_args(argv)

    if not args.pr_url:
        raise ValueError("set --pr-url or GITHUB_PR_MONITOR_URL")
    owner_repo, pr_number = parse_pr_ref(args.pr_url, args.repo, args.number)
    slug = safe_slug(f"{owner_repo}-{pr_number}")
    home = hermes_home()
    repo_dir = Path(args.repo_dir or home / "pr-worktrees" / "repo" / slug).expanduser()
    state_file = Path(args.state_file or home / "pr-monitors" / f"{slug}.json").expanduser()
    review_note = Path(args.review_note or home / "pr-reviews" / f"{slug}.md").expanduser()
    lock_file = Path(args.lock_file or home / "pr-monitors" / f"{slug}.lock").expanduser()
    hermes_cmd = args.hermes or which_executable("hermes", "HERMES_CLI") or "hermes"
    skills = [s.strip() for s in args.skills.split(",") if s.strip()]
    return MonitorConfig(
        pr_url=args.pr_url,
        owner_repo=owner_repo,
        pr_number=str(pr_number),
        repo_dir=repo_dir,
        state_file=state_file,
        review_note=review_note,
        lock_file=lock_file,
        hermes_cmd=hermes_cmd,
        delivery_target=args.deliver,
        skills=skills,
        review_instruction=args.review_instruction,
        schedule_review=not args.no_schedule_review,
        initialize_only=args.initialize_only,
    )


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=check, env=ENV)


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(path)


def acquire_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fh = path.open("w")
    try:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return None
    lock_fh.write(f"pid={os.getpid()} started_at={now_iso()}\n")
    lock_fh.flush()
    return lock_fh


def gh_pr(cfg: MonitorConfig) -> dict[str, Any]:
    cp = run([
        "gh", "pr", "view", cfg.pr_url,
        "--json", "headRefOid,state,closed,mergedAt,title,url,updatedAt,reviewDecision,mergeStateStatus,baseRefName,headRefName",
        "--jq", ".",
    ], timeout=60)
    return json.loads(cp.stdout)


def pause_self(cfg: MonitorConfig, state: dict[str, Any]) -> str:
    job_id = state.get("job_id")
    if not job_id:
        return ""
    try:
        cp = run([cfg.hermes_cmd, "cron", "pause", str(job_id)], timeout=60, check=False)
        if cp.returncode == 0:
            return f"\nPaused monitor job `{job_id}`."
        detail = (cp.stderr or cp.stdout).strip()
        return f"\nTried to pause monitor job `{job_id}`, but pause failed: {detail}"
    except Exception as exc:
        return f"\nTried to pause monitor job `{job_id}`, but pause failed: {exc}"


def ensure_checkout(cfg: MonitorConfig, pr: dict[str, Any]) -> None:
    cfg.repo_dir.parent.mkdir(parents=True, exist_ok=True)
    if not (cfg.repo_dir / ".git").exists():
        if cfg.repo_dir.exists():
            import shutil
            shutil.rmtree(cfg.repo_dir)
        run(["gh", "repo", "clone", cfg.owner_repo, str(cfg.repo_dir), "--", "--quiet"], timeout=600)
    run(["git", "fetch", "origin", f"pull/{cfg.pr_number}/head", "--quiet"], cwd=cfg.repo_dir, timeout=300)
    run(["git", "fetch", "origin", pr.get("baseRefName") or "main", "--quiet"], cwd=cfg.repo_dir, timeout=300)
    run(["git", "checkout", "-B", f"pr-{cfg.pr_number}", "FETCH_HEAD", "--quiet"], cwd=cfg.repo_dir, timeout=120)
    run(["git", "reset", "--hard", pr["headRefOid"], "--quiet"], cwd=cfg.repo_dir, timeout=120)


def build_review_prompt(cfg: MonitorConfig, pr: dict[str, Any], state: dict[str, Any]) -> str:
    previous_sha = state.get("last_seen_sha") or "unknown"
    return f"""
Use pr-review-guardrails to re-review PR {cfg.pr_url} because the watcher detected a new head SHA.

Context:
- Repository checkout: {cfg.repo_dir}
- Previous reviewed SHA: {previous_sha}
- New current SHA: {pr['headRefOid']}
- Base branch: {pr.get('baseRefName') or 'main'}
- Head branch: {pr.get('headRefName') or ''}
- Review continuity note: {cfg.review_note}
- Operator instruction: {cfg.review_instruction}

Mandatory steps:
1. Refresh live PR state from GitHub before deciding anything: head SHA, diff, changed files, title/body/comments, checks, reviewDecision/merge state.
2. Read {cfg.review_note} if it exists and compare what changed since the last review. Re-validate previous blockers before repeating them.
3. Review only the current head. Focus on blockers, tests/CI, rollout safety, security, and regressions relevant to this PR.
4. Run practical checks from the repo if available; at minimum inspect CI/check output from GitHub. Do not spend time on full local setup if CI gives decisive evidence.
5. If blockers remain or new blockers are found: post de-duplicated inline GitHub comments and a REQUEST_CHANGES summary review.
6. If no blockers are found: do not post noisy GitHub comments solely to say so unless the operator instruction asks for it.
7. Update {cfg.review_note} with dated status, latest SHA, verdict, blockers/suggestions, CI snapshot, and any GitHub review links.
8. After the review completes, update {cfg.state_file}: set `last_seen_sha` and `last_reviewed_sha` to `{pr['headRefOid']}`, set `last_review_completed_at` to the current UTC timestamp, set `closed_notified` to false, and remove `pending_review_sha`, `pending_review_job_id`, and `pending_review_created_at` if present.

Review delivery format:
{cfg.owner_repo} #{cfg.pr_number} — {pr.get('title','')}
🔗 {cfg.pr_url}
Verdict: <Approve | Needs changes | Blocked | Pass>
Why:
- <2-5 bullets>
Merge readiness: <merge-ready | not merge-ready | merge-ready after X>
GitHub action: <requested changes/commented/not posted because no blockers>
""".strip()


def schedule_review_job(cfg: MonitorConfig, pr: dict[str, Any], prompt: str) -> tuple[str, str]:
    name = f"Re-review {cfg.owner_repo} PR #{cfg.pr_number} @ {pr['headRefOid'][:8]}"
    cmd = [cfg.hermes_cmd, "cron", "create", "1m", prompt, "--name", name, "--repeat", "1"]
    if cfg.delivery_target:
        cmd.extend(["--deliver", cfg.delivery_target])
    for skill in cfg.skills:
        cmd.extend(["--skill", skill])
    cmd.extend(["--workdir", str(cfg.repo_dir)])
    cp = run(cmd, timeout=120)
    job_id = "unknown"
    for line in cp.stdout.splitlines():
        line = line.strip()
        if line.startswith("Created job:"):
            job_id = line.split(":", 1)[1].strip()
            break
    return job_id, cp.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    cfg = build_config(argv)
    lock_fh = acquire_lock(cfg.lock_file)
    if lock_fh is None:
        return 0
    try:
        state = load_state(cfg.state_file)
        pr = gh_pr(cfg)
        current_sha = pr.get("headRefOid")
        state["job_id"] = state.get("job_id") or os.getenv("HERMES_CRON_JOB_ID", "")
        state["last_checked_at"] = now_iso()
        state["last_pr_state"] = pr.get("state")
        state["last_pr_updated_at"] = pr.get("updatedAt")

        if pr.get("closed") or pr.get("state") != "OPEN":
            if not state.get("closed_notified"):
                state["closed_notified"] = True
                state["closed_at_seen"] = now_iso()
                save_state(cfg.state_file, state)
                merged = f"merged at {pr.get('mergedAt')}" if pr.get("mergedAt") else "closed without merge"
                print(f"{cfg.owner_repo} #{cfg.pr_number} is now closed ({merged}). Monitoring is complete.{pause_self(cfg, state)}")
            else:
                save_state(cfg.state_file, state)
            return 0

        if state.get("last_seen_sha") == current_sha or state.get("pending_review_sha") == current_sha:
            save_state(cfg.state_file, state)
            return 0

        if not state.get("last_seen_sha") and cfg.initialize_only:
            state["last_seen_sha"] = current_sha
            state["initialized_at"] = now_iso()
            save_state(cfg.state_file, state)
            return 0

        old_sha = state.get("last_seen_sha") or "unknown"
        state["last_detected_change_at"] = now_iso()
        state["last_detected_old_sha"] = old_sha
        state["last_detected_new_sha"] = current_sha
        save_state(cfg.state_file, state)

        if not cfg.schedule_review:
            state["last_seen_sha"] = current_sha
            save_state(cfg.state_file, state)
            print(f"Detected new commits on {cfg.owner_repo} #{cfg.pr_number}: `{old_sha}` → `{current_sha}`.")
            return 0

        ensure_checkout(cfg, pr)
        prompt = build_review_prompt(cfg, pr, state)
        review_job_id, create_output = schedule_review_job(cfg, pr, prompt)

        state = load_state(cfg.state_file)
        state["pending_review_sha"] = current_sha
        state["pending_review_job_id"] = review_job_id
        state["pending_review_created_at"] = now_iso()
        save_state(cfg.state_file, state)

        print(
            f"Detected new commits on {cfg.owner_repo} #{cfg.pr_number}: `{old_sha}` → `{current_sha}`.\n"
            f"Scheduled one-shot guardrail re-review job `{review_job_id}`; it should deliver the full review when complete.\n\n"
            f"```text\n{create_output}\n```"
        )
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"PR monitor command failed: {exc.cmd}\nexit={exc.returncode}\nstdout={exc.stdout}\nstderr={exc.stderr}", file=sys.stderr)
        raise
    finally:
        try:
            lock_fh.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
