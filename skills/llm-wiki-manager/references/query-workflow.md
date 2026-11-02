# Query Workflow

Use this when the user asks a question that depends on what's in the wiki. Examples: "what does my wiki say about X", "compare the two papers on Y", "based on what I've read, is Z plausible", "what did Pollan think about supplements".

The point of querying a wiki — versus asking a generic LLM — is that **the synthesis is already partly done**. Most pages have been written, cross-references already exist, contradictions are already flagged. Your job is to find the right pages, read them, and produce a focused answer.

## Goal

Answer the user's question using the wiki as the source of truth, citing wiki pages (and through them, raw sources). Where the wiki has gaps, name them. Where the answer is non-trivial, offer to file it back as a new page so future queries benefit.

## The full loop

### 1. Read `wiki/index.md` first

The index is the navigation aid. Don't grep blindly across `wiki/`. Read the index, identify candidate pages, then drill in. For most queries, two to five pages will be relevant.

**Hub navigation:** if the index marks a page with `★`, that page is the cluster's hub (MOC) — it lists every page in its cluster with one-line descriptions. When the question falls inside a theme that has a hub, the cheapest route is **short index → hub → page**: read the theme's section of the index, open the hub, and jump straight to the right page instead of scanning the whole index or grepping.

If the index is large (hundreds of entries) and skimming is slow, use a search approach:

```bash
grep -ri "<keyword>" wiki/ --include="*.md" -l
```

For larger wikis (~100+ sources), consider a proper search tool like [qmd](https://github.com/tobi/qmd). Document the choice in `CLAUDE.md`.

### 2. Read the candidate pages

Read them fully. Skim is not enough — the contradictions section, the "open questions" footer, the linked sources are often where the real answer hides.

If a page references a source summary or another concept page that seems load-bearing, follow the link.

### 3. Decide if the wiki has the answer

Three possibilities:

- **Wiki has it.** Pages cover the question well; synthesize from them.
- **Wiki has parts.** Some pages are relevant but the question requires connecting threads not yet connected. Synthesize and **flag this** — it's a candidate to file back as a new page.
- **Wiki has nothing.** The topic isn't in the wiki yet. Don't fabricate. Tell the user the wiki is silent on this, and either (a) suggest sources to add, (b) answer from general knowledge with a clear "this isn't from your wiki" disclaimer, or (c) both.

### 4. Synthesize the answer

Cite wiki pages, not raw sources, by default. Wiki pages are the user's curated synthesis; raw sources are below them. Use this style:

```markdown
Pollan's main objection to supplements is that they extend nutritionism — the idea that food is reducible to nutrients (see [Nutritionism](concepts/nutritionism.md)). He argues that isolating nutrients and packaging them in pills loses the synergistic effects of whole foods ([Pollan 2008](sources/pollan-eat-food.md)).

A counterpoint comes from [Smith 2019](sources/smith-2019-vitamin-d.md), who argues that vitamin D supplementation does have well-supported isolated benefits in deficient populations.
```

If the question deserves a structure (comparison, timeline, decision matrix), use one. Tables, lists, hierarchies. Don't force prose where structure is clearer.

### 5. Surface contradictions and gaps

If the wiki contains contradictions on the topic, name them. If there are open questions noted on the relevant pages, mention them. If the user's question hits a topic with thin coverage (one source only, dated source only), say so.

Honesty about thin coverage is more valuable than a confident synthesis from a thin base.

### 6. Offer to file the answer back

If the answer is non-trivial — a synthesis, a comparison, an analysis — offer to save it as a new wiki page:

> Want me to save this as `wiki/notes/pollan-on-supplements.md` so it shows up in future queries?

This is **the most underused part of the pattern**. Good answers should compound just like ingested sources do. Default to offering. Default to "yes, save it" unless the user declines.

If the user accepts:

- Pick a category — `notes/` is the default for synthesized answers; promote to `concepts/` or `entities/` if the page becomes substantial.
- Write the page using the same structure principles as ingest-produced pages: clear title, source citations, links to other relevant pages.
- Update `wiki/index.md`.
- Append to `wiki/log.md` as a `query` action.

### 7. Append to log

Even if the answer wasn't filed back. Every query gets a log entry:

```bash
python scripts/append_log.py --path . --action query \
  --title "What did Pollan think about supplements?" \
  --details "Read concepts/nutritionism.md and sources/pollan-eat-food.md. Filed answer to notes/pollan-on-supplements.md."
```

Logging queries serves two purposes: lets the user see "what have I been asking about" later, and lets the LLM in future sessions notice patterns ("the user has asked about X three times — maybe X deserves its own page").

## Output formats

A query answer is a flexible artifact. Common shapes:

- **Plain markdown response in chat.** Default for short questions.
- **A markdown page filed to `wiki/notes/`.** When the answer is substantial enough to be worth saving.
- **A comparison table.** When the question is "X vs Y".
- **A timeline.** When the question has a temporal dimension ("how did the user's thinking evolve").
- **A chart** (matplotlib or similar). For numeric data; render to image, save to `wiki/notes/assets/`, link from a notes page.
- **A slide deck** (Marp, if the wiki uses it). For presentation-shaped queries.

Pick the format that fits the question. Long prose in chat is rarely the best answer.

## When the wiki is silent

If after reading the index and candidate pages the wiki genuinely has nothing on the topic:

1. **Say so plainly.** "Your wiki has no pages on X."
2. **Offer paths forward:**
   - Suggest a couple of sources that would fill the gap (with web search if available).
   - Answer from general knowledge with a clear "not from your wiki" disclaimer.
   - Ask if they have a source ready to ingest first.
3. **Log it.** A query that hits empty space is itself useful information — it surfaces a gap. Log it as `query | <question> | wiki silent`.

## Heuristics

- **Read the index first.** Always. Even when you "know" where the answer is.
- **Cite wiki pages, not raw sources.** The wiki is the curated layer; that's the point.
- **Offer to file back.** Most users won't think to ask, but most users want it.
- **Name your gaps.** A confident answer from thin coverage is worse than an honest "the wiki is thin here, want me to find more sources?".
- **Don't re-ingest during a query.** If a query reveals that a relevant source exists in `raw/` but was never summarized into `wiki/`, note it and offer to ingest it after answering. Don't try to do both at once.

## Common mistakes

- **Skipping the index.** Searching with grep when a 30-second read of the index would have shown the answer page.
- **Overciting raw sources.** A query answer should sit on top of the wiki layer, not bypass it.
- **Not offering to file back.** Letting the synthesis disappear into chat history. The whole point is compounding.
- **Synthesizing a confident answer from one thin page.** State the limitation; don't paper over it.
- **Forgetting the log entry.** Easy to skip on a "quick question". Don't.
