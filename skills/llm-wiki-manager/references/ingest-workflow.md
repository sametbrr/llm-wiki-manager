# Ingest Workflow

The most-used mode. Use this when the user drops a new file in `raw/`, pastes a URL or quote, attaches a PDF, or says something like "I just read X, let's add it" or "file this".

This is where the wiki actually compounds. Done well, every ingest leaves the wiki noticeably richer. Done lazily — just a flat summary, no cross-references — and the wiki is just RAG with extra steps.

## Goal

Read the source carefully, integrate its information into the existing wiki at every relevant point, and leave a clear trail (source-summary page, updated entity/concept pages, index entries, log entry). The user should be able to come back in three months and see exactly what was added and why.

## The full loop

### 1. Locate and read the source

If the user dropped a file: confirm the path under `raw/`. If they pasted a URL: download it (use whatever fetch tool is available), save the markdown/HTML/PDF to `raw/` with a sortable filename (`YYYY-MM-author-short-title.ext`), then read it. If they pasted text directly: write it to `raw/` first — never ingest something that doesn't have a stable file to cite back to.

Read the source end-to-end before writing anything. For long sources (books, long papers), read in passes:

1. First pass — skim for structure, key claims, named entities, key concepts.
2. Second pass — re-read the parts that matter for the wiki.

For PDFs with images that matter (charts, diagrams), view the relevant pages as images. For audio/video transcripts, read the transcript and note timestamps for the standout moments.

### 2. Survey the existing wiki

Before writing, **read `wiki/index.md`** to understand what's already there. Then read pages that look related — entities you recognize, concepts that overlap. This is what makes the ingest integrative rather than additive.

A common failure: writing a source summary that mentions "Pollan" without checking that `wiki/entities/michael-pollan.md` already exists. The integration disappears. **Always check first.**

### 3. Discuss with the user (briefly)

Before producing pages, give a 4-6 line summary of what you saw and what you plan to do:

> Read *In Defense of Food*. Key takeaways: (1) "Eat food, not too much, mostly plants" — Pollan's full thesis; (2) coins **nutritionism** as critique of reductive nutrition science; (3) heavy critique of the **USDA** food pyramid era. Existing pages I'd update: `entities/michael-pollan.md` (extend), `concepts/nutritionism.md` (new). Want me to proceed, or anything to emphasize / leave out?

This 30-second checkpoint catches misdirected ingests early. The user might say "skip the USDA stuff, that's not relevant to this wiki" or "actually focus on the supplements chapter". Cheap to ask, expensive to redo.

If the user has set up the wiki for batch-ingest with low supervision, skip this step. Note it in `CLAUDE.md` if so.

### 4. Write the source summary

Create `wiki/sources/<slug>.md` using `assets/templates/source-summary.md.tmpl`. Standard sections:

- **Frontmatter** (optional): type, date, length, status (read/skim/excerpt)
- **One-line summary** at the top
- **Key claims** as a bulleted list, each with a source reference (page number, timestamp, paragraph)
- **Methodology / evidence quality** — useful especially for papers, studies, journalism
- **How this relates to the wiki** — explicit pointers to entity/concept pages this source touches
- **Notable quotes** — sparingly, with citation
- **Open questions** — things this source raised that aren't answered

The summary is **not** a substitute for the source. Don't try to compress everything; capture what's load-bearing for future synthesis.

### 5. Update entity and concept pages

For each entity or concept the source touches significantly:

- **If the page exists:** read it, then update in place. Add a new bullet under the relevant section, extend an existing claim, or add a "Disputes" subsection if the source contradicts something already there. Use the source-summary page as a cite.
- **If the page doesn't exist** but the entity/concept is substantial enough to warrant one: create it from `assets/templates/entity-page.md.tmpl` or `concept-page.md.tmpl`. Don't create pages for entities that are only mentioned in passing — those can stay in the source summary.

A rule of thumb: an entity or concept earns a page once it's mentioned in **two or more sources**, or it's central to the user's purpose. Until then, keep it in source summaries.

### 6. Cross-link

Link from each updated page back to the source summary, and from the source summary to the entity/concept pages. The connectivity is the value.

Standard markdown link style:

```markdown
See [Nutritionism](../concepts/nutritionism.md) for Pollan's coined term.
This contradicts [USDA's 1992 pyramid](../entities/usda.md#1992-food-pyramid).
```

If the wiki is set up for Obsidian-style `[[wikilinks]]`, use those — check `CLAUDE.md`.

**Maintain the `## Related` footer.** Every page ends with a `## Related` section: 2–5 links, each with a one-line *why* (`- [Page](path.md) — same program, parallel track`). When this ingest creates a meaningful connection between two pages, add it to both pages' Related footers. Don't mirror the links into a `related:` frontmatter field — the footer is the single source of truth.

