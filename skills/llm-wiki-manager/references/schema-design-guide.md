# Schema Design Guide

How to write the wiki's `CLAUDE.md` and how to evolve it. Read this when bootstrapping (you'll write the initial file from a template) or when conventions need updating mid-flight.

The schema file is the single most important configuration in the system. It's what makes future LLM sessions disciplined wiki maintainers rather than generic chatbots that touched some markdown files.

## Where it lives

At the wiki root, one level above `wiki/`:

```
my-wiki/
├── CLAUDE.md        ← here
├── raw/
└── wiki/
```

Claude Code reads `CLAUDE.md` on session start; Codex and most other agents read `AGENTS.md`. The contents are identical, only the filename differs. A wiki used from both keeps the schema in `AGENTS.md` and a one-line `CLAUDE.md` containing `@AGENTS.md`. `init_wiki.py` sets this up for new wikis, and every script auto-detects which file holds the schema.

## What goes in it

The schema declares conventions. Not philosophy, not tutorials — terse declarations that an LLM can follow on session start.

A minimum-viable schema covers six areas:

### 1. The wiki's purpose

One paragraph. What is this wiki for? Why does it exist? What's the user actually trying to accomplish?

```markdown
## Purpose
A research wiki for my dissertation on the cultural history of nutritionism (2026-2027). Sources are books, papers, and journalism on food science, public health policy, and food industry history. The output is the dissertation itself, drawing on this synthesis.
```

This grounds every decision the LLM makes about what's relevant.

### 2. The three layers

Restate the convention. Don't assume future Claude sessions know the pattern just from the directory structure.

```markdown
## Layers
- `raw/` — immutable sources. User-curated. Never modify.
- `wiki/` — LLM-managed pages. Owned by Claude. User reads, doesn't write.
- This file (`CLAUDE.md`) — the schema. Evolved over time when conventions change.
```

### 3. Categories

What's in `wiki/` and what kinds of pages go in each subfolder. The defaults are `sources/`, `entities/`, `concepts/`, `notes/`. Many wikis end up customizing — name yours specifically.

```markdown
## Categories
- `sources/` — one summary per ingested source
- `entities/` — people, organizations, places, products
- `concepts/` — ideas, theories, terms-of-art, frameworks
- `papers/` — academic papers, with extended structure (abstract, methods, findings, critique)
- `findings/` — synthesized findings across multiple papers — pages like "what we know about X"
- `open-questions/` — questions raised but not yet answered, parked for further investigation
```

### 4. Naming and linking conventions

Specific. Decisions removed from the LLM's discretion in future sessions are decisions made consistently across pages.

```markdown
## Conventions
- Slugs are lowercase-with-hyphens. `michael-pollan.md`, not `Michael Pollan.md`.
- Source filenames in `raw/` follow `YYYY-MM-author-short-title.ext` — e.g. `2026-04-pollan-eat-food.pdf`.
- Wiki links are standard markdown: `[Title](../entities/title.md)`. Not `[[wikilinks]]`.
- Frontmatter is required on every wiki page: `tags`, `updated`, `sources` (count). See `wiki/notes/_template.md` for the canonical example.
```

### 5. Page structure

Per category, what sections does a page have? This is what makes the wiki feel coherent over hundreds of pages.

```markdown
## Page structure

### Source-summary pages (`wiki/sources/<slug>.md`)
Sections in order:
1. Frontmatter (type, date, length, status)
2. One-line summary
3. Key claims (bulleted, each with page/timestamp citation)
4. Methodology / evidence quality
5. How it relates to the wiki (explicit links to entity/concept pages)
6. Notable quotes (sparingly, with citation)
7. Open questions

### Entity pages (`wiki/entities/<slug>.md`)
Sections in order:
1. Frontmatter
2. One-line description
3. Background
4. Key positions / contributions / events (with source citations)
5. Disputes (when sources disagree about this entity)
6. Sources (list of source-summary pages cited)

### Concept pages (`wiki/concepts/<slug>.md`)
Sections in order:
1. Frontmatter
2. Definition (in one or two sentences)
3. Origin
4. Key claims
5. Disputes
6. Related concepts (links)
7. Sources
```

### 6. Workflow notes

Anything specific about how this wiki gets used. Per-wiki preferences for ingest aggressiveness, query output format, lint cadence.

