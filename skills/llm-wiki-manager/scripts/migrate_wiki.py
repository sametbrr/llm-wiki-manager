#!/usr/bin/env python3
"""
migrate_wiki.py — Upgrade an existing wiki to the current structural conventions.

When a skill release changes the wiki's structural conventions (hot.md shape,
one-entry-per-page index, hub rule, tag policy...), this script moves an
existing wiki to the new schema. It performs only the MECHANICAL steps; the
semantic steps (tag consolidation, theme-grouped index rewrite, hub election,
Related footers) are LLM work described in references/migrate-workflow.md and
are listed in the dry-run output as manual steps.

The wiki's schema file (AGENTS.md or CLAUDE.md) carries a `schema_version` stamp. An
unstamped wiki counts as v1. This script knows how to migrate v1 -> v2 (and
future versions get their own registry entries).

Usage:
    python migrate_wiki.py --path <wiki-root>           # dry-run (default): show what would change
    python migrate_wiki.py --path <wiki-root> --apply   # apply (commit your wiki to git first!)

Safety:
- Never touches raw/.
- Dry-run by default; --apply is explicit.
- Idempotent: re-running at the current version is a no-op.
- Every applied run appends a `restructure` entry to log.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema_file import ensure_claude_pointer, resolve_schema_file  # noqa: E402

# Set from --schema-file in main(); None = auto-detect AGENTS.md / CLAUDE.md.
SCHEMA_OVERRIDE: str | None = None


# The schema version the bundled templates/conventions correspond to.
# Bump this ONLY when a release changes structural conventions, and add a
# matching entry to the migration steps below. lint_wiki.py imports this.
EXPECTED_SCHEMA_VERSION = 2

LOG_DATE_PATTERN = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]")
INDEX_LINK_PATTERN = re.compile(r"^\s*-\s*\[([^\]]+)\]\(([^)]+)\)")
INDEX_WIKILINK_PATTERN = re.compile(r"^\s*-\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

# Manual (LLM) steps per target version — shown in dry-run output, executed by
# the Migrate mode following references/migrate-workflow.md.
MANUAL_STEPS = {
    2: [
        "Consolidate tags to the canonical list in the schema file (AGENTS.md or CLAUDE.md) (max 4/page, 2+ pages per tag, merge synonyms)",
        "Rewrite the index as theme-grouped v2 (one entry per page, `★` marks hubs)",
        "Elect hubs for 3+ page clusters and add `## Pages in this cluster` sections",
        "Add `## Related` footers (2-5 links + one-line why) to wiki pages",
        "Update the schema file with the new conventions (tag policy, hub rule, index rule)",
    ],
}


def find_file(root: Path, name: str) -> Path | None:
    """Locate a structural file — wiki/<name> first (standard), then root/<name> (flat)."""
    for candidate in [root / "wiki" / name, root / name]:
        if candidate.exists():
            return candidate
    return None


def read_schema_version(root: Path, schema_override: str | None = None) -> int:
    """schema_version from the schema file's frontmatter (AGENTS.md or CLAUDE.md); unstamped wiki = v1."""
    claude_md = resolve_schema_file(root, schema_override)
    if not claude_md.exists():
        return 1
    text = claude_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return 1
    end = text.find("\n---", 4)
    if end == -1:
        return 1
    for line in text[4:end].splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "schema_version" and value.strip().isdigit():
            return int(value.strip())
    return 1


def stamp_schema_version(
    root: Path, version: int, apply: bool, schema_override: str | None = None,
) -> str:
    """Set schema_version in the schema file's frontmatter (insert frontmatter if absent)."""
    claude_md = resolve_schema_file(root, schema_override)
    name = claude_md.name
    if not claude_md.exists():
        if apply:
            claude_md.write_text(
                f"---\nschema_version: {version}\n---\n", encoding="utf-8"
            )
            ensure_claude_pointer(root, claude_md)
        return f"create {name} with schema_version: {version}"

    text = claude_md.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        body = text[4:end]
        if "schema_version" in body:
            new_body = re.sub(
                r"^schema_version:.*$", f"schema_version: {version}",
                body, flags=re.MULTILINE,
            )
            new_text = "---\n" + new_body + text[end:]
        else:
            new_text = "---\n" + body + f"\nschema_version: {version}" + text[end:]
    else:
        new_text = f"---\nschema_version: {version}\n---\n\n" + text

    if apply:
        claude_md.write_text(new_text, encoding="utf-8")
    return f"stamp {name} frontmatter with schema_version: {version}"


def dedupe_index(root: Path, apply: bool) -> str:
    """
    One page = one index entry: keep the FIRST entry for each target, drop the rest.
    """
    index_md = find_file(root, "index.md")
    if index_md is None:
        return "index.md not found — skipped"
    index_dir = index_md.parent
    wiki_dir = root / "wiki" if (root / "wiki").exists() else root

    def resolve(line: str) -> Path | None:
        m = INDEX_LINK_PATTERN.match(line)
        if m:
            url = m.group(2)
            if url.startswith(("http://", "https://", "#", "mailto:")):
                return None
            return (index_dir / url.split("#", 1)[0]).resolve()
        wm = INDEX_WIKILINK_PATTERN.match(line)
        if wm:
            slug = wm.group(1).strip()
            matches = list(wiki_dir.rglob(f"{slug}.md"))
            return matches[0].resolve() if matches else (wiki_dir / f"{slug}.md").resolve()
        return None

    lines = index_md.read_text(encoding="utf-8", errors="replace").splitlines()
    seen: set[Path] = set()
    kept: list[str] = []
    dropped: list[str] = []
    for line in lines:
        target = resolve(line)
        if target is not None:
            if target in seen:
                dropped.append(line.strip())
                continue
            seen.add(target)
        kept.append(line)

    if not dropped:
        return "index has no duplicate entries — nothing to do"
    if apply:
        index_md.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return f"drop {len(dropped)} duplicate index entr{'y' if len(dropped) == 1 else 'ies'} (first occurrence kept)"


