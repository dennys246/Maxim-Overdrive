# Fidelity review: `docs/plans/foundations_plan.md` at 72bf36c

Lens: does each line of the plan say what its source says? Not just whether every id is there (`check_plan.py`
PASSes, 0 missing), but whether the summary misstates or overstates it, drops a condition, gets decided/open wrong,
or cites the wrong place. Sources: `docs/design/boundaries.md` §0, §7.4, §11, §12; `docs/design/npcs_and_sem.md` §0,
§6.2, §6.6, §12; `docs/design/world_model.md` §0, §10, §12; `docs/roadmap.md`; `docs/design/reviews/maxim_response_1/`,
`npcs_v3_1/`, and `npcs_and_sem.md`'s last fold table; `CLAUDE.md` and `docs/standards_backlog.md` on
`phase1/standards`; git (`git branch -vv -a`, `git merge-base`, `gh pr list`); Maxim `origin/main` 6fee7377 and
`gh issue view` on dennys246/Maxim (read-only).

"Plan Lnn" is the line in `foundations_plan.md` at 72bf36c.

**Counts: 4 BLOCKER, 12 SHOULD-FIX, 16 NIT.** Of 103 table rows: 52 correct, 31 partly, 11 wrong, 6 missing from the plan, 3 stale
or superseded source texts not flagged.

## Table of every item checked

### §1 Where things stand (git and GitHub facts)

| Item | Plan | Verdict | Note |
|---|---|---|---|
| "Four draft PRs, all based on `phase1/standards` (PR #1)" | L11 | partly | #2–#4 are; PR #1's base is `foundations/world-server-v0` (`gh pr list`), the branch `boundaries.md` §11.3 and §12 Q3 propose abandoning (S7) |
| PR #1 local head `87593fe` | L16 | correct | |
| PR #1 "`e5aa3e1` pushed" | L16 | wrong | `origin/phase1/standards` is `87593fe`; the new standard is already pushed (S7) |
| PR #2 local `0480ab6`, remote `2f200b5`, needs rebase | L17 | correct | merge-base with standards `15bd3aa` |
| PR #2 contents, "its B21" | L17 | correct | B21 is **done** on act-validation (the owner's decision, 2026-11-17) |
| PR #3 local `6291fd0`, remote `a8225d1`, `8a0b325` | L18 | correct | `8a0b325` exists on that branch; the PASS line itself is unverifiable here |
| PR #3 rebase need | L18 | partly | not stated; its merge-base with standards is `9bad3bd`, older than #2's and #4's |
| PR #4 "pushed at `73c0eb8`" | L19 | wrong | remote is `72bf36c` (S7) |
| PR #4 branched at `15bd3aa` | L19 | correct | |
| `main` at `d02c0a2`, no `.gitignore` or source | L21 | correct | `main` holds only `LICENSE` |

### §2.1 Boundaries decisions (`boundaries.md` §0, lines 40–52)

