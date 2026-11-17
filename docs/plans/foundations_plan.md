# Foundations plan: from here to the first visible tile

For the owner and any session starting cold: where things stand, what comes next, what is open. Paths are on
`phase1/design-v2` unless a branch is named. `scripts/check_plan.py` fails if this drops a decision, a Phase 3 id or an
open question, or passes 2,500 words; it checks presence, not truth. Source: the review in `docs/plans/reviews/`.

## 1. Status, as of 2026-11-17

| PR | Branch (worktree) | Base | Head (local / origin) | Owner |
|---|---|---|---|---|
| #1 | `phase1/standards` (`.worktrees/standards`) | `main` (retargeted) | `87593fe` / `87593fe` | this line |
| #2 | `phase1/act-validation` (`.worktrees/act-validation`) | `phase1/standards` | `0480ab6` / `0480ab6` | the other session |
| #3 | `phase1/realtime-design` (`.worktrees/realtime-design`) | `phase1/standards` | `6291fd0` / `6291fd0` | the other session |
| #4 | `phase1/design-v2` (`.worktrees/design-v2`) | `phase1/standards` | ahead / `72bf36c` | this line |

"This line" works in `.worktrees/standards` and `.worktrees/design-v2`; "the other session" in the other two. The
main checkout is the owner's, on `main`. Nothing has merged to `main` yet.

**Security gate.** The repository is private since 2026-11-17. `phase1/design-v2`'s history (and PR #4) holds the
details of a defect Maxim handles as a private advisory (OD-I5). Before it is public again: remove them from the
files, and the owner decides on history (an approved force-push, plus GitHub support for PR #4's refs, which a
force-push leaves). Security findings go to private notes from now on.

## 2. The order: tile first (D26)

Phase 1's exit (`docs/roadmap.md`): walk into the alley, set a crate on fire, watch it crack, glow and burn away by a
fuel-mass law, the same apart from detail at each rendering tier.

| # | Step | Blocked by | Owner | First action | Done when | Lenses beyond the three always run | Closes |
|---|---|---|---|---|---|---|---|
| 0a | A `.venv` per worktree | nothing | each session | in the worktree: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev,maxim]'`, then record `pip show pymaxim` | the gate runs with no `PYTHON=` | none | shared-venv hazard (B20) |
| 0b | Owner answers §4's open questions | nothing | owner | read §4 | each answered or deferred by name | none | |
| 0c | Send `docs/design/reviews/maxim_response_1/erratum_1.md` to the Maxim session | nothing | owner | paste a pointer to it | Maxim acknowledges | none | |
| 0d | Tile spec, `docs/design/tile_and_client.md` (≤ 6,000 words): the alley in metres, player movement, camera, the exit scenario, snapshot channels to 3-D textures, one shader, the golden-screenshot method | nothing | this line | draft it | its design review is folded and accepted | Bio-faithful, Client and rendering, Physics | |
| 1 | The merge line: follow `docs/merge_notes.md` on `phase1/realtime-design`; merge, never rebase (O21) | 0a | owner merges; each session does its branch's items | read the notes | every merged commit prints `prepush: PASS`, `main` carries the four branches | per merge | |
| 2 | Godot skeleton in `client/`: 4.7.2 pinned, typed GDScript, warnings as errors, a headless check in the gate and CI, one golden frame | 1 (PR #1 on `main`) | this line | `client/project.godot` | the gate runs Godot headless and passes | Client and rendering | B6 |
| 3a | `phase1/boundaries`, structure only: the engine package (`simcore`, proposed), the layers, import contracts | 1, 0b (Q1, Q2) | this line | split `scripts/lint_standards.py` into one module per check first | no behaviour change; import-linter in the gate | Determinism | B19 (1), B19 (4) |
| 3b | `phase1/gates`, scoped to what the tile calls: frames as copies, validating constructors, the gate registry, the write window as a dev check (O8) | 3a | this line | `simcore` gate registry | every gate's rejection paths tested | Trust boundary, Determinism | |
| 4 | `phase1/verify`, slim: refine space and time separately; heat retrofitted; under D20 the resolution rule becomes the verification rule | 3b | this line | the harness | heat's order-of-accuracy test passes for the right reason | Physics and resolution | |
| 5 | `phase1/sim-clock`: `Simulation`, integer tick, 0.1 m truth, preallocated buffers, the intent log and a replay test | 4 | this line | `Simulation` | bit-identical replay; turn time measured on a quiet machine | Physics, Determinism, Performance | B2, B5 |
| 6 | Fuel by mass: fuel by volume overlap, a burn law, burnout, material table v1 with provenance | 5 | this line | flip `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating` red-first | closed-form and verification tests pass; the Known gap closes | Physics, Determinism | fire burnout gap |
| 7 | `phase1/protocol` v0: versioned `welcome`, `act_result`, `error`; WebSocket on 127.0.0.1 with the token and the `Origin` refusal; golden wire fixtures read by Python and Godot; the lane skeleton | 5, 2 | this line | `tests/fixtures/wire/` | both readers pass the fixtures | Wire, Trust, Concurrency, Determinism | B3, B14 |
| 8 | The tile: the alley, player movement, the client drawing snapshots, one shader for crack and glow (never colour alone), golden screenshots per tier | 6, 7, 0d | this line | the alley scene | the exit scenario passes automatically, then a playtest | Client and rendering, Physics | B7 |
| 9 | Save v0: world grid plus scene spec | 8 | this line | save fixture | round trip plus a golden save | Wire, Determinism | B4 |

**In parallel, off the path:**
- **The LLM spike (O20):** a throwaway script in `spikes/llm/`, raw model calls, no Maxim, on a quiet machine:
  latency to first token and full reply, tokens, cost or local throughput, NPCs per local model. Results go in
  `docs/design/research/llm_spike.md`.
- **The agent line, as tests (O19),** against the scripted double behind the real worker channel, after step 5 (it
  needs the tick): types, codec and `data/agents/` gates; then the worker channel and environment; then `AgentPort`,
  the double and the membrane. Its red-first tests:
  1. a hash probe in the worker's first frame, so a worker started with `-I` (which ignores `PYTHONHASHSEED`) fails;
  2. the worker's `HOME`, `XDG_*`, `TMPDIR` and `HF_HOME` set under the agent home, with a probe that resolves Maxim's
     profile and key paths and a planted read of the real home;
  3. the codec refuses a pickle;
  4. resume at the modelled landing tick, with an agent-state digest the double's `think` folds its step sequence and
     staleness verdict into, so the plant can go red;
  5. credit shares at two step rates: a strict red gate against pymaxim, not a test the double can turn green.
- **Real NPCs** wait for Maxim's stepped `think` (candidates B1, the 1.5 hybrid line's src phase, after the 1.4.0
  cut and the decomposition slices), not only 1.4.0.

