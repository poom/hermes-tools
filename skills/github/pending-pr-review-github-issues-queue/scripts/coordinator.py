#!/usr/bin/env python3
"""Mirror Poom's live pending PR review queue into GitHub Issues.

Default mode is dry-run. Pass --apply to create/edit/close issues.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from queue_common import (
    QueueItem,
    classify_pr_for_queue,
    compute_queue_key,
    label_names,
    now_iso,
    parse_queue_item,
    render_queue_issue_body,
    repo_number_from_pending_pr,
    REQUIRED_LABELS,
)

DEFAULT_QUEUE_REPO = os.environ.get("HERMES_PR_REVIEW_QUEUE_REPO", "poom/hermes-pr-review-queue")
DEFAULT_REVIEWER = os.environ.get("HERMES_PR_REVIEW_REVIEWER", "poom")


@dataclass
class Summary:
    created: list[str] = field(default_factory=list)
    already_queued: list[str] = field(default_factory=list)
    closed_existing: list[str] = field(default_factory=list)
    superseded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run_actions: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            "pending-pr-review-discovery",
            f"- created: {len(self.created)}",
            f"- already queued: {len(self.already_queued)}",
            f"- superseded: {len(self.superseded)}",
            f"- closed/skipped: {len(self.closed_existing) + len(self.skipped)}",
            f"- errors: {len(self.errors)}",
        ]
        if self.created:
            lines.append("")
            lines.append("New queue issues:")
            lines.extend(f"- {url}" for url in self.created)
        if self.dry_run_actions:
            lines.append("")
            lines.append("Dry-run actions:")
            lines.extend(f"- {action}" for action in self.dry_run_actions)
        if self.errors:
            lines.append("")
            lines.append("Errors:")
            lines.extend(f"- {err}" for err in self.errors)
        return "\n".join(lines)


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
    if not raw:
        raise ValueError("empty JSON output")
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


def default_discovery_command() -> list[str]:
    here = Path(__file__).resolve()
    sibling = here.parents[2] / "pending-pr-review" / "scripts" / "list_pending_prs.sh"
    if sibling.exists():
        return ["bash", str(sibling), "--stats-json"]
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    return ["bash", str(hermes_home / "skills" / "github" / "pending-pr-review" / "scripts" / "list_pending_prs.sh"), "--stats-json"]


def normalize_discovery_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        prs = payload.get("prs")
        if isinstance(prs, list):
            return [item for item in prs if isinstance(item, dict)]
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    raise ValueError("pending PR discovery output must be a JSON array or an object with a prs array")


def discover_pending_prs(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.pending_pr_json:
        return normalize_discovery_payload(json.loads(Path(args.pending_pr_json).read_text()))
    command = shlex.split(args.discovery_command) if args.discovery_command else default_discovery_command()
    payload = json_from_text(run(command, timeout=args.discovery_timeout).stdout)
    return normalize_discovery_payload(payload)


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


def ensure_labels(queue_repo: str, *, apply: bool, summary: Summary) -> None:
    if not apply:
        summary.dry_run_actions.append(f"would ensure {len(REQUIRED_LABELS)} labels in {queue_repo}")
        return
    for name, (color, description) in REQUIRED_LABELS.items():
        result = run(
            [
                "gh",
                "label",
                "create",
                name,
                "--repo",
                queue_repo,
                "--color",
                color,
                "--description",
                description,
            ],
            check=False,
        )
        if result.returncode != 0 and "already exists" not in (result.stderr + result.stdout).lower():
            summary.errors.append(f"label {name}: {result.stderr.strip() or result.stdout.strip()}")


def ensure_queue_repo(queue_repo: str, *, apply: bool, summary: Summary) -> bool:
    result = run(["gh", "repo", "view", queue_repo], timeout=60, check=False)
    if result.returncode == 0:
        return True
    if not apply:
        summary.dry_run_actions.append(f"would create private queue repo {queue_repo}")
        return False
    created = run(
        [
            "gh",
            "repo",
            "create",
            queue_repo,
            "--private",
            "--description",
            "Hermes distributed pending PR review queue",
        ],
        timeout=120,
        check=False,
    )
    if created.returncode != 0:
        summary.errors.append(f"create queue repo {queue_repo}: {created.stderr.strip() or created.stdout.strip()}")
        return False
    return True


def list_issues_by_search(queue_repo: str, search: str, *, state: str = "all") -> list[dict[str, Any]]:
    payload = gh_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            queue_repo,
            "--state",
            state,
            "--search",
            search,
            "--limit",
            "100",
            "--json",
            "number,state,title,labels,url,body,createdAt",
        ],
        timeout=120,
    )
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def list_open_queue_issues(queue_repo: str) -> list[dict[str, Any]]:
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
            "200",
            "--json",
            "number,state,title,labels,url,body,createdAt",
        ],
        timeout=120,
    )
    issues = [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []
    claimed = gh_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            queue_repo,
            "--state",
            "open",
            "--label",
            "hermes:claimed",
            "--limit",
            "200",
            "--json",
            "number,state,title,labels,url,body,createdAt",
        ],
        timeout=120,
    )
    if isinstance(claimed, list):
        seen = {issue.get("number") for issue in issues}
        issues.extend(item for item in claimed if isinstance(item, dict) and item.get("number") not in seen)
    return issues


def create_issue(queue_repo: str, item: QueueItem, *, apply: bool, summary: Summary) -> str:
    title = f"Review PR: {item.repo}#{item.pr_number} @ {item.short_head}"
    body = render_queue_issue_body(item)
    labels = f"hermes:queued,source:{item.source}"
    if not apply:
        summary.dry_run_actions.append(f"would create issue for {item.queue_key}")
        return ""
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
            tmp.write(body)
            tmp_path = tmp.name
        result = run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                queue_repo,
                "--title",
                title,
                "--body-file",
                tmp_path,
                "--label",
                labels,
            ],
            timeout=120,
        )
        return result.stdout.strip()
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass


def issue_comment(queue_repo: str, issue_number: int, body: str, *, apply: bool, summary: Summary) -> None:
    if not apply:
        summary.dry_run_actions.append(f"would comment on issue #{issue_number}: {body.splitlines()[0] if body else 'comment'}")
        return
    run(["gh", "issue", "comment", str(issue_number), "--repo", queue_repo, "--body", body], timeout=90)


def issue_edit_labels(queue_repo: str, issue_number: int, *, add: list[str] | None = None, remove: list[str] | None = None, apply: bool, summary: Summary) -> None:
    add = add or []
    remove = remove or []
    if not add and not remove:
        return
    if not apply:
        summary.dry_run_actions.append(f"would edit labels on issue #{issue_number}: add={add} remove={remove}")
        return
    if add:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--add-label", ",".join(add)], timeout=90, check=False)
    if remove:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--remove-label", ",".join(remove)], timeout=90, check=False)


def issue_close(queue_repo: str, issue_number: int, *, reason: str, apply: bool, summary: Summary) -> None:
    if not apply:
        summary.dry_run_actions.append(f"would close issue #{issue_number} as {reason}")
        return
    run(["gh", "issue", "close", str(issue_number), "--repo", queue_repo, "--reason", reason], timeout=90, check=False)


def supersede_issue(queue_repo: str, issue: dict[str, Any], current: QueueItem, *, apply: bool, summary: Summary) -> None:
    old = parse_queue_item(issue.get("body") or "")
    if not old:
        return
    issue_number = int(issue["number"])
    body = (
        f"Superseded by current PR head `{current.head_sha}`.\n\n"
        f"Old queue key: `{old.queue_key}`\n"
        f"Current queue key: `{current.queue_key}`"
    )
    issue_comment(queue_repo, issue_number, body, apply=apply, summary=summary)
    issue_edit_labels(
        queue_repo,
        issue_number,
        add=["hermes:superseded"],
        remove=["hermes:queued", "hermes:claimed"],
        apply=apply,
        summary=summary,
    )
    issue_close(queue_repo, issue_number, reason="not planned", apply=apply, summary=summary)
    summary.superseded.append(issue.get("url") or f"#{issue_number}")


def close_existing_issue(queue_repo: str, issue: dict[str, Any], classification: str, detail: str, *, apply: bool, summary: Summary) -> None:
    issue_number = int(issue["number"])
    issue_comment(queue_repo, issue_number, detail, apply=apply, summary=summary)
    if classification in {"closed", "draft", "already-reviewed"}:
        add = ["hermes:skipped", "result:skipped"]
    elif classification == "stale":
        add = ["hermes:stale", "hermes:superseded"]
    else:
        add = ["hermes:skipped"]
    issue_edit_labels(
        queue_repo,
        issue_number,
        add=add,
        remove=["hermes:queued", "hermes:claimed"],
        apply=apply,
        summary=summary,
    )
    issue_close(queue_repo, issue_number, reason="not planned", apply=apply, summary=summary)
    summary.closed_existing.append(issue.get("url") or f"#{issue_number}")


def reconcile_same_pr_open_issues(queue_repo: str, open_issues: list[dict[str, Any]], current: QueueItem, *, apply: bool, summary: Summary) -> None:
    for issue in open_issues:
        old = parse_queue_item(issue.get("body") or "")
        if not old:
            continue
        if old.repo == current.repo and old.pr_number == current.pr_number and old.head_sha != current.head_sha:
            supersede_issue(queue_repo, issue, current, apply=apply, summary=summary)


def reconcile_obsolete_open_issues(queue_repo: str, open_issues: list[dict[str, Any]], live_pr_refs: set[str], *, apply: bool, summary: Summary) -> None:
    for issue in open_issues:
        item = parse_queue_item(issue.get("body") or "")
        if not item or item.pr_ref in live_pr_refs:
            continue
        try:
            pr_state = fetch_pr_state(item.repo, item.pr_number)
            reviews = fetch_reviews(item.repo, item.pr_number)
            classification = classify_pr_for_queue(item, pr_state, reviews, reviewer=item.reviewer)
            if classification.should_review:
                continue
            close_existing_issue(queue_repo, issue, classification.status, classification.reason, apply=apply, summary=summary)
        except Exception as exc:
            summary.errors.append(f"reconcile obsolete {item.queue_key}: {exc}")


def process_pending_prs(args: argparse.Namespace) -> Summary:
    summary = Summary()
    if args.create_repo:
        repo_ready = ensure_queue_repo(args.queue_repo, apply=args.apply, summary=summary)
        if not repo_ready and not args.apply:
            if args.ensure_labels:
                ensure_labels(args.queue_repo, apply=False, summary=summary)
            return summary
    if args.ensure_labels:
        ensure_labels(args.queue_repo, apply=args.apply, summary=summary)

    pending_prs = discover_pending_prs(args)
    open_queue_issues = list_open_queue_issues(args.queue_repo)
    live_pr_refs: set[str] = set()

    for pending in pending_prs:
        try:
            repo, number = repo_number_from_pending_pr(pending)
            live_pr_refs.add(f"{repo}#{number}")
            pr_state = fetch_pr_state(repo, number)
            head_sha = str(pr_state.get("headRefOid") or "")
            if not head_sha:
                summary.errors.append(f"{repo}#{number}: missing headRefOid")
                continue
            item = QueueItem(
                queue_key=compute_queue_key(repo, number, head_sha),
                repo=repo,
                pr_number=number,
                pr_url=str(pr_state.get("url") or pending.get("url") or f"https://github.com/{repo}/pull/{number}"),
                head_sha=head_sha,
                reviewer=args.reviewer,
                source="pending-pr-review",
                created_by="hermes-pr-review-discovery",
                created_at=now_iso(),
            )
            reviews = fetch_reviews(repo, number)
            classification = classify_pr_for_queue(item, pr_state, reviews, reviewer=args.reviewer)
            if not classification.should_review:
                summary.skipped.append(f"{item.queue_key}: {classification.reason}")
                continue

            existing = list_issues_by_search(args.queue_repo, f'"queue_key: {item.queue_key}"', state="all")
            open_exact = [issue for issue in existing if str(issue.get("state") or "").upper() == "OPEN"]
            closed_done = [
                issue
                for issue in existing
                if str(issue.get("state") or "").upper() != "OPEN"
                and ("hermes:done" in label_names(issue) or "hermes:skipped" in label_names(issue))
            ]
            if open_exact:
                summary.already_queued.append(open_exact[0].get("url") or item.queue_key)
            elif closed_done:
                summary.closed_existing.append(closed_done[0].get("url") or item.queue_key)
            else:
                created_url = create_issue(args.queue_repo, item, apply=args.apply, summary=summary)
                summary.created.append(created_url or item.queue_key)

            reconcile_same_pr_open_issues(args.queue_repo, open_queue_issues, item, apply=args.apply, summary=summary)
        except Exception as exc:
            summary.errors.append(f"{pending.get('url') or pending}: {exc}")

    if args.reconcile_obsolete:
        reconcile_obsolete_open_issues(args.queue_repo, open_queue_issues, live_pr_refs, apply=args.apply, summary=summary)

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirror pending PR review requests into a GitHub Issues queue.")
    parser.add_argument("--queue-repo", default=DEFAULT_QUEUE_REPO, help="Queue repo, for example poom/hermes-pr-review-queue")
    parser.add_argument("--reviewer", default=DEFAULT_REVIEWER)
    parser.add_argument("--apply", action="store_true", help="Mutate GitHub Issues. Default is dry-run.")
    parser.add_argument("--create-repo", action="store_true", help="Create the private queue repo if it does not exist")
    parser.add_argument("--ensure-labels", action="store_true", help="Create required queue labels before reconciling")
    parser.add_argument("--pending-pr-json", help="Offline fixture for pending PR discovery JSON")
    parser.add_argument("--discovery-command", help="Override pending PR discovery command")
    parser.add_argument("--discovery-timeout", type=int, default=300)
    parser.add_argument("--no-reconcile-obsolete", dest="reconcile_obsolete", action="store_false", help="Do not close obsolete open queue issues")
    parser.set_defaults(reconcile_obsolete=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = process_pending_prs(args)
        print(summary.render())
        return 1 if summary.errors else 0
    except Exception as exc:
        print(f"pending-pr-review-discovery failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
