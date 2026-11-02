# Architecture

The structural model the skill uses everywhere. Three layers, five files (index, log, hot + schema + README), a small set of conventions. Read this when designing a new wiki, debugging "where should this go?" questions, or evolving the schema.

## Three layers

### Layer 1 — `raw/`: the source corpus

Immutable. User-curated. The single source of truth.

What goes here:

- Articles (markdown via Obsidian Web Clipper, or plain HTML, or PDF prints)
- Papers (PDF)
- Transcripts (auto-generated from podcasts, meetings, video)
- Book chapters (markdown export, or PDF, or scanned + OCR'd)
- Screenshots and images (with the article they came from, or in `raw/assets/`)
- Data files (CSV, JSON) when they support a claim later
- The user's own journal entries, voice memo transcripts, raw notes

Conventions:

- One file per source. If a source is huge (a 600-page book), split by chapter at most.
- Filenames should sort usefully. A common pattern: `YYYY-MM-AUTHOR-short-title.ext` — e.g. `2026-04-pollan-eat-food.pdf`. The skill doesn't enforce this; document whatever convention the user picks in `CLAUDE.md`.
- The LLM **never modifies files in `raw/`**. If the source has a typo, leave it. If the markdown rendering is ugly, leave it. The LLM's job is to summarize and integrate elsewhere.

### Layer 2 — `wiki/`: the LLM-managed knowledge base

Owned by the LLM. The user reads it; the LLM writes it.

What goes here (default categories, customizable per wiki):

- **`wiki/sources/`** — one summary page per ingested source. Strong link back to the file in `raw/`. Captures the source's key claims, methodology, evidence quality, and how it relates to other sources already in the wiki.
- **`wiki/entities/`** — pages for people, organizations, products, places, events. Updated in-place as new sources mention them.
- **`wiki/concepts/`** — pages for ideas, frameworks, theories, terms-of-art. Often the most synthesized pages; pull from many sources.
- **`wiki/notes/`** — anything that doesn't yet fit a category. Promoted to a "real" category once it has enough material to warrant it.
- **`wiki/reports/`** — auto-generated dated reports from `lint_wiki.py` and (in the future) audit tooling. Filenames are slugs like `lint-2026-05-07.md`. The LLM does not author files here directly; scripts do. Same-day re-runs overwrite (idempotent daily). This folder is excluded from orphan/stub/index-drift checks during lint.

Plus three structural files at `wiki/` root:

- **`wiki/index.md`** — content catalog. Updated by `update_index.py` on every ingest.
- **`wiki/log.md`** — chronological log. Appended by `append_log.py` on every ingest, query, and lint.
- **`wiki/hot.md`** — ~500-word hot cache: vault state, latest ingests, open work items, tag inventory. **Rewritten entirely** after every ingest. First file a cross-project reader sees. Created from `assets/templates/hot.md.tmpl` by `init_wiki.py`.

Conventions:

- **One topic per page.** If a page is doing two jobs, split it.
- **Links over duplication.** If two pages need the same fact, write the fact once and link from the other page.
- **Cite back to sources.** Every claim should be traceable. Use a "Sources" section at the bottom listing the `wiki/sources/` pages this page draws from.
- **Frontmatter is optional but useful.** A page with `---\ntags: [book, philosophy]\nupdated: 2026-04-12\nsources: 4\n---` plays well with editors that read frontmatter (Dataview in Obsidian, etc.). Decide once, document in `CLAUDE.md`.

### Layer 3 — `CLAUDE.md`: the schema

Lives at the wiki root (one level above `wiki/`). Tells the LLM how this particular wiki is organized.

It is **not** generic — it is co-evolved with the user as conventions emerge. A research wiki's `CLAUDE.md` looks different from a fan-wiki `CLAUDE.md`. See `references/schema-design-guide.md` for what to include.

The single most important property: when a new convention works, it gets written into `CLAUDE.md` immediately. The next session starts informed.

## Two structural files: index.md and log.md

These are easy to confuse. They serve different purposes.

### `wiki/index.md` — content-oriented

A catalog. "What's in this wiki right now?"

Organized by category, each entry is a one-liner with a link:

```markdown
# Index

## Entities
- [Michael Pollan](entities/michael-pollan.md) — food writer, author of *Eat Food* (4 sources)
- [USDA](entities/usda.md) — federal agency setting US dietary guidelines (2 sources)

## Concepts
- [Nutritionism](concepts/nutritionism.md) — reductive ideology that food = nutrients (5 sources)
- [Western Diet](concepts/western-diet.md) — processed-food-heavy modern American eating pattern (3 sources)

## Sources
- [Pollan 2008 — In Defense of Food](sources/pollan-eat-food.md) — book, foundational
- [NYT 2024 — Ultra-processed food review](sources/nyt-2024-upf.md) — article, secondary
```

The index is the LLM's primary navigation tool when the wiki is large. When answering a query, **read the index first**, decide which pages to drill into, then read those.

Updated by `scripts/update_index.py` — call it after creating or substantially updating a page.

### `wiki/log.md` — chronological

An append-only record. "What happened, and when?"

Every entry starts with a consistent prefix so it's greppable:

```markdown
## [2026-04-02] ingest | In Defense of Food (Pollan, 2008)
Created sources/pollan-eat-food.md. Updated entities/michael-pollan.md (new). Created concepts/nutritionism.md. Updated entities/usda.md (new). Touched 4 wiki pages.

## [2026-04-03] query | What does Pollan think about supplements?
Read concepts/nutritionism.md and sources/pollan-eat-food.md. Answered with 3 quotes. Filed answer to notes/pollan-on-supplements.md.

## [2026-04-09] lint | Found 1 orphan page, 2 missing index entries
Fixed: linked notes/2026-04-shopping.md from concepts/western-diet.md. Added missing index entries.
```

Maintained by `scripts/append_log.py`. The user can quickly see "what did I do last week" and the LLM can use the log to ground its sense of recent activity.

`grep "^## \[" wiki/log.md | tail -20` is the canonical way to skim recent activity.

## How the layers interact during operations

### Ingest

1. User puts a file in `raw/`.
2. LLM reads the source.
3. LLM writes `wiki/sources/<slug>.md` summarizing it.
4. LLM identifies entities/concepts mentioned. For each one, either creates a new page in `wiki/entities/` or `wiki/concepts/`, or **updates the existing page** in place.
5. LLM cross-links: source-summary links to entity pages, entity pages link to source-summary, related concepts link to each other.
6. LLM updates `wiki/index.md` with new pages.
7. LLM appends one entry to `wiki/log.md` summarizing what was touched.
8. LLM **rewrites `wiki/hot.md`** entirely — updates vault state, moves new ingest to top of active knowledge, refreshes open work items and tag inventory.

### Query

1. User asks a question.
2. LLM reads `wiki/index.md` first to find candidate pages.
3. LLM reads candidate pages and (if needed) the linked source summaries.
4. LLM may drill into specific files in `raw/` for direct quotes.
5. LLM produces an answer with citations to wiki pages.
6. If the answer is substantial, LLM offers to **file it back** as a new page in `wiki/notes/` or `wiki/concepts/`.
7. LLM appends one entry to `wiki/log.md`.

### Lint

1. LLM runs `scripts/lint_wiki.py`.
2. LLM reviews the report and proposes fixes.
3. With user approval, LLM fixes (broken links, missing index entries, orphan promotions).
4. LLM appends one entry to `wiki/log.md`.

## Naming conventions

Slugs only — lowercase, hyphenated, no spaces. `michael-pollan.md`, not `Michael Pollan.md`. This keeps URLs/paths predictable and scripts simple.

For source files in `raw/`, the user picks the convention; the LLM follows it. The standard suggestion is `YYYY-MM-author-short-title.ext` but anything sortable works.

For wiki pages, the slug is the title in lowercase-with-hyphens. Document in `CLAUDE.md` if a different scheme is chosen (e.g. some users like `2026-04-12-some-note.md` for journal-style notes).