```markdown
## Workflow notes
- Ingest mode: discuss before writing — give a 4-line summary of plan and wait for confirmation. Skip the discussion only when I explicitly say "fast ingest".
- Query answers default to filed-back as `wiki/findings/` pages when they synthesize across 3+ sources. Otherwise just answer in chat.
- Lint cadence: every ~10 ingests, prompt me to run a pass.
- An entity earns its own page once mentioned in 2+ sources. Until then it lives in source summaries.
```

## Hub pages (MOC)

A hub is **not a folder — it's a normal wiki page** that serves as a cluster's entry point (Obsidian calls this a Map of Content). Rules to write into the schema:

- A topic cluster with **3+ pages** elects its most encompassing page as the hub.
- The hub carries a `## Pages in this cluster` section: one line per member page + short description.
- Mark hubs with `★` in the index. Query navigation becomes **short index → hub → page** — far cheaper than scanning the whole index.
- Fewer than 3 pages = no hub yet. Promote when the cluster grows; if a theme later justifies a real folder (~10+ pages), the tag-promotion rule takes over.

## Tag policy

Tags are classifiers, not keywords. Without a policy they inflate fast (a real vault hit ~6 tags/page with mostly single-use tags). Write into the schema:

- **Max 4 tags per page.** A tag must apply to **2+ pages** to enter frontmatter — single-use keywords belong in the page body.
- **Canonical tag list lives in the wiki's `CLAUDE.md`** (not in hot.md). New tag = conscious decision: add to the list first, then use.
- **Merge synonyms** (`setup`/`kurulum`, `api`/`api-reference`) — `lint_wiki.py` surfaces single-use tags and over-tagged pages as findings.

## How the schema evolves

The schema is **not written once and frozen**. It evolves as the wiki grows and conventions emerge.

Triggers to update `CLAUDE.md`:

- **Convention drift detected during lint.** "Three pages now use `## Findings` and four use `## Key findings`. Pick one and write it down."
- **A new pattern works well.** "We started doing `> [!warning] Sources disagree` callouts for contradictions. Should we make that the standard? If yes, write it in."
- **A new category emerges.** "We've created six pages that don't fit existing categories — they're all reading lists. Promote `wiki/reading-lists/` to a real category? If yes, add it."
- **The wiki's purpose shifts.** Maybe the dissertation became a book. Update the purpose paragraph.

Don't make the user do this manually. When you notice a convention emerging, propose the schema update inline:

> I've noticed that the last four entity pages all have a "Notable mentions" section. Want me to add that as a standard section in `CLAUDE.md` so future entity pages include it consistently?

## What not to put in CLAUDE.md

- **The pattern's philosophy.** That's in the skill's `philosophy.md`, not the wiki's schema. The wiki's schema is for *this wiki's* specifics.
- **Exhaustive examples.** A schema file is reference material, not a tutorial. Link out to a sample page instead of inlining one.
- **Personal information beyond what's needed.** "I'm working on a dissertation" — fine. Personal details unrelated to wiki operation — leave them out.
- **Things that change frequently.** If something needs updating every week, it's status, not schema. Status goes in `wiki/log.md` or a dedicated `wiki/status.md` page.

## Length

The schema should be short. A page or two. If it's growing toward five pages, something is overcomplicated.

A common failure: turning the schema into a kitchen sink of every preference the user has ever expressed. That dilutes the load-bearing rules. Keep the schema to what genuinely affects how the LLM operates the wiki.

## Starter template

`assets/templates/wiki-CLAUDE.md.tmpl` is the file `init_wiki.py` writes on bootstrap. It contains:

- A purpose placeholder (filled from the bootstrap conversation)
- The standard layers
- Structural files: `wiki/index.md`, `wiki/log.md`, `wiki/hot.md` (with rewrite-on-ingest rule)
- Default categories (sources, entities, concepts, notes, reports)
- Default conventions (lowercase-hyphenated slugs, standard markdown links, optional frontmatter)
- A minimal default page structure for each category
- A "Workflow notes" section, mostly empty, for the user to populate

Read the template directly to see the format. Adapt freely — it's a starting point.

## Common mistakes

- **Skipping the schema entirely.** "It's just markdown, the LLM will figure it out." It will, inconsistently, every session. Write the schema.
- **Schema-by-committee.** Asking the user 30 questions up front. The pattern is "default first, evolve as you go". Don't pre-design the perfect schema.
- **Schema drift.** Writing a schema and then ignoring it. If three sessions in a row violate the same rule, either the rule is wrong or the LLM isn't reading the schema. Fix one or the other.
- **Burying load-bearing rules.** A "this is how Disputes sections work" rule needs to be visible at the top, not on page two.
