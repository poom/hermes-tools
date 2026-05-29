#!/usr/bin/env python3
"""Claim and hand off one pending PR review queue issue.

Default mode is dry-run. Pass --apply plus either --schedule-hermes or
--claim-only to mutate queue state.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from queue_common import (
    QueueItem,
    choose_winning_claim,
    classify_pr_for_queue,
    compute_queue_key,
    iso_after,
    label_names,
    now_iso,
    now_utc,
    parse_queue_item,
    render_claim_comment,
    render_heartbeat_comment,
    render_requeue_comment,
    render_result_comment,
    result_labels,
    safe_worker_name,
)

DEFAULT_QUEUE_REPO = os.environ.get("HERMES_PR_REVIEW_QUEUE_REPO", "poom/hermes-pr-review-queue")
DEFAULT_REVIEWER = os.environ.get("HERMES_PR_REVIEW_REVIEWER", "poom")


@dataclass(frozen=True)
class ClaimedIssue:
    issue: dict[str, Any]
    item: QueueItem
    lease_id: str


def run(cmd: list[str], *, input_text: str | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr or result.stdout}")
    return result


def json_from_text(text: str) -> Any:
    raw = text.strip()
    for idx, char in enumerate(raw):
        if char not in "[{":
            continue
        try:
            return json.loads(raw[idx:])
        except json.JSONDecodeError:
            continue
    raise ValueError(f"could not parse JSON output: {raw[:200]}")


def gh_json(cmd: list[str], *, timeout: int = 120) -> Any:
    return json_from_text(run(cmd, timeout=timeout).stdout)


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def queue_repo_api_path(queue_repo: str) -> str:
    if "/" not in queue_repo:
        raise ValueError("--queue-repo must be OWNER/REPO")
    return f"repos/{queue_repo}"


@contextmanager
def local_worker_lock(worker_name: str, lock_dir: str | None):
    root = Path(lock_dir).expanduser() if lock_dir else hermes_home() / "run" / f"pending-pr-review-worker-{worker_name}.lock"
    root.parent.mkdir(parents=True, exist_ok=True)
    try:
        root.mkdir()
    except FileExistsError:
        yield None
        return
    owner_file = root / "owner"
    owner_file.write_text(f"pid={os.getpid()} started_at={now_iso()}\n", encoding="utf-8")
    try:
        yield root
    finally:
        try:
            owner_file.unlink(missing_ok=True)
            root.rmdir()
        except OSError:
            pass


def ensure_label(queue_repo: str, name: str, *, color: str = "ededed", description: str = "Hermes PR-review queue") -> None:
    result = run(
        ["gh", "label", "create", name, "--repo", queue_repo, "--color", color, "--description", description],
        check=False,
    )
    if result.returncode != 0 and "already exists" not in (result.stderr + result.stdout).lower():
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def issue_comment(queue_repo: str, issue_number: int, body: str) -> None:
    run(["gh", "issue", "comment", str(issue_number), "--repo", queue_repo, "--body", body], timeout=90)


def issue_edit_labels(queue_repo: str, issue_number: int, *, add: list[str] | None = None, remove: list[str] | None = None) -> None:
    add = add or []
    remove = remove or []
    if not add and not remove:
        return
    if add:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--add-label", ",".join(add)], timeout=90, check=False)
    if remove:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--remove-label", ",".join(remove)], timeout=90, check=False)


def issue_close(queue_repo: str, issue_number: int, reason: str) -> None:
    run(["gh", "issue", "close", str(issue_number), "--repo", queue_repo, "--reason", reason], timeout=90, check=False)


def list_candidate_issues(queue_repo: str, source_labels: set[str], limit: int) -> list[dict[str, Any]]:
    payload = gh_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            queue_repo,
            "--state",
            "open",
            "--label",
            "hermes:queued",
            "--limit",
            str(limit),
            "--json",
            "number,title,url,body,labels,createdAt",
        ],
        timeout=120,
    )
    issues = [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []
    candidates: list[dict[str, Any]] = []
    for issue in issues:
        labels = label_names(issue)
        if source_labels and not labels.intersection(source_labels):
            continue
        if parse_queue_item(issue.get("body") or ""):
            candidates.append(issue)
    return sorted(candidates, key=lambda issue: issue.get("createdAt") or "")


def fetch_comments(queue_repo: str, issue_number: int) -> list[dict[str, Any]]:
    payload = gh_json(["gh", "api", "--paginate", "--slurp", f"{queue_repo_api_path(queue_repo)}/issues/{issue_number}/comments"], timeout=120)
    if isinstance(payload, list) and payload and all(isinstance(page, list) for page in payload):
        comments: list[dict[str, Any]] = []
        for page in payload:
            comments.extend(item for item in page if isinstance(item, dict))
        return comments
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def fetch_pr_state(repo: str, number: int) -> dict[str, Any]:
    return gh_json(
        [
            "gh",
            "pr",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "headRefOid,state,isDraft,reviewRequests,reviewDecision,mergeStateStatus,url,title,author",
            "--jq",
            ".",
        ],
        timeout=90,
    )


def fetch_reviews(repo: str, number: int) -> list[dict[str, Any]]:
    payload = gh_json(["gh", "api", "--paginate", "--slurp", f"repos/{repo}/pulls/{number}/reviews"], timeout=120)
    if isinstance(payload, list) and payload and all(isinstance(page, list) for page in payload):
        reviews: list[dict[str, Any]] = []
        for page in payload:
            reviews.extend(item for item in page if isinstance(item, dict))
        return reviews
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def record_result(
    *,
    queue_repo: str,
    issue_number: int,
    worker_name: str,
    lease_id: str,
    queue_key: str,
    result: str,
    pr_review_id: str = "",
    review_state: str = "",
    commit_id: str = "",
    summary: str = "",
    apply: bool,
) -> None:
    body = render_result_comment(
        worker=worker_name,
        lease_id=lease_id,
        queue_key=queue_key,
        result=result,
        pr_review_id=pr_review_id,
        review_state=review_state,
        commit_id=commit_id,
        summary=summary,
    )
    remove, add, close_reason = result_labels(result)
    if not apply:
        print("Dry-run result comment:")
        print(body)
        print(f"Would remove labels: {', '.join(remove)}")
        print(f"Would add labels: {', '.join(add)}")
        print(f"Would close issue #{issue_number} as {close_reason}")
        return
    issue_comment(queue_repo, issue_number, body)
    issue_edit_labels(queue_repo, issue_number, add=add, remove=remove)
    issue_close(queue_repo, issue_number, close_reason)


def claim_issue(args: argparse.Namespace, issue: dict[str, Any], item: QueueItem) -> ClaimedIssue | None:
    worker_name = safe_worker_name(args.worker_name)
    lease_id = f"{worker_name}-{now_utc().strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
    claimed_at = now_iso()
    expires_at = iso_after(args.lease_minutes)
    issue_number = int(issue["number"])
    issue_comment(args.queue_repo, issue_number, render_claim_comment(item, worker=worker_name, lease_id=lease_id, claimed_at=claimed_at, expires_at=expires_at))
    if args.claim_wait_seconds:
        time.sleep(args.claim_wait_seconds)
    comments = fetch_comments(args.queue_repo, issue_number)
    winner = choose_winning_claim(comments, queue_key=item.queue_key, now=now_utc())
    if not winner:
        print(f"No active claim winner for issue #{issue_number}; exiting without review.")
        return None
    if winner.lease_id != lease_id:
        print(f"Claim lost for issue #{issue_number}; winner is {winner.worker} lease {winner.lease_id}.")
        return None
    ensure_label(args.queue_repo, f"worker:{worker_name}", description=f"Hermes worker {worker_name}")
    issue_edit_labels(
        args.queue_repo,
        issue_number,
        add=["hermes:claimed", f"worker:{worker_name}"],
        remove=["hermes:queued"],
    )
    return ClaimedIssue(issue=issue, item=item, lease_id=lease_id)


def preflight_claimed_issue(args: argparse.Namespace, claimed: ClaimedIssue) -> bool:
    item = claimed.item
    issue_number = int(claimed.issue["number"])
    pr_state = fetch_pr_state(item.repo, item.pr_number)
    live_head = str(pr_state.get("headRefOid") or "")
    if live_head:
        expected = compute_queue_key(item.repo, item.pr_number, live_head)
        if expected != item.queue_key and live_head != item.head_sha:
            pass
    reviews = fetch_reviews(item.repo, item.pr_number)
    classification = classify_pr_for_queue(item, pr_state, reviews, reviewer=args.reviewer)
    if classification.should_review:
        return True
    result = "skipped"
    if classification.status in {"stale", "closed", "draft", "already-reviewed"}:
        result = classification.status
    record_result(
        queue_repo=args.queue_repo,
        issue_number=issue_number,
        worker_name=safe_worker_name(args.worker_name),
        lease_id=claimed.lease_id,
        queue_key=item.queue_key,
        result=result,
        commit_id=item.head_sha,
        summary=classification.reason,
        apply=True,
    )
    print(f"Skipped issue #{issue_number}: {classification.reason}")
    return False


def build_review_prompt(args: argparse.Namespace, claimed: ClaimedIssue) -> str:
    item = claimed.item
    script_path = Path(__file__).resolve()
    issue_number = int(claimed.issue["number"])
    worker_name = safe_worker_name(args.worker_name)
    return f"""
