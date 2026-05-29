#!/usr/bin/env python3
"""Backward-compatible entrypoint for the generic GitHub PR monitor.

Configure with --pr-url or GITHUB_PR_MONITOR_URL. Prefer using
monitor_github_pr.py for new cron jobs.
"""
from __future__ import annotations

from monitor_github_pr import main

if __name__ == "__main__":
    raise SystemExit(main())
