#!/usr/bin/env python3
"""
update_index.py: add or update an entry in wiki/index.md under a given category.

Idempotent on (category, page): if an entry for the same page (or the same title)
already exists under the category, it is replaced in place. Otherwise it is added.

The index format, in either link style:

    # Index
    ...
    ## Sources
    - [Title](sources/slug.md) — summary        (markdown style)
    - [[slug]] — summary                        (wikilink / Obsidian style)

Usage:
    python update_index.py --category concepts \\
        --title "Nutritionism" \\
        --page-path "wiki/concepts/nutritionism.md" \\
        --summary "Reductive ideology that food = nutrients (5 sources)"

Behaviour:
- Categories match existing `## ` headings case-insensitively, and the existing
  heading's spelling is kept ("ai tools" updates "## AI Tools"). A new category
  keeps the casing you pass; an all-lowercase name gets its first letter
  capitalised; the standard ones (sources, entities, ...) use their canonical
  spelling.
- Existing section order and section content (blank lines, sub-headings, prose)
  are preserved. A new category is inserted before the first "tail" section
  (default: Meta; see --tail), else appended at the end.
- Link style follows the index (--link-style auto): if most entries are
  [[wikilinks]], the new entry is a wikilink; otherwise a markdown link.
- Updating an entry keeps a hub marker (★) right after its link. With no
  --summary, an update keeps the old summary.
- The link path is relative to the directory holding index.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Canonical spelling for the standard categories.
CANONICAL_NAMES = ["Sources", "Entities", "Concepts", "Notes", "Reports"]
# Sections that stay at the end of the index; new categories go before them.
DEFAULT_TAIL = ["Meta"]

MD_ENTRY = re.compile(r"^\s*-\s*\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)(?P<rest>.*)$")
WIKI_ENTRY = re.compile(r"^\s*-\s*\[\[(?P<target>[^\]|#]+)(?:#[^\]|]*)?(?:\|(?P<alias>[^\]]*))?\]\](?P<rest>.*)$")
HUB_MARK = "★"


def find_index(root: Path) -> tuple[Path, Path]:
    """Returns (index_path, index_dir). Checks wiki/index.md first (standard), then root/index.md (flat)."""
    for candidate in [root / "wiki" / "index.md", root / "index.md"]:
        if candidate.exists():
            return candidate, candidate.parent
    raise FileNotFoundError(
        f"No index.md found at {root / 'wiki' / 'index.md'} or {root / 'index.md'}. "
        "Run init_wiki.py first to scaffold the wiki."
    )


def normalize_category(category: str, existing: list[str]) -> str:
    """Match an existing heading case-insensitively; otherwise pick a spelling for a new one."""
    cat = category.strip()
    if cat.startswith("## "):
        cat = cat[3:].strip()
    for name in existing:
        if name.casefold() == cat.casefold():
            return name
    if cat.startswith(("#", "@")):
        return cat
    for name in CANONICAL_NAMES:
        if name.casefold() == cat.casefold():
            return name
    if cat == cat.lower():
        return cat[:1].upper() + cat[1:]
    return cat


def relative_link_target(page_path: Path, root: Path, index_dir: Path) -> str:
    """Link target for an index entry, relative to index_dir (wiki/ or the flat wiki root)."""
    page_path = Path(page_path)
    if page_path.is_absolute():
        resolved = page_path.resolve()
    else:
        resolved = (root / page_path).resolve()
        if not resolved.exists() and (index_dir / page_path).exists():
            resolved = (index_dir / page_path).resolve()
    try:
        return resolved.relative_to(index_dir.resolve()).as_posix()
    except ValueError as e:
        raise ValueError(
            f"page-path {page_path} resolves to {resolved}, which is not inside index dir ({index_dir})"
        ) from e


def parse_index(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Split index.md into (header_lines, [(heading, body_lines), ...]) preserving order."""
    header: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif not sections:
            header.append(line)
        else:
            sections[-1][1].append(line)
    return header, sections


def render_index(header: list[str], sections: list[tuple[str, list[str]]]) -> str:
    """Reassemble the index: header, then each section with exactly one blank line after it."""
    out: list[str] = []
    head = "\n".join(header).rstrip()
    if head:
        out.append(head + "\n\n")
    for name, body in sections:
        while body and not body[-1].strip():
            body.pop()
        while body and not body[0].strip():
            body.pop(0)
        out.append(f"## {name}\n")
        if body:
            out.append("\n".join(body) + "\n")
        out.append("\n")
    return "".join(out).rstrip() + "\n"


def detect_link_style(sections: list[tuple[str, list[str]]]) -> str:
    """'wikilink' if most index entries are [[wikilinks]], else 'markdown'."""
    wiki = md = 0
    for _, body in sections:
        for line in body:
            if WIKI_ENTRY.match(line):
                wiki += 1
            elif MD_ENTRY.match(line):
                md += 1
    return "wikilink" if wiki > md else "markdown"


