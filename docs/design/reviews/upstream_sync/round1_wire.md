# Wire integrity review: `phase3/upstream-sync`, diff `1ed9caa..71bb320`

Reviewer: Wire integrity lens, read-only. Sources: Maxim `f145e27b` (origin/main), PR #1787 head `29dda704`
(`docs/plans/world_clock_a_pre.md`), GitHub via `gh`, and Overdrive's tree at `71bb320`. I checked every citation in
the changed text, one by one, with `git show`/`git grep` at those revisions or with `gh issue/pr view`.

**Verdict: 0 BLOCKER, 3 SHOULD-FIX, 4 NIT.** Nearly every citation resolves. The defects are omissions and two
pointers that land on the wrong file or attribute.

## Findings

**W1 SHOULD-FIX: `world_clock_release_DRAFT.md::§3.4` and `docs/roadmap.md::OD-A3`. The list of prompt-time sites
leaves out sites that exist at the cited sha.** §3.4 says "Sites on `f145e27b`:" and names only
`build_datetime_section` with the `datetime.now()` at about `:1202-1204`. The OD-A3 row says the same ("the
`datetime.now()` at about `:1202`"). At `f145e27b`, `PromptBuilder._build_engage_prompt` makes a second
`datetime.now()` render at `agents/prompt_builder.py:2389-2391`, and #1787 names both (`build_prompt` and
`_build_engage_prompt`, §Motivation item 1 and PR 2). #1787's PR 2 also puts two raw-epoch tool results under the port:
`tools/introspection.py::_format_episodic_memory` (`:744`) and `SceneSummaryTool.execute` (`:542`). Neither appears
in the draft or in the row.
*Failure scenario:* the lane checks #1787's PR 2 against OD-A3's "Covers …" list. The engage prompt and the two tool
results are not on that list, so the check could call OD-A3 covered while host time still reaches a tool-path prompt,
or a reader could take #1787 to be widening our scope. The closing "PR 0's census fixes the counts" doesn't help,
because the list is headed as the sites at a sha.
*Fix (verified by `git grep -n 'datetime\.now' f145e27b -- src/maxim/agents/prompt_builder.py` and the two symbol
greps):* add `_build_engage_prompt` (about `:2389`) and the two tool results to §3.4 and to OD-A3.

