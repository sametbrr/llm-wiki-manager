# Teaching Mode

Use this when the user is new to the LLM-managed wiki pattern and asks how it works, or wants a walkthrough before committing to setting one up. Common phrasings: "explain this idea", "how does this differ from X", "is this for me", "walk me through it".

This mode is **not** for someone who already understands the pattern and just wants to get started — that's bootstrap. Teaching mode is the explanation; bootstrap is the action.

## Goal

Help the user form an accurate mental model of the pattern in 5-10 minutes, so they can decide whether to adopt it and steer it well once they do. Avoid jargon-dumping. Use concrete examples.

## What to convey, in order

### 1. The contrast with RAG (one minute)

Most people who've used LLMs with documents have used something RAG-like — upload a PDF to ChatGPT, ask questions. That model rediscovers everything on every query. There's no accumulation.

This pattern is different: a **persistent wiki** that the LLM writes and maintains as new sources arrive. Cross-references already exist when you query. Contradictions are already flagged. Synthesis is already done.

A useful one-liner: *"RAG retrieves at query time. This pattern compiles knowledge once and keeps it current."*

### 2. The three layers (two minutes)

Sketch them in plain words:

- **`raw/`** — the user's library. PDFs, articles, notes. Curated by the human, never edited by the LLM.
- **`wiki/`** — the LLM's knowledge base. Markdown pages — one per source, plus pages for the people, ideas, and concepts that span sources. The LLM writes all of it.
- **`CLAUDE.md`** — the instruction sheet for the LLM. How this particular wiki is organized. Co-evolved over time as conventions emerge.

Use a concrete example: "If you ingested *In Defense of Food* by Michael Pollan, you'd end up with a page summarizing the book in `wiki/sources/`, a page on Pollan in `wiki/entities/`, a page on the concept of *nutritionism* in `wiki/concepts/`, entries for all three in `wiki/index.md`, a log entry in `wiki/log.md`, and a rewritten `wiki/hot.md` with a summary of the ingest."

### 3. The division of labor (one minute)

The user does:

- Decides what to read
- Drops sources in `raw/`
- Asks questions
- Steers when conventions evolve

The LLM does:

- Reads sources end-to-end
- Writes summaries, entity pages, concept pages
- Updates cross-references
- Maintains the index and the log
- Flags contradictions
- Surfaces gaps

The user almost never writes wiki pages by hand.

### 4. The compounding effect (two minutes)

This is the part that's hard to convey without showing it. Try a concrete walkthrough:

> Imagine you've ingested 10 sources on a topic. Now you ingest the 11th. Three things happen that wouldn't happen with RAG:
>
> 1. The LLM **reads the new source against the existing wiki**. It notices: "this contradicts what *Source 4* said about X" and flags both on the relevant page.
> 2. It **updates pages that already existed**. The page on Person Y, who is mentioned in Sources 2, 5, 7, and now 11, gains a new bullet under their views. You don't lose the cumulative picture.
> 3. The new source's summary **links into and out of existing pages**. The connective tissue grows.
>
> Three months from now, when you ask "what does my wiki say about Y", the answer reflects all 11 sources. You don't have to re-derive that — it's built into the pages.

### 5. When this fits (one minute)

Good fits:

- Going deep on a topic over weeks or months (research, dissertation, due diligence)
- Reading a long book and wanting a companion wiki by the end
- Personal: tracking goals, health, psychology over time
- Team: an internal wiki maintained by an LLM, fed by Slack, transcripts, project docs
- Hobby deep-dives, course notes, trip planning

Bad fits:

- One-off questions
- Corpora you'll query once and never add to
- Highly transactional content (database records)
- When the user doesn't actually want to curate — the pattern dies without that input

### 6. What setup looks like (30 seconds)

End with: "If you want to try it, the setup is one command and a sentence about what the wiki is for. We'd run `init_wiki.py`, drop your first source in `raw/`, and ingest it together. Want to do that?"

If yes → switch to bootstrap mode (`references/bootstrap-workflow.md`).

## What to avoid

- **Avoid implementation details up front.** Don't talk about index.md or log.md mechanics until they ask. Concept first, mechanics later.
- **Avoid the word "RAG"** if the user isn't already technical. Use "the standard way of using ChatGPT with documents" instead.
- **Avoid claims of magic.** This is just markdown files, scripts, and an LLM. The compounding is real but it's mechanical, not mystical.
- **Avoid pretending the user has to know everything.** They can learn the conventions as they go. The skill steers.
- **Avoid over-explaining the file structure.** A casual user doesn't need to know the difference between `entities/` and `concepts/` until they're ingesting.

## When the user has questions

Common ones:

- *"How is this different from Notion / Obsidian / Roam?"* — Those are editors. This pattern works in any editor — it's about the workflow, not the tool. The LLM is what makes the maintenance affordable; that's the missing piece in tools where humans had to maintain everything themselves.
- *"How big can it get?"* — Hundreds of pages with the index alone. Thousands with proper search (qmd or similar). The pattern stays sane because every page has a purpose and the LLM keeps connections live.
- *"What if the LLM makes a mistake?"* — It's a git repo. Roll back. The user reviewing summaries catches most issues; the lint pass catches mechanical ones.
- *"Does my data leave my machine?"* — Depends on what LLM is used. Claude Code runs the LLM remotely but the files are local. If that's a concern, suggest local LLMs as an option for sensitive material.
- *"Can multiple people use one wiki?"* — Yes. Git handles the collaboration. The LLM can be told the wiki is shared and review changes from other users on each session start.
- *"What if I already have a pile of markdown notes?"* — Treat each existing file as an ingested source and run them through the ingest workflow. Migration, not bootstrap.

## Heuristics

- **Concrete over abstract.** Always reach for an example.
- **Stop talking when they want to start doing.** If the user shows readiness, switch to bootstrap.
- **Don't oversell.** The pattern works for the right use cases and is wrong for others. Be honest about the bad fits.
- **Their attention is finite.** A 10-minute teaching session that lands beats a 45-minute one that overwhelms.
