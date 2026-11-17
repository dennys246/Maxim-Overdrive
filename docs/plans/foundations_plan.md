# Foundations plan: where things stand and what comes next (2026-11-17)

Written for the owner and for any session picking this work up cold. It records every decision made so far, the
order of the next steps and what blocks what, and the state of the work with Maxim. It links to the detailed
documents rather than repeating them; where this file and a linked document disagree, the linked document wins and
this file is stale. `docs/plans/check_plan.py` fails if a decision id, a Phase 3 item or an open owner question in the
sources is missing here.

## 1. Where things stand

Four draft PRs, all based on `phase1/standards` (PR #1). Sessions push only their own branch; the owner reviews and
merges (§2.4).

| PR | Branch (worktree) | What it holds | State |
|---|---|---|---|
| [#1](https://github.com/dennys246/Maxim-Overdrive/pull/1) | `phase1/standards` (`.worktrees/standards`) | The engineering standards, the pre-push gate, the lessons document, the transport decision | Local head `87593fe` (search-Maxim-first rule), gate run in progress; `e5aa3e1` pushed with `prepush: PASS e5aa3e11518f` |
| [#2](https://github.com/dennys246/Maxim-Overdrive/pull/2) | `phase1/act-validation` (`.worktrees/act-validation`) | PR 1: SEM actions validated at the trust boundary; closed loader schemas; versioned data formats (its B21) | **Another session's work, still active.** Local head `0480ab6`, remote `2f200b5`. Don't touch it until that session hands it off. Needs a rebase onto standards. |
| [#3](https://github.com/dennys246/Maxim-Overdrive/pull/3) | `phase1/realtime-design` (`.worktrees/realtime-design`) | The real-time, lanes and co-op design v1 and its reviews (partly superseded), plus the other session's marker-lint work | **Another session's branch.** Local head `6291fd0`, remote `a8225d1`; that session reported `prepush: PASS 8a0b32523bd6` at `8a0b325`. |
| [#4](https://github.com/dennys246/Maxim-Overdrive/pull/4) | `phase1/design-v2` (`.worktrees/design-v2`) | The design: [boundaries](../design/boundaries.md), [world model](../design/world_model.md), [NPCs and SEM](../design/npcs_and_sem.md), the research, every review record, the Maxim drafts and this plan | Docs only; pushed at `73c0eb8`. Branched from standards at `15bd3aa`, so it needs a rebase. |

The main checkout belongs to the owner and is on `main` (`d02c0a2`, the initial commit). `main` has no `.gitignore`
or source yet, so the shared `.venv`'s editable install points at an empty `src/` there (§5.6).

## 2. Every owner decision

### 2.1 Boundaries (`docs/design/boundaries.md` §0)

| Id | Decision |
|---|---|
| O1 | One repository, with an enforced engine/game boundary and a written split trigger. |
| O2 | *Superseded by O6.* The action-result contract "(a) now, (b) later". |
| O3 | The agent substrate runs outside the sealed core, behind an engine-defined `AgentPort`; refined by O6: the host steps it. |
| O4 | Three clocks (world, body, perceived); no time field reaches cognition; thought cost modelled in world time and phased; couples to fatigue and sleep pressure, not hunger. Its "the world slows when thoughts run late" is refined by O11 and O16. |
| O5 | Refining Maxim's SEM is in scope and a priority of the foundations work, through Maxim's process. |
| O6 | Mode (a) dropped; agents follow a host-driven embeddable contract. Its mechanism is corrected by O6a. |
| O7 | The world half proceeds; the agent half parked until Maxim answered. |
| O7a | Maxim answered, so the agent half was unparked for one revision and one review round (done; now frozen by O19). |
| O8 | The write window is a dev and test-build check; correctness rests on structure. |

### 2.2 NPCs and SEM (`docs/design/npcs_and_sem.md` §0)

| Id | Decision |
|---|---|
| O6a | O6's mechanism corrected after Maxim's answers: no inner tool loop; `AgentPort` is host-called `step`, resumable `think` and `settle`, plus `apply`. |
| OA1 | A thought's kind is chosen by the agent's policy before the call; a logged, host-only settings table may override its modelled cost. |
| OA2 | The player sees dilation on a three-handed analogue clock, blue/red for slowing and speeding. |
| OA3 | Overdrive builds no conversational repertoire of its own; *revised*: the turn-taking substrate is proposed to Maxim as OD-H5 and is an OPEN divergence until it lands. |
| OA4 | Speech is stamped per syllable. |
| OA5 | One mental-fatigue drive that rises with load, per-kind load weights; recovers with rest and sleep; separate from stamina. |
| O9 | A reply's content may only make it land later, never earlier (capped, counted against the dilation budget). |
| O10 | No developer mode with real Maxim before tier A, except inside strict red-gate tests. |
| O11 | Live play holds the floor instead of dilating; amended by O11a; in co-op, until OD-H5 exists, O16 applies. |
| O11a | Floor-holding is filler, then an account at about 600–700 ms, then a yield at about 1 s, thresholds per world in world time; the first filler from the modelled delay; a lateness meter per machine. |
| O12 | Processing speed is a per-NPC trait in world time (lognormal, median 1 at a reference age, sigma about 0.15), never read from hardware. Refinements proposed in §12.1 item 5. |
| O13 | Each real Maxim agent runs in its own worker process; the process boundary is the trust boundary. Detailed in §6.6. |
| O14 | Guest sessions with real-Maxim NPCs wait for five gates; O18 adds a sixth. |
| O15 | Engineering seams are asked of Maxim on engineering grounds, not behind the hybrid line's experiment gate. |
| O15a | Maxim's answer: the clock seam and dispatch/settle go in as refactors behind a parity guard; the stepped `think` lands after the 1.4.0 cut, so Phase 4's real NPCs wait for 1.4.0. |
| O16 | Interim live-play policy: dilate in single-player (shown on the clock); silent late landing in co-op. |
| O17 | Guests' speech held agent-side is purged on request and never shipped in a bug report. |
| O18 | Guest sessions use a local model only by default; a remote model needs a disclosure the guest accepts. |
| O19 | The agent half is frozen at v3.1; its remaining blockers become red-first tests in `phase1/agents` (§3, step 5). |

### 2.3 Standards added this session (`CLAUDE.md` on `phase1/standards`)

| Standard | Commit | Guard |
|---|---|---|
| Separation of concerns; no god functions (review-held) | `441509f`, `9da35f2`, `cabee85` | Architecture lens, B19 |
| Size tripwires: complexity 10, 40-line bodies, 500-line modules, 12 public methods; limits only tighten | same | `check_sizes`, `check_size_ratchet`, ruff canary tests |
| Assume other agents are working: one worktree per session, main checkout is the owner's, no shared temp paths or fixed ports, tests' git only through `tests/_gitutil.py`, no install into a shared venv | `0bed47b` | `refuse_main_branch`, `tests/test_isolation.py`, B20 |
| Search Maxim before proposing to it | `87593fe` (gate pending) | Bio-faithful lens, B22 |
| Maxim's process described by kind of change | `d75b134` | B1 |

### 2.4 Working decisions

- **Pushing** (`e5aa3e1`): a session may push its own `phaseN/<step>` branch to keep its draft PR current; never `main`,
  never force, never another session's branch, never merge.
- **Stop paper rounds on the agent half** (O19); the world half is converged.
- **Backlog numbering:** B21 is reserved by the other session on `phase1/act-validation`; this line used B22.

## 3. The plan, in order

| # | Step | Blocked by | Owner |
|---|---|---|---|
| 1 | Send Maxim [`correction_1.md`](../design/reviews/maxim_response_1/correction_1.md) | nothing | owner (paste) |
| 2 | Land PR #1 (standards) once its gate passes | owner's review | owner |
| 3 | Rebase PR #2 onto standards and hand off | the other session finishing its delta round | other session |
| 4 | Rebase PR #4 (this design) onto standards | step 2 | this line |
| 5 | **`phase1/boundaries`** ([`world_model.md` §10](../design/world_model.md) row 2b): packages and layers, import-linter contracts (B19 (1)) | steps 2–3 | this line |
| 6 | **`phase1/gates`** (row 2c): gates by input source and the gate registry | step 5 | this line |
| 7 | **`phase1/agents`** (row 9b): `AgentPort` against the scripted double behind the real worker channel, with the red-first tests below | step 6 | this line |
| 8 | Part 3, `lab_and_core_loop.md` | step 5 | this line |
| 9 | Per-worktree `.venv`s for this line's worktrees | nothing | this line |
| 10 | The calibration ledger: provenance for every tunable in `data/`, with a lint and a ranked report of guesses. **Proposed, not designed**; its first row is the speed spread (O12) | step 5 | this line |
| 11 | Phase 4's first real NPCs | Maxim tier A, OD-A1 to OD-A18, and the 1.4.0 cut (O15a) | both |

**Red-first tests for step 7** (O19), from the open BLOCKERs in
[`reviews/npcs_v3_1/`](../design/reviews/npcs_v3_1/):

1. **The hash seed is in effect in the worker:** the worker's first frame carries a hash probe that must match the
   pinned seed. Starting the worker with `python -I` ignores `PYTHONHASHSEED`, so this test must go red under `-I`
   (`executor_wire.md` B1, `architecture_trust.md` B1).
2. **The worker can't reach the owner's home:** `HOME`, the `XDG_*` variables, `TMPDIR` and `HF_HOME` point under the
   agent home, and a no-effect test that covers reads as well as writes finds nothing outside it (Python falls back
   to the password database when `HOME` is unset; `architecture_trust.md` B2).
3. **The channel codec refuses a pickle** and any unknown version (O13, §6.6).
4. **Resume happens at the modelled landing tick:** an agent-state digest in the comparison, so the resume test can
   fail when `think` resumes on wall arrival (`executor_wire.md` B2, `determinism_bio.md` B3).
5. **Credit at two step rates:** replace OD-EA12 with a test of credit shared among several traces and of trace expiry
   into the wall-clock fallback, since a lone trace gets full credit at any rate (`determinism_bio.md` B2).

The SHOULD-FIX and NIT findings of that round are the frozen design's known-issues list; each becomes a test or a
backlog row when `phase1/agents` touches it.

## 4. The Maxim side

**Asked** (`reply.md`, [`docs/design/reviews/maxim_response_1/`](../design/reviews/maxim_response_1/)): a resumable
`think`, how far the advisor stretches, a turn-taking substrate, determinism hooks, the pickle load.

**Accepted by Maxim** ([`response.md`](../design/reviews/maxim_response_1/response.md),
[`response_2.md`](../design/reviews/maxim_response_1/response_2.md)): the request/reply cut and host-called `think`;
the machinery clock plus perceived-time port with a planted-render test and a prompt-module lint; multi-call
deliberation and a frozen continuation with `basis_seq`; reserved `cancelled`/`truncated` reply variants; the
embedded-path leak closure; keyed substreams; the clock seam and dispatch/settle as refactors behind a parity guard.
Pushback we accepted: no `__str__`-less type as the guard; keyed `random.Random` over Philox; the stepped `think` after
1.4.0.

**Pending from Maxim:** the ranked candidates document (they offered; the owner said go); filing OD-I3 (pickle),
OD-I1 (all five sites), OD-I4 (`ARCHITECTURE.md:182`) and OD-I5 (the redaction question).

**Owed to Maxim:** `correction_1.md`, which withdraws our wall-clock decay claim (it is #1361 S3a, our OD-A1) and asks
whether S3a covers the temporal-anchor fallback that still reads the host clock.

**Phase 4's real NPCs depend on** Maxim tier A and the 1.4.0 cut (O15a); until then everything is built against the
scripted double.

### Phase 3 items ([`docs/roadmap.md`](../roadmap.md) Phase 3)

| Status | Items |
|---|---|
| Issues, to file now | OD-I1, OD-I3, OD-I4, OD-I5; OD-I2 downgraded to a docstring nit |
| Tier A, active | OD-A1 (a dependency on #1361), OD-A2, OD-A3, OD-A4, OD-A5, OD-A6, OD-A7, OD-A8, OD-A9, OD-A10, OD-A11, OD-A12, OD-A14, OD-A15, OD-A16, OD-A17, OD-A18 |
| Tier A, moved or withdrawn | OD-A13 (moved to OD-I3); OD-A19 (withdrawn: duplicated #1361 S3a; now a question in `correction_1.md`) |
| Tier B, the 1.4 line | OD-B1, OD-B2, OD-B3, OD-B4, OD-B5, OD-B6, OD-B7, OD-B8, OD-B9, OD-B10, OD-B11, OD-B12, OD-B13 |
| Tier C, SEM additive | OD-C1, OD-C2, OD-C3, OD-C4, OD-C5, OD-C6, OD-C7, OD-C8, OD-C9, OD-C10 |
| Tier C, the hybrid line | OD-H1, OD-H2, OD-H3, OD-H5, OD-H6; OD-H4 folded into OD-H5 |
| Experiments that earn mechanisms | OD-X1 (an entrained clock), OD-X2 (state-dependent timing); the hybrid questions OD-HX1 to OD-HX5 |
| Exit tests named in the roadmap | OD-WC1; the embeddable draft's OD-EA4, OD-EA5, OD-EA6, OD-EA9, OD-EA10, OD-EA11, OD-EA12 (OD-EA12 to be replaced, §3 test 5) |

## 5. Open questions and known risks

### 5.1 Owner questions in `npcs_and_sem.md` §12.1

1. Guest sessions: decided (O14, plus O18's sixth gate).
2. Local or remote LLM: decided by O18 for guests; the general disclosure wording is still to write.
3. The stale-refusal fix (OD-A16) gates Phase 4: confirm the ordering.
4. Bug reports and dialogue: `speak` text redacted by default; is that right, or should the reporter choose? (O17
   settles it for guests.)
5. The speed trait's structure: age shift, a general factor plus domain residuals, turn gaps mostly from the pair, an
   optional slow tail. Proposed; the owner said to take all four but it isn't recorded as a decision yet.
6. Interim live-play policy: decided (O16).
7. Retention of guest speech: decided (O17).

The text of items 2, 6 and 7 in §12.1 still reads as open; it should point at O16–O18.

### 5.2 Known OPEN divergences (`npcs_and_sem.md` §12.2)

Real Maxim reads the host clock and renders host time into prompts (tier A); two clocks reach one agent; memory writes
are ungated until OD-A18; memory authority waits for per-agent homes and pickle-free load; stale refusals and
slow-effect credit wait for OD-A16; the NPC is a statue in flight until OD-H5; real NPCs wait for 1.4.0;
LLM-bypassing replies on the core path until OD-A17; credit depends on the tick rate (**§12.2 still says this closes
with OD-A19; it closes with OD-A1, #1361 S3a**); model calls outside `think`; a shared router serialises inference; no
turn-taking substrate; the SCN phase and the weekly to annual scales are oracles; the interim coarse time readout is an
ANALOG; region sensors are omniscient instruments; outcome class isn't promised across model profiles.

### 5.3 Risks in how the work is done

- **Fold tables keep overstating.** Five rounds in a row the author's "folded" count was too high (most recently a
  claimed 165 was at most 155). The generator now refuses a missing id or a row with no place, but accepts a section
  that doesn't exist, and the status is the author's judgment. Proposed, not yet decided: the delta reviewer, not the
  author, sets each row's status.
- **Upstream asks that duplicate Maxim's own work** (three so far). Now a standard (search Maxim first, B22).
- **The shared `.venv`:** its editable install points at the main checkout's `src/`, which `main` doesn't have yet.
  Inside a worktree tests still work; outside one, `import maxim_overdrive` fails. Step 9 fixes it for this line.
- **Machine load:** concurrent sessions pushed the gate's test time from about 1 min to about 4 min (load average
  about 24). Timing results are noisy; the B5 performance budgets need a quiet machine, CPU time, or a minimum over
  repeated runs.
- **Open backlog rows that bear on the next steps:** B2 (replay), B3 and B4 (versioned formats), B5 (performance
  budgets), B9 (property tests), B12 (data files load), B14 (the server refuses bad clients), B19 (layer contracts,
  step 5), B20 (concurrency held by review), B22 (search Maxim first).
- **Partial fold rows** carried into `phase1/agents`: BD-1, BD-13, BD-14, BD-18, TBR-11, TB3-S8, Arch 1.2, Arch 4.3,
  Exec3 N8, and the rows the v3.1 delta round moved to partial
  ([`reviews/npcs_v3_1/executor_wire.md`](../design/reviews/npcs_v3_1/executor_wire.md)).
