#!/usr/bin/env python3
"""Run Claude Code interactive (no -p) inside rmux/tmux and capture output.

This is for scheduled pending-pr-review runs where Claude Code subscription
policy may disallow print mode (-p). The wrapper drives the TUI with rmux/tmux,
pastes a prompt from a file, asks the model to finish with a sentinel, captures
pane output to a file, and exits non-zero only on orchestration failure.
"""
from __future__ import annotations

import argparse
import atexit
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# Avoid leading/trailing underscores because Claude Code's TUI can render them as
# markdown emphasis and remove them from captured pane text.
DEFAULT_SENTINEL = "HERMESCLAUDEREVIEWDONE7F3C2A"
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def run(cmd: list[str], *, check: bool = False, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, timeout=timeout)


def clean_screen(text: str) -> str:
    text = ANSI_RE.sub("", text)
    text = text.replace("\r", "")
    # Strip trailing spaces while preserving the TUI line layout.
    return "\n".join(line.rstrip() for line in text.splitlines())


def shell_quote(s: str) -> str:
    # Avoid importing shlex solely for one call in older embedded environments.
    import shlex
    return shlex.quote(s)


def capture(mux: str, session: str) -> str:
    cp = run([mux, "capture-pane", "-t", session, "-p", "-S", "-5000"], timeout=10)
    return clean_screen((cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else ""))


def session_exists(mux: str, session: str) -> bool:
    return run([mux, "has-session", "-t", session], timeout=5).returncode == 0