**Hub bookkeeping.** If a topic cluster reaches 3+ pages with this ingest, elect its most encompassing page as the hub: add a `## Pages in this cluster` section there, and mark it with `★` in the index (see `CLAUDE.md` hub rules).

### 7. Flag contradictions

If the new source contradicts a claim on an existing page, **don't overwrite**. Add the new claim alongside the old one, mark both with their source, and note the conflict:

```markdown
## Effect of saturated fat on heart disease

Two sources disagree:

- [Keys 1980](../sources/keys-1980.md): saturated fat strongly correlates with heart disease incidence (r=0.87 across seven countries).
- [Teicholz 2014](../sources/teicholz-big-fat-surprise.md): the seven-country selection cherry-picked outcomes; broader sample shows weak correlation.

> [!warning] Sources disagree
> Open question for further investigation.
```

This is the "contradictions are flagged" part of the value proposition. Silent overwrites destroy that.

**When the contradiction spans multiple pages**, the local Disputes pattern is not enough. If you notice that the new source's claim invalidates content on **3 or more existing pages** (entities, other concepts, notes), stop and switch to the **update workflow** (`references/update-workflow.md`). It runs a semantic sweep across the wiki, shows diffs page-by-page, and propagates the correction with one coherent log entry. Use it when the same idea is paraphrased across the wiki and patching one page leaves the others stale.

### 8. Update the index

Run `scripts/update_index.py` for each new page and for any page whose summary changed substantially:

```bash
python scripts/update_index.py --category concepts \
  --title "Nutritionism" \
  --page-path "wiki/concepts/nutritionism.md" \
  --summary "Reductive ideology that food = nutrients (5 sources)"
```

The script is idempotent on (category, title) — re-running updates the existing entry rather than duplicating.

### 9. Append to log

One entry. Use `scripts/append_log.py`:

```bash
python scripts/append_log.py --action ingest \
  --title "In Defense of Food (Pollan, 2008)" \
  --details "Created sources/pollan-eat-food.md. New: concepts/nutritionism.md. Updated: entities/michael-pollan.md, entities/usda.md. Touched 4 pages."
```

The log entry should be specific enough that "what did I do last week" returns useful answers later.

### 10. Rewrite hot.md

If the wiki has a `hot.md` (at `wiki/hot.md` or at the wiki root), **rewrite it entirely** — do not append. The file has exactly five sections (see `assets/templates/hot.md.tmpl`), ~500 words total:

- **State:** one paragraph — page count, layout, active policies.
- **Last ingest:** ONLY the most recent 1-2 operations; everything older lives in log.md. Never accumulate dated `## [...]` blocks here — those are log entries.
- **Active themes:** one line per theme + link to its hub (`★`) page.
- **Open items:** add anything surfaced during ingest (a gap in coverage, an open question, a follow-up source worth finding); remove resolved ones.
- **Conventions:** 3-4 lines a cross-project reader must know; details live in CLAUDE.md.

If this ingest introduced a new tag, add it to the **canonical tag list in `CLAUDE.md`** (if it fits the tag policy) — the tag inventory does NOT live in hot.md.

Rewriting (not appending) is important: `hot.md` is a cache, not a log. Its job is to give a future session — or a cross-project reader — an instant orientation. An append-only `hot.md` becomes too long to serve that purpose; `lint_wiki.py` flags it when it bloats.

### 11. Brief recap to the user

End with a short summary: pages created, pages updated, anything notable (a strong contradiction with existing material, an open question worth investigating, a missing source that would help). Three to six lines.

If the user is engaged and curious, offer follow-ups: "This source gestures at [some related thing] but doesn't develop it. Want to find a source that does?"

## Heuristics

- **Five to fifteen pages touched is normal** for a substantive source. Two pages touched usually means the integration was lazy. Twenty-five pages touched usually means the source got over-integrated and trivial mentions got their own pages.
- **Source summary first, then ripple outward.** Write the source summary, then update pages it points to, then update the index, then log. Don't bounce around.
- **Quote sparingly.** A wiki page is a synthesis, not a copy. Direct quotes are reserved for moments where the exact wording matters.
- **Match the schema.** Read `CLAUDE.md` if there's any doubt about page structure, frontmatter, or category names. The schema is the authority.

## Common mistakes

- **Skipping the survey step.** Writing as if the wiki is empty when it isn't. Cross-references die quietly.
- **One giant page per source.** No, the source summary is one page; the entities and concepts spread across many pages. The summary points outward, not inward.
- **Creating premature entity pages.** A name mentioned in passing once is not an entity yet. Wait until it earns the page.
- **Forgetting the index or the log.** Both are easy to skip and both quietly degrade the wiki. The scripts are short; just run them.
- **Silent contradiction handling.** Overwriting old claims with new ones. Flag instead.
- **Duplicating content across pages.** If a fact is needed in two pages, write it once and link.
