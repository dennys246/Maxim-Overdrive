# Delta round: `phase3/upstream-sync`, fold `858cc2b..e4d4df3`

Reviewer: delta round, all four lenses (Architecture, Wire integrity, Executor, Bio-faithful integration), read-only.
I read Maxim through git at `5bcc2cf0` (#1787's merge commit, merged 2026-11-24T17:05Z). Its `src/` is identical to
`f145e27b` (`git diff --shortstat f145e27b 5bcc2cf0 -- src` is empty), and its plan is byte-identical to `29dda704`.
I read the two posted comments with `gh`.

**Verdict: 0 BLOCKER, 1 SHOULD-FIX, 4 NIT.** Every new citation resolves at `5bcc2cf0`. One fold claim is
overstated: E2 and Arch SF-1 are only partly folded, so they stay `open`.

## Exit test (the brief's block, run from the worktree at `e4d4df3`)

```
check_plan: PASS (0 finding(s))
exit=0
```

The draft is 2,431 words (3,146 on `origin/main`); the fold added 159, still below base.
E3's awk (`/^#+ /`) also passes on the tree.

## 1. Status of each round 1 finding (O25, read from the tree)

| Finding | Status |
|---|---|
| Bio B1 | **fixed.** The OD-I13 row is restated. The #1305 correction is posted, cites `src/`, names `seed_honoured` as the design it argues against, and narrows the ask to three gaps. Every fact in it checks at `f145e27b`/`5bcc2cf0` (see NIT 1 for one line range). |
| Bio B2 | **fixed.** Open question (a) sits beside O29, and it is asked on #1787 (question 1, posted). Phase 4's start (`roadmap.md:378`, "store routing don't block it") is outside this step's files and still says so. Question (a)'s trigger covers it. |
| E2, Arch SF-1 | **open.** OD-A2, A3, A6, A7 and I8 are cut to the O76 form. OD-A4's and OD-A5's statuses still restate the placements, and OD-A4 still gives the reason (`tool_dispatch.py` fenced). §3.7 holds the same placements, so there are still two copies. Drift risk is lower now that the plan is merged. Fix: cut both to "the A-pre plan (#1787, merged); in no release. Placements: draft §3.7". |
| E1, Arch SF-2 | **fixed.** OD-A4 is A-post, OD-A7 is after the 1.4.0 cut and OD-A5 is split. §3.7 matches the roadmap. |
| Arch SF-3 | **fixed**, as Bio B2, with (b) for OD-WC1. Draft §7 notes it too. |
| Arch SF-4 | **rejected by owner ruling UP5** (status set per the owner, as the author records it). The row keeps its text, which was public before the advisory, and now says so. |
| Bio SF-1 | **fixed.** The wording is corrected in §3.5 and OD-A5, open question (d) is added, and #1787 question 2 is posted. The plan's §Placements (lines 238-239) does move SCN registration and the EC hash "with the stamp half", as the fold says. |
| Bio SF-2 | **fixed.** The OD-A9 row names salience and gaze (plan :129, :240), and (c) records the coarse readout. |
| Bio SF-3 | **fixed.** "with refractory gating" is verbatim (`pain_bus.py` docstring), and the body-time argument is made. |
| Bio SF-4 | **fixed.** The fold adds "from Maxim's plan and code, not a run", says the binning readers bin rather than subtract, and gives the save rule to (e). |
| Bio SF-5 | **fixed** in §3.1 (plan :241, `pending:A-post`). See NIT 2 for §3.4. |
| W1, E6, Arch N-2 | **fixed.** `prompt_builder.py:2389` is `datetime.now()` in `_build_engage_prompt` (:2388). `introspection.py:744` is `_format_episodic_memory` and `:542` is `SceneSummaryTool`. The list is now headed "examples; census authoritative". |
| W2 | **fixed.** §7 places OD-WC4 (plan :298-299). OD-WC1's ids reason matches plan :300. |
| W3 | **fixed.** `class LockstepTime` is at `scripts/survival_world/scripted_water.py:79`. |
| E3 | **deferred.** Reason: the brief is outside this step's files. Trigger: the lane's next run from the brief. The deferral is recorded only in this review folder (see SHOULD-FIX D1). |
| W4, Arch N-4 | **fixed.** No "proposed" or `29dda704` is left in the touched drafts or rows. |
| W5 | **fixed.** A5 is added and OD-I3 points at its roadmap row. |
| W6, Bio NIT | **fixed.** The row now reads "a draft private security advisory". |
| W7 | **fixed.** The row now reads "must feed both (OD-A10, A-post); nothing in A-pre makes them agree". |
| E4 | **rejected** (author's call on a NIT). Review stays the guard. Accepted. |
| E5, Arch N-1 | **fixed.** The status block is gone from `issues_now_DRAFT.md`, and the README points at the roadmap rows. |
| E7 | **fixed.** |
| E8 | **rejected.** The blanket O76/O77 trigger paragraph covers every row. Accepted, as long as the PR body says so. |
| E9 | **fixed.** Lesson 42's lines are all under 125 characters. |
| Arch N-3 | **fixed.** It is carried by (d) and (e), each with an owner document or design. |

## 2. New defects in the fold's text

### D1. SHOULD-FIX: `docs/design/reviews/upstream_sync/README.md::Round 1 folds` (the E3 row). The deferral sits only where its trigger won't read it

**Defect.** E3 is a verified false green in the brief's exit test, with a verified one-token fix. The fold defers it
to "the next planning session (O79 part 5), which owns `next_steps/`; trigger: the lane's next run from this brief".
The only record is this review record. No roadmap row, decisions row or brief note names it. The scope rule says an
out-of-scope find becomes "an open item for the roadmap, with an owner and a trigger".

**Failure scenario.** At the next Overdrive tag or Maxim release, a fresh lane session reads the brief and the
roadmap, not last run's review folder. It runs the unpatched `/^#/` awk. A wrapped `#NNNN …superseded…` line at
column 0 then masks a resurrected `setprofile` tripwire, and the check exits 0. The deferral's trigger fires, but
nobody sees it.

**Fix (unverified as placement).** Add one line to the roadmap's Phase 3 lane paragraph or the next-steps section,
whichever this step may touch: "E3: brief's awk heading check, fix `/^#+ /`, owner: planning session". Or ask the owner
to rule it into this step's file list and fold the one token.

### NIT 1: `docs/roadmap.md::OD-I13` and the #1305 correction. The line range leaves out `seed`, and the per-call claim overreaches

- **The line range.** Both cite "`top_p`, `top_k`, `repeat_penalty` and `seed`, `models/language/config.py:733-735`".
  At `5bcc2cf0`, lines 733-735 hold `top_p`, `top_k` and `repeat_penalty`; `seed` is at `:738`. A Maxim reader
  checking the hint finds no seed in the range.
- **The per-call claim.** The row says the samplers are applied "per call on the llama backend only". That is true
  of `top_p`, `top_k` and `repeat_penalty` (`_LlamaCppBackend.complete`). The seed is set only at load
  (`llama_kwargs(seed=cfg.seed)`, :138), not per call. The posted comment gets this right ("passes the seed when it
  is set"); the row doesn't.

Fix: `:733-738`, and "per call (seed at load)". Re-correcting the posted comment is the owner's call.

### NIT 2: `world_clock_release_DRAFT.md::§3.4`. The last bullet contradicts the fold's own §3.1 exception

The fold rewrote it to "SCN-derived text … which the plan omits under no calendar". §3.1 now says, correctly, that
`exec_agent.py`'s SCN phase dict still renders until A-post (plan :241: "the last SCN-derived render, listed as
`pending:A-post`").

**Failure scenario.** A reader of §3.4 alone counts OD-A3 as complete at A-pre. This is Bio SF-5's failure,
reintroduced one section down.

Fix: "… omits under no calendar, except `exec_agent.py`'s phase dict (A-post, §3.1)".

### NIT 3: `docs/roadmap.md::OD-A12`. A scripted replace left a lowercase sentence start

The row reads "…is its related issue. the A-pre plan (`world_clock_a_pre.md`, #1787, merged) lands…". Fix: capitalise
"The".

### NIT 4: `docs/roadmap.md::Tier A, open questions` and `UP4`/`UP6`. Questions on a merged PR may get no owner on Maxim's side

The asks for (a) and (d) are comments on #1787, posted after it merged (the comment says "after reading this plan as merged"). A merged PR's
thread has no assignee or milestone, so Maxim's process may never pick them up. The fallback trigger ("or Phase 4's
start, whichever is first") keeps them from being dropped. The owner chose the channel (UP4, UP6).

**Failure scenario.** No answer comes, and Phase 4 starts with (a) unanswered: Bio B2's late discovery.

Trigger: if #1787 is silent at the next Maxim release, re-ask on the issue the stamp half lands under (#984, or
A-post's plan when it opens).

## 3. Citations checked at `5bcc2cf0` (all resolve unless noted)

- **`prompt_builder.py`:** `:1202` and `:2389` (`datetime.now()`); `_build_engage_prompt` at `:2388`.
- **`similarity/signature.py`:** `SituationSignature.from_memory`, with `datetime.fromtimestamp(ts)` at `:126` and
  `temporal_hash` the SCN bins.
- **`config.py`:** `:733-735` (seed at `:738`, NIT 1); the environment knobs at `:1006-1010`.
- **`router.py:1245`:** `seed_honoured=isinstance(backend, _LlamaCppBackend)`.
- **`openai_backend.py`:** no `seed`/`top_p`, so the correction's gap 2 holds.
- **`scripted_water.py:79`:** `LockstepTime`.
- **`pain_bus.py`:** "Bio-mapping: FUNCTIONAL … with refractory gating", and the severity latch as "an engineering
  analog".
- **The plan:** D-WC1 to D-WC7, I4 (:181, :319), PR 1 for D-WC5 (:121), "~54 years" (:237), WC4 static plus G-long
  (:298), and WC1, WC3 and WC7 not in A-pre ("A-post picks them up", :300).
- **#1787:** state MERGED, merge commit `5bcc2cf0`. Both posted comments match the fold's descriptions.
- **Not verifiable from the tree:** that the owner took UP3 to UP6 (the rows are the author's record).
