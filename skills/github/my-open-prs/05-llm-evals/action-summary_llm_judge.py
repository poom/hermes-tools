#!/usr/bin/env python3
"""Judge replayed action summaries against golden blocker expectations."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Verdict:
    status: str
    reason: str


def judge_summary(summary: str, expected: dict) -> Verdict:
    lowered = summary.lower()
    missing = [term for term in expected.get("must_include", []) if term.lower() not in lowered]
    forbidden = [term for term in expected.get("must_not_include", []) if term.lower() in lowered]

    if missing:
        return Verdict("fail", "missing required term(s): " + ", ".join(missing))
    if forbidden:
        return Verdict("fail", "included forbidden term(s): " + ", ".join(forbidden))
    return Verdict("pass", "summary matches blocker rubric")


def load_json(path: Path):
    with path.open() as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", required=True, type=Path, help="Golden case JSON")
    parser.add_argument("--from", dest="actuals", type=Path, help="Optional replayed summaries keyed by case id")
    args = parser.parse_args()

    cases = load_json(args.golden)
    actuals = load_json(args.actuals) if args.actuals else {}
    failures: list[dict[str, str]] = []

    for case in cases:
        summary = actuals.get(case["id"], case["passing_summary"])
        verdict = judge_summary(summary, case["expected"])
        if verdict.status != "pass":
            failures.append({"id": case["id"], "reason": verdict.reason})

    print(json.dumps({"status": "pass" if not failures else "fail", "failures": failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
