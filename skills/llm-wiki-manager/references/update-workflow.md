# Update Workflow

Use this when a new source genuinely **invalidates** an existing claim across the wiki — not just contradicts it on one page (that's the standard ingest workflow's "Disputes" handling), but supersedes it broadly enough that multiple existing pages are now wrong or misleading.

This mode is the difference between **change tracking** (the wiki recording what was edited) and **change propagation** (the wiki staying internally consistent as new evidence arrives). The bookkeeping disciplines from ingest — log entries, frontmatter `updated`, git history — handle change tracking. They do not handle propagation. A new source can update one page via ingest, while three other pages quietly retain the now-stale claim. Update mode exists to sweep those.

## When to invoke this mode (vs. ingest-with-Disputes)

The default is still ingest's Disputes handling: when a new source contradicts an existing claim on one page, add both with citations and flag the conflict. That's enough when the conflict is local.

Switch to update mode when **any** of these hold:

- The user explicitly says "update the wiki for new info — X is no longer right" or "Smith 2024 supersedes Keys 1980, please correct everywhere".
- During ingest, you find the new source's central claim contradicts material on **3 or more** existing pages (not just the page being directly created/updated).
- A lint pass surfaces an unflagged contradiction that turns out to span multiple pages.
- The user is explicitly correcting a factual error they noticed while reading the wiki.

If you're unsure whether the conflict is "local" or "broad", default to update mode — its diff-before-write discipline is safe to invoke, and the worst case is you confirm only one page needs changing and proceed.

## Why a dedicated mode

Three failure modes the ingest workflow alone can't catch:

1. **The new source doesn't mention the entity directly.** Smith 2024 critiques the seven-countries methodology without naming Ancel Keys. Ingest will create `sources/smith-2024.md` and update `concepts/saturated-fat.md`. It will not touch `entities/ancel-keys.md` because Smith never said "Keys" — but that page now contains a stale framing.
2. **The same claim is paraphrased differently across pages.** "r=0.87 across seven countries" / "strong correlation" / "primary driver" / "drove decades of policy" — same idea, four wordings, four pages. Grep won't find them all; semantic search will.
3. **Silent overwriting destroys the audit trail.** Just editing each page leaves no record of why it changed. Update mode emits a single coherent log entry that ties the four edits to the new source.

## The full loop

### 1. Identify the claim being superseded

State it in one sentence, in the language the wiki was written in:

> "The seven-countries study established that saturated fat consumption strongly correlates with heart disease."

This is the *claim under review*. Everything that follows refers to it.

### 2. Identify the source authorizing the change

Update mode is only invoked when there's a **specific source** that justifies the change — either a newly-ingested one, or one already in the wiki that wasn't fully integrated when it arrived. State the source-summary page that grounds the update:

> Authority: `wiki/sources/smith-2024-seven-countries-reanalysis.md`

If no such source-summary page exists yet, ingest first, then come back to update mode. **Never run update mode from general LLM knowledge alone.** The wiki's claim-to-source traceability is the entire reason it's trustworthy.

### 3. Sweep — find every page that asserts (or implies) the claim

Read `wiki/index.md`. Pick candidate categories: usually `concepts/`, often `entities/`, sometimes `notes/`. Read each candidate page that's plausibly related, and collect occurrences:

```
[
  ("concepts/saturated-fat.md", 22-25, "Keys (1980) found that saturated fat..."),
  ("entities/ancel-keys.md", 14-16, "famous for showing strong correlation..."),
  ("concepts/heart-disease-causes.md", 33, "saturated fat is a primary driver per Keys"),
  ("concepts/dietary-policy.md", 47, "the saturated fat hypothesis drove decades..."),
]
```

Don't grep — it misses paraphrases. Read pages and judge semantically. Be conservative: a sentence that *mentions* Keys without asserting the disputed claim is not a hit. A sentence that *asserts* the claim, with or without naming Keys, is a hit.

If the candidate set is empty, the claim was either never widely propagated or you've over-narrowed the candidate categories. Re-check.

### 4. Show the user the proposed scope

Before writing anything, present the sweep result:

> Found 4 pages affected. Proposed action: update each in light of `sources/smith-2024-seven-countries-reanalysis.md`. Want to proceed? I'll show diffs for each one and confirm individually.

This is the **most important checkpoint** in the workflow. A 4-page update is cheap to confirm, expensive to undo. Wait for explicit go-ahead.