| Id | Verdict | Note |
|---|---|---|
| O1 | correct | |
| O2 | correct | marked superseded, points at O6 |
| O3 | correct | drops "in integer ticks: frozen frames in, logged intents out"; npcs §0 says refined by O6 *and O6a* (N1) |
| O4 | partly | drops "Abandoning late thoughts is an explicit, logged host policy" and "by cause"; "refined by O11 and O16" is the plan's own inference, recorded in neither source's O4 row, and `boundaries.md` §7.4 (L599–602) still says "otherwise it dilates", which O16 contradicts for co-op (S10) |
| O5 | partly | drops "additive first in 1.x" and the "cite its `OD-` id and path" rule (N1) |
| O6 | correct | |
| O7 | partly | its own row doesn't say the condition is met; npcs §0 O7 does ("*Its condition is met: see O7a*"). Drops the "after PR 1 is rebased" condition, where "PR 1" means act-validation (N2) |
| O7a | partly | drops "Each real agent runs in its own worker process" (boundaries' O7a); listed only under boundaries though npcs §0 has its own O7a row with different wording (N1) |
| O8 | correct | |

### §2.2 NPCs and SEM decisions (`npcs_and_sem.md` §0, lines 77–107)

| Id | Verdict | Note |
|---|---|---|
| O6a | partly | O6a says `think` is host-called and resumable and returns model requests as values; "`step` … `settle`, plus `apply`" is §6.6 and `world_model.md` §10 row 9b, not O6a (N3) |
| OA1 | partly | drops "from a closed vocabulary" and "experiments always run on fixed defaults", a condition (N1) |
| OA2 | correct | blue/red is §5.4, accurate |
| OA3 | correct | drops "interfaces only in Phase 1" |
| OA4 | correct | |
| OA5 | partly | drops "feeds sleep pressure" (N1) |
| O9 | correct | |
| O10 | correct | |
| O11 | **wrong** | "in co-op, until OD-H5 exists, O16 applies": O16 applies in *both* modes until OD-H5 (O11 itself says "Needs OD-H5 first"); single-player dilates (S1) |
| O11a | correct | drops "proposed to Maxim as a fifth hybrid split-out plan" |
| O12 | correct | |
| O13 | partly | "Detailed in §6.6" hides that §6.6 *replaces* O13's mechanism (spawn → `subprocess.Popen`, pipe → socketpair, scrubbed → allowlist); `npcs_v3_1/executor_wire.md` S4 asked for a note on the owner row and it isn't there (S3) |
| O14 | correct | |
| O15 | correct | |
| O15a | partly | drops "plus that slice": real NPCs wait for 1.4.0 *plus the agent-loop decomposition slice* (S2) |
| O16 | correct | |
| O17 | correct | |
| O18 | correct | |
| O19 | partly | content right; cites "(§3, step 5)" but `phase1/agents` is step 7 (S4) |
| The two unnumbered "—" decisions (thought-cost unit; lay foundations now, test per tier) | missing | npcs §0 L106–107 (N4) |
| `world_model.md` §0 D20–D25 (one truth, resolution follows the world, rubble to Phase 2, lab as benchmark, three documents, physics standard) | missing | the heading says "Every owner decision" (S8) |

### §2.3 Standards (`CLAUDE.md` on `phase1/standards`)

| Standard | Verdict | Note |
|---|---|---|
| Separation of concerns; guard Architecture lens, B19 | correct | CLAUDE.md L184–188 |
| Size tripwires: 10 / 40 / 500 / 12, only tighten; guards | correct | L189–197 |
| Assume other agents are working; guards | partly | guard list omits `tests/test_prepush.py::test_the_tests_cannot_reach_a_repository_named_in_the_environment` (L230) (N5) |
| Search Maxim before proposing; `87593fe`; Bio-faithful lens, B22 | correct | |
| Maxim's process by kind of change; `d75b134`; guard B1 | partly | CLAUDE.md's guard is "`docs/roadmap.md`, B1" (N5) |
| "Added this session" set | partly | `31818e1` (record lessons, B18) is also after the branch point `15bd3aa` and is missing, if it was this session's (N5) |

### §2.4 Working decisions

| Item | Verdict | Note |
|---|---|---|
| Pushing (`e5aa3e1`) | correct | CLAUDE.md L207–210 |
| Stop paper rounds (O19) | correct | "the world half is converged" has no source; O19 says it "proceeds" (N6) |
| B21 reserved, B22 used | correct | |

### §3 The plan, in order

| Step | Verdict | Note |
|---|---|---|
| 1 Send `correction_1.md`, blocked by nothing | partly | Maxim's candidates doc on origin/main repeats our wrong claim (B2 "depends on A3's A-post (NAc's event time is the wall clock, `decisions/nac.py:1162`)", `overdrive_refactor_candidates.md` L285); the note answers only `reply.md` §7 (S11) |
| 2 Land PR #1 (standards) | partly | PR #1 targets `foundations/world-server-v0`; `boundaries.md` §11.3 proposes act-validation → standards → design-v2, the reverse of steps 2–3, and the plan doesn't say it supersedes that order (S7) |
| 3 Rebase PR #2 | correct | |
| 4 Rebase PR #4 | correct | |
| 5 `phase1/boundaries`, blocked by steps 2–3 | **wrong** | `world_model.md` §10 row 2 puts "Parts 1, 2 and 3 of this design accepted" before 2b; backlog B19 (1) lands "once `docs/design/boundaries.md` merges"; `boundaries.md` §12 Q1 (package name) and Q2 (two PRs or one) are open and shape this step (B3, B4) |
| 6 `phase1/gates` after step 5 | correct | |
| 7 `phase1/agents`, blocked by step 6 | **wrong** | every source puts it after `phase1/sim-clock`: npcs §6.2 L707, `boundaries.md` §11.1 L772, roadmap Phase 1 L26, world_model §10 (row 9b after rows 3–9) (B2) |
| 8 Part 3 after step 5 | **wrong** | world_model §10 row 2 needs part 3 *accepted* before 2b (B4) |
| 9 Per-worktree `.venv`s | correct | |
| 10 Calibration ledger, "proposed, not designed" | correct | |
| 11 Phase 4's NPCs: tier A, OD-A1–A18, 1.4.0 | partly | drops the decomposition slice (S2) and the Phase 3 exit's OD-A16 (§12.1 item 3) |
| Red-first test 1 (hash seed, `-I`) | correct | EW B1, ATR-B1 |
| Red-first test 2 (home, XDG, TMPDIR, HF_HOME; reads) | correct | ATR-B2 |
| Red-first test 3 (codec refuses pickle) | partly | from O19's list (the v3 round), not an open npcs_v3_1 BLOCKER as the lead-in says (N7) |
| Red-first test 4 (resume at landing tick) | partly | keeps the digest, drops DB-B3's other load-bearing part: the double's `think` must fold its step sequence and staleness verdict into its output, or the plant still can't go red (S12) |
| Red-first test 5 (credit at two rates) | correct | DB-B2 |
| DB-B1 (OD-A19 duplicate) | missing | resolved by the withdrawal; worth one line saying so (N7) |

### §4 The Maxim side

| Item | Verdict | Note |
|---|---|---|
| "Asked (`reply.md`)": five questions | partly | those are the original embeddable-agent questions that `response.md` answers; `reply.md` is our reply to the answers (N8) |
| Accepted by Maxim | correct | matches `response_2.md` |
| Pushback we accepted | correct | omits the Stivers→Jefferson citation fix, "shortcut fires without a wake word", "latch doesn't close prefetch" (N8) |
| Pending from Maxim: candidates doc; filing OD-I3, I1, I4, I5 | **wrong** | landed: `docs/plans/overdrive_refactor_candidates.md` (Maxim PR #1688, `a7825aa1`, 2026-11-17 00:31); filed #1684 (OD-I1), #1685 (OD-I3), #1686 (OD-I4), a draft private security advisory for OD-I5 (proven end to end), plus #1687 (Windows latch, closed) (B1) |
| "the owner said go" | partly | recorded nowhere in the sources; consistent with the doc existing (S6) |
| Owed: `correction_1.md` summary | partly | drops its S3a time-constant question and smaller corrections; see step 1 (N8) |
| Phase 4 depends on tier A and 1.4.0 | partly | drops the slice (S2) |
| Phase 3 "Issues, to file now" | **wrong** | filed (B1) |
| Tier A active list | partly | ids right; OD-A18 still says "After OD-A19" (roadmap L119), a dependency on a withdrawn item, unflagged; Maxim mapped OD-A7 to #1305 and OD-A18 to #1150 (S10, B1) |
| Tier A moved/withdrawn | correct | |
| Tier B, Tier C, hybrid, experiments | correct | |
| "Exit tests named in the roadmap" | partly | the roadmap names OD-WC1, EA5, EA10, EA11, EA12 (L180); EA4, EA6, EA9 come from the design docs (N9) |

### §5 Open questions and risks

| Item | Verdict | Note |
|---|---|---|
| §12.1 item 1 "decided (O14, plus O18's sixth gate)" | partly | the OS sandbox for guest workers is still an open proposal (npcs L1143–1145, roadmap L198); dropped (S6) |
| item 2 | correct | |
| item 3 | correct | open |
| item 4 | correct | |
| item 5 "all four" | partly | §12.1 item 5 has **five** proposals (filler propensity, BD-5/BF3-11, was added in v3.1); "owner said take all four" is recorded nowhere: either record it in §0 or call it open (S6) |
| item 6 | correct | |
| item 7 | correct | |
| L164 "items 2, 6 and 7 still read as open" | **wrong** | 72bf36c marked them decided (S5) |
| §12.2 list | partly | omits "prompt and dial-invisibility tests red until tier A" (N10) |
| L171–172 "§12.2 still says this closes with OD-A19" | **wrong** | 72bf36c changed it to OD-A1 (S5) |
| Fold tables overstating (165 → ≤155) | correct | `npcs_v3_1/executor_wire.md` L13 |
| Duplicating asks (three) | correct | `87593fe` lesson 13 |
| Shared `.venv`, machine load | correct | not checkable from sources; plausible |
| Open backlog rows | correct | all open on standards; B12 is partly in place on act-validation (N10) |
| Partial fold rows (9) | correct | matches the table; TBR-11 and TB3-S8 say "the owner decides" a sixth gate that O18 has since decided (N10) |
| Owner questions in `boundaries.md` §12 (5) | missing | (B3) |
| Owner questions in `world_model.md` §12 (3) | missing | (B3) |
| Roadmap "Open questions" (3) | missing | (B3) |
| L6 "check_plan.py fails if … an open owner question in the sources is missing" | wrong | it reads only npcs §12.1 and only `O…`/`OA…`/`OD-…` ids; it can't see D20–D25 or any other §12 (S8) |

### Superseded and stale decisions: are they marked?

| Item | Verdict |
|---|---|
| O2 → O6; O6 → O6a; O11 → O11a; OD-A13 → OD-I3; OD-A19 withdrawn; OD-H4 → OD-H5; OD-I2 downgraded | correct |
| O7 → O7a | partly (N2) |
| O13's mechanism → §6.6 | not marked (S3) |
| Roadmap Phase 4 "OD-A1 to OD-A19" (L188), "Proposed for the owner: … remote model egress" (L198, now O18) and its five gates without O18's sixth | not flagged (S10) |
| `boundaries.md` §7.4 "otherwise it dilates" vs O16; npcs §6.2 three-method port vs §6.6 (EW S1); `boundaries.md` §11.1 "worker processes … arrive with `phase1/lanes`" vs O19 and row 9b | not flagged (S10) |
| Roadmap L71 "Maxim's design session will write a ranked candidates doc … rows are proposals until it lands" | it has landed; not flagged (B1) |

## BLOCKER

**B1. The Maxim side is a round out of date, and following it would duplicate filings (plan L128–129, L141; roadmap
L71, Phase 3 "Issues now").** Plan: "Pending from Maxim: the ranked candidates document …; filing OD-I3 (pickle), OD-I1
…, OD-I4 … and OD-I5", and "Issues, to file now". Maxim `origin/main` has `docs/plans/overdrive_refactor_candidates.md`
(PR #1688, merged `a7825aa1`, 2026-11-17 00:31 −0700), whose "Filed alongside this list" names #1684 (OD-I1, open),
#1685 (OD-I3, open), #1686 (OD-I4, open), #1687 (Windows `maxim._offline`, closed) and a draft private security
advisory for the redaction forgery (OD-I5), "proven end to end, with both `\n` and U+2028". It also maps OD-A7 onto
#1305 (a 1.4.0 release gate) and OD-A18 onto #1150, and lists five "Not decided here" questions back to us. Failure
scenario: a session takes §3/§4 at face value and files OD-I1 again, which is the very failure B22 and lesson 13
exist to stop. Fix: rewrite §4 and the Phase 3 table from the candidates doc; record the issue numbers in roadmap
Phase 3; add Maxim's "Not decided here" questions to §5; record that Maxim's doc carries our wrong `nac.py:1162`
claim (step 1, S11).

**B2. Step 7 (`phase1/agents`) is blocked by the wrong thing (plan L91).** Plan: "blocked by step 6". Sources:
npcs §6.2 L707 "after `phase1/sim-clock` (it needs the intent record and the tick) and before `phase1/lanes`";
`boundaries.md` §11.1 L772 "after sim-clock and before lanes"; roadmap L26 "after the clock and before the lanes";
`world_model.md` §10 puts row 9b after rows 3–9 (`verify`, `sim-clock`, `protocol`, `zones`, fuel, phase change).
The plan's §3 has no `phase1/verify` or `phase1/sim-clock` step at all. Failure scenario: a session starts
`phase1/agents` straight after gates, with no integer tick or intent record to build `AgentPort` on, and the
membrane's TEMPORARY marker (§6.2) has no tick to schedule against. Fix: add world_model §10's rows 3–4 (and say
whether 5–9 must precede 9b or only sim-clock does) and block step 7 on sim-clock.

**B3. Owner questions that gate the next steps are missing; the plan's only open-question list is npcs §12.1
(plan §5.1, L6).** Missing: `boundaries.md` §12 (1 the engine's package name, 2 two PRs or one, 3 abandoning
`phase1/transport` and `foundations/world-server-v0`, 4 imagination budgets, 5 frame cadence); `world_model.md` §12
(1 the 0.1 m truth resolution, 2 the band gate, 3 CSG footprints' timing); roadmap "Open questions" (turn length,
pip-installable server, copyright holder). Steps 5 and 6 assume Q2's answer ("two PRs"), and step 5 can't name a
package until Q1 is answered; Q3 decides what step 2's base branch even is. L6 claims the checker catches a missing
open question; it reads only npcs §12.1. Fix: list them in §5 with status; extend `check_plan.py` to every `## 12.`
section and the roadmap's open questions, or narrow L6's claim.

**B4. Steps 5 and 8 reverse the design's own order (plan L89, L92).** `world_model.md` §10 row 2: "Parts 1, 2 and 3
of this design accepted", before 2b `phase1/boundaries`; backlog B19 (1) lands "once `docs/design/boundaries.md`
merges". The plan writes part 3 *after* step 5 and has no "designs accepted" or "PR #4 merged" step; step 5 is
blocked only by steps 2–3. Either the plan is changing the order (then say so and record it as a decision, and fix
world_model §10) or it misstates it. Fix: add "the owner accepts parts 1–2 (PR #4 merges)" as a step blocking 5, and
decide whether part 3 still precedes 2b.

## SHOULD-FIX

**S1. O11 is misstated (plan L52 vs npcs §0 O11, O16).** Plan: "in co-op, until OD-H5 exists, O16 applies". O11
"Needs OD-H5 first", so until OD-H5 O16 governs *both* modes: dilate in single-player, silent late landing in co-op.
The plan's row implies single-player holds the floor before OD-H5. Fix: "until OD-H5 exists, O16 applies (dilate
single-player, silent late landing co-op)"; also carry O11's guards (a yield never feeds fatigue, credit or learning;
dilate stays for experiments and the lockstep reference).

**S2. "Plus the decomposition slice" is dropped three times (L58, L95, L134 vs npcs O15a, roadmap L188, §12.2).**
O15a: "Phase 4's first real NPCs wait for 1.4.0 plus that slice". The plan says 1.4.0 only. That slice carries the
stepped `think` (OD-A15), so 1.4.0 alone is not the gate.

**S3. O13 is presented as current when §6.6 replaced its mechanism (L55 vs npcs §0 O13, §6.6 L777–778,
`executor_wire.md` S4).** O13 still says `spawn`, a pipe and a scrubbed environment; §6.6 uses `subprocess.Popen`,
a socketpair and an allowlist. S4 asked for a dated note on O13 and a flag for the owner; neither exists. The plan
should mark O13 "mechanism pinned by §6.6 (v3.1), owner to confirm", as it does for O6 → O6a.

**S4. O19 cites the wrong step (L62).** "(§3, step 5)": step 5 is `phase1/boundaries`; `phase1/agents` is step 7.

**S5. Two claims about the sources are false at 72bf36c (L164, L171–172).** 72bf36c ("Fix the contradictions the
plan surfaced") marked §12.1 items 2, 6 and 7 decided and changed §12.2's credit line to "closes with OD-A1 (#1361
S3a)". The plan, at the same commit, still says both are unfixed. Delete both remarks. (Items 6 and 7's bodies still
end "The owner decides" / "Proposed:", which could get a "decided by O16/O17" note.)

**S6. Owner questions marked decided that aren't, and owner decisions recorded only in the plan (L154, L159–160,
L128).** Item 1: the OS sandbox for guest workers is still an open proposal (npcs L1143–1145, roadmap L198); the plan
says decided. Item 5: the source has five proposals, not four (filler propensity was added in v3.1), and "the owner
said to take all four" appears in no source, nor does "the owner said go" (L128). An owner decision that exists only
in a status file is the Exec3 N9 problem: record it in npcs §0 (O20, say) or mark it unconfirmed, and say whether
filler propensity is in.

**S7. Branch and PR facts (L11, L16, L19, step 2).** `origin/phase1/standards` is `87593fe` (pushed), not `e5aa3e1`;
`origin/phase1/design-v2` is `72bf36c`, not `73c0eb8`. PR #1's base is `foundations/world-server-v0`, not `main`, so
"land PR #1" merges into a branch that `boundaries.md` §11.3 proposes abandoning (Q3); the plan names neither that
branch nor `phase1/transport`. §11.3's proposed merge order (act-validation first) is reversed by steps 2–3 with no
note that it's superseded. PR #3 (merge-base `9bad3bd`) needs a rebase too.

**S8. "Every owner decision" isn't (§2 heading, L6).** `world_model.md` §0 D20–D25 are owner decisions (2026-11-16)
the next PRs rest on (D20's 0.1 m truth, D21, D25's physics standard), and the checker's regex can't see `D\d+`. Add
a §2.x for them or narrow the heading; extend `check_plan.py` to `world_model.md`.

**S9. Exit tests heading (L148)** — see N9; promoted here only if the owner uses that row as the Phase 3 exit
checklist, since EA4/EA6/EA9 are not Phase 3 exit tests in the roadmap. Otherwise a NIT.

**S10. Stale source text the plan should flag, as it did (wrongly, S5) for §12.2.** Roadmap L119 OD-A18 "After
OD-A19" (withdrawn); roadmap L188 "OD-A1 to OD-A19"; roadmap L198 still "Proposed for the owner: … remote model
egress" (decided, and stronger, by O18) and Phase 4 lists five gates, not six; `boundaries.md` §7.4 L599 "otherwise it
dilates" (O16 says co-op lands silently); npcs §6.2 still the three-method port (`executor_wire.md` S1 open);
`boundaries.md` §11.1 "the worker processes … arrive with `phase1/lanes`", while O19 and world_model row 9b put the
worker channel and a spawned double in `phase1/agents`. The plan silently uses the corrected versions (A1–A18, O19's
tests), so a reader who follows the link ("the linked document wins", L5) gets the stale one.

**S11. Step 1 sends a correction that no longer covers the whole error (L85).** Maxim's merged candidates doc
already adopted our wrong claim (B2: "NAc's event time is the wall clock, `decisions/nac.py:1162`", L285) and says
A3 "does not own decay timing" (L113–116, that is #1361's). `correction_1.md` corrects only `reply.md` §7. Update it to
name the candidates doc's B2 line before the owner pastes it; "blocked by nothing" should be "blocked by that edit".

**S12. Red-first test 4 drops half of its BLOCKER's fix (L107–108 vs `determinism_bio.md` DB-B3).** DB-B3 names two
load-bearing parts: the double's `think` must fold its step sequence and staleness verdict into its output, *and* the
agent digest joins the compared set. With only the digest, a scripted double resumed early produces the same output
and state, and the plant still can't go red. Add the first part.

## NIT

- **N1.** Conditions dropped from one-line summaries: O3 (integer ticks; "and O6a"), O4 (the abandon policy, "by
  cause"), O5 ("additive first in 1.x"), OA1 (closed vocabulary; experiments on fixed defaults), OA5 (feeds sleep
  pressure), O7a (the worker-process clause; npcs has its own O7a row).
- **N2.** O7's row doesn't say its condition is met (npcs §0 does). "PR 1" in the design docs is act-validation;
  "PR #1" here is standards. One sentence would prevent a cold reader mixing them.
- **N3.** O6a's row attributes `step`, `settle` and `apply` to O6a; they come from §6.6 and world_model row 9b.
- **N4.** npcs §0's two unnumbered "—" decisions are absent.
- **N5.** Standards: the concurrency guard list omits `tests/test_prepush.py::…named_in_the_environment`; "Maxim's
  process by kind" is guarded by "`docs/roadmap.md`, B1", not B1 alone; `31818e1` (record lessons, B18) is after the
  branch point and missing, if it was this session's.
- **N6.** "The world half is converged" (L78) has no source.
- **N7.** Red-first test 3 is from O19's list, not an open npcs_v3_1 BLOCKER; DB-B1 (resolved by withdrawing
  OD-A19) isn't mentioned.
- **N8.** §4 "Asked (`reply.md`)" lists the original questions `response.md` answers; the accepted-pushback and
  correction summaries are partial (Jefferson 1989 for the 1 s yield; the wake-word and prefetch corrections; the
  S3a τ question).
- **N9.** L148 "Exit tests named in the roadmap" includes OD-EA4, EA6, EA9, which the roadmap doesn't name.
- **N10.** §5.2 omits "prompt and dial-invisibility tests red until tier A"; B12 is partly in place on
  act-validation; partial rows TBR-11 and TB3-S8 still say "the owner decides" a gate O18 has decided.
- **N11.** §5.1 item 2: "the general disclosure wording is still to write" is the plan's addition, fine, but it is a
  new open item and has no owner or step.
- **N12.** §2.3 says `87593fe` "gate pending" and L16 "gate run in progress": unverifiable here; give the PASS line or
  say none exists yet.
- **N13.** L11 "Sessions push only their own branch" is right per standards CLAUDE.md L207–210, but design-v2's own
  CLAUDE.md still says "Never push"; it changes on rebase (step 4), worth a word.
- **N14.** Step 11's "OD-A1 to OD-A18" includes OD-A13, which moved to OD-I3.
- **N15.** §4 "Accepted by Maxim" could cite the candidates doc's tiers now that it exists (B1).
- **N16.** The red-first test lead-in says "from the open BLOCKERs"; there are seven BLOCKER entries across the three
  npcs_v3_1 files (ATR-B1, B2; DB-B1–B3; EW B1, B2), four distinct after merging duplicates, plus DB-B1 resolved:
  saying that would show the mapping is complete.