You are processing one claimed Hermes pending PR review queue issue.

Queue repo: {args.queue_repo}
Queue issue: {claimed.issue.get('url') or f'https://github.com/{args.queue_repo}/issues/{issue_number}'}
Queue issue number: {issue_number}
Worker name: {worker_name}
Lease id: {claimed.lease_id}
Queue key: {item.queue_key}

PR: {item.pr_url}
Repository: {item.repo}
PR number: {item.pr_number}
Expected head SHA: {item.head_sha}
Reviewer: {args.reviewer}

Use `pr-review-guardrails` and the per-PR policy from `pending-pr-review`.

Mandatory safety gates:
1. Re-fetch the live PR state before reviewing.
2. Abort without posting if the live head SHA differs from `{item.head_sha}`.
3. Re-fetch pulls reviews immediately before posting.
4. Do not post if `{args.reviewer}` already has a current-head APPROVED or CHANGES_REQUESTED review for `{item.head_sha}`.
5. If review work is long, post a heartbeat with:
   python3 {script_path} heartbeat --queue-repo {args.queue_repo} --issue-number {issue_number} --worker-name {worker_name} --lease-id {claimed.lease_id} --queue-key {item.queue_key} --apply
6. After posting and verifying the formal review, record the result with:
   python3 {script_path} record-result --queue-repo {args.queue_repo} --issue-number {issue_number} --worker-name {worker_name} --lease-id {claimed.lease_id} --queue-key {item.queue_key} --result <approved|changes-requested|commented|skipped|failed> --pr-review-id <id-if-any> --review-state <APPROVED|CHANGES_REQUESTED|COMMENTED|SKIPPED> --commit-id {item.head_sha} --summary "<short summary>" --apply

