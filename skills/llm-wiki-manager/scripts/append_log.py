#!/usr/bin/env python3
"""
append_log.py — Append a log entry to wiki/log.md with the standard prefix.

The prefix `## [YYYY-MM-DD] action | title` is enforced so the log is
greppable: `grep "^## \\[" log.md | tail -20`.

Usage:
    python append_log.py --action ingest --title "Source title"
    python append_log.py --action ingest --title "Pollan 2008" --details "Created sources/pollan-2008.md, updated entities/pollan.md"
    python append_log.py --action query --title "What did Pollan think about supplements?"
    python append_log.py --action lint --title "Health check pass" --details "Fixed 2 broken links."
    python append_log.py --action bootstrap --title "Wiki initialized" --details "Topic: nutrition history"

Notes:
- --action is constrained to a known set so the log stays consistent.
- --details is optional; if provided it's written as a sub-paragraph after the heading.
- The log file is created if it doesn't exist.
- Date defaults to today (UTC); pass --date to override (useful for backfilling).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path


VALID_ACTIONS = {"ingest", "query", "lint", "bootstrap", "schema-evolve", "note", "update", "audit", "setup", "restructure"}


def find_log(root: Path) -> Path:
    """Find log.md — checks wiki/log.md first (standard layout), then root/log.md (flat layout)."""
    for candidate in [root / "wiki" / "log.md", root / "log.md"]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No log.md found at {root / 'wiki' / 'log.md'} or {root / 'log.md'}. "
        "Run init_wiki.py first to scaffold the wiki."
    )


def append_entry(log_path: Path, action: str, title: str, details: str, date: str) -> None:
    """Append a single entry to the log, preserving trailing newline."""
    existing = log_path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"

    entry_lines = [f"\n## [{date}] {action} | {title}"]
    if details:
        entry_lines.append(details.strip())
    entry = "\n".join(entry_lines) + "\n"

    log_path.write_text(existing + entry, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append an entry to wiki/log.md with the standard prefix.",
    )
    parser.add_argument(
        "--path", default=".",
        help="Wiki root directory (default: current directory).",
    )
    parser.add_argument(
        "--action", required=True, choices=sorted(VALID_ACTIONS),
        help="The kind of operation being logged.",
    )
    parser.add_argument(
        "--title", required=True,
        help="One-line title for the entry.",
    )
    parser.add_argument(
        "--details", default="",
        help="Optional multi-line details. Written under the heading.",
    )
    parser.add_argument(
        "--date", default=None,
        help="Date in YYYY-MM-DD format. Defaults to today (local).",
    )
    args = parser.parse_args()

    if "\n" in args.title:
        print("error: --title must be a single line", file=sys.stderr)
        return 2

    date = args.date or dt.date.today().isoformat()
    # Validate date format
    try:
        dt.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        print(f"error: --date must be YYYY-MM-DD, got {date!r}", file=sys.stderr)
        return 2

    root = Path(args.path).expanduser().resolve()

    try:
        log_path = find_log(root)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    append_entry(log_path, args.action, args.title, args.details, date)
    print(f"Logged: [{date}] {args.action} | {args.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
