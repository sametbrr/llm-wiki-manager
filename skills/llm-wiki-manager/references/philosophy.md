# Philosophy

Read this when the user asks why this pattern exists, when teaching a newcomer, or when a workflow decision needs grounding. Short on purpose.

## The problem with RAG

The default way of using LLMs with documents looks like RAG: upload a corpus, the LLM retrieves chunks at query time, generates an answer. This works, but the LLM rediscovers knowledge from scratch on every question. There is no accumulation. Ask a subtle question requiring synthesis across five documents, and the LLM has to find and piece together the relevant fragments every time. Nothing is built up. NotebookLM, ChatGPT file uploads, and most RAG systems work this way.

## The wiki alternative

This pattern keeps a **persistent, compounding artifact** between the user and the raw sources: a structured, interlinked collection of markdown files (the wiki). When a new source arrives, the LLM doesn't just index it — it reads it, extracts what matters, and integrates it into the existing wiki. Entity pages get updated. Topic summaries get revised. Contradictions get flagged. The synthesis evolves. The knowledge is compiled once and then *kept current*, not re-derived on every query.

By the time the user asks a question, most of the work is already done:

- The cross-references already exist
- The contradictions are already surfaced
- The synthesis already reflects everything that has been read

Querying becomes more like reading a well-maintained encyclopedia than running a fresh search.

## Why the LLM is the right maintainer

The tedious part of any knowledge base is not the reading or the thinking — it's the bookkeeping. Updating cross-references when a new fact arrives. Keeping summaries current. Noting when new data contradicts old claims. Maintaining consistency across dozens of pages.

Humans abandon wikis because the maintenance burden grows faster than the value. The LLM doesn't get bored, doesn't forget to update a cross-reference, and can touch fifteen files in one pass. The cost of maintenance approaches zero, so the wiki stays maintained.

## Division of labor

| The user does | The LLM does |
|---|---|
| Curates sources (decides what to read) | Reads sources end-to-end |
| Asks questions, directs the analysis | Writes summaries, entity pages, concept pages |
| Decides what matters | Cross-references aggressively |
| Steers when conventions evolve | Updates the index and the log |
| Reviews the wiki, follows links | Flags contradictions, surfaces gaps |
| Owns `raw/` | Owns `wiki/` |

The user almost never writes wiki pages by hand. If they want to, fine — but the skill never asks them to.

## The Memex connection

Vannevar Bush's 1945 essay "As We May Think" described the Memex: a personal, curated knowledge store with associative trails between documents. A private, actively maintained second brain where the connections between documents were as valuable as the documents themselves.

The web went a different direction — public, search-driven, ad-funded, transient. Bush's original vision is closer to this pattern than to anything the web became. The piece Bush couldn't solve was who does the maintenance. That's the LLM's job now.

## When this pattern is the right tool

Good fit:

- A topic the user is going deep on over weeks or months (research project, dissertation, due diligence)
- Reading a long book and wanting a companion wiki by the end (characters, themes, plot threads)
- Tracking personal goals, health, psychology over time across journals, articles, and notes
- A team's internal knowledge base fed by Slack, transcripts, project docs, customer calls
- Hobby deep-dives, course notes, trip planning, competitive analysis

Bad fit:

- One-off questions ("what's the GDP of Japan?") — just ask the LLM
- A corpus you'll only query once and never add to — RAG is fine
- Highly transactional content (database records, ticket queues) — use a real DB
- When the user genuinely doesn't want to curate sources — the pattern dies without that input

## The single most important principle

The LLM does the bookkeeping. That is the entire value proposition. Skipping the bookkeeping because "the user didn't ask" defeats the pattern. Every ingest updates the index and the log. Every query that produces a useful synthesis can be filed back. Every lint pass tightens the connective tissue. The compounding is real because the maintenance is automatic.
