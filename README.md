[![Release](https://img.shields.io/github/v/release/sametbrr/llm-wiki-manager?display_name=tag&sort=semver)](https://github.com/sametbrr/llm-wiki-manager/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/agentskills.io-compatible-blue)](https://agentskills.io)

[Quick Start](#quick-start) • [Installation](#installation) • [Usage](#usage) • [Update mode](#update-mode) • [Multi-wiki](#multi-wiki) • [Compatibility](#compatibility)

# LLM Wiki Manager

An Agent Skill and plugin for Claude Code and Codex for building and maintaining a personal LLM-managed wiki — a persistent, compounding knowledge base where the LLM does all the writing, cross-referencing, and bookkeeping while you curate sources and ask questions.

> 🇹🇷 Türkçe için [README.tr.md](README.tr.md)

---

## Quick Start

```bash
claude plugin marketplace add sametbrr/skill-hub && claude plugin install llm-wiki-manager@skill-hub   # Claude Code
codex plugin marketplace add sametbrr/skill-hub && codex plugin add llm-wiki-manager@skill-hub         # Codex
```

Start a new session in your research folder:

```bash
mkdir ~/research/my-topic && cd ~/research/my-topic && claude   # or: codex
> "Set up an LLM wiki here. Topic: history of nutrition science."
```

---

## Features

Instead of RAG — where the LLM rediscovers answers from raw documents on every query — this pattern has the LLM **compile** raw sources into a persistent, interlinked markdown wiki. Each new source enriches existing pages. Cross-references are built eagerly. Contradictions are flagged. Knowledge compounds over time.

Implements [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) as a full agent skill with 9 operating modes (including multi-wiki routing and migrate), 5 idempotent Python scripts, 8 page templates, and 11 reference documents.

```
Without this pattern          With this pattern
────────────────────          ──────────────────
Query 1 → re-read 50 docs     Query 1 → read compiled wiki (already synthesized)
Query 2 → re-read 50 docs     Query 2 → read updated wiki (cross-refs already there)
Query 3 → re-read 50 docs     Query 3 → read updated wiki (contradictions already flagged)
```

---

## Requirements

- Claude Code, OpenAI Codex, or any [agentskills.io](https://agentskills.io)-compatible agent
- Python 3.9+ (stdlib only, for the 5 included scripts — no pip install needed)

---

## Installation

**Option 1 — Claude Code plugin (recommended)**
```bash
claude plugin marketplace add sametbrr/skill-hub
claude plugin install llm-wiki-manager@skill-hub
```

**Option 2 — Codex plugin**
```bash
codex plugin marketplace add sametbrr/skill-hub
codex plugin add llm-wiki-manager@skill-hub
```

**Option 3 — GitHub CLI, any agent** (gh CLI with `gh skill`)
```bash
gh skill install sametbrr/llm-wiki-manager llm-wiki-manager --agent claude-code --scope user   # or --agent codex
```

**Option 4 — manual copy:** copy `skills/llm-wiki-manager/` into `~/.claude/skills/` or `~/.agents/skills/`.

After installing, start a new session. The skill loads automatically when relevant.

---

## Usage

The skill auto-detects which mode applies from natural language. No slash commands needed.

```
> "Set up an LLM wiki here"                             # Bootstrap: scaffold raw/, wiki/ and the schema file
> "Add this PDF to the wiki"                            # Ingest: summarize, cross-reference, index, log
> "What does the wiki say about X?"                     # Query: answer with citations, offer to file back
> "Smith 2024 supersedes Keys 1980, update the wiki"    # Update: sweep every page that paraphrases the claim
> "Lint the wiki"                                       # Lint: dated health report in wiki/reports/
> "We should always do X going forward"                 # Schema-evolve: record a convention for future sessions
> "Add this to my global wiki"                          # Multi-wiki: route between project and global wiki
> "How does this pattern work?"                         # Teach: explain the pattern and compare it with RAG
```

### Modes

| Mode | Trigger examples | What happens |
|---|---|---|
| **Bootstrap** | "Set up a wiki", "start a knowledge base here" | Scaffolds `raw/`, `wiki/` and the schema file (`AGENTS.md` + a `CLAUDE.md` pointer) from templates |
| **Ingest** | "Add this PDF to the wiki", "I just read X, file it" | Reads source → writes summary → updates entity/concept pages → indexes → logs |
| **Query** | "What does the wiki say about X?", "Compare X and Y" | Reads index → candidate pages → synthesizes answer with citations → offers to file back |
| **Update** | "Smith 2024 supersedes Keys 1980, update the wiki" | Semantic sweep across all pages → diff-before-write per page → single log entry |
| **Lint** | "Health check the wiki", "anything broken?" | Runs `lint_wiki.py` → auto-saves `wiki/reports/lint-YYYY-MM-DD.md` → auto-tracks in index and log |
| **Schema-evolve** | "We should always do X going forward" | Updates the schema file (`AGENTS.md` / `CLAUDE.md`) so future sessions inherit the convention |
| **Multi-wiki** | "Add this to my global wiki", "promote this page to global" | Routes between project wiki and global wiki using the `External Wiki:` declaration in project `CLAUDE.md` |
| **Teach** | "How does this pattern work?", "explain the LLM wiki idea" | Explains the pattern, compares with RAG, walks through a concrete example |

### Full walkthrough

```bash
# 1. Go to your research folder
mkdir ~/research/my-topic && cd ~/research/my-topic && claude

# 2. Bootstrap the wiki
> "Set up an LLM wiki here. Topic: history of nutrition science."

# 3. Drop a source
cp ~/Downloads/pollan-2008.pdf raw/

# 4. Ingest it
> "Ingest Pollan's In Defense of Food"

# 5. Ask questions
> "What does the wiki say about nutritionism?"

# 6. Health check (auto-saves dated report to wiki/reports/)
> "Lint the wiki"
```

---

## The three-layer model

```
your-wiki/
├── AGENTS.md          # Schema — conventions for this wiki (co-evolved over time)
├── CLAUDE.md          # One line: @AGENTS.md (Claude Code reads CLAUDE.md, Codex reads AGENTS.md)
├── raw/               # YOUR layer — immutable sources you curate. LLM reads, never writes.
└── wiki/              # LLM layer — all pages written and maintained by the LLM
    ├── index.md       # Content catalog (updated on every ingest)
    ├── log.md         # Append-only operation log (greppable)
    ├── hot.md         # Hot cache — most recently ingested sources and active references
    ├── sources/       # One summary page per ingested source
    ├── entities/      # People, organizations, places, products
    ├── concepts/      # Ideas, theories, frameworks, terms
    ├── notes/         # Filed-back query answers and loose pages
    └── reports/       # Auto-generated dated lint reports (wiki/reports/lint-YYYY-MM-DD.md)
```

**Division of labor:**

| You do | The LLM does |
|---|---|
| Curate sources (decide what to read) | Read sources end-to-end |
| Ask questions, steer direction | Write summaries, entity and concept pages |
| Review the wiki, follow links | Update cross-references in-place |
| Decide what matters | Maintain index.md and log.md |
| Own `raw/` | Flag contradictions, surface gaps |

You almost never write wiki pages by hand. The LLM does the bookkeeping — that's what makes the wiki compound instead of collapse.

---

## Core disciplines

1. **LLM owns `wiki/`. You own `raw/`.** No exceptions.
2. **Every operation logs to `log.md`** via `append_log.py`. Greppable: `grep "^## \[" log.md | tail -20`
3. **Every new or updated page touches `index.md`** via `update_index.py`. Stale index = wiki that feels lost.
4. **Cross-reference aggressively.** When a source mentions an entity that already has a page, update that page. Don't leave connections implicit.
5. **Cite back to `raw/`.** Every claim is traceable to a specific source file.
6. **Flag contradictions, don't overwrite.** New source disagrees with old claim? Both stay, marked with their source, with a `> [!warning] Sources disagree` callout.
7. **Schema lives in `CLAUDE.md`.** When a convention works, write it down. The next session starts informed.

---

## What's inside

### Scripts (Python stdlib, no dependencies, all idempotent)

| Script | Purpose |
|---|---|
| `scripts/init_wiki.py` | Scaffold a new wiki — creates `raw/`, `wiki/`, the schema file (`AGENTS.md` + `CLAUDE.md` pointer, or keeps an existing one), `index.md`, `log.md`, and `hot.md`. Idempotent. |
| `scripts/append_log.py` | Append a `## [YYYY-MM-DD] action \| title` entry to `log.md`. Supports flexible log path detection. |
| `scripts/update_index.py` | Add or update an entry under a category in `index.md`. Case-insensitive categories, keeps section order and content, follows the index link style (markdown or `[[wikilinks]]`), new categories go before `## Meta`. |
| `scripts/lint_wiki.py` | Health check. Detects orphan pages, broken links and index drift in both standard markdown and Obsidian wiki-link format (`[[page#heading]]`, `![[embed.png]]` included). Default: writes `wiki/reports/lint-<today>.md` and auto-tracks. Run `--stdout` for terminal output. |
| `scripts/migrate_wiki.py` | Schema upgrade (v1 → v2). Deduplicates `index.md`, moves dated changelog blocks from `hot.md` into `log.md`, stamps the schema version. Idempotent. |

### Templates

| Template | Used for |
|---|---|
| `wiki-CLAUDE.md.tmpl` | The schema file dropped into a fresh wiki |
| `source-summary.md.tmpl` | One ingested source — claims, methodology, cross-links, open questions |
| `entity-page.md.tmpl` | People, organizations, places, products |
| `concept-page.md.tmpl` | Ideas, frameworks, theories, terms |
| `comparison-page.md.tmpl` | "X vs Y" pages, often filed-back query answers |
| `index.md.tmpl` | Initial content catalog |
| `log.md.tmpl` | Initial log with bootstrap entry |
| `hot.md.tmpl` | Initial hot cache — rewritten after each ingest with latest sources and active references |

### Reference docs

Eleven detailed workflow documents in `references/`:
`philosophy.md` · `architecture.md` · `bootstrap-workflow.md` · `ingest-workflow.md` · `query-workflow.md` · `update-workflow.md` · `lint-workflow.md` · `migrate-workflow.md` · `schema-design-guide.md` · `multi-wiki-routing.md` · `teaching-mode.md`

The skill reads these selectively — you don't need to. They're there to give the LLM depth on each mode.

---

## Update mode

Standard ingest already handles contradictions on a single page (Disputes section). **Update mode** is for when a new source supersedes a claim that's paraphrased across multiple pages — the same idea written four different ways in four different files.

```
Scenario: Smith 2024 reanalysis shows Keys 1980's seven-countries study cherry-picked data.
The Keys r=0.87 claim appears as:
  concepts/saturated-fat.md     → "Keys found r=0.87 across seven countries"
  entities/ancel-keys.md        → "famous for showing strong correlation"
  concepts/heart-disease.md     → "saturated fat is a primary driver per Keys"
  concepts/dietary-policy.md    → "the saturated fat hypothesis drove decades of policy"

Update mode:
  1. Semantic sweep — finds all four (grep won't, LLM will)
  2. Shows scope: "4 pages affected. Proceed?"
  3. Diff-before-write per page — y/n/skip/edit per change
  4. Per-page strategy: revise / disputes / annotate (not one-size-fits-all)
  5. One log entry tying all four edits to Smith 2024
```

This is change **propagation**, not change tracking. The log and frontmatter track what was edited. Update mode ensures the edit reaches everywhere it should.

---

## Auto-dated lint reports

`lint_wiki.py` with no flags:
- Writes `wiki/reports/lint-YYYY-MM-DD.md` (overwrites same-day run — idempotent daily)
- Adds a `Reports` index entry automatically
- Appends a `lint | Health check` log entry automatically
- Exits with code 1 if any block-severity issue found (useful for CI)

Reports accumulate as a longitudinal health record. `git log wiki/reports/` shows how wiki quality evolved over time.

Override flags: `--stdout` (terminal, no tracking), `--no-track` (write file, skip index/log), `--report PATH` (custom path).

---

## Multi-wiki

Most users start with one wiki. Once you have **two** — say, a per-project wiki at the working directory plus a long-lived global "second brain" (often an existing Obsidian vault) — the skill routes writes between them based on a single declaration in the project's `CLAUDE.md`.

```
~/projects/x-project/          ← active project (current working directory)
├── CLAUDE.md                  ← project schema — declares the global wiki path
├── raw/                       ← project sources
└── wiki/                      ← project wiki

~/Documents/obsidian/          ← global wiki (long-lived, exists across projects)
├── CLAUDE.md                  ← global schema
├── raw/
└── wiki/
```

### One-time setup

Add this to the project's `CLAUDE.md` (or ask the agent to do it):

```markdown
## External Wiki

Global knowledge base: ~/Documents/obsidian/

### Routing rules
- Project-specific code decisions, architecture, bugs, configuration → this project's `wiki/`
- Concepts, frameworks, patterns, ideas applicable beyond this project → global wiki
- When in doubt, ask before writing
- Scripts always need `--path` flag pointing to the right wiki root

### Cross-wiki links
- Use absolute paths (`~/...`) when linking from one wiki to the other.
- Never use relative paths that cross wiki boundaries.
```

### Four canonical scenarios

| # | Scenario | Trigger | What the agent does |
|---|---|---|---|
| **A** | **Write to global** while in a project | "Add JWT refresh rotation to my global wiki" | Reads project `CLAUDE.md` → resolves global path → writes to global, project wiki untouched |
| **B** | **Pull from global** into a project | "What does the global wiki say about rate limiting? Apply it to /api/search" | Reads global pages → synthesizes recommendation → writes a project-specific page that **links** to the global one (never copies) |
| **C** | **Promote** a page from project to global | "concepts/event-sourcing.md has matured, promote it" | Moves content to global → leaves a one-line redirect stub at the project path → updates both indexes and logs |
| **D** | **Lint both** wikis at once | "Lint both wikis" | Runs `lint_wiki.py --path` against each → reads both reports → returns one summary |

Full walkthroughs of all four scenarios in [`references/multi-wiki-routing.md`](references/multi-wiki-routing.md).

---

## Compatibility

| Tool | Install | Schema file it reads |
|---|---|---|
| Claude Code | plugin (`claude plugin install llm-wiki-manager@skill-hub`) or `~/.claude/skills/` | `CLAUDE.md` |
| OpenAI Codex | plugin (`codex plugin add llm-wiki-manager@skill-hub`) or `~/.agents/skills/` | `AGENTS.md` |
| GitHub Copilot, Cursor, Gemini CLI, … | `gh skill install … --agent <name>` | usually `AGENTS.md` |

A wiki that keeps its schema in `AGENTS.md` with a one-line `CLAUDE.md` (`@AGENTS.md`) works in all of them; `init_wiki.py` sets that up.

---

## Related

- [Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the original idea
- [agentskills.io](https://agentskills.io) — open standard spec

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

[Report Bug](https://github.com/sametbrr/llm-wiki-manager/issues) · [Request Feature](https://github.com/sametbrr/llm-wiki-manager/issues)

</div>
