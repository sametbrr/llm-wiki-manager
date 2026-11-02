# Multi-wiki routing — project wiki + global wiki

Most users start with a single wiki at the working directory root. As soon as they have **two** wikis — one per project plus one global "second brain" — the skill needs a routing rule so the LLM knows where each piece of knowledge belongs.

This document covers:
- The mental model (two wikis, one agent)
- The one-time setup (declare the global wiki path in the project's `CLAUDE.md`)
- Four canonical scenarios with the exact decisions the agent makes
- Cross-wiki link rules (absolute paths, never relative)
- Routing heuristics for "where does this go?"

---

## Mental model

```
~/projects/x-project/          ← active project (current working directory)
├── CLAUDE.md                  ← project schema — declares the external wiki path
├── raw/                       ← project sources
└── wiki/                      ← project wiki

~/Documents/obsidian/          ← global wiki (long-lived, exists across projects)
├── CLAUDE.md                  ← global schema
├── raw/
└── wiki/
```

The skill itself only knows one path at a time — whichever the user is currently inside. The trick is that the **project's `CLAUDE.md`** declares the global wiki's location. The agent reads project `CLAUDE.md` at session start, sees `External Wiki: ~/Documents/obsidian/`, and knows it has two valid write targets.

---

## One-time setup

Add this section to the project's `CLAUDE.md`. Either tell the agent to do it ("add an External Wiki link to my CLAUDE.md pointing to ~/Documents/obsidian") or paste the template below directly:

```markdown
## External Wiki

Global knowledge base: ~/Documents/obsidian/

### Routing rules
- Project-specific code decisions, architecture, bugs, configuration → this project's `wiki/`
- Concepts, frameworks, patterns, ideas applicable beyond this project → global wiki
- When in doubt, ask before writing
- Scripts always need `--path` flag pointing to the right wiki root

### Cross-wiki links
- Use absolute paths (`~/...`) when linking from one wiki to the other
- Never use relative paths that cross wiki boundaries — they break under git history rewrites and directory moves
```

After this, every session inherits the awareness. The user never has to repeat it.

The global wiki's own `CLAUDE.md` does *not* need to know about specific projects. Projects are leaves; the global wiki is the trunk.

---

## Scenario A — Working in a project, writing to the global wiki

**When this happens:** You discover or articulate a pattern that's useful beyond this one project. Authentication flows, caching strategies, deployment recipes — anything portable.

**User says:**
> "JWT refresh token rotation pattern: [explanation]. Add this to the global wiki."

**What the agent reads (silently, before acting):**
1. Project `CLAUDE.md` → finds `External Wiki: ~/Documents/obsidian/`
2. `~/Documents/obsidian/wiki/index.md` → checks if a related page already exists
3. `~/Documents/obsidian/CLAUDE.md` → loads global wiki's schema (slug style, frontmatter rules, citation conventions may differ from the project)

**What the agent shows (before writing):**
```
Writing to global wiki: ~/Documents/obsidian/

Existing state:
  - concepts/jwt-basics.md    (will update — add cross-link to new page)
  - concepts/authentication.md (does not exist — will not create unrequested)

Plan:
  1. wiki/concepts/jwt-refresh-rotation.md  (new, core pattern)
  2. wiki/concepts/jwt-basics.md             (update — link to new page)
  3. index.md                                (new entry)
  4. log.md                                  (ingest entry)

Source attribution: x-project's auth implementation, 2026-05-07.

Proceed?
```

**Scripts the agent runs (note `--path` always points at the target wiki; `<skill-dir>` is the folder holding this skill's `SKILL.md`):**

```bash
python3 <skill-dir>/scripts/update_index.py \
  --path ~/Documents/obsidian \
  --category concepts \
  --title "JWT Refresh Token Rotation" \
  --page-path "wiki/concepts/jwt-refresh-rotation.md" \
  --summary "Sliding window rotation pattern for refresh tokens (from x-project)"

python3 <skill-dir>/scripts/append_log.py \
  --path ~/Documents/obsidian \
  --action ingest \
  --title "JWT refresh rotation pattern" \
  --details "Source: x-project auth implementation. Created concepts/jwt-refresh-rotation.md. Updated concepts/jwt-basics.md."
```

**Result:** The global wiki gains the new pattern with proper cross-references. The project wiki is **untouched** (the project doesn't need its own copy unless there's project-specific config — see Scenario B).

---

## Scenario B — Pulling from global wiki into a project

**When this happens:** A new project task lands. You've already written about this topic in the global wiki. You want to (1) recall what you know and (2) record the project-specific instantiation.

**User says:**
> "Rate limiting for this project. What does the global wiki say, and how do we apply it to /api/search?"

**What the agent does:**
1. Reads project `CLAUDE.md` → finds external wiki path
2. Reads `~/Documents/obsidian/wiki/index.md` → finds `concepts/rate-limiting.md` and `sources/stripe-rate-limiting-2024.md`
3. Reads those pages → synthesizes recommendation
4. Considers project context (stack, traffic profile, existing infrastructure)

**What the agent answers:**
```
Global wiki has 2 relevant pages:

  concepts/rate-limiting.md
    Token bucket vs sliding window comparison.
    Cites Kleppmann (DDIA), Cloudflare blog, Stripe API docs.

  sources/stripe-rate-limiting-2024.md
    Stripe's production approach: Redis sorted set pattern.

For x-project's Express stack: sliding window + Redis sorted set
(Stripe pattern, full implementation in the source page).

Want me to add a project-specific page in this project's wiki?
(Project notes: which endpoints, what thresholds.)
```

**User confirms:** "Yes, add it for /api/search at 100 req/min."

**The agent writes to the *project* wiki, links *out* to the global wiki:**

```markdown
# Rate Limiting — /api/search

Implementation notes for x-project's search endpoint.

Base pattern: see [Rate Limiting](~/Documents/obsidian/wiki/concepts/rate-limiting.md)
in global wiki — sliding window + Redis sorted set.

## Project-specific config
- Endpoint: `/api/search`
- Threshold: 100 req/min per user
- Key: `user_id` with IP fallback for anonymous
- Storage: existing Redis instance, prefix `rl:search:`
```

**Critical:** the project page **links** to the global wiki, doesn't **copy** the content. Copying defeats the point — when the global page evolves, copies rot. Links stay fresh.

---

## Scenario C — Promoting a project page to the global wiki

**When this happens:** A page you started in a project wiki has matured. It's no longer project-specific — it's a general pattern. Time to move it.

**User says:**
> "concepts/event-sourcing.md in this project's wiki has matured. Promote it to the global wiki."

**What the agent does:**
1. Reads `~/projects/x-project/wiki/concepts/event-sourcing.md`
2. Reads `~/Documents/obsidian/wiki/index.md` → checks for collision
3. Plans the move and the redirect

**Plan shown:**
```
Promotion: x-project/concepts/event-sourcing.md → global wiki

Steps:
  1. Create global: ~/Documents/obsidian/wiki/concepts/event-sourcing.md
     (full content from project wiki, project-specific examples generalized)
  2. Update global: index.md → new entry under Concepts
  3. Append global: log.md → "ingest | event sourcing (promoted from x-project)"
  4. Project wiki: replace original with stub redirect:
     "→ Promoted to global wiki: ~/Documents/obsidian/wiki/concepts/event-sourcing.md"
  5. Update project: index.md → mark as redirect/stub
  6. Append project: log.md → "schema-evolve | promoted event-sourcing to global"

Proceed?
```

**Resulting structure:**

```
~/Documents/obsidian/wiki/concepts/event-sourcing.md   ← full content lives here
~/projects/x-project/wiki/concepts/event-sourcing.md   ← stub: "→ global wiki"
```

The redirect stub is one line of content plus the absolute path. Future readers (and future agent sessions) following the link land on the global wiki without confusion.

**Variant — copy instead of move:** If the page is genuinely useful in both contexts (e.g., the project page has heavy project-specific config alongside the general pattern), keep both. Generalize the global page; trim the project page to only the project-specific delta and link out to the global page for the base pattern.

---

## Scenario D — Linting both wikis at once

**When this happens:** Periodic health check. The user wants both wikis audited.

**User says:**
> "Lint both wikis."

**The agent runs `lint_wiki.py` against each wiki separately:**

```bash
python3 <skill-dir>/scripts/lint_wiki.py \
  --path ~/projects/x-project

python3 <skill-dir>/scripts/lint_wiki.py \
  --path ~/Documents/obsidian
```

Each wiki gets its own dated report:
```
~/projects/x-project/wiki/reports/lint-2026-05-07.md
~/Documents/obsidian/wiki/reports/lint-2026-05-07.md
```

**The agent reads both reports and summarizes:**

```
Project wiki (23 pages): 0 block, 2 quality
  - concepts/rate-limiting-search-endpoint.md uses dead absolute link
    to global wiki (target file moved). Suggest: re-link to current path.
  - 1 stub page older than 30 days (notes/onboarding.md).

Global wiki (67 pages): 1 block, 4 quality
  - Broken link in concepts/cap-theorem.md → sources/old-article.md (deleted).
  - 3 orphan pages (no inbound links): notes/2025-conference-takeaways.md,
    sources/abandoned-paper.md, entities/short-lived-startup.md.

Recommend fixing the block-severity broken link in global wiki first.
```

The lint scripts don't know about cross-wiki links — they only check links within their own wiki root. **Cross-wiki link rot is detected by the agent**, not the script: when the agent next reads a project page that links to global, it'll notice if the target is gone. There's no automated cross-wiki broken-link check.

---

## Cross-wiki link rules (always apply)

```markdown
# Yes — absolute path with `~/`, survives moves and git rewrites
[X Project Notes](~/projects/x-project/wiki/concepts/foo.md)

# No — relative path crossing wiki boundaries, brittle
[X Project Notes](../../projects/x-project/wiki/concepts/foo.md)

# Yes — short-form prose reference when a real link is overkill
(see global wiki: concepts/event-sourcing)
```

Add the rule explicitly to **both** the project `CLAUDE.md` and the global `CLAUDE.md`:

```markdown
## Cross-wiki links
Use absolute paths (`~/...`) when linking between project wiki and global wiki.
Never use relative paths that cross wiki boundaries.
```

---

## Routing heuristics — "where does this go?"

When the user adds new knowledge and doesn't specify the target wiki, ask if it's ambiguous. Otherwise apply this:

| Type of knowledge | Target |
|---|---|
| Project-specific bug, config, architecture decision | Project wiki |
| API contract, endpoint behavior, project-specific schema | Project wiki |
| Person on the team, vendor account, internal stakeholder | Project wiki |
| General pattern (caching, auth, retries, rate limiting) | Global wiki |
| Framework concept (event sourcing, CRDTs, consensus) | Global wiki |
| Public source (paper, book, conference talk, blog post) | Global wiki |
| External person or organization (paper author, vendor company) | Global wiki |
| Both — project-specific use of a general pattern | **Both:** generic in global, project-specific in project, link from project → global |

If the user has explicit routing rules in their project `CLAUDE.md`, those win. The defaults above only apply when no rule has been declared.

---

## When *not* to use multi-wiki

Don't introduce a multi-wiki setup just because it's possible. Add a global wiki when:
- You have **2+ active projects** that share concepts.
- You catch yourself re-explaining the same pattern across project wikis.
- You have a long-running personal knowledge base that predates the project (e.g., an existing Obsidian vault) and the project would benefit from referencing it.

A single project wiki with everything inside is *not* worse than splitting prematurely. Splitting too early creates routing decisions on every ingest with no payoff.

---

## Bootstrapping a multi-wiki setup

If both wikis already exist (typical case): just add the `## External Wiki` section to the project's `CLAUDE.md` as shown above. No script needed.

If only the project wiki exists and the user wants to start a global one:

```bash
# 1. Bootstrap the global wiki at its target location
mkdir ~/Documents/obsidian
cd ~/Documents/obsidian
python3 <skill-dir>/scripts/init_wiki.py .

# 2. Back in the project, add the External Wiki link to the project CLAUDE.md
#    (agent does this on request: "link this project to a global wiki at ~/Documents/obsidian")
```

The `init_wiki.py` script is the same in both cases — there's nothing global-specific about a global wiki structurally. It's just a wiki the user has chosen to share across projects.

---

## Summary

- The skill knows one path at a time. The **project's `CLAUDE.md`** carries the link to the global wiki.
- Routing decision belongs to the user; defaults only apply when no rule is declared.
- Cross-wiki links are **absolute paths** (`~/...`). Never relative across wiki boundaries.
- Project pages **link** to global pages. They don't copy content. Links stay fresh; copies rot.
- Each wiki lints independently. Cross-wiki link rot is detected ad-hoc by the agent, not the linter.
- A page lives in **one** wiki at a time. Promote across wikis with an explicit move + redirect stub.