def append_line(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")


def cleanup_session(mux: str, session: str) -> None:
    """Best-effort rmux/tmux cleanup; safe to call repeatedly."""
    if not session:
        return
    run([mux, "send-keys", "-t", session, "/exit", "Enter"], timeout=5)
    time.sleep(0.5)
    run([mux, "kill-session", "-t", session], timeout=5)


def looks_like_idle_startup_prompt(text: str) -> bool:
    """Detect Claude Code sitting at the initial prompt with no submitted review."""
    return (
        "Try \"create a util" in text
        and "gh auth login" in text
        and "⏺" not in text
        and DEFAULT_SENTINEL not in text
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="rmux/tmux session name")
    ap.add_argument("--workdir", required=True, help="working directory for Claude")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--output-file", required=True)
    ap.add_argument("--timeout-seconds", type=int, default=1800)
    ap.add_argument("--sentinel", default=DEFAULT_SENTINEL)
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", str(Path.home() / ".local/bin/claude")))
    ap.add_argument("--mux-bin", default=os.environ.get("RMUX_BIN") or shutil.which("rmux") or shutil.which("tmux") or "rmux")
    ap.add_argument("--startup-wait", type=float, default=6.0)
    ap.add_argument("--poll-interval", type=float, default=5.0)
    ap.add_argument(
        "--startup-idle-timeout",
        type=float,
        default=90.0,
        help="Abort if Claude remains at the startup prompt this long after paste/submit",
    )
    args = ap.parse_args()

    prompt_path = Path(args.prompt_file)
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workdir = Path(args.workdir)
    if not prompt_path.exists():
        output_path.write_text(f"__CLAUDE_WRAPPER_ERROR__: prompt file not found: {prompt_path}\n", encoding="utf-8")
        return 2
    if not workdir.exists():
        output_path.write_text(f"__CLAUDE_WRAPPER_ERROR__: workdir not found: {workdir}\n", encoding="utf-8")
        return 2

    raw_prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
    if args.sentinel not in raw_prompt:
        prompt = raw_prompt.rstrip() + f"\n\nEnd your final answer with this exact sentinel on its own line:\n{args.sentinel}\n"
    else:
        prompt = raw_prompt

    mux = args.mux_bin
    session = args.session
    buffer_name = f"{session}-prompt"
    claude_bin = args.claude_bin
    output_path.write_text("__CLAUDE_WRAPPER_START__\n", encoding="utf-8")

    # Clean up any stale session with the same deterministic name.
    run([mux, "kill-session", "-t", session], timeout=5)

    cleaned = False

    def cleanup_once(reason: str | None = None) -> None:
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        if reason:
            append_line(output_path, reason)
        cleanup_session(mux, session)

    def signal_handler(signum, _frame) -> None:
        cleanup_once(f"__CLAUDE_WRAPPER_SIGNAL:{signum}__")
        raise SystemExit(128 + signum)

    atexit.register(cleanup_once)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, signal_handler)
        except Exception:
            pass

    # Start interactive Claude Code without print mode. Empty tools keeps Reviewer B evidence-only/read-only.
    cmd = f"cd {shell_quote(str(workdir))} && {shell_quote(claude_bin)} --tools ''"
    cp = run([mux, "new-session", "-d", "-s", session, "-x", "140", "-y", "44", cmd], timeout=15)
    if cp.returncode != 0:
        output_path.write_text(f"__CLAUDE_WRAPPER_ERROR__: failed to start {mux}:\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}\n", encoding="utf-8")
        return 3

    try:
        time.sleep(args.startup_wait)
        # If first-run workspace-trust dialog appears, Enter accepts the default "Yes".
        # If Claude is already at the prompt, this is a harmless empty submit.
        run([mux, "send-keys", "-t", session, "Enter"], timeout=5)
        time.sleep(1.0)
        # Paste prompt via mux buffer; this avoids shell ARG_MAX/quoting issues for long PR evidence.
        setbuf = subprocess.run([mux, "set-buffer", "-b", buffer_name, prompt], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if setbuf.returncode != 0:
            output_path.write_text(f"__CLAUDE_WRAPPER_ERROR__: failed to set prompt buffer:\n{setbuf.stderr}\n", encoding="utf-8")
            return 4
        paste = run([mux, "paste-buffer", "-t", session, "-b", buffer_name], timeout=10)
        if paste.returncode != 0:
            output_path.write_text(f"__CLAUDE_WRAPPER_ERROR__: failed to paste prompt buffer:\n{paste.stderr}\n", encoding="utf-8")
            return 4
        enter = run([mux, "send-keys", "-t", session, "Enter"], timeout=5)
        if enter.returncode != 0:
            output_path.write_text(f"__CLAUDE_WRAPPER_ERROR__: failed to submit pasted prompt:\n{enter.stderr}\n", encoding="utf-8")
            return 4

        start = time.time()
        last = ""
        stable_count = 0
        saw_assistant = False
        while time.time() - start < args.timeout_seconds:
            time.sleep(args.poll_interval)
            text = capture(mux, session)
            if "⏺" in text or args.sentinel in text:
                saw_assistant = True
            elapsed = int(time.time() - start)
            output_path.write_text(text + f"\n\n__CLAUDE_WRAPPER_ELAPSED:{elapsed}__\n", encoding="utf-8")
            if (
                not saw_assistant
                and elapsed >= args.startup_idle_timeout
                and looks_like_idle_startup_prompt(text)
            ):
                output_path.write_text(
                    text
                    + "\n\n__CLAUDE_STARTUP_PROMPT_IDLE__\n"
                    + "__CLAUDE_EXIT:6__\n",
                    encoding="utf-8",
                )
                return 6
            if text.count(args.sentinel) >= 2:
                output_path.write_text(text + f"\n\n__CLAUDE_SENTINEL_FOUND:{args.sentinel}__\n__CLAUDE_EXIT:0__\n", encoding="utf-8")
                return 0
            # Fallback completion detector: assistant responded, the screen stopped changing, and the input prompt is back.
            if saw_assistant and text == last and "❯" in text:
                stable_count += 1
                if stable_count >= 3:
                    output_path.write_text(text + "\n\n__CLAUDE_IDLE_WITHOUT_SENTINEL__\n__CLAUDE_EXIT:0__\n", encoding="utf-8")
                    return 0
            else:
                stable_count = 0
                last = text
            if not session_exists(mux, session):
                output_path.write_text(text + "\n\n__CLAUDE_SESSION_EXITED__\n", encoding="utf-8")
                return 0 if saw_assistant else 5

        text = capture(mux, session)
        output_path.write_text(text + f"\n\n__CLAUDE_TIMEOUT:{args.timeout_seconds}__\n__CLAUDE_EXIT:124__\n", encoding="utf-8")
        return 124
    finally:
        # Ask nicely, then force-clean the session. Ignore failures.
        cleanup_once()


if __name__ == "__main__":
    sys.exit(main())
