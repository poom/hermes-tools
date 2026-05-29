#!/usr/bin/env python3
"""Deterministic helpers for the Hermes pending PR review issue queue.

The queue backend is GitHub Issues, but the safety-critical state is kept in
machine-readable comment/body blocks so it can be tested offline.
"""
from __future__ import annotations

import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

QUEUE_ITEM_MARKER = "hermes-pr-review-queue-item"
CLAIM_MARKER = "hermes-pr-review-claim"
HEARTBEAT_MARKER = "hermes-pr-review-heartbeat"
REQUEUE_MARKER = "hermes-pr-review-requeue"
RESULT_MARKER = "hermes-pr-review-result"
CHAT_REQUEST_MARKER = "hermes-pr-review-chat-request"

FORMAL_DECISION_STATES = {"APPROVED", "CHANGES_REQUESTED"}
DONE_RESULTS = {"approved", "changes-requested", "commented"}
SKIPPED_RESULTS = {"skipped", "stale", "superseded", "already-reviewed", "closed", "draft"}

REQUIRED_LABELS: dict[str, tuple[str, str]] = {
    "hermes:queued": ("ededed", "Hermes PR-review queue item waiting for a worker"),
    "hermes:claimed": ("c5def5", "Hermes PR-review queue item claimed by a worker"),
    "hermes:done": ("0e8a16", "Hermes PR-review queue item completed"),
    "hermes:failed": ("b60205", "Hermes PR-review queue item failed"),
    "hermes:skipped": ("fbca04", "Hermes PR-review queue item skipped safely"),
    "hermes:stale": ("d4c5f9", "Hermes PR-review queue item is stale or requeued"),
    "hermes:superseded": ("d4c5f9", "Hermes PR-review queue item superseded by a newer head"),
    "source:pending-pr-review": ("ededed", "Created by pending-pr-review discovery"),
    "source:chat-request": ("ededed", "Created from a chat-originated PR review request"),
    "origin:discord": ("ededed", "Originated from Discord"),
    "origin:telegram": ("ededed", "Originated from Telegram"),
    "origin:manual": ("ededed", "Originated from a manual request"),
    "priority:normal": ("ededed", "Normal priority queue item"),
    "priority:high": ("b60205", "High priority queue item"),
    "needs:poom-confirmation": ("fbca04", "Needs Poom confirmation before review"),
    "result:approved": ("0e8a16", "Worker approved the PR"),
    "result:changes-requested": ("b60205", "Worker requested changes on the PR"),
    "result:commented": ("1d76db", "Worker commented without approval/request-changes"),
    "result:skipped": ("fbca04", "Worker skipped without posting a formal review"),
}