def entry_targets(line: str, index_dir: Path) -> tuple[str | None, str | None]:
    """(title, page stem) referenced by an entry line, or (None, None)."""
    m = MD_ENTRY.match(line)
    if m:
        return m.group("title"), Path(m.group("url").split("#", 1)[0]).stem
    w = WIKI_ENTRY.match(line)
    if w:
        target = w.group("target").strip()
        stem = Path(target[:-3] if target.endswith(".md") else target).name
        return (w.group("alias") or "").strip() or None, stem
    return None, None


def split_rest(rest: str) -> tuple[bool, str]:
    """From the text after the link, return (has_hub_mark, summary)."""
    rest = rest.strip()
    hub = rest.startswith(HUB_MARK)
    if hub:
        rest = rest[len(HUB_MARK):].strip()
    if rest.startswith("—") or rest.startswith("-"):
        rest = rest[1:].strip()
    return hub, rest


def build_entry(style: str, title: str, link: str, summary: str, hub: bool) -> str:
    stem = Path(link).stem
    if style == "wikilink":
        label = f"[[{stem}]]" if title.strip() in ("", stem) else f"[[{stem}|{title}]]"
    else:
        label = f"[{title}]({link})"
    parts = [f"- {label}"]
    if hub:
        parts.append(HUB_MARK)
    if summary:
        parts.append(f"— {summary}")
    return " ".join(parts)


def upsert_entry(
    sections: list[tuple[str, list[str]]],
    category: str,
    title: str,
    link: str,
    summary: str | None,
    style: str,
    tail: list[str],
    index_dir: Path,
) -> str:
    """Add or update the entry. Returns 'added' or 'updated'."""
    stem = Path(link).stem
    for name, body in sections:
        if name != category:
            continue
        for i, line in enumerate(body):
            line_title, line_stem = entry_targets(line, index_dir)
            if line_stem is None:
                continue
            if line_stem == stem or (line_title is not None and line_title == title):
                m = MD_ENTRY.match(line) or WIKI_ENTRY.match(line)
                hub, old_summary = split_rest(m.group("rest"))
                body[i] = build_entry(style, title, link, old_summary if summary is None else summary, hub)
                return "updated"
        # Append after the last entry line, keeping any trailing prose below it.
        last = max((i for i, ln in enumerate(body) if entry_targets(ln, index_dir)[1]), default=None)
        new_line = build_entry(style, title, link, summary or "", False)
        if last is None:
            body.append(new_line)
        else:
            body.insert(last + 1, new_line)
        return "added"

    new_section = (category, [build_entry(style, title, link, summary or "", False)])
    tail_cf = {t.casefold() for t in tail}
    for i, (name, _) in enumerate(sections):
        if name.casefold() in tail_cf:
            sections.insert(i, new_section)
            return "added"
    sections.append(new_section)
    return "added"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add or update an entry in wiki/index.md under a category.",
    )
    parser.add_argument("--path", default=".", help="Wiki root directory (default: current directory).")
    parser.add_argument("--category", required=True, help="Category heading. Matched case-insensitively.")
    parser.add_argument("--title", required=True, help="Page title (markdown link text / wikilink alias).")
    parser.add_argument(
        "--page-path", required=True,
        help="Path to the page being indexed: absolute, relative to the wiki root, or relative to wiki/.",
    )
    parser.add_argument(
        "--summary", default=None,
        help="One-line summary after an em-dash. Omit on update to keep the old summary.",
    )
    parser.add_argument(
        "--link-style", choices=["auto", "markdown", "wikilink"], default="auto",
        help="Entry link style (default: auto = follow the majority of existing entries).",
    )
    parser.add_argument(
        "--tail", action="append", default=None,
        help="Section that stays at the end; new categories go before it. Repeatable. Default: Meta.",
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    try:
        index_path, index_dir = find_index(root)
        link = relative_link_target(Path(args.page_path), root, index_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    header, sections = parse_index(index_path.read_text(encoding="utf-8"))
    category = normalize_category(args.category, [name for name, _ in sections])
    style = detect_link_style(sections) if args.link_style == "auto" else args.link_style

    # One page = one index entry: warn (don't block) if the page already lives elsewhere.
    stem = Path(link).stem
    for name, body in sections:
        if name == category:
            continue
        if any(entry_targets(line, index_dir)[1] == stem for line in body):
            print(
                f"warning: {link} is already indexed under '{name}' — one page should have "
                "one index entry; remove the duplicate unless it is intentional.",
                file=sys.stderr,
            )

    action = upsert_entry(
        sections, category, args.title, link, args.summary, style,
        args.tail if args.tail else DEFAULT_TAIL, index_dir,
    )
    index_path.write_text(render_index(header, sections), encoding="utf-8")
    print(f"Index {action}: [{category}] {args.title} -> {link} ({style})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