Do not include secrets or internal token usage in GitHub review bodies.
""".strip()


def schedule_hermes(args: argparse.Namespace, claimed: ClaimedIssue) -> str:
    prompt = build_review_prompt(args, claimed)
    item = claimed.item
    name = f"Review {item.repo} PR #{item.pr_number} @ {item.short_head}"
    hermes = args.hermes_cmd or os.environ.get("HERMES_CLI") or "hermes"
    cmd = [
        hermes,
        "cron",
        "create",
        "1m",
        prompt,
        "--name",
        name,
        "--repeat",
        "1",
        "--skill",
        "pending-pr-review-github-issues-queue",
        "--skill",
        "pending-pr-review",
        "--skill",
        "pr-review-guardrails",
    ]
    if args.deliver:
        cmd.extend(["--deliver", args.deliver])
    if args.workdir:
        cmd.extend(["--workdir", args.workdir])
    result = run(cmd, timeout=120)
    issue_comment(
        args.queue_repo,
        int(claimed.issue["number"]),
        f"Scheduled Hermes guardrail review job for {item.pr_url}.\n\n```text\n{result.stdout.strip()}\n```",
    )
    return result.stdout.strip()


def run_once(args: argparse.Namespace) -> int:
    args.worker_name = safe_worker_name(args.worker_name)
    source_labels = set(args.source_label or [])
    candidates = list_candidate_issues(args.queue_repo, source_labels, args.limit)
    if not candidates:
        print("No queued PR review issue found.")
        return 0
    issue = candidates[0]
    item = parse_queue_item(issue.get("body") or "")
    if not item:
        print(f"Oldest candidate issue #{issue.get('number')} has no parseable queue metadata.")
        return 0
    if not args.apply:
        print(f"Dry-run: would claim issue #{issue['number']} for {item.pr_url}")
        print(f"Queue key: {item.queue_key}")
        return 0
    if not args.schedule_hermes and not args.claim_only:
        print("Refusing to claim live work without --schedule-hermes or --claim-only.", file=sys.stderr)
        return 2
    with local_worker_lock(args.worker_name, args.lock_dir) as lock:
        if lock is None:
            print("Previous worker run still active; exiting.")
            return 0
        claimed = claim_issue(args, issue, item)
        if not claimed:
            return 0
        if not preflight_claimed_issue(args, claimed):
            return 0
        if args.schedule_hermes:
            output = schedule_hermes(args, claimed)
            print(f"Claimed issue #{issue['number']} and scheduled Hermes review.")
            print(output)
            return 0
        print(build_review_prompt(args, claimed))
        return 0


def heartbeat(args: argparse.Namespace) -> int:
    worker_name = safe_worker_name(args.worker_name)
    heartbeat_at = now_iso()
    expires_at = iso_after(args.lease_minutes)
    body = render_heartbeat_comment(
        queue_key=args.queue_key,
        worker=worker_name,
        lease_id=args.lease_id,
        heartbeat_at=heartbeat_at,
        expires_at=expires_at,
    )
    if not args.apply:
        print(body)
        return 0
    issue_comment(args.queue_repo, args.issue_number, body)
    print(f"Heartbeat posted for issue #{args.issue_number}; lease expires at {expires_at}.")
    return 0


def record_result_command(args: argparse.Namespace) -> int:
    record_result(
        queue_repo=args.queue_repo,
        issue_number=args.issue_number,
        worker_name=safe_worker_name(args.worker_name),
        lease_id=args.lease_id,
        queue_key=args.queue_key,
        result=args.result,
        pr_review_id=args.pr_review_id,
        review_state=args.review_state,
        commit_id=args.commit_id,
        summary=args.summary,
        apply=args.apply,
    )
    return 0


def sweep_stale(args: argparse.Namespace) -> int:
    payload = gh_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            args.queue_repo,
            "--state",
            "open",
            "--label",
            "hermes:claimed",
            "--limit",
            str(args.limit),
            "--json",
            "number,title,url,body,labels,createdAt",
        ]
    )
    issues = [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []
    requeued = 0
    for issue in issues:
        item = parse_queue_item(issue.get("body") or "")
        if not item:
            continue
        comments = fetch_comments(args.queue_repo, int(issue["number"]))
        winner = choose_winning_claim(comments, queue_key=item.queue_key, now=now_utc())
        if winner:
            continue
        if not args.apply:
            print(f"Dry-run: would requeue expired claimed issue #{issue['number']} ({item.queue_key})")
            requeued += 1
            continue
        issue_comment(args.queue_repo, int(issue["number"]), render_requeue_comment(reason="lease_expired"))
        issue_edit_labels(args.queue_repo, int(issue["number"]), add=["hermes:queued", "hermes:stale"], remove=["hermes:claimed"])
        requeued += 1
    print(f"Requeued stale issues: {requeued}")
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--queue-repo", default=DEFAULT_QUEUE_REPO)
    parser.add_argument("--worker-name", default=os.environ.get("HERMES_PR_REVIEW_WORKER_NAME", ""))
    parser.add_argument("--apply", action="store_true", help="Mutate GitHub Issues. Default is dry-run.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claim and hand off pending PR review queue work.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Claim at most one queue issue")
    add_common_args(run_parser)
    run_parser.add_argument("--reviewer", default=DEFAULT_REVIEWER)
    run_parser.add_argument("--source-label", action="append", default=["source:pending-pr-review", "source:chat-request"])
    run_parser.add_argument("--limit", type=int, default=50)
    run_parser.add_argument("--lease-minutes", type=int, default=90)
    run_parser.add_argument("--claim-wait-seconds", type=float, default=3.0)
    run_parser.add_argument("--lock-dir")
    run_parser.add_argument("--claim-only", action="store_true", help="Claim and print the handoff prompt instead of scheduling Hermes")
    run_parser.add_argument("--schedule-hermes", action="store_true", help="Schedule a one-shot Hermes guardrail review after claiming")
    run_parser.add_argument("--hermes-cmd", default=os.environ.get("HERMES_CLI", ""))
    run_parser.add_argument("--deliver", default=os.environ.get("HERMES_PR_REVIEW_DELIVER", ""))
    run_parser.add_argument("--workdir", default=os.environ.get("HERMES_PR_REVIEW_WORKDIR", ""))
    run_parser.set_defaults(func=run_once)

    heartbeat_parser = subparsers.add_parser("heartbeat", help="Post a lease heartbeat")
    add_common_args(heartbeat_parser)
    heartbeat_parser.add_argument("--issue-number", type=int, required=True)
    heartbeat_parser.add_argument("--lease-id", required=True)
    heartbeat_parser.add_argument("--queue-key", required=True)
    heartbeat_parser.add_argument("--lease-minutes", type=int, default=90)
    heartbeat_parser.set_defaults(func=heartbeat)

    result_parser = subparsers.add_parser("record-result", help="Comment result labels and close the queue issue")
    add_common_args(result_parser)
    result_parser.add_argument("--issue-number", type=int, required=True)
    result_parser.add_argument("--lease-id", required=True)
    result_parser.add_argument("--queue-key", required=True)
    result_parser.add_argument("--result", required=True)
    result_parser.add_argument("--pr-review-id", default="")
    result_parser.add_argument("--review-state", default="")
    result_parser.add_argument("--commit-id", default="")
    result_parser.add_argument("--summary", default="")
    result_parser.set_defaults(func=record_result_command)

    sweep_parser = subparsers.add_parser("sweep-stale", help="Requeue claimed issues whose lease expired")
    add_common_args(sweep_parser)
    sweep_parser.add_argument("--limit", type=int, default=50)
    sweep_parser.set_defaults(func=sweep_stale)

    parser.set_defaults(func=run_once, command="run")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv:
        argv.insert(0, "run")
    elif argv[0] not in {"run", "heartbeat", "record-result", "sweep-stale", "-h", "--help"}:
        argv.insert(0, "run")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"pending-pr-review worker failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