**W2 SHOULD-FIX: `world_clock_release_DRAFT.md::§7` (the closing line). OD-WC4 is never placed.** The line says
"#1787 takes OD-WC5, OD-WC6 and OD-WC2 … and leaves OD-WC1, OD-WC3 and OD-WC7 to A-post." #1787 §Gates ("Exit tests
chosen") also takes **WC4**, in its static form: "M72 at zero outside the allowlist on A-pre's families … plus
G-long", with G-long's full-loop half going to A-post.
*Failure scenario:* when the lane reconciles, it finds OD-WC4 neither taken nor left, and may re-raise an exit test
that Maxim already planned. Or OD-WC4 drops out of tracking, which is the "a future bar is tracked, never dropped"
failure.
*Fix (verified against `29dda704:docs/plans/world_clock_a_pre.md`, §Gates):* "takes OD-WC5, OD-WC6, OD-WC2 and
OD-WC4 (static form plus G-long's A-pre half; the full-loop half is A-post)".

**W3 SHOULD-FIX: `world_clock_release_DRAFT.md::§2` (the `_StepClock` row). `LockstepTime` is attributed to the wrong
file.** The row reads "`tests/unit/_loop_harness.py::_StepClock`, `LockstepTime` (#951)". The old draft named
`scripts/survival_world/scripted_water.py::StepClock` between the two, and this diff deleted that name. As written,
`LockstepTime` now reads as a symbol of `_loop_harness.py`. At `f145e27b`, `class LockstepTime` is at
`scripts/survival_world/scripted_water.py:79`. `_loop_harness.py:13` mentions it only in a "WHY NOT" docstring.
*Failure scenario:* a Maxim reader resolves `tests/unit/_loop_harness.py::LockstepTime`, finds nothing, and either
discounts the row or concludes the harness changed.
*Fix (verified with `git grep -n 'class LockstepTime' f145e27b`):* cite `scripts/survival_world/scripted_water.py::LockstepTime`
(#951).

**W4 NIT: `world_clock_release_DRAFT.md` header, and every "(proposed in #1787, D-WC…)". The rulings' status is
understated.** The header says D-WC1 to D-WC7 are quoted "as **proposed in #1787**, not as decided". #1787 records
them as decisions Maxim's owner took on 2026-11-24 ("Owner, 2026-11-24, asked together at the start"; D-WC2 revised
and D-WC5 to D-WC7 "re-taken after the plan review"). What is unmerged is the plan, not the rulings.
*Failure scenario:* a later reconciliation treats D-WC5 (the whole `CostTracker` on the wall) as still open and
re-argues it.
*Fix (unverified wording):* "owner rulings recorded in #1787, an unmerged plan; they bind once it merges."

**W5 NIT: `docs/maxim_upstream/README.md::the embeddable_agent row`. The status leaves out a candidate and a merged
fix for an id the row lists.** The row lists OD-I3 and gives "Maxim's candidates A1, A4, B1, B2 … no plan, nothing in
a release". The embeddable draft's own map (`embeddable_agent_DRAFT.md:27`) puts OD-I3 under **cand. A5** (#1685), and
#1685 was closed on 2026-11-23 by #1773 (`1b2e60a9`, on `f145e27b`, not an ancestor of `v1.3.4`). "Nothing in a
release" is true, but the row reads as if nothing had moved. OD-I3's roadmap row belongs to step 2 (O79), but this
README row belongs to the lane.
*Fix (verified with `gh issue view 1685` and `git merge-base --is-ancestor 1b2e60a9 v1.3.4` → not in it):* add A5,
and "OD-I3: #1685, fixed by #1773, in no release".

**W6 NIT: `docs/roadmap.md::OD-I11`. "Filed" overstates the advisory's state.** `gh api …/security-advisories/GHSA-rjg9-f5r9-7x7p`
returns `state: draft`, created 2026-11-24T16:49:36Z. A draft is private, so the UP1 reasoning holds. But under O76 a
status line should give the cited object's own state.
*Fix (verified):* "Filed 2026-11-24 as a draft private security advisory, GHSA-rjg9-f5r9-7x7p".

**W7 NIT: `world_clock_release_DRAFT.md::§2` (the `ExperienceClockDriver` row). A placement is stated as a fact.**
"Under embedding the entry point (OD-A10) feeds both from one host source." #1787 §Placements makes this a
requirement on OD-A10, which is outside A-pre ("must derive both … A-post"), and adds that "Nothing in A-pre makes
them agree."
*Fix (unverified wording):* "must feed both from one host source (OD-A10, A-post; #1787 §Placements)".

## Checked and correct

- **Shas.** `f145e27b` is the merge of #1778, dated 2026-11-23 local time. `29dda704` is #1787's head: open, not a
  draft, no milestone. `v1.3.4` is the latest tag apart from `o19/*` attempt tags.
- **Issue and PR states and milestones.** #1684: closed, milestone 1.3.5, by #1773, which fixes "five sites". #1773:
  merged, not in `v1.3.4`. #1769: open, deferred to line 2's port plan, which matches "routed to this plan". #1305:
  open, milestone 1.3.5, with the world-clock comment at 16:33Z and the lane's OD-I13 comment at 16:49Z, both on
  2026-11-24. #1361: open. #1782: open, milestone 1.3.5. #984: open, milestone 1.3.5. #1150: open, in roadmap_1_3_x
  §1.3.6. #1200: open. #1689: closed, with its shortcut deleted by #1694. No `strftime` or `datetime` is left in
  `llm_fallback.py`.
- **#1787 claims.** D-WC1 to D-WC7, I4, G-tool-duration red in PR 0, PR 0 to PR 5 with PR 5 in 1.3.6, the
  `xfail(strict=True, raises=AssertionError)` gates, the Placements for OD-A4, OD-A5, OD-A8, OD-A9, OD-I8 (#1361 S4,
  Q4) and OD-A7 (after 1.4.0), "~54 years", the divergence from `ExperienceClockDriver` for windows, and the reader set
  in lesson 42: all match.
- **Symbols and lines at `f145e27b`.**
  - `tool_dispatch.py`: `execute_and_learn` with `exec_start` at `:1515`; `_observe_energy_cost` at `:698`, NEGATIVE
    above 2.0 s at `:702`.
  - `context_pool.py`: `localtime` at `:468` and `:493`.
  - `prompt_builder.py`: `build_datetime_section` and `build_identity_section` with `date_str`/`time_str`.
  - `semantic.py:205` (`or 42`), `seeding.py::make_agent_rng(base_seed, agent_id)`, `nac.py:1163` (`time_ns`),
    `body.py:293` (drift in `evaluate_failures`).
  - `hippocampus.py` (`dedup_window_s = 30.0`); `pain_bus.py` (refractory 0.5 s, "Bio-mapping: FUNCTIONAL", rejects
    `ContextVar`); `ReactionBus`.
  - `bio_stack.py:489` and `:654`; `openai_backend.py:273` (still keyed on the name).
- **Verbatim quotes.**
  - The fence (`roadmap_1_3_x.md:358`).
  - M72's allowlist (`outstanding.md:123`).
  - The three §(g) rows of `experience_clock_decay.md`. They are quoted as prefixes, and the trailing text is dropped.
  - G17's "waits for the stage that needs it" (`DECISIONS.md:717`, in G17's rationale) and G3's "loop/tick clock".
  - `SECURITY.md:15`, and `CONTRIBUTING.md` §Issues ("a discrete defect").
- **Release plan, candidates and Maxim's ids.** D9 and line 2 in `release_1_3_5.md`. "A3 A-post with #1361's slices
  and 1.3.6" (candidates §Order). OD-A16 in cand. B2, OD-H2 as cand. C2, M83.
- **Overdrive-internal.** `npcs_and_sem.md` §3.1, §3.2 (the coarse interim readout), §3.4 and §12.2. The OD-B9,
  OD-A1, OD-A8 to OD-A10, OD-A15, OD-A20 and OD-H6 rows, O40, and O76 to O79. Every draft named in the README exists,
  as does `maxim_response_1/response.md` (OD-I2 "nit-level"). The brief's exit-test greps pass, and the word count
  went from 3,146 to 2,272.

## Outside this lens (for the owner and the Trust-boundary or Architecture readers)

- **Disclosure.** UP1 sends OD-I11 to a private advisory under Maxim's `SECURITY.md`. Yet the OD-I11 row in this
  public repo still carries the full reproduction, and the diff adds the advisory id beside it. The reproduction was
  already public before this diff, but the ruling's purpose and the row disagree.
- **O76's status form.** O76 says a status "never restates Maxim's discussion". The new OD-A2 to OD-A7 status
  clauses summarise #1787's reasoning: D-WC6 reader sets, port modes, and what moved where.
