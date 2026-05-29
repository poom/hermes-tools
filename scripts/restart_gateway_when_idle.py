#!/usr/bin/env python3
"""Restart Hermes gateway once it appears idle.

Created by Hermes on request. It gives the current response a short grace
period, then waits for gateway_state.json active_agents == 0 for two
consecutive checks before restarting the launchd service.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from hermes_tools_common import hermes_home

HOME = hermes_home()
STATE = HOME / "gateway_state.json"
LOG = HOME / "logs" / "restart_when_idle.log"
LABEL = os.getenv("HERMES_GATEWAY_LAUNCHD_LABEL", "ai.hermes.gateway")
INITIAL_GRACE_SECONDS = 12
CHECK_INTERVAL_SECONDS = 2
REQUIRED_IDLE_CHECKS = 2
MAX_WAIT_SECONDS = 30 * 60


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def active_agents() -> int:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return int(data.get("active_agents") or 0)
    except Exception as exc:
        log(f"could not read {STATE}: {exc!r}; treating as busy")
        return 1


def main() -> int:
    log("restart-when-idle watcher started")
    time.sleep(INITIAL_GRACE_SECONDS)

    deadline = time.time() + MAX_WAIT_SECONDS
    idle_checks = 0
    while time.time() < deadline:
        count = active_agents()
        log(f"active_agents={count}")
        if count == 0:
            idle_checks += 1
            if idle_checks >= REQUIRED_IDLE_CHECKS:
                uid = os.getuid()
                cmd = ["launchctl", "kickstart", "-k", f"gui/{uid}/{LABEL}"]
                log("restarting gateway: " + " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                log(f"restart exit={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}")
                return result.returncode
        else:
            idle_checks = 0
        time.sleep(CHECK_INTERVAL_SECONDS)

    log("timed out waiting for gateway to become idle; not restarting")
    return 1


if __name__ == "__main__":
    sys.exit(main())
