#!/usr/bin/env python3
"""Report and persist the user's GitHub PR queue.

The script has two modes:

- default Markdown report: grouped open PR queue, compatible with the original skill
- --actions-json: update <home>/.hermes/my-open-prs/*.md and emit Discord post actions
  for new PR topics, changed blockers/statuses, stale/no-activity pings, and closed/merged PRs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_QUERY = "is:open is:pr author:@me archived:false org:ewa-services draft:false"
DEFAULT_PARENT_TARGET = "discord:1505939375983427796"
DEFAULT_PING_MENTION = os.environ.get("MY_OPEN_PRS_PING_MENTION", "Poom")
BUCKET_CATEGORY_NAMES = {
    "Waiting on Review": "pr-waiting-for-approval",
    "Needs My Feedback": "pr-need-actions",
    "Waiting on Checks / Merge": "pr-waiting-for-checks",
}
DEFAULT_STATUS_DIR = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "my-open-prs"
META_RE = re.compile(r"<!--\s*my-open-prs:(.*?)\s*-->", re.S)
STALE_AFTER = timedelta(hours=24)

PR_FIELDS = """
        number
        title
        url
        state
        merged
        closedAt
        mergedAt
        createdAt
        updatedAt
        reviewDecision
        mergeStateStatus
        repository {
          name
          nameWithOwner
          owner { login }
        }
        reviewRequests(first: 20) {
          nodes {
            requestedReviewer {
              __typename
              ... on User { login }
              ... on Team { name slug }
            }
          }
        }
        latestReviews(first: 20) {
          nodes {
            state
            body
            submittedAt
            author { login }
          }
        }
        statusCheckRollup {
          state
          contexts(first: 50) {
            nodes {
              __typename
              ... on CheckRun { name status conclusion detailsUrl }
              ... on StatusContext { context state targetUrl }
            }
          }
        }
