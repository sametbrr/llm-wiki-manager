# Lint Workflow

Use this when the user wants a health check on the wiki. Triggers: "audit the wiki", "lint", "anything broken", "what's stale", or after a long break ("I haven't touched this in a month, what's the state").

Linting is preventive maintenance. Wikis decay quietly — broken links from renamed files, orphan pages no one links to, claims contradicted by later sources but never updated, gaps where a page should exist. The script catches the mechanical problems; the LLM has to spot the substantive ones.

## Goal

Produce a short report of issues, organized by severity. Propose fixes. With user approval, apply them. Append a single log entry summarizing the pass.

## The full loop

### 1. Run the lint script

```bash
python scripts/lint_wiki.py --path .
```

By default this writes the report to `wiki/reports/lint-<today>.md`, then auto-tracks it: adds an entry under the `Reports` category in `wiki/index.md`, and appends a single `lint | Health check` entry to `wiki/log.md`. Re-running on the same day overwrites the day's report file (idempotent daily) — but each run logs a new entry, so you can see "I lint-checked twice today" in the log.

Useful flags:

- `--stdout` — print to terminal, don't write a file, don't auto-track. For one-off inspection.
- `--report /custom/path.md` — custom path. If the path is outside `wiki/`, auto-tracking is skipped (treated as one-off external snapshot).
- `--no-track` — write the report file but skip the index/log updates.
- `--stub-words 30` — change the threshold for stub detection (default 50).
- `--log-gap-days 60` — change the threshold for log-gap warnings (default 30).
- `--hot-max-words 900` — change the hot.md bloat threshold (default 700).
- `--max-tags 5` — change the per-page frontmatter tag limit (default 4).

The report is markdown, organized by severity (block / quality / suggestion). Past reports accumulate in `wiki/reports/`, giving you a longitudinal view of wiki health — "how was the wiki last month vs now". Git history of `wiki/reports/` is the audit trail.

### 2. Layer in the substantive checks

The script can't see semantics. The LLM has to read the report and add:

- **Stale claims** — pages whose latest cited source is much older than the most recent ingest. The world may have moved.
- **Unflagged contradictions** — pages where two cited sources clearly disagree but no "Disputes" section exists.
- **Missing pages** — entities or concepts mentioned across multiple sources that don't have their own page yet.
- **Over-thin pages** — pages that have one source citation and no synthesis. Often candidates for deletion or merge.
- **Wiki schema drift** — `CLAUDE.md` says one convention, recent pages use another. Either update `CLAUDE.md` or fix the pages.

To find these, skim recent source-summary pages and check whether their contents have actually been integrated upstream. Skim the index categories and check that they still match the actual contents.

### 3. Triage by severity

Organize the report into three buckets:

- **Block bug** — something is actively broken (broken links, index pointing to dead files). Fix without asking.
- **Quality issue** — orphan pages, missing index entries, unflagged contradictions, empty pages. Propose fixes; apply with user approval.
- **Suggestion** — stale claims, missing pages worth creating, schema drift. Surface but don't pressure.

### 4. Present and propose

Show the user a tight summary, not the full report:

> Lint pass over `wiki/` (47 pages):
> - **2 broken links** in `concepts/nutritionism.md` (auto-fix incoming)
> - **3 orphan pages** — likely belong under `concepts/`. Want me to link them from related pages?
> - **1 contradiction** between `sources/keys-1980.md` and `sources/teicholz-2014.md` — `concepts/saturated-fat.md` doesn't have a "Disputes" section yet. Want me to add one?
> - **Suggestion:** `entities/marion-nestle.md` is mentioned in 4 source summaries but has no page. Want me to create one?

Wait for direction before applying anything beyond the block bugs.

### 5. Apply approved fixes

Apply changes one bucket at a time. Show what changed. For substantive changes (creating a new page, adding a Disputes section), draft and confirm before saving.

### 6. Update index and log

After fixes:

```bash
# Update index for any new or substantially-changed pages
python scripts/update_index.py --path . --category ... --title ... --page-path ... --summary ...

# One log entry summarizing the pass
python scripts/append_log.py --action lint \
  --title "Health check pass" \
  --details "Fixed 2 broken links. Linked 3 orphans. Added Disputes section to concepts/saturated-fat.md. Created entities/marion-nestle.md (4 sources)."
```

## Cadence

- After every 5-10 ingests is reasonable.
- After a long break (more than a month).
- Before sharing the wiki with someone else.
- Whenever the wiki "feels" off — usually a sign it actually is.

The user will rarely ask for it on schedule. It's worth proactively suggesting after a few ingests if it hasn't happened: "Your wiki has grown by ~12 pages since the last lint. Want me to do a pass?"

## What the lint script catches

`scripts/lint_wiki.py` is intentionally conservative — it only flags things that are mechanically clear. The full check list:

| Check | What it does | Severity |
|---|---|---|
| `broken_links` | Markdown links **and `[[wiki-links]]`** to non-existent files within the wiki | block |
| `index_missing` | Pages that exist but aren't in `wiki/index.md` (reads both `[markdown](links)` and `[[wiki-links]]` in the index) | quality |
| `index_dead` | Index entries pointing to deleted files | block |
| `orphans` | Pages with zero inbound links (checks both `[markdown](links)` and `[[wiki-links]]`) | quality |
| `stub_pages` | Pages under ~50 words | quality |
| `raw_missing` | Wiki pages citing `raw/` files that don't exist | block |
| `log_gaps` | Stretches of >30 days with no log entry, in an otherwise active wiki | suggestion |
| `slug_mismatch` | Filenames not conforming to `CLAUDE.md` slug convention | quality |
| `index_duplicates` | The same page listed more than once in the index (one page = one entry) | quality |
| `hot_health` | `hot.md` over the word threshold or accumulating dated `## [...]` changelog blocks | quality |
| `overtagged` | Pages with more frontmatter tags than the limit | quality |
| `single_use_tags` | Tags appearing on exactly one page (keywords, not classifiers) | suggestion |
| `wikilink_collisions` | `[[slugs]]` matching more than one file (silent ambiguity) | quality |
| `schema_version` | Wiki's `schema_version` stamp behind what the skill expects — points to `migrate_wiki.py` | suggestion |

The thresholds (50 words, 30 days, 700 hot words, 4 tags) are tunable via flags — see `--help`.

**Consciously ignored findings:** if the wiki's `CLAUDE.md` has a "Lint exceptions" section, findings on the files/slugs listed there are expected — report them but don't propose fixes. When the user repeatedly dismisses the same finding, propose adding it to that section (schema-evolve).

## What the lint script does not catch

Anything semantic. The LLM is responsible for:

- Stale claims
- Unflagged contradictions
- Missing pages on cross-cutting entities
- Schema drift between `CLAUDE.md` and actual practice
- Pages that exist but say nothing useful

These require reading the wiki. The lint script just gives you a starting point.

## Heuristics

- **Block bugs first, fix without asking.** Broken links and dead index entries are pure damage.
- **Don't auto-fix orphans.** An orphan page might genuinely be unused (delete) or a future-relevant page (link from somewhere). Ask.
- **Don't create suggested pages on autopilot.** The user might have reasons for not wanting them.
- **Suggest schema updates when patterns emerge.** If three lint passes in a row found the same kind of problem, the schema needs to evolve.

## Common mistakes

- **Treating the script's output as the whole job.** The script is the floor, not the ceiling. Layer in semantic checks.
- **Skipping user approval on substantive changes.** Autonomous edits to substantive content erodes trust. Block bugs only.
- **Logging the lint as if nothing happened.** The log entry should say what was found and what was fixed — that becomes useful audit trail later.