### 5. Diff-before-write, page by page

For each hit, show a unified diff before writing:

```diff
# concepts/saturated-fat.md, lines 22-25
- Keys (1980) found that saturated fat consumption strongly correlates
- with heart disease incidence (r=0.87 across seven countries).
- This finding shaped USDA dietary guidance for four decades.
+ Keys (1980) initially reported a strong correlation (r=0.87) across
+ seven cherry-picked countries; subsequent reanalysis with the full
+ 22-country dataset shows weak correlation
+ (see [Smith 2024](../sources/smith-2024-seven-countries-reanalysis.md)).
+ This earlier finding nonetheless shaped USDA guidance for four decades.
```

Ask `y/n/skip/edit` per page, or offer `all` after the first one if the user wants to batch-confirm. Apply each approved diff immediately; don't wait until the end (if something fails halfway, the wiki should be in a coherent partial state, not a corrupt one).

### 6. Decide between revision and Disputes

For each hit, the right action is one of:

- **Revise** — replace the stale claim with the corrected one, citing the new source. Right when the new source clearly settles the question.
- **Disputes** — keep both claims side-by-side under a `> [!warning] Sources disagree` callout. Right when both sides have non-trivial evidence and the wiki should record the disagreement rather than pick a winner.
- **Annotate** — keep the original claim with a parenthetical note: "(this 1980 framing was later contested; see Smith 2024)". Right when the historical claim is itself a fact (e.g. *that* USDA based policy on Keys is true regardless of whether Keys was right).

The user makes this call per page. Don't default to one strategy across all four — each page may warrant a different choice.

### 7. Update the index for any pages whose summary changed

If a page's index summary now misrepresents the page (e.g., entry says "primary driver of heart disease" when the page now says "contested"), run `update_index.py` for it. Most updates won't change the index summary, but check.

### 8. One log entry summarizing the whole sweep

```bash
python scripts/append_log.py --action update \
  --title "Saturated fat / Keys 1980 correction" \
  --details "Smith 2024 reanalysis. Revised: concepts/saturated-fat.md, entities/ancel-keys.md, concepts/heart-disease-causes.md. Annotated: concepts/dietary-policy.md. 4 pages touched."
```

The log entry ties all the edits to one source-driven event. This is the audit trail. Six months from now, if someone asks "when did we update the Keys framing?", `grep "update | Saturated fat" log.md` is the answer.

## Optional: pre-update git commit

Strongly recommended for non-trivial sweeps. Before applying any diffs:

```bash
git add -A && git commit -m "Pre-update snapshot before Keys correction"
```

This gives you a single rollback point. Update mode does not enforce git, but the workflow is materially safer with it. Mention this once when the user invokes update mode for the first time in a wiki that's a git repo; subsequently, just do it silently as part of step 5.

## Heuristics

- **Don't run update mode from general knowledge.** The trigger is always "a specific source supersedes a specific claim". If the user invokes it without a source, ingest the source first.
- **Confirm scope before writing.** Step 4 is non-negotiable. A silent multi-page edit erodes trust faster than any other failure mode in the wiki.
- **Diffs over prose summaries.** "I'll change line 23 to say X" is worse than showing the unified diff. The diff is unambiguous; the prose hides what's actually being changed.
- **Per-page choice between revise/dispute/annotate.** Don't apply one strategy uniformly. The right action depends on the nature of each page.
- **One log entry, not four.** The sweep is one logical event. Logging four entries fragments the audit trail and makes future grep less useful.
- **Don't over-sweep.** A passing mention of "Keys 1980" inside a long paragraph is not necessarily a hit — only flag pages that *assert* the disputed claim.

## Common mistakes

- **Running update mode for local conflicts.** If only one page is affected, ingest's Disputes handling is correct. Update mode is for multi-page propagation; using it for single-page edits is overkill and dilutes the mode's signal.
- **Skipping the source check (step 2).** "I just remember that Keys was wrong" is not a basis for a sweep. The wiki is grounded in cited sources or it's nothing.
- **Silent edits.** No diffs shown, no log entry, just edits. Most damaging failure mode — completely defeats the purpose.
- **Aggressive replacement when annotation was right.** When the historical claim is itself a fact (people *did* believe X), erasing it loses information. Annotate instead.
- **Forgetting the index sweep.** A page's body now says "contested" but its index summary still says "primary driver". The index is now lying.