"""

GRAPHQL_SEARCH_QUERY = f"""
query($searchQuery: String!) {{
  search(query: $searchQuery, type: ISSUE, first: 100) {{
    issueCount
    nodes {{
      ... on PullRequest {{
{PR_FIELDS}
      }}
    }}
  }}
}}
"""

GRAPHQL_PR_QUERY = f"""
query($owner: String!, $name: String!, $number: Int!) {{
  repository(owner: $owner, name: $name) {{
    pullRequest(number: $number) {{
{PR_FIELDS}
    }}
  }}
}}
"""


@dataclass(frozen=True)
class Entry:
    bucket: str
    repo: str
    repo_full: str
    number: int
    title: str
    url: str
    summary: str
    state: str = "OPEN"
    merged: bool = False
    updated_at: str = ""
    closed_at: str = ""
    merged_at: str = ""

    @property
    def link(self) -> str:
        title = self.title.replace("[", "\\[").replace("]", "\\]")
        return f"[{self.repo} #{self.number} {title}]({self.url})"

    @property
    def plain_ref(self) -> str:
        return f"{self.repo_full or self.repo} #{self.number}"

    @property
    def topic_title(self) -> str:
        title = re.sub(r"\s+", " ", self.title).strip()
        raw = f"{self.repo} #{self.number} {title}"
        return raw[:100]

    @property
    def channel_name(self) -> str:
        raw = f"{self.repo}-pr-{self.number}".lower()
        name = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")
        return (name or f"pr-{self.number}")[:90]

    @property
    def signature(self) -> str:
        # Only fields that should trigger a Discord update belong here.
        # GitHub's updatedAt changes for bot comments/check reruns even when the
        # human-visible PR status did not change; including it causes duplicate
        # "same status" alerts.
        payload = {
            "bucket": self.bucket,
            "repo_full": self.repo_full,
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "state": self.state,
            "merged": self.merged,
            "closed_at": self.closed_at,
            "merged_at": self.merged_at,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()[:16]


@dataclass
class StatusRecord:
    repo: str
    repo_full: str
    number: int
    title: str = ""
    url: str = ""
    bucket: str = ""
    summary: str = ""
    state: str = "OPEN"
    merged: bool = False
    channel_id: str = ""
    channel_message_id: str = ""
    channel_deleted_at: str = ""
    thread_id: str = ""
    thread_message_id: str = ""
    current_signature: str = ""
    last_posted_signature: str = ""
    first_seen_at: str = ""
    last_seen_at: str = ""
    last_change_at: str = ""
    last_posted_at: str = ""
    last_stale_ping_at: str = ""
    closed_reported: bool = False
    github_updated_at: str = ""
    closed_at: str = ""
    merged_at: str = ""

    @property
    def key(self) -> tuple[str, int]:
        return (self.repo_full or self.repo, int(self.number))


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def run_gh(query: str) -> dict[str, Any]:
    if shutil.which("gh") is None:
        raise SystemExit("gh CLI not found on PATH")

    cmd = ["gh", "api", "graphql", "-f", f"query={GRAPHQL_SEARCH_QUERY}", "-f", f"searchQuery={query}"]
    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"gh api graphql failed: {message}")
    return json.loads(result.stdout)


def run_gh_pr(repo_full: str, number: int) -> dict[str, Any] | None:
    if "/" not in repo_full:
        return None
    owner, name = repo_full.split("/", 1)
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={GRAPHQL_PR_QUERY}",
        "-f",
        f"owner={owner}",
        "-f",
        f"name={name}",
        "-F",
        f"number={int(number)}",
    ]
    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"gh api graphql failed for {repo_full} #{number}: {message}")
    payload = json.loads(result.stdout)
    return (((payload.get("data") or {}).get("repository") or {}).get("pullRequest"))


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        payload = json.load(fh)
    if isinstance(payload, list):
        return {"data": {"search": {"issueCount": len(payload), "nodes": payload}}}
    return payload


def check_name(node: dict[str, Any]) -> str:
    if node.get("__typename") == "CheckRun":
        return node.get("name") or "unnamed check"
    return node.get("context") or "unnamed status"


def check_state(node: dict[str, Any]) -> str:
    if node.get("__typename") == "CheckRun":
        return node.get("conclusion") or node.get("status") or "UNKNOWN"
    return node.get("state") or "UNKNOWN"


def collect_checks(pr: dict[str, Any]) -> tuple[list[str], list[str]]:
    contexts = (((pr.get("statusCheckRollup") or {}).get("contexts") or {}).get("nodes")) or []
    failing: list[str] = []
    pending: list[str] = []

    for node in contexts:
        state = check_state(node)
        name = check_name(node)
        if state in {"FAILURE", "ERROR", "ACTION_REQUIRED", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE"}:
            append_unique(failing, name)
        elif state in {"EXPECTED", "PENDING", "QUEUED", "REQUESTED", "WAITING", "IN_PROGRESS"}:
            append_unique(pending, name)

    return failing, pending


def append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def reviewer_names(pr: dict[str, Any]) -> list[str]:
    requests = ((pr.get("reviewRequests") or {}).get("nodes")) or []
    names: list[str] = []
    for request in requests:
        reviewer = request.get("requestedReviewer") or {}
        if reviewer.get("__typename") == "User" and reviewer.get("login"):
            names.append("@" + reviewer["login"])
        elif reviewer.get("__typename") == "Team":
            names.append("@" + (reviewer.get("slug") or reviewer.get("name") or "team"))
    return names


def latest_change_requests(pr: dict[str, Any]) -> list[str]:
    reviews = ((pr.get("latestReviews") or {}).get("nodes")) or []
    authors: list[str] = []
    for review in reviews:
        if review.get("state") == "CHANGES_REQUESTED":
            author = ((review.get("author") or {}).get("login")) or "reviewer"
            authors.append("@" + author)
    return sorted(set(authors))


def compact(items: list[str], limit: int = 3) -> str:
    if not items:
        return ""
    shown = items[:limit]
    suffix = "" if len(items) <= limit else f" (+{len(items) - limit} more)"
    return ", ".join(shown) + suffix


def repo_names(pr: dict[str, Any]) -> tuple[str, str]:
    repository = pr.get("repository") or {}
    repo_full = repository.get("nameWithOwner") or repository.get("name") or "repo"
    repo = repository.get("name") or repo_full.split("/")[-1]
    return repo, repo_full


def classify(pr: dict[str, Any]) -> Entry:
    repo, repo_full = repo_names(pr)
    failing_checks, pending_checks = collect_checks(pr)
    review_decision = pr.get("reviewDecision")
    merge_state = pr.get("mergeStateStatus")
    rollup_state = (pr.get("statusCheckRollup") or {}).get("state")
    reasons: list[str] = []

    if (pr.get("state") or "OPEN") != "OPEN":
        merged = bool(pr.get("merged"))
        status = "merged" if merged else "closed"
        when = pr.get("mergedAt") if merged else pr.get("closedAt")
        summary = f"PR was {status}" + (f" at {when}" if when else "")
        return make_entry("Closed / Merged", pr, repo, repo_full, summary)

    if rollup_state in {"FAILURE", "ERROR"} and not failing_checks:
        failing_checks = ["status checks"]
    elif rollup_state in {"EXPECTED", "PENDING"} and not pending_checks:
        pending_checks = ["status checks"]

    change_requesters = latest_change_requests(pr)
    if review_decision == "CHANGES_REQUESTED" or change_requesters:
        who = compact(change_requesters) or "reviewer"
        reasons.append(f"changes requested by {who}")
    if failing_checks:
        reasons.append(f"failing checks: {compact(failing_checks)}")
    if merge_state == "DIRTY":
        reasons.append("merge conflicts with the base branch")
    elif merge_state == "BEHIND":
        reasons.append("branch is behind the base branch")

    if reasons:
        return make_entry("Needs My Feedback", pr, repo, repo_full, "; ".join(reasons))

    reviewers = reviewer_names(pr)
    policy_pending = [name for name in pending_checks if "policy-bot" in name.lower()]
    if review_decision in {None, "REVIEW_REQUIRED"} or (merge_state == "BLOCKED" and reviewers):
        summary = "waiting for review"
        if reviewers:
            summary += f" from {compact(reviewers)}"
        elif policy_pending:
            summary += f" / policy approval: {compact(policy_pending)}"
        return make_entry("Waiting on Review", pr, repo, repo_full, summary)

    if merge_state == "BLOCKED" and policy_pending:
        return make_entry(
            "Waiting on Review",
            pr,
            repo,
            repo_full,
            f"waiting for required policy approval: {compact(policy_pending)}",
        )

    if pending_checks:
        return make_entry("Waiting on Checks / Merge", pr, repo, repo_full, f"pending checks: {compact(pending_checks)}")

    if merge_state in {"CLEAN", "HAS_HOOKS"} and review_decision == "APPROVED":
        return make_entry("Waiting on Checks / Merge", pr, repo, repo_full, "approved and appears mergeable; likely waiting on merge queue or manual merge")

    if merge_state == "UNKNOWN":
        return make_entry("Waiting on Checks / Merge", pr, repo, repo_full, "GitHub is still computing mergeability")

    if merge_state == "BLOCKED":
        return make_entry("Waiting on Checks / Merge", pr, repo, repo_full, "blocked by branch protection or merge requirements")

    return make_entry("Waiting on Checks / Merge", pr, repo, repo_full, f"review={review_decision or 'unknown'}, merge={merge_state or 'unknown'}")


def make_entry(bucket: str, pr: dict[str, Any], repo: str, repo_full: str, summary: str) -> Entry:
    return Entry(
        bucket=bucket,
        repo=repo,
        repo_full=repo_full,
        number=int(pr.get("number") or 0),
        title=pr.get("title") or "Untitled PR",
        url=pr.get("url") or "",
        summary=summary,
        state=pr.get("state") or "OPEN",
        merged=bool(pr.get("merged")),
        updated_at=pr.get("updatedAt") or "",
        closed_at=pr.get("closedAt") or "",
        merged_at=pr.get("mergedAt") or "",
    )


def extract_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return (((payload.get("data") or {}).get("search") or {}).get("nodes")) or []


def render_markdown(entries: list[Entry], include_empty: bool) -> str:
    buckets = ["Waiting on Review", "Waiting on Checks / Merge", "Needs My Feedback"]
    by_bucket = {bucket: [] for bucket in buckets}
    for entry in sorted(entries, key=lambda item: (item.repo.lower(), item.number)):
        if entry.state == "OPEN":
            by_bucket.setdefault(entry.bucket, []).append(entry)

    lines: list[str] = []
    for bucket in buckets:
        items = by_bucket.get(bucket, [])
        if not items and not include_empty:
            continue
        lines.append(f"## {bucket}")
        if items:
            for item in items:
                if bucket == "Waiting on Review":
                    lines.append(f"- {item.link}")
                else:
                    lines.append(f"- {item.link}: {item.summary}")
        else:
            lines.append("- None")
        lines.append("")

    return "\n".join(lines).rstrip() or "No matching open PRs found."


def slug_for(repo_full: str, number: int) -> str:
    repo = re.sub(r"[^A-Za-z0-9_.-]+", "-", repo_full.strip("/").replace("/", "-"))
    return f"{repo}-pr-{int(number)}.md"


def status_path(status_dir: Path, repo_full: str, number: int) -> Path:
    return status_dir / slug_for(repo_full, number)


def load_record(path: Path) -> StatusRecord | None:
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    match = META_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return StatusRecord(**{k: v for k, v in data.items() if k in StatusRecord.__dataclass_fields__})


def load_records(status_dir: Path) -> dict[tuple[str, int], StatusRecord]:
    records: dict[tuple[str, int], StatusRecord] = {}
    if not status_dir.exists():
        return records
    for path in status_dir.glob("*-pr-*.md"):
        record = load_record(path)
        if record:
            records[record.key] = record
    return records


def record_from_entry(entry: Entry, previous: StatusRecord | None, observed_at: str) -> StatusRecord:
    material_changed = True
    last_posted_signature = previous.last_posted_signature if previous else ""
    if previous:
        material_changed = any(
            [
                previous.repo != entry.repo,
                previous.repo_full != entry.repo_full,
                int(previous.number) != int(entry.number),
                previous.title != entry.title,
                previous.url != entry.url,
                previous.bucket != entry.bucket,
                previous.summary != entry.summary,
                previous.state != entry.state,
                bool(previous.merged) != bool(entry.merged),
                previous.closed_at != entry.closed_at,
                previous.merged_at != entry.merged_at,
            ]
        )
        # Migration/noise guard: if the previously observed material state was
        # already posted and only github_updated_at/signature algorithm changed,
        # treat the new signature as posted so the monitor stays silent.
        if not material_changed and previous.last_posted_signature == previous.current_signature:
            last_posted_signature = entry.signature

    rec = StatusRecord(
        repo=entry.repo,
        repo_full=entry.repo_full,
        number=entry.number,
        title=entry.title,
        url=entry.url,
        bucket=entry.bucket,
        summary=entry.summary,
        state=entry.state,
        merged=entry.merged,
        channel_id=previous.channel_id if previous else "",
        channel_message_id=previous.channel_message_id if previous else "",
        channel_deleted_at=previous.channel_deleted_at if previous else "",
        thread_id=previous.thread_id if previous else "",
        thread_message_id=previous.thread_message_id if previous else "",
        current_signature=entry.signature,
        last_posted_signature=last_posted_signature,
        first_seen_at=previous.first_seen_at if previous else observed_at,
        last_seen_at=observed_at,
        last_change_at=(observed_at if (not previous or material_changed) else previous.last_change_at),
        last_posted_at=previous.last_posted_at if previous else "",
        last_stale_ping_at=previous.last_stale_ping_at if previous else "",
        closed_reported=previous.closed_reported if previous else False,
        github_updated_at=entry.updated_at,
        closed_at=entry.closed_at,
        merged_at=entry.merged_at,
    )
    if rec.state == "OPEN":
        rec.closed_reported = False
    return rec


def write_record(status_dir: Path, rec: StatusRecord) -> Path:
    status_dir.mkdir(parents=True, exist_ok=True)
    path = status_path(status_dir, rec.repo_full or rec.repo, rec.number)
    meta = json.dumps(asdict(rec), sort_keys=True, separators=(",", ":"))
    state_line = "merged" if rec.merged else rec.state.lower()
    body = [
        f"<!-- my-open-prs:{meta} -->",
        f"# {rec.repo_full or rec.repo} PR #{rec.number}",
        "",
        f"- Title: {rec.title}",
        f"- URL: {rec.url}",
        f"- State: {state_line}",
        f"- Bucket: {rec.bucket or 'n/a'}",
        f"- Blocker/status: {rec.summary or 'n/a'}",
        f"- Discord channel: {rec.channel_id or 'not created yet'}",
        f"- Discord channel deleted at: {rec.channel_deleted_at or 'n/a'}",
        f"- Legacy Discord thread: {rec.thread_id or 'n/a'}",
        f"- GitHub updated at: {rec.github_updated_at or 'unknown'}",
        f"- Last observed at: {rec.last_seen_at or 'unknown'}",
        f"- Last posted at: {rec.last_posted_at or 'never'}",
        "",
    ]
    path.write_text("\n".join(body))
    return path


def entry_message(entry: Entry, *, stale: bool = False, ping_mention: str = DEFAULT_PING_MENTION) -> str:
    lines = [entry.topic_title, "", f"{entry.link}", f"Status: {entry.bucket}", f"Blocker: {entry.summary}"]
    if entry.updated_at:
        lines.append(f"GitHub activity: {entry.updated_at}")
    if stale:
        lines.append("")
        lines.append(f"{ping_mention} no GitHub activity for more than 24 hours.")
    return "\n".join(lines)


def record_message(rec: StatusRecord, *, stale: bool = False, ping_mention: str = DEFAULT_PING_MENTION) -> str:
    entry = Entry(rec.bucket, rec.repo, rec.repo_full, rec.number, rec.title, rec.url, rec.summary, rec.state, rec.merged, rec.github_updated_at, rec.closed_at, rec.merged_at)
    return entry_message(entry, stale=stale, ping_mention=ping_mention)


def discord_channel_target(channel_id: str) -> str:
    return f"discord:{channel_id}"


def bucket_category_name(bucket: str) -> str:
    return BUCKET_CATEGORY_NAMES.get(bucket, "pr-waiting-for-checks")


def closed_message(rec: StatusRecord) -> str:
    status = "merged" if rec.merged else "closed"
    when = rec.merged_at if rec.merged else rec.closed_at
    suffix = f" at {when}" if when else ""
    link = f"[{rec.repo} #{rec.number} {rec.title}]({rec.url})"
    return f"{rec.repo} #{rec.number} {rec.title}\n\n{link}\nStatus: PR was {status}{suffix}."


def should_stale_ping(rec: StatusRecord, observed_at: str) -> bool:
    updated = parse_time(rec.github_updated_at) or parse_time(rec.last_change_at) or parse_time(rec.first_seen_at)
    now = parse_time(observed_at) or datetime.now(UTC)
    if not updated or now - updated < STALE_AFTER:
        return False
    last_ping = parse_time(rec.last_stale_ping_at)
    return not last_ping or now - last_ping >= STALE_AFTER


def update_status_and_actions(
    entries: list[Entry],
    status_dir: Path,
    *,
    parent_target: str = DEFAULT_PARENT_TARGET,
    ping_mention: str = DEFAULT_PING_MENTION,
    fetch_closed: bool = True,
    observed_at: str | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or now_iso()
    records = load_records(status_dir)
    current_keys: set[tuple[str, int]] = set()
    actions: list[dict[str, Any]] = []
    written: list[str] = []

    for entry in entries:
        if entry.state != "OPEN":
            continue
        key = (entry.repo_full or entry.repo, entry.number)
        current_keys.add(key)
        previous = records.get(key)
        rec = record_from_entry(entry, previous, observed_at)
        write_record(status_dir, rec)
        written.append(str(status_path(status_dir, rec.repo_full or rec.repo, rec.number)))

        entry_for_names = Entry(rec.bucket, rec.repo, rec.repo_full, rec.number, rec.title, rec.url, rec.summary)
        category_name = bucket_category_name(rec.bucket)

        if not rec.channel_id:
            actions.append({
                "type": "create_channel",
                "target": parent_target,
                "repo": rec.repo_full or rec.repo,
                "number": rec.number,
                "signature": rec.current_signature,
                "channel_name": entry_for_names.channel_name,
                "category_name": category_name,
                "topic_title": entry_for_names.topic_title,
                "message": record_message(rec, ping_mention=ping_mention),
            })
        elif rec.current_signature != rec.last_posted_signature:
            actions.append({
                "type": "post_update",
                "target": discord_channel_target(rec.channel_id),
                "repo": rec.repo_full or rec.repo,
                "number": rec.number,
                "signature": rec.current_signature,
                "channel_id": rec.channel_id,
                "category_name": category_name,
                "message": record_message(rec, ping_mention=ping_mention),
            })
        elif should_stale_ping(rec, observed_at):
            actions.append({
                "type": "ping_stale",
                "target": discord_channel_target(rec.channel_id),
                "repo": rec.repo_full or rec.repo,
                "number": rec.number,
                "signature": rec.current_signature,
                "channel_id": rec.channel_id,
                "category_name": category_name,
                "message": record_message(rec, stale=True, ping_mention=ping_mention),
            })

    if fetch_closed:
        for key, previous in sorted(records.items()):
            if key in current_keys or previous.state != "OPEN" or previous.closed_reported:
                continue
            pr = run_gh_pr(previous.repo_full or previous.repo, previous.number)
            if not pr:
                continue
            entry = classify(pr)
            if entry.state == "OPEN":
                continue
            rec = record_from_entry(entry, previous, observed_at)
            write_record(status_dir, rec)
            written.append(str(status_path(status_dir, rec.repo_full or rec.repo, rec.number)))
            actions.append({
                "type": "post_closed",
                "target": parent_target,
                "repo": rec.repo_full or rec.repo,
                "number": rec.number,
                "signature": rec.current_signature,
                "channel_id": rec.channel_id,
                "message": closed_message(rec),
            })

    return {"observed_at": observed_at, "actions": actions, "status_dir": str(status_dir), "written": written}


def update_record_posted(
    status_dir: Path,
    repo: str,
    number: int,
    *,
    signature: str = "",
    channel_id: str = "",
    thread_id: str = "",
    message_id: str = "",
    kind: str = "update",
    posted_at: str | None = None,
) -> StatusRecord:
    posted_at = posted_at or now_iso()
    path = status_path(status_dir, repo, number)
    rec = load_record(path)
    if rec is None:
        # Try matching by repo suffix/full name in existing records.
        for candidate in load_records(status_dir).values():
            if candidate.number == int(number) and (candidate.repo == repo or candidate.repo_full == repo):
                rec = candidate
                path = status_path(status_dir, candidate.repo_full or candidate.repo, number)
                break
    if rec is None:
        raise SystemExit(f"status record not found for {repo} #{number}")

    if channel_id:
        rec.channel_id = str(channel_id)
        rec.channel_deleted_at = ""
    if thread_id:
        rec.thread_id = str(thread_id)
    if message_id:
        if channel_id or rec.channel_id:
            rec.channel_message_id = str(message_id)
        else:
            rec.thread_message_id = str(message_id)
    if signature:
        rec.last_posted_signature = signature
    if kind == "stale":
        rec.last_stale_ping_at = posted_at
    elif kind == "closed":
        rec.closed_reported = True
        if rec.channel_id:
            rec.channel_deleted_at = posted_at
    rec.last_posted_at = posted_at
    write_record(status_dir, rec)
    return rec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default=DEFAULT_QUERY, help="GitHub PR search query")
    parser.add_argument("--from-json", type=Path, help="Read a saved GraphQL payload instead of calling gh")
    parser.add_argument("--json", action="store_true", help="Emit classified entries as JSON")
    parser.add_argument("--include-empty", action="store_true", help="Print empty buckets")
    parser.add_argument("--actions-json", action="store_true", help="Persist status files and emit Discord post actions as JSON")
    parser.add_argument("--status-dir", type=Path, default=DEFAULT_STATUS_DIR, help="Directory for per-PR Markdown status files")
    parser.add_argument("--parent-target", default=DEFAULT_PARENT_TARGET, help="Discord target for summary/forum channel")
    parser.add_argument("--ping-mention", default=DEFAULT_PING_MENTION, help="Mention/name to use for stale pings")
    parser.add_argument("--no-fetch-closed", action="store_true", help="Do not query previously tracked PRs that disappeared from the open search")
    parser.add_argument("--mark-posted", action="store_true", help="Mark a previously emitted action as posted")
    parser.add_argument("--repo", help="Repo full name for --mark-posted, e.g. owner/repo")
    parser.add_argument("--number", type=int, help="PR number for --mark-posted")
    parser.add_argument("--signature", default="", help="Signature from the emitted action")
    parser.add_argument("--channel-id", default="", help="Discord text channel ID created for a PR")
    parser.add_argument("--thread-id", default="", help="Legacy Discord thread ID created for a PR topic")
    parser.add_argument("--message-id", default="", help="Discord message ID returned by send_message")
    parser.add_argument("--kind", choices=["update", "stale", "closed"], default="update", help="Posted action kind")
    args = parser.parse_args()

    if args.mark_posted:
        if not args.repo or not args.number:
            raise SystemExit("--mark-posted requires --repo and --number")
        rec = update_record_posted(
            args.status_dir,
            args.repo,
            args.number,
            signature=args.signature,
            channel_id=args.channel_id,
            thread_id=args.thread_id,
            message_id=args.message_id,
            kind=args.kind,
        )
        print(json.dumps(asdict(rec), indent=2, sort_keys=True))
        return 0

    payload = load_fixture(args.from_json) if args.from_json else run_gh(args.query)
    entries = [classify(pr) for pr in extract_nodes(payload)]

    if args.actions_json:
        result = update_status_and_actions(
            entries,
            args.status_dir,
            parent_target=args.parent_target,
            ping_mention=args.ping_mention,
            fetch_closed=not args.no_fetch_closed and not args.from_json,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps([asdict(entry) for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_markdown(entries, args.include_empty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
