# Bootstrap Workflow

Use this when the user wants to start a new wiki. The user said something like "set up a wiki", "init a knowledge base", "I want to start a research notebook", or dropped a single source and asked Claude to "build a wiki around this". Working directory has no `wiki/` yet.

## Goal

Get the user from zero to a working wiki in under five minutes, with `CLAUDE.md` written, `init_wiki.py` run, and (if they have a source ready) one source ingested. **Don't interrogate them up front** — bootstrap quickly, let conventions emerge.

## The fast path (default)

1. **Confirm the wiki root.** Default is the current working directory. Confirm with one line: "Bootstrap a wiki here? (`pwd`)" — proceed unless they say no.
2. **Ask the topic in one sentence.** "What's this wiki about?" One sentence is enough. Don't ask about taxonomy yet — that emerges from the first few sources.
3. **Run `init_wiki.py`.** This scaffolds the layout and writes a starter `CLAUDE.md`:

   ```bash
   python scripts/init_wiki.py --path . --name "<wiki name>" --topic "<one-sentence topic>"
   ```

   The script is idempotent: if `wiki/` already exists, it merges rather than overwriting. Safe to re-run.
4. **Show the tree.** `tree -L 2` or equivalent. Two folders, three files, ready to go.
5. **Offer the next step.** "If you have a first source, drop it in `raw/` and I'll ingest it. Otherwise, the wiki is ready and you can add sources whenever."
6. **Append to log.**
   ```bash
   python scripts/append_log.py --action bootstrap --title "Initial wiki created" --details "Topic: <topic>"
   ```

That's it for the fast path. Total interaction: one confirmation, one sentence, two commands, one log entry.

## What `init_wiki.py` produces

```
.
├── CLAUDE.md              # Wiki schema — see below
├── README.md              # Brief human-facing overview
├── raw/
│   └── .gitkeep
└── wiki/
    ├── index.md           # Empty, with category headers
    ├── log.md             # Empty, with one bootstrap entry
    ├── hot.md             # Hot cache — rewrite after every ingest
    ├── sources/
    │   └── .gitkeep
    ├── entities/
    │   └── .gitkeep
    ├── concepts/
    │   └── .gitkeep
    ├── notes/
    │   └── .gitkeep
    └── reports/
        └── .gitkeep
```

The starter `CLAUDE.md` (from `assets/templates/wiki-CLAUDE.md.tmpl`) declares the conventions a fresh wiki uses:

- Three layers (raw / wiki / schema)
- Structural files: `wiki/index.md`, `wiki/log.md`, `wiki/hot.md`
- Default categories (sources, entities, concepts, notes, reports)
- Wiki-link style: standard markdown `[Title](path.md)`
- Slug naming: lowercase-with-hyphens
- Source filename suggestion: `YYYY-MM-author-short-title.ext`
- Page frontmatter: optional, off by default
- Bookkeeping discipline: every operation logs, indexes, and rewrites hot.md

These are starting defaults. The user changes them as conventions evolve.

## When the user wants more interactivity

Some users want a brief setup conversation. If they signal that — "let's talk through the structure first", or they're new to the pattern — slow down and walk through:

1. **Topic and scope.** What's this wiki for? What kinds of sources will go in it? How long is the project (a week, a month, a year)?
2. **Categories.** The defaults (sources / entities / concepts / notes) are generic. Some wikis benefit from custom categories — e.g. a research wiki might want `papers / methods / findings / open-questions`. If the user has a clear picture, reflect it in `CLAUDE.md` before running `init_wiki.py` (or edit `CLAUDE.md` after).
3. **Naming.** Default is lowercase-with-hyphens for everything. If they want something else (like Obsidian-style `[[Wiki Links]]` with capitalized titles), settle it now and document.
4. **Git.** Should the wiki be a git repo? Default yes — `git init` happens during bootstrap. Lets them version-control summaries and roll back bad LLM edits.

Don't push for this conversation if the user hasn't asked for it. The pattern works better when conventions emerge from real sources rather than being designed in the abstract.

## When the user already has sources ready

Common case: the user drops three PDFs and a markdown file in `raw/` (or pastes URLs) and says "build a wiki for these".

1. Run the fast bootstrap.
2. Switch to the **ingest workflow** (`references/ingest-workflow.md`) and process them one by one.
3. After 2-3 sources, the natural taxonomy starts to show. **Update `CLAUDE.md`** with any conventions that have emerged (e.g. "every paper gets a `wiki/papers/` page with these sections…").

## When `init_wiki.py` finds an existing wiki

Idempotent: on an existing wiki (one with `.md` files already under `wiki/`), it only adds `wiki/reports/` if missing — it will **not** create `sources/`, `entities/`, `concepts/`, or `notes/` directories, and leaves all existing files untouched. This preserves flat or custom wiki structures. Re-running after manual reorganization is always safe.

If the user is moving an existing pile of markdown into the pattern, that's not "bootstrap" — that's migration. Treat each existing file like an ingested source and run them through the ingest workflow.

## What "done" looks like

- `CLAUDE.md` exists at the wiki root, customized with the topic and any agreed conventions.
- `wiki/index.md` exists with category headers, possibly empty.
- `wiki/log.md` has at least one entry: the bootstrap.
- `wiki/hot.md` exists — will be rewritten after the first ingest.
- The user knows where to drop sources (`raw/`) and how to ask for an ingest.
- The user understands the LLM owns `wiki/`, never `raw/`.

If the bootstrap produced a wiki but the user is still confused about how to use it, flip to **teaching mode** (`references/teaching-mode.md`) for a brief walkthrough.

## Common mistakes

- **Designing the taxonomy up front.** The defaults work. Customize when real pages start straining them, not before.
- **Creating empty entity/concept pages "in case".** Pages should be created when a source motivates them. An empty page with three sections and no real content is a maintenance liability.
- **Forgetting `CLAUDE.md`.** If the bootstrap skips writing the schema file, the next session has no idea what's going on. Always write it. Always use the template.
- **Mixing raw and wiki content in one folder.** The three-layer separation is load-bearing. Don't shortcut it.