**Deferred to Phase 2 (D26):** zones and vents, fuel recession and pyrolysis, combustion per zone, phase change, the
CSG footprints, the lab, the thinking lane and save with agents.

## 3. Maxim, as of `origin/main` 6fee7377

**Done there:** the candidates doc (`docs/plans/overdrive_refactor_candidates.md`, #1688); #1684 (OD-I1), #1685
(OD-I3, which absorbed OD-A13), #1686 (OD-I4); OD-I5 as a private advisory; #1687 closed (the latch imports on
Windows but refuses to engage off POSIX, so real NPCs are macOS and Linux only); #1396 (directly built routers ask
before a download, so O18 must also guard a silent cloud fallback and a blocking prompt). OD-I2 stays a nit.

**We owe:** `erratum_1.md`, which withdraws `correction_1.md`'s anchor question (#1361 S3b answers it), fixes "10 Hz"
(4.75 s is the 2 Hz fixture; 0.95 s at 10 Hz), and answers the candidates doc's front gate (why the 1.1.4 world seam
can't serve Overdrive). OD-A19 is withdrawn as a duplicate of #1361.

**Phase 3 ids, by where Maxim put them** (detail: `docs/plans/reviews/maxim_side.md` §1):
- Tier A: OD-A1 (#1361), OD-A2, OD-A3, OD-A4, OD-A8 (A3); OD-A5 (split with #1361); OD-A7 (A2, #1305); OD-A12 (A1,
  with #984); OD-A11, OD-A17 (A4, behind the front gate).
- Tier B: OD-A10, OD-A14, OD-A15 (B1, B3); OD-A16, OD-A18 (B2, #1150).
- Tier C: OD-H2 (C2), OD-H4 and OD-H5 (C5), OD-H6 (C3, disagreeing), OD-H1, OD-HX1, OD-HX5 (cautions).
- Not in it yet: OD-A6, OD-A9, OD-H3, OD-X1, OD-X2; OD-B1, OD-B2, OD-B3, OD-B4, OD-B5, OD-B6, OD-B7 (Exp 64a's
  prerequisites), OD-B8, OD-B9, OD-B10, OD-B11, OD-B12, OD-B13; OD-C1, OD-C2, OD-C3, OD-C4, OD-C5, OD-C6, OD-C7,
  OD-C8, OD-C9, OD-C10.
- Exit tests: OD-WC1, OD-EA4, OD-EA5, OD-EA6, OD-EA9, OD-EA10, OD-EA11, OD-EA12.

## 4. Decisions

| Id | Decision | Where |
|---|---|---|
| O1 | One repository, an enforced engine/game boundary, a written split trigger | boundaries §0 |
| O2 | Superseded by O6 | boundaries §0 |
| O3 | The substrate runs outside the sealed core behind `AgentPort`, in integer ticks; refined by O6, O6a | both §0 |
| O4 | Three clocks; no time field reaches cognition; thought cost modelled and phased in world time; late thoughts dilate, abandoning is a logged host policy; thinking couples to fatigue and sleep pressure, not hunger | both §0 |
| O5 | Refining SEM is in scope and a priority, through Maxim's process, additive first in 1.x, each item citing its OD- id | both §0 |
| O6 | Mode (a) dropped; a host-driven embeddable agent contract. Its mechanism is corrected by O6a | both §0 |
| O6a | `think` is host-called and resumable and returns model requests as values; no inner tool loop | npcs §0 |
| O7 | World half proceeds, agent half parked; its condition is met (O7a) | both §0 |
| O7a | The agent half unparked for one revision and one round; each real agent in its own worker process | both §0 |
| O8 | The write window is a dev and test-build check; correctness rests on structure | boundaries §0 |
| O9 | A reply's content may only make it land later, never earlier | npcs §0 |
| O10 | No developer mode with real Maxim before tier A, except in strict red gates | npcs §0 |
| O11 | End state: live play holds the floor rather than dilating; amended by O11a; until OD-H5, O16 applies | npcs §0 |
| O11a | Filler, then an account at about 600–700 ms, then a yield at about 1 s; thresholds per world | npcs §0 |
| O12 | Processing speed is a per-NPC trait in world time, never the hardware's | npcs §0 |
| O13 | Each real agent in a worker process, the trust boundary; its mechanism is replaced by §6.6 (subprocess, socketpair, an environment allowlist) | npcs §0, §6.6 |
| O14 | Guest sessions with real NPCs wait for five gates (sixth: O18); the OS sandbox is still open | npcs §0 |
| O15 | Engineering seams accepted on engineering grounds | npcs §0 |
| O15a | The stepped `think` lands after 1.4.0 plus the decomposition slice, in the 1.5 hybrid src phase | npcs §0 |
| O16 | Until OD-H5, in both modes: dilate in single-player, silent late landing in co-op | npcs §0 |
| O17 | Guests' speech purged on request, never in a bug report | npcs §0 |
| O18 | Guest sessions use a local model by default; remote needs the guest's informed consent | npcs §0 |
| O19 | The agent half frozen at v3.1; its findings become red-first tests (§2) | npcs §0 |
| O20 | The LLM spike is allowed, without Maxim | npcs §0 |
| O21 | Merge, never rebase; PR #1 targets `main` | boundaries §0 |
| O22 | Word budget: no design doc grows; new ones ≤ 6,000 words; the plan ≤ 2,500; a review ≤ 3,000 (a standard still to write) | boundaries §0 |
| OA1 | A thought's kind from the agent's policy, a closed vocabulary; a logged host table may change its cost; experiments on fixed defaults | npcs §0 |
| OA2 | Dilation shown on a three-handed clock | npcs §0 |
| OA3 | No conversational repertoire of our own; proposed to Maxim as OD-H5 | npcs §0 |
| OA4 | Speech stamped per syllable | npcs §0 |
| OA5 | One mental-fatigue drive rising with load, per-kind weights, recovering with rest and sleep, feeding sleep pressure | npcs §0 |
| D20 | One simulation truth, 0.1 m cells; rigs are rendering tiers | world_model §0 |
| D21 | Resolution follows the world, not the machine | world_model §0 |
| D22 | Rubble and collapse in Phase 2, foundations now | world_model §0 |
| D23 | Amended by D26: the lab is Phase 2's benchmark tile | world_model §0 |
| D24 | Three design documents, each reviewed | world_model §0 |
| D25 | Reconstruct, decide at the point, integrate upward | world_model §0 |
| D26 | Tile first; the exit as above; lab fires to Phase 2 | world_model §0 |

Unnumbered (npcs §0): the thought-cost unit as fine as useful; lay foundations now and test per Maxim tier. Standards
added this session, on `phase1/standards`: separation of concerns with size tripwires, assume other agents are
working, search Maxim before proposing, and a session pushes only its own phase branch.

## 5. Open questions, with recommendations

### Open: boundaries §12
1. Engine package name: `simcore` (proposed).
2. Two PRs, structure then behaviour: yes (steps 3a, 3b).
3. Abandon `phase1/transport` and `foundations/world-server-v0`: yes, both are inside `phase1/standards`.
4. Imagination budgets as engine mechanism with per-actor values in game data: yes.
5. Frames published on change, not per tick: yes.

### Open: world_model §12
1. Truth resolution 0.1 m: yes.
2. The band gate for binary outcomes: yes.
3. CSG footprints: Phase 2 (D26).

### Open: npcs_and_sem §12.1
1. Decided (O14), but the OS sandbox for guest workers is open: decide before guest sessions, not before the tile.
2. Decided (O18).
3. OD-A16 gates Phase 4: yes.
4. `speak` text redacted from bug reports by default: yes.
5. The speed trait's five proposed refinements: take the age shift, the general-plus-domain factor and the weak gap
   loading; decide the slow tail and the filler propensity after the LLM spike.
6. Decided (O16).
7. Decided (O17).

### Open: roadmap
1. Turn length: settle in the tile spec (0d).
2. The world server as a pip dependency of Maxim experiments: defer to Phase 3.
3. Copyright holder: the owner's call.

**Also undecided:** whether reviewers rather than authors set fold status.

## 6. Risks

- **Designing forever.** About 372,000 words of design and review against under 1,700 lines of code
  (`reviews/skeptic.md`). O22's budget and tile first are the answer; the agent line stays frozen (O19), with errata
  only.
- **Fold tables overstated five times;** a script checks completeness, not truth.
- **Timing on a shared machine:** concurrent sessions push the load past 20, so budgets need a quiet machine.
