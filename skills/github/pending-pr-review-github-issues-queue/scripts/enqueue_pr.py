#!/usr/bin/env python3
"""Create or update one manual/chat-originated PR review queue issue.

Default mode is dry-run. Pass --apply to create/update GitHub Issues.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from queue_common import (
    QueueItem,
    classify_pr_for_queue,
    compute_queue_key,
    label_names,
    now_iso,
    parse_pr_identifier,
    parse_queue_item,
    render_chat_request_comment,
    render_queue_issue_body,
    REQUIRED_LABELS,
)

DEFAULT_QUEUE_REPO = os.environ.get("HERMES_PR_REVIEW_QUEUE_REPO", "poom/hermes-pr-review-queue")
DEFAULT_REVIEWER = os.environ.get("HERMES_PR_REVIEW_REVIEWER", "poom")


@dataclass(frozen=True)
class EnqueueResult:
    action: str
    queue_key: str
    pr_url: str
    issue_url: str = ""
    reason: str = ""
    notes: tuple[str, ...] = ()

    def render(self) -> str:
        lines = [
            "pending-pr-review-enqueue",
            f"- action: {self.action}",
            f"- pr: {self.pr_url}",
            f"- queue_key: {self.queue_key}",
        ]
        if self.issue_url:
            lines.append(f"- issue: {self.issue_url}")
        if self.reason:
            lines.append(f"- reason: {self.reason}")
        for note in self.notes:
            lines.append(f"- {note}")
        return "\n".join(lines)


def run(cmd: list[str], *, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
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


def ensure_labels(queue_repo: str, *, apply: bool) -> list[str]:
    actions: list[str] = []
    if not apply:
        return [f"would ensure {len(REQUIRED_LABELS)} queue labels in {queue_repo}"]
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
            actions.append(f"label {name} failed: {result.stderr.strip() or result.stdout.strip()}")
    return actions


def list_issues_by_queue_key(queue_repo: str, queue_key: str) -> list[dict[str, Any]]:
    payload = gh_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            queue_repo,
            "--state",
            "all",
            "--search",
            f'"queue_key: {queue_key}"',
            "--limit",
            "50",
            "--json",
            "number,state,title,labels,url,body,createdAt",
        ],
        timeout=120,
    )
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def list_open_issues_by_pr_ref(queue_repo: str, repo: str, number: int) -> list[dict[str, Any]]:
    payload = gh_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            queue_repo,
            "--state",
            "open",
            "--search",
            f'"{repo}#{number}"',
            "--limit",
            "50",
            "--json",
            "number,state,title,labels,url,body,createdAt",
        ],
        timeout=120,
    )
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def issue_comment(queue_repo: str, issue_number: int, body: str) -> None:
    run(["gh", "issue", "comment", str(issue_number), "--repo", queue_repo, "--body", body], timeout=90)


def issue_edit_labels(queue_repo: str, issue_number: int, *, add: list[str] | None = None, remove: list[str] | None = None) -> None:
    if add:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--add-label", ",".join(add)], timeout=90, check=False)
    if remove:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--remove-label", ",".join(remove)], timeout=90, check=False)


def issue_close(queue_repo: str, issue_number: int, reason: str) -> None:
    run(["gh", "issue", "close", str(issue_number), "--repo", queue_repo, "--reason", reason], timeout=90, check=False)


def issue_add_labels(queue_repo: str, issue_number: int, labels: list[str]) -> None:
    if labels:
        run(["gh", "issue", "edit", str(issue_number), "--repo", queue_repo, "--add-label", ",".join(labels)], timeout=90, check=False)


def create_issue(queue_repo: str, item: QueueItem, body: str, labels: list[str], *, title_prefix: str = "Review PR") -> str:
    title = f"{title_prefix}: {item.repo}#{item.pr_number} @ {item.short_head}"
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
                ",".join(labels),
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


def repo_needs_confirmation(repo: str, allowed_owners: list[str]) -> bool:
    if not allowed_owners:
        return False
    owner = repo.split("/", 1)[0].lower()
    return owner not in {allowed.lower() for allowed in allowed_owners}


def queue_labels(*, origin: str, priority: str, needs_confirmation: bool) -> list[str]:
    labels = ["source:chat-request", f"origin:{origin}", f"priority:{priority}"]
    if needs_confirmation:
        labels.append("needs:poom-confirmation")
    else:
        labels.insert(0, "hermes:queued")
    return labels


def build_queue_item(repo: str, number: int, pr_state: dict[str, Any], reviewer: str) -> QueueItem:
    head_sha = str(pr_state.get("headRefOid") or "")
    if not head_sha:
        raise ValueError(f"{repo}#{number}: missing headRefOid")
    return QueueItem(
        queue_key=compute_queue_key(repo, number, head_sha),
        repo=repo,
        pr_number=number,
        pr_url=str(pr_state.get("url") or f"https://github.com/{repo}/pull/{number}"),
        head_sha=head_sha,
        reviewer=reviewer,
        source="chat-request",
        created_by="hermes-pr-review-chat-task-creator",
        created_at=now_iso(),
    )


def supersede_old_open_issues(args: argparse.Namespace, current: QueueItem) -> tuple[str, ...]:
    notes: list[str] = []
    for issue in list_open_issues_by_pr_ref(args.queue_repo, current.repo, current.pr_number):
        old = parse_queue_item(issue.get("body") or "")
        if not old:
            continue
        if old.repo != current.repo or old.pr_number != current.pr_number or old.head_sha == current.head_sha:
            continue
        issue_number = int(issue["number"])
        issue_ref = str(issue.get("url") or f"#{issue_number}")
        note = f"superseded_old_issue: {issue_ref} ({old.short_head} -> {current.short_head})"
        if args.apply:
            issue_comment(
                args.queue_repo,
                issue_number,
                (
                    f"Superseded by current PR head `{current.head_sha}`.\n\n"
                    f"Old queue key: `{old.queue_key}`\n"
                    f"Current queue key: `{current.queue_key}`"
                ),
            )
            issue_edit_labels(
                args.queue_repo,
                issue_number,
                add=["hermes:superseded"],
                remove=["hermes:queued", "hermes:claimed"],
            )
            issue_close(args.queue_repo, issue_number, "not planned")
        else:
            note = f"would_supersede_old_issue: {issue_ref} ({old.short_head} -> {current.short_head})"
        notes.append(note)
    return tuple(notes)


def request_block(args: argparse.Namespace, pr_url: str) -> str:
    return render_chat_request_comment(
        requested_by=args.requested_by,
        requested_at=now_iso(),
        source_platform=args.origin,
        source_message_url=args.source_message_url,
        delivery_target=args.delivery_target,
        request_text=args.request_text or pr_url,
        priority=args.priority,
    )


def enqueue(args: argparse.Namespace) -> EnqueueResult:
    repo, number = parse_pr_identifier(args.pr)
    if args.ensure_labels:
        label_actions = ensure_labels(args.queue_repo, apply=args.apply)
        for action in label_actions:
            print(action)

    pr_state = fetch_pr_state(repo, number)
    item = build_queue_item(repo, number, pr_state, args.reviewer)
    reviews = fetch_reviews(repo, number)
    classification = classify_pr_for_queue(item, pr_state, reviews, reviewer=args.reviewer)
    if classification.status == "draft" and args.allow_draft:
        classification = type(classification)("pending", "Draft PR accepted by --allow-draft")
    if not classification.should_review:
        return EnqueueResult(
            action="skipped",
            queue_key=item.queue_key,
            pr_url=item.pr_url,
            reason=classification.reason,
        )

    needs_confirmation = repo_needs_confirmation(repo, args.allowed_owner or [])
    labels = queue_labels(origin=args.origin, priority=args.priority, needs_confirmation=needs_confirmation)
    chat_block = request_block(args, item.pr_url)
    existing = list_issues_by_queue_key(args.queue_repo, item.queue_key)
    open_existing = [issue for issue in existing if str(issue.get("state") or "").upper() == "OPEN"]
    closed_done = [
        issue
        for issue in existing
        if str(issue.get("state") or "").upper() != "OPEN"
        and ("hermes:done" in label_names(issue) or "hermes:skipped" in label_names(issue))
    ]

    if open_existing:
        issue = open_existing[0]
        notes = supersede_old_open_issues(args, item)
        if args.apply:
            issue_comment(args.queue_repo, int(issue["number"]), chat_block)
            issue_add_labels(args.queue_repo, int(issue["number"]), labels)
        return EnqueueResult(
            action="updated-existing" if args.apply else "would-update-existing",
            queue_key=item.queue_key,
            pr_url=item.pr_url,
            issue_url=str(issue.get("url") or ""),
            reason="same current-head queue issue already exists",
            notes=notes,
        )

    if closed_done and not args.force_rereview:
        issue = closed_done[0]
        return EnqueueResult(
            action="skipped",
            queue_key=item.queue_key,
            pr_url=item.pr_url,
            issue_url=str(issue.get("url") or ""),
            reason="same current-head queue issue is already closed as done/skipped; pass --force-rereview to override",
        )

    body = render_queue_issue_body(item) + "\n" + chat_block
    if not args.apply:
        notes = supersede_old_open_issues(args, item)
        return EnqueueResult(
            action="would-create-confirmation" if needs_confirmation else "would-create",
            queue_key=item.queue_key,
            pr_url=item.pr_url,
            reason="outside allowed owner scope" if needs_confirmation else "",
            notes=notes,
        )

    issue_url = create_issue(
        args.queue_repo,
        item,
        body,
        labels,
        title_prefix="Needs confirmation" if needs_confirmation else "Review PR",
    )
    notes = supersede_old_open_issues(args, item)
    return EnqueueResult(
        action="created-confirmation" if needs_confirmation else "created",
        queue_key=item.queue_key,
        pr_url=item.pr_url,
        issue_url=issue_url,
        reason="outside allowed owner scope" if needs_confirmation else "",
        notes=notes,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Queue one PR URL into the Hermes PR review GitHub Issues board.")
    parser.add_argument("pr", help="GitHub PR URL or OWNER/REPO#NUMBER")
    parser.add_argument("--queue-repo", default=DEFAULT_QUEUE_REPO)
    parser.add_argument("--reviewer", default=DEFAULT_REVIEWER)
    parser.add_argument("--apply", action="store_true", help="Create/update GitHub Issues. Default is dry-run.")
    parser.add_argument("--ensure-labels", action="store_true")
    parser.add_argument("--origin", default="manual", choices=["manual", "discord", "telegram"])
    parser.add_argument("--priority", default="normal", choices=["normal", "high"])
    parser.add_argument("--requested-by", default=os.environ.get("HERMES_PR_REVIEW_REQUESTED_BY", "manual"))
    parser.add_argument("--request-text", default="")
    parser.add_argument("--source-message-url", default="")
    parser.add_argument("--delivery-target", default="")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--allowed-owner", action="append", default=[])
    parser.add_argument("--force-rereview", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = enqueue(args)
        print(result.render())
        return 0
    except Exception as exc:
        print(f"pending-pr-review enqueue failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