PR_URL_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)", re.I)
PR_SHORTHAND_RE = re.compile(r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(?P<number>\d+)")


@dataclass(frozen=True)
class QueueItem:
    queue_key: str
    repo: str
    pr_number: int
    pr_url: str
    head_sha: str
    reviewer: str = "poom"
    source: str = "pending-pr-review"
    created_by: str = "hermes-pr-review-discovery"
    created_at: str = ""
    schema_version: int = 1

    @property
    def short_head(self) -> str:
        return self.head_sha[:7]

    @property
    def pr_ref(self) -> str:
        return f"{self.repo}#{self.pr_number}"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "QueueItem":
        required = ["queue_key", "repo", "pr_number", "pr_url", "head_sha"]
        missing = [key for key in required if data.get(key) in (None, "")]
        if missing:
            raise ValueError(f"missing queue item fields: {', '.join(missing)}")
        return cls(
            queue_key=str(data["queue_key"]),
            repo=str(data["repo"]),
            pr_number=int(data["pr_number"]),
            pr_url=str(data["pr_url"]),
            head_sha=str(data["head_sha"]),
            reviewer=str(data.get("reviewer") or "poom"),
            source=str(data.get("source") or "pending-pr-review"),
            created_by=str(data.get("created_by") or "hermes-pr-review-discovery"),
            created_at=str(data.get("created_at") or ""),
            schema_version=int(data.get("schema_version") or 1),
        )


@dataclass(frozen=True)
class LeaseRecord:
    kind: str
    worker: str
    lease_id: str
    queue_key: str
    expires_at: datetime
    comment_id: int
    event_at: datetime


@dataclass(frozen=True)
class QueueClassification:
    status: str
    reason: str
    review: dict[str, Any] | None = None

    @property
    def should_review(self) -> bool:
        return self.status == "pending"


def now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def now_iso() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def iso_after(minutes: int, *, start: datetime | None = None) -> str:
    base = start or now_utc()
    return (base + timedelta(minutes=minutes)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _quote_yaml(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text:
        return '""'
    if re.search(r"[:#\n\r\t]|^\s|\s$", text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def render_yaml(data: dict[str, Any], field_order: list[str]) -> str:
    lines: list[str] = []
    for key in field_order:
        if key not in data:
            continue
        lines.append(f"{key}: {_quote_yaml(data[key])}")
    for key in sorted(data):
        if key not in field_order:
            lines.append(f"{key}: {_quote_yaml(data[key])}")
    return "\n".join(lines) + "\n"


def parse_yaml_block(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
            value = value.replace('\\"', '"').replace("\\\\", "\\")
        if value.isdigit():
            data[key] = int(value)
        else:
            data[key] = value
    return data


def extract_marked_yaml(text: str, marker: str) -> dict[str, Any] | None:
    pattern = re.compile(
        rf"<!--\s*{re.escape(marker)}\s*-->\s*```(?:yaml|yml)?\s*\n(.*?)\n```",
        re.I | re.S,
    )
    match = pattern.search(text or "")
    if not match:
        return None
    return parse_yaml_block(match.group(1))


def compute_queue_key(repo: str, pr_number: int | str, head_sha: str) -> str:
    repo_text = str(repo).strip()
    if "/" not in repo_text:
        raise ValueError(f"repo must be OWNER/REPO, got {repo!r}")
    sha = str(head_sha).strip()
    if not sha:
        raise ValueError("head_sha is required")
    return f"{repo_text}#{int(pr_number)}@{sha}"


def parse_pr_identifier(value: str) -> tuple[str, int]:
    text = value.strip()
    url_match = PR_URL_RE.search(text)
    if url_match:
        owner, repo, number = url_match.groups()
        return f"{owner}/{repo}", int(number)
    short_match = PR_SHORTHAND_RE.search(text)
    if short_match:
        return short_match.group("repo"), int(short_match.group("number"))
    raise ValueError("PR identifier must be a GitHub PR URL or OWNER/REPO#NUMBER")


def repo_number_from_pending_pr(pr: dict[str, Any]) -> tuple[str, int]:
    repo = (
        pr.get("repo")
        or pr.get("repositoryNameWithOwner")
        or ((pr.get("repository") or {}).get("nameWithOwner"))
        or ((pr.get("repository") or {}).get("full_name"))
        or ((pr.get("repository") or {}).get("name_with_owner"))
    )
    number = pr.get("number") or pr.get("pr_number") or pr.get("pullRequestNumber")
    if (not repo or not number) and pr.get("url"):
        parsed_repo, parsed_number = parse_pr_identifier(str(pr["url"]))
        repo = repo or parsed_repo
        number = number or parsed_number
    if not repo or number is None:
        raise ValueError(f"cannot derive repo/PR number from pending PR payload: {pr}")
    return str(repo), int(number)


def render_queue_issue_body(item: QueueItem) -> str:
    block = render_yaml(
        {
            "schema_version": item.schema_version,
            "queue_key": item.queue_key,
            "repo": item.repo,
            "pr_number": item.pr_number,
            "pr_url": item.pr_url,
            "head_sha": item.head_sha,
            "reviewer": item.reviewer,
            "source": item.source,
            "created_by": item.created_by,
            "created_at": item.created_at or now_iso(),
        },
        [
            "schema_version",
            "queue_key",
            "repo",
            "pr_number",
            "pr_url",
            "head_sha",
            "reviewer",
            "source",
            "created_by",
            "created_at",
        ],
    )
    return f"""<!-- {QUEUE_ITEM_MARKER} -->
```yaml
{block}```

## Instructions for worker

Review this PR using `pr-review-guardrails` and the per-PR policy from
`pending-pr-review`.

Before posting any GitHub review, re-fetch the live PR head and verify that
{item.reviewer} has no current-head formal APPROVED or CHANGES_REQUESTED review.
"""


def render_chat_request_comment(
    *,
    requested_by: str,
    requested_at: str,
    source_platform: str,
    request_text: str,
    priority: str,
    source_message_url: str = "",
    delivery_target: str = "",
) -> str:
    block = render_yaml(
        {
            "schema_version": 1,
            "requested_by": requested_by,
            "requested_at": requested_at,
            "source_platform": source_platform,
            "source_message_url": source_message_url,
            "delivery_target": delivery_target,
            "request_text": request_text,
            "priority": priority,
        },
        [
            "schema_version",
            "requested_by",
            "requested_at",
            "source_platform",
            "source_message_url",
            "delivery_target",
            "request_text",
            "priority",
        ],
    )
    return f"<!-- {CHAT_REQUEST_MARKER} -->\n```yaml\n{block}```\n"


def parse_queue_item(body: str) -> QueueItem | None:
    data = extract_marked_yaml(body, QUEUE_ITEM_MARKER)
    if not data:
        return None
    try:
        return QueueItem.from_mapping(data)
    except (TypeError, ValueError):
        return None


def safe_worker_name(value: str | None = None) -> str:
    raw = value or socket.gethostname().split(".", 1)[0] or "worker"
    name = re.sub(r"[^a-z0-9._-]+", "-", raw.lower()).strip("-._")
    return name or "worker"


def render_claim_comment(item: QueueItem, *, worker: str, lease_id: str, claimed_at: str, expires_at: str) -> str:
    block = render_yaml(
        {
            "kind": "claim",
            "schema_version": 1,
            "worker": worker,
            "lease_id": lease_id,
            "claimed_at": claimed_at,
            "expires_at": expires_at,
            "queue_key": item.queue_key,
        },
        ["kind", "schema_version", "worker", "lease_id", "claimed_at", "expires_at", "queue_key"],
    )
    return f"<!-- {CLAIM_MARKER} -->\n```yaml\n{block}```\n"


def render_heartbeat_comment(*, queue_key: str, worker: str, lease_id: str, heartbeat_at: str, expires_at: str) -> str:
    block = render_yaml(
        {
            "kind": "heartbeat",
            "schema_version": 1,
            "worker": worker,
            "lease_id": lease_id,
            "heartbeat_at": heartbeat_at,
            "expires_at": expires_at,
            "queue_key": queue_key,
        },
        ["kind", "schema_version", "worker", "lease_id", "heartbeat_at", "expires_at", "queue_key"],
    )
    return f"<!-- {HEARTBEAT_MARKER} -->\n```yaml\n{block}```\n"


def render_requeue_comment(*, reason: str, previous_worker: str = "", previous_lease_id: str = "", requeued_at: str = "") -> str:
    block = render_yaml(
        {
            "kind": "requeue",
            "schema_version": 1,
            "reason": reason,
            "previous_worker": previous_worker,
            "previous_lease_id": previous_lease_id,
            "requeued_at": requeued_at or now_iso(),
        },
        ["kind", "schema_version", "reason", "previous_worker", "previous_lease_id", "requeued_at"],
    )
    return f"<!-- {REQUEUE_MARKER} -->\n```yaml\n{block}```\n"


def render_result_comment(
    *,
    worker: str,
    lease_id: str,
    queue_key: str,
    result: str,
    pr_review_id: str = "",
    review_state: str = "",
    commit_id: str = "",
    completed_at: str = "",
    summary: str = "",
) -> str:
    block = render_yaml(
        {
            "kind": "result",
            "schema_version": 1,
            "worker": worker,
            "lease_id": lease_id,
            "queue_key": queue_key,
            "result": result,
            "pr_review_id": pr_review_id,
            "review_state": review_state,
            "commit_id": commit_id,
            "completed_at": completed_at or now_iso(),
            "summary": summary,
        },
        [
            "kind",
            "schema_version",
            "worker",
            "lease_id",
            "queue_key",
            "result",
            "pr_review_id",
            "review_state",
            "commit_id",
            "completed_at",
            "summary",
        ],
    )
    return f"<!-- {RESULT_MARKER} -->\n```yaml\n{block}```\n"


def _comment_id(comment: dict[str, Any]) -> int:
    raw = comment.get("id") or comment.get("databaseId") or 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _comment_created_at(comment: dict[str, Any]) -> datetime:
    parsed = parse_time(comment.get("created_at") or comment.get("createdAt"))
    return parsed or datetime.fromtimestamp(0, UTC)


def _parse_lease_comment(comment: dict[str, Any], *, marker: str, event_field: str) -> LeaseRecord | None:
    data = extract_marked_yaml(comment.get("body") or "", marker)
    if not data:
        return None
    expires_at = parse_time(data.get("expires_at"))
    event_at = parse_time(data.get(event_field)) or _comment_created_at(comment)
    worker = str(data.get("worker") or "")
    lease_id = str(data.get("lease_id") or "")
    queue_key = str(data.get("queue_key") or "")
    if not expires_at or not worker or not lease_id or not queue_key:
        return None
    return LeaseRecord(
        kind=str(data.get("kind") or ""),
        worker=worker,
        lease_id=lease_id,
        queue_key=queue_key,
        expires_at=expires_at,
        comment_id=_comment_id(comment),
        event_at=event_at,
    )


def parse_claims(comments: list[dict[str, Any]]) -> list[LeaseRecord]:
    records: list[LeaseRecord] = []
    for comment in comments:
        record = _parse_lease_comment(comment, marker=CLAIM_MARKER, event_field="claimed_at")
        if record:
            records.append(record)
    return records


def parse_heartbeats(comments: list[dict[str, Any]]) -> list[LeaseRecord]:
    records: list[LeaseRecord] = []
    for comment in comments:
        record = _parse_lease_comment(comment, marker=HEARTBEAT_MARKER, event_field="heartbeat_at")
        if record:
            records.append(record)
    return records


def active_expiry_for_claim(claim: LeaseRecord, heartbeats: list[LeaseRecord]) -> datetime:
    matching = [
        heartbeat
        for heartbeat in heartbeats
        if heartbeat.queue_key == claim.queue_key
        and heartbeat.lease_id == claim.lease_id
        and heartbeat.worker == claim.worker
    ]
    if not matching:
        return claim.expires_at
    latest = sorted(matching, key=lambda record: (record.event_at, record.comment_id))[-1]
    return latest.expires_at


def choose_winning_claim(
    comments: list[dict[str, Any]],
    *,
    queue_key: str,
    now: datetime | None = None,
) -> LeaseRecord | None:
    cutoff = now or now_utc()
    claims = [claim for claim in parse_claims(comments) if claim.queue_key == queue_key]
    heartbeats = parse_heartbeats(comments)
    active: list[LeaseRecord] = []
    for claim in claims:
        if active_expiry_for_claim(claim, heartbeats) > cutoff:
            active.append(claim)
    if not active:
        return None
    return sorted(active, key=lambda record: (record.event_at, record.comment_id))[0]


def label_names(issue_or_labels: dict[str, Any] | list[Any]) -> set[str]:
    labels = issue_or_labels.get("labels", []) if isinstance(issue_or_labels, dict) else issue_or_labels
    names: set[str] = set()
    for label in labels or []:
        if isinstance(label, str):
            names.add(label)
        elif isinstance(label, dict) and label.get("name"):
            names.add(str(label["name"]))
    return names


def current_head_formal_review(
    reviews: list[dict[str, Any]],
    *,
    reviewer: str,
    head_sha: str,
) -> dict[str, Any] | None:
    for review in reversed(reviews or []):
        user = review.get("user") or review.get("author") or {}
        login = (user.get("login") or "").lower()
        state = str(review.get("state") or "").upper()
        commit_id = str(review.get("commit_id") or review.get("commitId") or "")
        if login == reviewer.lower() and commit_id == head_sha and state in FORMAL_DECISION_STATES:
            return review
    return None


def classify_pr_for_queue(
    item: QueueItem,
    pr_state: dict[str, Any],
    reviews: list[dict[str, Any]],
    *,
    reviewer: str | None = None,
) -> QueueClassification:
    reviewer_login = reviewer or item.reviewer
    state = str(pr_state.get("state") or "").upper()
    if pr_state.get("closed") or pr_state.get("merged") or state in {"CLOSED", "MERGED"}:
        return QueueClassification("closed", "PR is closed or merged")
    if pr_state.get("isDraft") or pr_state.get("is_draft"):
        return QueueClassification("draft", "PR is draft")
    live_head = str(pr_state.get("headRefOid") or pr_state.get("head_sha") or "")
    if live_head and live_head != item.head_sha:
        return QueueClassification("stale", f"PR head moved from {item.head_sha} to {live_head}")
    review = current_head_formal_review(reviews, reviewer=reviewer_login, head_sha=item.head_sha)
    if review:
        state = str(review.get("state") or "").upper()
        review_id = review.get("id") or review.get("databaseId") or ""
        return QueueClassification("already-reviewed", f"{reviewer_login} already has {state} review {review_id} on this head", review)
    return QueueClassification("pending", "PR still needs current-head review")


def result_labels(result: str) -> tuple[list[str], list[str], str]:
    normalized = result.strip().lower()
    remove = ["hermes:queued", "hermes:claimed"]
    if normalized == "approved":
        return remove, ["hermes:done", "result:approved"], "completed"
    if normalized in {"changes-requested", "changes_requested"}:
        return remove, ["hermes:done", "result:changes-requested"], "completed"
    if normalized == "commented":
        return remove, ["hermes:done", "result:commented"], "completed"
    if normalized in {"stale", "superseded"}:
        return remove, ["hermes:stale", "hermes:superseded", "result:skipped"], "not planned"
    if normalized == "already-reviewed":
        return remove, ["hermes:skipped", "result:skipped"], "not planned"
    if normalized in SKIPPED_RESULTS:
        return remove, ["hermes:skipped", "result:skipped"], "not planned"
    return remove, ["hermes:failed"], "not planned"
