#!/usr/bin/env python3
"""
lint_wiki.py — Health check an LLM-managed wiki.

Catches mechanical issues only (broken links, orphan pages, index drift, stub
pages, log gaps). Semantic issues — stale claims, unflagged contradictions,
missing pages on cross-cutting entities — are out of scope; the LLM has to
spot those by reading.

By default writes a dated report to wiki/reports/lint-YYYY-MM-DD.md, then
auto-tracks it: adds an index entry under "Reports" and appends a log entry.
Re-running on the same day overwrites the day's report (idempotent daily).

Usage:
    python lint_wiki.py                              # default: wiki/reports/lint-<today>.md + auto-track
    python lint_wiki.py --path /path/to/wiki-root
    python lint_wiki.py --stdout                     # print to stdout, no file, no tracking
    python lint_wiki.py --report /tmp/lint.md        # custom path; auto-track only if inside wiki/
    python lint_wiki.py --no-track                   # write report file but skip index + log updates
    python lint_wiki.py --stub-words 30 --log-gap-days 60   # tune thresholds

Output is markdown, organized by severity (block, quality, suggestion).
Exit code 1 if any block-severity issue found.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


LINK_PATTERN = re.compile(
    r"\[(?P<text>[^\]]+)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
# Obsidian wiki-links: [[slug]], [[slug|alias]], [[slug#heading]], [[slug#^block]],
# [[folder/slug]] and embeds ![[image.png]] / ![[note]]. Group 1 is the raw target
# (before the alias); wikilink_target() strips the #heading part.
WIKILINK_PATTERN = re.compile(r"!?\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
LOG_DATE_PATTERN = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]")
INDEX_LINK_PATTERN = re.compile(
    r"^\s*-\s*\[([^\]]+)\]\(([^)]+)\)"
)
# Obsidian-style [[slug]] or [[slug|alias]] wiki-links in index entries
INDEX_WIKILINK_PATTERN = re.compile(
    r"^\s*-\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]"
)


FENCED_CODE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]+`")


def strip_code(text: str) -> str:
    """Drop fenced blocks and inline code spans: links shown as code are examples, not links."""
    return INLINE_CODE.sub("", FENCED_CODE.sub("", text))


def wikilink_target(raw: str) -> str | None:
    """Target of a wiki-link without its #heading / #^block part; None for same-page anchors."""
    target = raw.split("#", 1)[0].strip()
    return target or None


def resolve_wikilink(target: str, wiki_dir: Path) -> tuple[str, Path]:
    """
    Resolve a wiki-link target to a file. Notes ([[slug]], [[slug.md]], [[dir/slug]])
    are searched under wiki/; attachments with another extension ([[img.png]]) are
    searched under the whole wiki root (wiki/ and raw/). Unresolved targets map to
    a nominal path that doesn't exist, so the caller reports them as broken.
    """
    suffix = Path(target).suffix.lower()
    if suffix and suffix != ".md":
        name = Path(target).name
        for base in (wiki_dir, wiki_dir.parent):
            matches = list(base.rglob(name))
            if matches:
                return f"[[{target}]]", matches[0].resolve()
        return f"[[{target}]]", (wiki_dir / target).resolve()
    slug = target[:-3] if suffix == ".md" else target
    matches = list(wiki_dir.rglob(f"{slug}.md"))
    if matches:
        return f"[[{slug}]]", matches[0].resolve()
    return f"[[{slug}]]", (wiki_dir / f"{slug}.md").resolve()


# Schema version the bundled templates/conventions correspond to.
# Kept in sync with migrate_wiki.py's registry. The script can be invoked from
# any cwd (e.g. via subprocess), so make the script dir importable first.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from migrate_wiki import EXPECTED_SCHEMA_VERSION
except ImportError:
    EXPECTED_SCHEMA_VERSION = 2
from schema_file import resolve_schema_file  # noqa: E402


def is_external(url: str) -> bool:
    return url.startswith(("http://", "https://", "mailto:", "ftp://"))


