#!/usr/bin/env python3
"""
schema_file.py: locate the wiki's schema file (AGENTS.md or CLAUDE.md).

Claude Code reads CLAUDE.md; Codex and most other agents read AGENTS.md. A wiki
may use either, or both with CLAUDE.md importing AGENTS.md (`@AGENTS.md`).
All scripts resolve the schema through this module so that none of them
hardcodes one filename.

Resolution order:
1. Explicit override (`--schema-file`), relative to the wiki root or absolute.
2. Both files exist: CLAUDE.md wins if it holds real content. If it only
   imports AGENTS.md (lines like `@AGENTS.md`), AGENTS.md wins.
3. Exactly one exists: that one.
4. Neither exists: AGENTS.md (new wikis get AGENTS.md plus a one-line CLAUDE.md
   that imports it, so both hosts load the same schema).
"""

from __future__ import annotations

from pathlib import Path

AGENTS = "AGENTS.md"
CLAUDE = "CLAUDE.md"
CLAUDE_POINTER = "@AGENTS.md\n"


def _is_pointer_only(path: Path) -> bool:
    """True if the file only imports other files (`@path` lines) and has no own content."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return bool(lines) and all(ln.startswith("@") for ln in lines)


def resolve_schema_file(root: Path, override: str | None = None) -> Path:
    """Return the path of the schema file for the wiki at `root` (it may not exist yet)."""
    root = Path(root)
    if override:
        p = Path(override).expanduser()
        return p if p.is_absolute() else root / p
    agents, claude = root / AGENTS, root / CLAUDE
    if agents.exists() and claude.exists():
        return agents if _is_pointer_only(claude) else claude
    if claude.exists():
        return claude
    return agents


def ensure_claude_pointer(root: Path, schema: Path) -> Path | None:
    """
    When the schema is AGENTS.md at the wiki root and no CLAUDE.md exists, write a
    one-line CLAUDE.md that imports it. Returns the created path, else None.
    """
    root = Path(root)
    if schema.resolve() != (root / AGENTS).resolve():
        return None
    claude = root / CLAUDE
    if claude.exists():
        return None
    claude.write_text(CLAUDE_POINTER, encoding="utf-8")
    return claude
