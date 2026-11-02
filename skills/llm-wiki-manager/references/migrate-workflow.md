# Migrate Workflow

Use this when a skill update changed the wiki's structural conventions and an existing wiki needs to move to the new schema. Triggers: "wiki güncelle", "upgrade wiki", "migrate wiki", "move the wiki to the new structure" — or the Step 0 schema-version check in any mode found the wiki behind (`schema_version` in the wiki's `CLAUDE.md` lower than the skill expects; unstamped wiki = v1).

Migration has two halves: **mechanical steps** (`scripts/migrate_wiki.py` does them) and **semantic steps** (you do them, page by page, with user approval). The script's dry-run output lists both.

## Goal

Bring the wiki to the current `schema_version` without losing content: every mechanical change git-revertible, every semantic change diff-shown-and-approved, one `restructure` log entry per applied run.

## The full loop

### 1. Dry-run first — always

```bash
python scripts/migrate_wiki.py --path <wiki-root>
```

Shows: current vs expected schema version, the mechanical steps that would run (with counts — e.g. "drop 4 duplicate index entries"), and the manual steps you'll perform after. **No files are modified.**

If the output says "already at the current schema (no-op)", stop — nothing to do.

### 2. Commit, then apply

The wiki must be committed to git before applying (rollback safety). Then:

```bash
python scripts/migrate_wiki.py --path <wiki-root> --apply
```

Mechanical steps for v1 → v2:

- **Index dedupe** — one page = one entry; the first occurrence is kept, the rest dropped.
- **hot.md → log.md** — dated `## [YYYY-MM-DD]` changelog blocks are moved to log.md (copy → verify → delete; headings without `action | title` form become `note |` entries).
- **Stamp** — `schema_version: 2` written into `CLAUDE.md` frontmatter.

The script never touches `raw/`, logs the run as `restructure`, and is idempotent — re-running at the current version is a no-op.

### 3. Semantic steps (LLM work, diff-before-write)

Work through these in order, showing the user a diff or summary before each write:

1. **Tag consolidation.** Collect all frontmatter tags (lint's tag-health output is the inventory). Merge synonyms, demote single-use tags to body text, cut pages to ≤4 tags. Write the surviving canonical list into the wiki's `CLAUDE.md` tag-policy section.
2. **Index v2 rewrite.** Regroup the index by theme/category (NOT by tag), one entry per page, format `- [Title](path.md) — one-line summary #tag`. Keep it short — the index is read on every query.
3. **Hub election.** For each 3+ page cluster, elect the most encompassing page as hub: add a `## Pages in this cluster` section there (one line per member + short description) and mark the hub with `★` in the index.
4. **Related footers.** Add `## Related` (2–5 links + one-line why) to wiki pages, starting with the most-linked ones. No `related:` frontmatter field — the footer is the single source of truth.
5. **Schema update.** Make sure the wiki's `CLAUDE.md` reflects the new conventions (tag policy, hub rule, index rule — copy the blocks from `assets/templates/wiki-CLAUDE.md.tmpl` and adapt).

Steps 1–4 can be spread over multiple sessions; the stamp is already at the new version, so lint findings (not the version check) track the remaining semantic debt.

### 4. Verify and log

- Run `python scripts/lint_wiki.py --path <wiki-root> --stdout` — the migration-related findings (duplicate index entries, hot bloat, schema version) should be gone; tag findings shrink as step 1 proceeds.
- The script already appended the `restructure` log entry for the mechanical half. Append one more after finishing the semantic half:

```bash
python scripts/append_log.py --path <wiki-root> --action restructure \
  --title "Schema v2 semantic migration" \
  --details "Tags 80->20, index rewritten theme-grouped, 3 hubs elected, Related footers on 13 pages."
```

### 5. Brief recap to the user

Three to six lines: what moved, what was merged, what's left (if the semantic steps are being spread over sessions).

## Heuristics

- **Never skip the dry-run.** It's the user's approval surface.
- **Mechanical before semantic.** The script's output (deduped index, clean hot) is the foundation the semantic steps build on.
- **Don't do semantic steps silently.** Each one rewrites user-visible structure; show diffs.
- **Respect the Lint exceptions section** in the wiki's `CLAUDE.md` — consciously ignored findings stay ignored during migration too.

## Common mistakes

- **Applying without a git commit.** The only rollback is git; insist on it.
- **Treating the stamp as "migration done".** The stamp tracks the mechanical half; the semantic half is tracked by lint findings.
- **Re-grouping the index by tag.** That's the v1 failure mode this migration removes — group by theme, one entry per page.
- **Touching `raw/`.** Never. Sources are immutable regardless of schema version.