def move_hot_changelog(root: Path, apply: bool) -> str:
    """
    hot.md is a cache, not a log: move dated `## [YYYY-MM-DD] ...` blocks from
    hot.md to log.md (copy -> verify -> delete), oldest first.
    """
    hot_md = find_file(root, "hot.md")
    log_md = find_file(root, "log.md")
    if hot_md is None:
        return "hot.md not found — skipped"
    if log_md is None:
        return "log.md not found — skipped (create it first with init_wiki.py)"

    lines = hot_md.read_text(encoding="utf-8", errors="replace").splitlines()
    kept: list[str] = []
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if LOG_DATE_PATTERN.match(line):
            current = [line]
            blocks.append(current)
            continue
        if current is not None and not line.startswith("## "):
            current.append(line)
            continue
        current = None
        kept.append(line)

    if not blocks:
        return "hot.md has no dated changelog blocks — nothing to do"

    if apply:
        # Copy to log (normalize heading to `## [date] note | title` when it
        # lacks the `action | title` form), then verify, then delete from hot.
        log_text = log_md.read_text(encoding="utf-8", errors="replace")
        if not log_text.endswith("\n"):
            log_text += "\n"
        additions: list[str] = []
        for block in blocks:
            heading = block[0]
            if "|" not in heading:
                m = LOG_DATE_PATTERN.match(heading)
                rest = heading[m.end():].strip() or "migrated from hot.md"
                heading = f"## [{m.group(1)}] note | {rest}"
            body = "\n".join(line for line in block[1:]).strip()
            additions.append(heading + ("\n" + body if body else ""))
        new_log = log_text + "\n" + "\n\n".join(additions) + "\n"
        log_md.write_text(new_log, encoding="utf-8")
        # Verify the full block content landed on disk before deleting from hot.
        written = log_md.read_text(encoding="utf-8", errors="replace")
        if all(a in written for a in additions):
            hot_md.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
        else:
            return "ERROR: log verification failed — hot.md left untouched"
    return f"move {len(blocks)} dated block(s) from hot.md to log.md"


# Registry: target version -> ordered mechanical steps (callables returning a
# human-readable summary). Adding a release that changes structure = adding an
# entry here + a MANUAL_STEPS entry. Part of the release checklist.
MIGRATIONS: dict[int, list] = {
    2: [
        dedupe_index,
        move_hot_changelog,
        lambda root, apply: stamp_schema_version(root, 2, apply, SCHEMA_OVERRIDE),
    ],
}


def append_restructure_log(root: Path, summary: str) -> None:
    """Best-effort log entry via append_log.py."""
    scripts_dir = Path(__file__).resolve().parent
    res = subprocess.run(
        [
            sys.executable, str(scripts_dir / "append_log.py"),
            "--path", str(root),
            "--action", "restructure",
            "--title", f"Schema migration to v{EXPECTED_SCHEMA_VERSION}",
            "--details", summary,
        ],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        print(f"warning: append_log failed: {res.stderr.strip()}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate an existing wiki to the current structural schema.",
    )
    parser.add_argument(
        "--path", default=".",
        help="Wiki root directory (default: current directory).",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply the migration. Default is dry-run. Commit the wiki to git first.",
    )
    parser.add_argument(
        "--schema-file", default=None,
        help="Schema file (default: auto-detect AGENTS.md / CLAUDE.md).",
    )
    args = parser.parse_args()
    global SCHEMA_OVERRIDE
    SCHEMA_OVERRIDE = args.schema_file

    root = Path(args.path).expanduser().resolve()
    if not (root / "wiki").exists() and not (root / "index.md").exists():
        print(f"error: {root} doesn't look like a wiki root", file=sys.stderr)
        return 1

    current = read_schema_version(root, SCHEMA_OVERRIDE)
    print(f"Wiki schema: v{current} · skill expects: v{EXPECTED_SCHEMA_VERSION}")

    if current >= EXPECTED_SCHEMA_VERSION:
        print("Nothing to migrate — wiki is already at the current schema (no-op).")
        return 0

    mode = "APPLY" if args.apply else "DRY-RUN (no files modified; re-run with --apply)"
    print(f"Mode: {mode}\n")

    summaries: list[str] = []
    for target in range(current + 1, EXPECTED_SCHEMA_VERSION + 1):
        steps = MIGRATIONS.get(target, [])
        print(f"v{target - 1} -> v{target} — mechanical steps:")
        for step in steps:
            summary = step(root, args.apply)
            summaries.append(summary)
            print(f"  - {summary}")
        manual = MANUAL_STEPS.get(target, [])
        if manual:
            print(f"\nv{target - 1} -> v{target} — manual steps (LLM, see references/migrate-workflow.md):")
            for m in manual:
                print(f"  * {m}")
        print()

    if args.apply:
        append_restructure_log(root, "; ".join(summaries))
        print("Migration applied and logged. Run the manual steps next (Migrate mode).")
    else:
        print("Dry-run complete. Commit your wiki to git, then re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