def parse_frontmatter(text: str) -> dict | None:
    """
    Minimal YAML frontmatter parser (stdlib only). Supports `key: value`,
    inline lists `tags: [a, b]`, and block lists:
        tags:
          - a
          - b
    Returns None when there is no frontmatter or it can't be parsed.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    body = text[4:end]
    data: dict = {}
    current_list_key: str | None = None
    try:
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- ") and current_list_key:
                data[current_list_key].append(stripped[2:].strip().strip("'\""))
                continue
            if ":" not in stripped:
                return None
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.split("#", 1)[0].strip()
            if value == "":
                data[key] = []
                current_list_key = key
            elif value.startswith("[") and value.endswith("]"):
                items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                data[key] = [v for v in items if v]
                current_list_key = None
            else:
                data[key] = value.strip("'\"")
                current_list_key = None
    except (ValueError, KeyError, AttributeError, IndexError):
        return None
    return data


def is_anchor_only(url: str) -> bool:
    return url.startswith("#")


def find_md_files(wiki_dir: Path) -> list[Path]:
    """All .md files under wiki/, excluding structural files and auto-generated reports.

    Skips:
      - wiki/index.md, wiki/log.md, wiki/hot.md (structural meta files)
      - wiki/reports/* (auto-generated lint/audit artifacts; tracked separately)
    """
    skip_names = {"index.md", "log.md", "hot.md"}
    reports_dir = (wiki_dir / "reports").resolve()
    out: list[Path] = []
    for p in wiki_dir.rglob("*.md"):
        if p.name in skip_names:
            continue
        try:
            p.resolve().relative_to(reports_dir)
            continue  # path is inside reports/, skip
        except ValueError:
            pass
        out.append(p)
    return out


def collect_links(md_path: Path, wiki_dir: Path) -> list[tuple[str, Path]]:
    """
    Returns list of (raw_url, resolved_path) for all internal links in the file.
    Handles both standard markdown links [text](url) and Obsidian [[slug]] wiki-links.
    Unresolved wiki-links resolve to the nominal path wiki/<slug>.md, which does
    not exist — so check_broken_links reports them instead of skipping silently.
    """
    text = strip_code(md_path.read_text(encoding="utf-8", errors="replace"))
    out: list[tuple[str, Path]] = []

    for m in LINK_PATTERN.finditer(text):
        url = m.group("url")
        if is_external(url) or is_anchor_only(url):
            continue
        target = url.split("#", 1)[0]
        if not target:
            continue
        resolved = (md_path.parent / target).resolve()
        out.append((url, resolved))

    for m in WIKILINK_PATTERN.finditer(text):
        target = wikilink_target(m.group(1))
        if target is None:
            continue  # [[#heading]]: same-page anchor
        out.append(resolve_wikilink(target, wiki_dir))

    return out


def check_wikilink_collisions(md_files: list[Path], wiki_dir: Path) -> list[dict]:
    """
    Wiki-link slugs that resolve to more than one file under wiki/.
    The first match wins at link time, so collisions are silent ambiguity.
    """
    collisions: list[dict] = []
    seen: set[str] = set()
    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in WIKILINK_PATTERN.finditer(text):
            target = wikilink_target(m.group(1))
            if target is None or Path(target).suffix.lower() not in ("", ".md"):
                continue
            slug = target[:-3] if target.lower().endswith(".md") else target
            if slug in seen:
                continue
            matches = list(wiki_dir.rglob(f"{slug}.md"))
            if len(matches) > 1:
                seen.add(slug)
                collisions.append({
                    "slug": slug,
                    "from": str(md),
                    "matches": [str(p) for p in matches],
                })
    return collisions


def check_broken_links(
    md_files: list[Path], wiki_dir: Path, raw_dir: Path,
) -> tuple[list[dict], list[dict]]:
    """
    Two outputs:
      - broken: links pointing to non-existent files inside the wiki repo
      - raw_missing: links to raw/ files that don't exist
    """
    broken: list[dict] = []
    raw_missing: list[dict] = []
    for md in md_files:
        for url, resolved in collect_links(md, wiki_dir):
            if not resolved.exists():
                # Categorize: is the target inside raw/ ?
                try:
                    resolved.relative_to(raw_dir)
                    raw_missing.append({
                        "from": str(md),
                        "url": url,
                        "resolved": str(resolved),
                    })
                except ValueError:
                    broken.append({
                        "from": str(md),
                        "url": url,
                        "resolved": str(resolved),
                    })
    return broken, raw_missing


def check_orphans(md_files: list[Path], wiki_dir: Path, root: Path) -> list[Path]:
    """
    Pages with zero inbound links from any other page in wiki/ or from structural meta files.
    Returns list of orphan page paths.
    """
    referenced: set[Path] = set()
    content_resolved = {p.resolve() for p in md_files}

    # Scan content pages + structural meta files that contain links.
    # Try both standard (wiki/index.md) and flat-vault (root/index.md) locations.
    candidate_files = list(md_files)
    for meta in [
        wiki_dir / "index.md", root / "index.md",
        wiki_dir / "hot.md", wiki_dir / "overview.md",
    ]:
        if meta.exists() and meta.resolve() not in content_resolved:
            candidate_files.append(meta)

    for md in candidate_files:
        for _url, resolved in collect_links(md, wiki_dir):
            try:
                if resolved.exists():
                    referenced.add(resolved)
            except OSError:
                continue

    orphans = [p for p in md_files if p.resolve() not in referenced]
    return orphans


def check_index_drift(
    md_files: list[Path], wiki_dir: Path,
) -> tuple[list[Path], list[dict]]:
    """
    Returns (pages_missing_from_index, dead_index_entries).
    Checks wiki/index.md first (standard layout), then root/index.md (flat layout).
    """
    for candidate in [wiki_dir / "index.md", wiki_dir.parent / "index.md"]:
        if candidate.exists():
            index_md = candidate
            index_dir = candidate.parent
            break
    else:
        return md_files, []

    text = index_md.read_text(encoding="utf-8", errors="replace")

    # Collect targets the index points to.
    indexed_targets: set[Path] = set()
    dead: list[dict] = []
    for line in text.splitlines():
        # Standard markdown links: [Title](path.md)
        m = INDEX_LINK_PATTERN.match(line)
        if m:
            title, url = m.group(1), m.group(2)
            if is_external(url) or is_anchor_only(url):
                continue
            target = (index_dir / url.split("#", 1)[0]).resolve()
            if target.exists():
                indexed_targets.add(target)
            else:
                dead.append({"title": title, "url": url, "resolved": str(target)})
            continue

        # Obsidian wiki-links: [[slug]] or [[slug|alias]]
        wm = INDEX_WIKILINK_PATTERN.match(line)
        if wm:
            target = wikilink_target(wm.group(1))
            if target is None:
                continue
            label, resolved = resolve_wikilink(target, wiki_dir)
            if resolved.exists():
                indexed_targets.add(resolved)
            else:
                # An index entry must point at a real page: a dead [[slug]] in
                # the catalog is drift, same as a dead markdown link.
                dead.append({"title": label, "url": label, "resolved": str(resolved)})

    missing = [p for p in md_files if p.resolve() not in indexed_targets]
    return missing, dead


def check_index_duplicates(wiki_dir: Path) -> list[dict]:
    """
    Index entries pointing at the same file more than once (usually a page
    listed under several categories). One page = one index entry.
    """
    for candidate in [wiki_dir / "index.md", wiki_dir.parent / "index.md"]:
        if candidate.exists():
            index_md = candidate
            index_dir = candidate.parent
            break
    else:
        return []

    occurrences: dict[Path, list[str]] = defaultdict(list)
    category = "(no category)"
    for line in index_md.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            category = line[3:].strip()
            continue
        m = INDEX_LINK_PATTERN.match(line)
        if m:
            url = m.group(2)
            if is_external(url) or is_anchor_only(url):
                continue
            target = (index_dir / url.split("#", 1)[0]).resolve()
            occurrences[target].append(category)
            continue
        wm = INDEX_WIKILINK_PATTERN.match(line)
        if wm:
            raw_target = wikilink_target(wm.group(1))
            if raw_target is None:
                continue
            _, target = resolve_wikilink(raw_target, wiki_dir)
            occurrences[target].append(category)

    return [
        {"target": str(target), "count": len(cats), "categories": cats}
        for target, cats in occurrences.items()
        if len(cats) > 1
    ]


def check_hot_health(wiki_dir: Path, max_words: int) -> list[dict]:
    """
    hot.md is a ~500-word cache, rewritten on every ingest — not a log.
    Flags: word count over threshold, and 3+ dated `## [YYYY-MM-DD]` blocks
    (a sign the file is accumulating changelog entries that belong in log.md).
    """
    for candidate in [wiki_dir / "hot.md", wiki_dir.parent / "hot.md"]:
        if candidate.exists():
            hot_path = candidate
            break
    else:
        return []

    text = hot_path.read_text(encoding="utf-8", errors="replace")
    body = text
    if body.startswith("---\n"):
        end = body.find("\n---", 4)
        if end != -1:
            body = body[end + 4:]

    findings: list[dict] = []
    words = len(body.split())
    if words > max_words:
        findings.append({
            "path": str(hot_path),
            "issue": f"{words} words (threshold {max_words}) — rewrite, don't append",
        })
    dated_blocks = sum(
        1 for line in body.splitlines() if LOG_DATE_PATTERN.match(line)
    )
    if dated_blocks >= 3:
        findings.append({
            "path": str(hot_path),
            "issue": (
                f"{dated_blocks} dated `## [...]` blocks — hot.md is turning into "
                "a second log; move them to log.md and rewrite hot.md"
            ),
        })
    return findings


def check_tag_health(
    md_files: list[Path], max_tags: int,
) -> tuple[list[dict], list[dict], int]:
    """
    Frontmatter tag hygiene:
      - single_use: tags appearing on exactly one page (keywords, not classifiers)
      - overtagged: pages with more than max_tags tags
      - unparsed: count of files whose frontmatter could not be parsed (skipped)
    """
    tag_pages: dict[str, list[Path]] = defaultdict(list)
    overtagged: list[dict] = []
    unparsed = 0
    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---\n"):
            continue
        fm = parse_frontmatter(text)
        if fm is None:
            unparsed += 1
            continue
        tags = fm.get("tags")
        if not isinstance(tags, list):
            continue
        for tag in tags:
            tag_pages[tag].append(md)
        if len(tags) > max_tags:
            overtagged.append({"path": str(md), "count": len(tags), "tags": tags})

    single_use = [
        {"tag": tag, "page": str(pages[0])}
        for tag, pages in sorted(tag_pages.items())
        if len(pages) == 1
    ]
    return single_use, overtagged, unparsed


def check_schema_version(root: Path, schema_override: str | None = None) -> dict | None:
    """
    Compare the schema file's (AGENTS.md or CLAUDE.md) schema_version stamp against
    what this skill version expects. Unstamped wikis count as v1. Returns a finding
    dict when the wiki is behind, else None.
    """
    claude_md = resolve_schema_file(root, schema_override)
    current = 1
    if claude_md.exists():
        fm = parse_frontmatter(claude_md.read_text(encoding="utf-8", errors="replace"))
        if fm and str(fm.get("schema_version", "")).isdigit():
            current = int(fm["schema_version"])
    if current < EXPECTED_SCHEMA_VERSION:
        return {
            "current": current,
            "expected": EXPECTED_SCHEMA_VERSION,
            "hint": "run scripts/migrate_wiki.py --path <wiki-root> (dry-run) to see the upgrade steps",
        }
    return None


def check_stub_pages(md_files: list[Path], min_words: int) -> list[dict]:
    """Pages with fewer than min_words of body text (excluding frontmatter)."""
    stubs: list[dict] = []
    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="replace")
        # Strip YAML frontmatter
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end != -1:
                text = text[end + 5:]
        words = len(text.split())
        if words < min_words:
            stubs.append({"path": str(md), "words": words})
    return stubs


def check_log_gaps(wiki_dir: Path, gap_days: int) -> list[dict]:
    """Look for stretches of >gap_days between log entries in log.md."""
    for candidate in [wiki_dir / "log.md", wiki_dir.parent / "log.md"]:
        if candidate.exists():
            log_path = candidate
            break
    else:
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    dates: list[dt.date] = []
    for line in text.splitlines():
        m = LOG_DATE_PATTERN.match(line)
        if m:
            try:
                dates.append(dt.date.fromisoformat(m.group(1)))
            except ValueError:
                continue

    if len(dates) < 2:
        return []

    dates.sort()
    gaps: list[dict] = []
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i - 1]).days
        if delta > gap_days:
            gaps.append({
                "from": dates[i - 1].isoformat(),
                "to": dates[i].isoformat(),
                "days": delta,
            })
    return gaps


def check_slug_conventions(md_files: list[Path]) -> list[Path]:
    """Filenames that aren't lowercase-with-hyphens (excluding _-prefixed)."""
    bad: list[Path] = []
    pattern = re.compile(r"^[a-z0-9][a-z0-9\-]*\.md$")
    for md in md_files:
        name = md.name
        if name.startswith("_"):
            continue
        if not pattern.match(name):
            bad.append(md)
    return bad


def render_report(results: dict, root: Path, thresholds: dict) -> str:
    """Render the lint report as markdown."""
    today = dt.date.today().isoformat()
    lines: list[str] = []
    lines.append(f"# Lint report\n")
    lines.append(f"Wiki root: `{root}`")
    lines.append(f"Date: {today}\n")

    block_count = (
        len(results["broken_links"])
        + len(results["raw_missing"])
        + len(results["index_dead"])
    )
    quality_count = (
        len(results["orphans"])
        + len(results["index_missing"])
        + len(results["stubs"])
        + len(results["slug_mismatch"])
        + len(results["index_duplicates"])
        + len(results["hot_health"])
        + len(results["overtagged"])
        + len(results["wikilink_collisions"])
    )
    suggestion_count = (
        len(results["log_gaps"])
        + len(results["single_use_tags"])
        + (1 if results["schema_version"] else 0)
    )

    lines.append(
        f"Summary: **{block_count} block**, **{quality_count} quality**, "
        f"**{suggestion_count} suggestion**.\n"
    )

    # BLOCK
    lines.append("## Block (fix without asking)\n")
    if not block_count:
        lines.append("None. ✓\n")
    else:
        if results["broken_links"]:
            lines.append(f"### Broken links ({len(results['broken_links'])})\n")
            lines.append(
                "Markdown links and `[[wiki-links]]` pointing to files that don't "
                "exist inside the wiki.\n"
            )
            for entry in results["broken_links"]:
                lines.append(
                    f"- in `{entry['from']}`: `{entry['url']}` → `{entry['resolved']}`"
                )
            lines.append("")
        if results["raw_missing"]:
            lines.append(f"### Wiki citing missing `raw/` files ({len(results['raw_missing'])})\n")
            for entry in results["raw_missing"]:
                lines.append(
                    f"- in `{entry['from']}`: `{entry['url']}` → `{entry['resolved']}`"
                )
            lines.append("")
        if results["index_dead"]:
            lines.append(f"### Dead index entries ({len(results['index_dead'])})\n")
            lines.append("`wiki/index.md` references files that don't exist.\n")
            for entry in results["index_dead"]:
                if entry["url"].startswith("[["):
                    lines.append(f"- `{entry['url']}`")
                else:
                    lines.append(f"- [{entry['title']}]({entry['url']})")
            lines.append("")

    # QUALITY
    lines.append("## Quality (propose fixes, apply with approval)\n")
    if not quality_count:
        lines.append("None. ✓\n")
    else:
        if results["orphans"]:
            lines.append(f"### Orphan pages ({len(results['orphans'])})\n")
            lines.append("Pages with no inbound links from any other page or from the index.\n")
            for p in results["orphans"]:
                lines.append(f"- `{p}`")
            lines.append("")
        if results["index_missing"]:
            lines.append(f"### Pages missing from index ({len(results['index_missing'])})\n")
            for p in results["index_missing"]:
                lines.append(f"- `{p}`")
            lines.append("")
        if results["stubs"]:
            lines.append(
                f"### Stub pages — under {thresholds['stub_words']} words "
                f"({len(results['stubs'])})\n"
            )
            for s in results["stubs"]:
                lines.append(f"- `{s['path']}` ({s['words']} words)")
            lines.append("")
        if results["slug_mismatch"]:
            lines.append(f"### Slug convention mismatch ({len(results['slug_mismatch'])})\n")
            lines.append(
                "Filenames not matching `lowercase-with-hyphens.md`.\n"
            )
            for p in results["slug_mismatch"]:
                lines.append(f"- `{p}`")
            lines.append("")
        if results["index_duplicates"]:
            lines.append(
                f"### Duplicate index entries ({len(results['index_duplicates'])})\n"
            )
            lines.append(
                "The same page is listed more than once in the index. "
                "One page = one entry; pick the best category and drop the rest.\n"
            )
            for d in results["index_duplicates"]:
                cats = ", ".join(d["categories"])
                lines.append(f"- `{d['target']}` — {d['count']} entries ({cats})")
            lines.append("")
        if results["hot_health"]:
            lines.append(f"### hot.md health ({len(results['hot_health'])})\n")
            lines.append(
                "hot.md is a ~500-word cache, rewritten entirely on every ingest.\n"
            )
            for h in results["hot_health"]:
                lines.append(f"- `{h['path']}`: {h['issue']}")
            lines.append("")
        if results["overtagged"]:
            lines.append(
                f"### Pages over {thresholds['max_tags']} tags "
                f"({len(results['overtagged'])})\n"
            )
            lines.append(
                "Tags are classifiers, not keywords — trim to the canonical list "
                "in the schema file (AGENTS.md / CLAUDE.md).\n"
            )
            for t in results["overtagged"]:
                lines.append(f"- `{t['path']}` ({t['count']} tags: {', '.join(t['tags'])})")
            lines.append("")
        if results["wikilink_collisions"]:
            lines.append(
                f"### Ambiguous wiki-link slugs ({len(results['wikilink_collisions'])})\n"
            )
            lines.append(
                "These `[[slugs]]` match more than one file; the first match wins "
                "silently. Rename to unambiguous slugs.\n"
            )
            for c in results["wikilink_collisions"]:
                lines.append(
                    f"- `[[{c['slug']}]]` (first seen in `{c['from']}`): "
                    + ", ".join(f"`{m}`" for m in c["matches"])
                )
            lines.append("")

    # SUGGESTIONS
    lines.append("## Suggestions (informational)\n")
    if not suggestion_count:
        lines.append("None. ✓\n")
    else:
        if results["log_gaps"]:
            lines.append(
                f"### Log gaps over {thresholds['log_gap_days']} days "
                f"({len(results['log_gaps'])})\n"
            )
            for g in results["log_gaps"]:
                lines.append(f"- {g['from']} → {g['to']} ({g['days']} days)")
            lines.append("")
        if results["single_use_tags"]:
            lines.append(
                f"### Single-use tags ({len(results['single_use_tags'])})\n"
            )
            lines.append(
                "A tag on exactly one page is a keyword, not a classifier — "
                "move it to the page body or merge it into a canonical tag.\n"
            )
            for s in results["single_use_tags"]:
                lines.append(f"- `{s['tag']}` (only on `{s['page']}`)")
            lines.append("")
        if results["schema_version"]:
            sv = results["schema_version"]
            lines.append("### Wiki schema behind skill version\n")
            lines.append(
                f"- Wiki is at schema v{sv['current']}, skill expects "
                f"v{sv['expected']} — {sv['hint']}"
            )
            lines.append("")
    if results.get("tag_unparsed"):
        lines.append(
            f"*Note: frontmatter could not be parsed in "
            f"{results['tag_unparsed']} file(s); tag checks skipped them.*\n"
        )

    # Reminder of out-of-scope checks
    lines.append("---\n")
    lines.append("**Not checked here (LLM responsibility):** stale claims, ")
    lines.append("unflagged contradictions, missing pages on cross-cutting entities, ")
    lines.append("schema drift between the schema file (`AGENTS.md` / `CLAUDE.md`) and actual practice.\n")
    return "\n".join(lines)


def auto_track(
    report_path: Path,
    root: Path,
    block_total: int,
    quality_count: int,
    suggestion_count: int,
    today: str,
) -> None:
    """Update index.md and log.md to record this report.

    Best-effort: failures are reported but don't abort lint.
    Only called when report is being written inside wiki/reports/.
    """
    scripts_dir = Path(__file__).resolve().parent
    summary = (
        f"{block_total} block, {quality_count} quality, {suggestion_count} suggestion"
    )
    index_title = f"Lint {today}"
    log_title = "Health check"

    # Path relative to wiki/ for the index entry
    try:
        rel = report_path.resolve().relative_to((root / "wiki").resolve())
    except ValueError:
        return

    # update_index.py
    res = subprocess.run(
        [
            sys.executable, str(scripts_dir / "update_index.py"),
            "--path", str(root),
            "--category", "Reports",
            "--title", index_title,
            "--page-path", str(report_path),
            "--summary", summary,
        ],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        print(f"warning: update_index failed: {res.stderr.strip()}", file=sys.stderr)

    # append_log.py
    details = f"Wrote wiki/{rel.as_posix()}. {summary}."
    res = subprocess.run(
        [
            sys.executable, str(scripts_dir / "append_log.py"),
            "--path", str(root),
            "--action", "lint",
            "--title", log_title,
            "--details", details,
            "--date", today,
        ],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        print(f"warning: append_log failed: {res.stderr.strip()}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Health check an LLM-managed wiki.",
    )
    parser.add_argument(
        "--path", default=".",
        help="Wiki root directory (default: current directory).",
    )
    parser.add_argument(
        "--report", default=None,
        help="Custom report path. Default: wiki/reports/lint-<today>.md.",
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="Print report to stdout, do not write a file (no auto-track).",
    )
    parser.add_argument(
        "--no-track", action="store_true",
        help="Write the report file but skip the auto index/log updates.",
    )
    parser.add_argument(
        "--stub-words", type=int, default=50,
        help="Pages under this many body words are flagged as stubs (default: 50).",
    )
    parser.add_argument(
        "--log-gap-days", type=int, default=30,
        help="Log gaps longer than this many days are flagged (default: 30).",
    )
    parser.add_argument(
        "--hot-max-words", type=int, default=700,
        help="hot.md over this many body words is flagged (default: 700).",
    )
    parser.add_argument(
        "--max-tags", type=int, default=4,
        help="Pages with more frontmatter tags than this are flagged (default: 4).",
    )
    parser.add_argument(
        "--schema-file", default=None,
        help="Schema file (default: auto-detect AGENTS.md / CLAUDE.md).",
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    wiki_dir = root / "wiki"
    raw_dir = root / "raw"

    if not wiki_dir.exists():
        print(f"error: no wiki/ directory at {root}", file=sys.stderr)
        return 1

    today = dt.date.today().isoformat()

    md_files = find_md_files(wiki_dir)

    broken, raw_missing = check_broken_links(md_files, wiki_dir, raw_dir)
    orphans = check_orphans(md_files, wiki_dir, root)
    index_missing, index_dead = check_index_drift(md_files, wiki_dir)
    stubs = check_stub_pages(md_files, args.stub_words)
    log_gaps = check_log_gaps(wiki_dir, args.log_gap_days)
    slug_mismatch = check_slug_conventions(md_files)
    index_duplicates = check_index_duplicates(wiki_dir)
    hot_health = check_hot_health(wiki_dir, args.hot_max_words)
    single_use_tags, overtagged, tag_unparsed = check_tag_health(md_files, args.max_tags)
    wikilink_collisions = check_wikilink_collisions(md_files, wiki_dir)
    schema_version = check_schema_version(root, args.schema_file)

    results = {
        "broken_links": broken,
        "raw_missing": raw_missing,
        "orphans": orphans,
        "index_missing": index_missing,
        "index_dead": index_dead,
        "stubs": stubs,
        "log_gaps": log_gaps,
        "slug_mismatch": slug_mismatch,
        "index_duplicates": index_duplicates,
        "hot_health": hot_health,
        "single_use_tags": single_use_tags,
        "overtagged": overtagged,
        "tag_unparsed": tag_unparsed,
        "wikilink_collisions": wikilink_collisions,
        "schema_version": schema_version,
    }

    report = render_report(
        results, root,
        thresholds={
            "stub_words": args.stub_words,
            "log_gap_days": args.log_gap_days,
            "max_tags": args.max_tags,
        },
    )

    block_total = len(broken) + len(raw_missing) + len(index_dead)
    quality_count = (
        len(orphans) + len(index_missing) + len(stubs) + len(slug_mismatch)
        + len(index_duplicates) + len(hot_health) + len(overtagged)
        + len(wikilink_collisions)
    )
    suggestion_count = (
        len(log_gaps) + len(single_use_tags) + (1 if schema_version else 0)
    )

    # Decide where the report goes.
    if args.stdout:
        print(report)
    else:
        if args.report:
            report_path = Path(args.report).expanduser().resolve()
        else:
            report_path = (wiki_dir / "reports" / f"lint-{today}.md").resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"Report written to {report_path}")

        # Auto-track only when the report lives inside wiki/ — custom paths
        # outside the wiki are treated as one-off and not tracked.
        if not args.no_track:
            try:
                report_path.relative_to(wiki_dir.resolve())
            except ValueError:
                pass  # outside wiki/, skip tracking
            else:
                auto_track(
                    report_path, root,
                    block_total, quality_count, suggestion_count, today,
                )

    return 1 if block_total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
