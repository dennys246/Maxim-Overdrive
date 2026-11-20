# Foundations plan: from here to the first visible tile

For the owner and any session starting cold: where things stand, what comes next, what is open. Paths are on
`phase1/design-v2` unless a branch is named. `scripts/check_plan.py` checks that every decision, Phase 3 id and open
question is present (not true) and the 2,500-word budget. Source: the review in `docs/plans/reviews/`;
`reviews/fold.md` maps each finding to where it went and keys the ids; `checklists.md` holds the steps' items.

## 1. Status, as of 2026-11-18

| PR | Branch (worktree) | Base | Owner |
|---|---|---|---|
| #1 | `phase1/standards` | `main` | this line |
| #2 | `phase1/act-validation` | `phase1/standards` | the other session |
| #3 | `phase1/realtime-design` | `phase1/standards` | the other session |
| #4 | `phase1/design-v2` | `phase1/standards` | this line |
| — | `phase1/tile-spec` (step 0d) | `phase1/design-v2` | this line |

Each branch has a worktree of its name under `.worktrees/`. Heads: `git log`.

**Security gate.** Private since 2026-11-17. design-v2's history and PR #4 hold OD-I5's details; before going
public, the owner decides on a force-push plus GitHub support for PR #4's refs. Security findings go to private notes.

## 2. The order: tile first (D26)

Phase 1's exit (`docs/roadmap.md`): walk into the alley, set a crate on fire, watch it crack, glow and burn away by a
fuel-mass law, the same apart from detail at each rendering tier.

| # | Step | Blocked by | Owner | First action | Done when | Extra lenses | Closes |
|---|---|---|---|---|---|---|---|
| 0a | A `.venv` per worktree | nothing | each session | `python3 -m venv .venv && .venv/bin/pip install -e '.[dev,maxim]'`; record `pip show pymaxim` | the gate runs with no `PYTHON=` | none | shared-venv hazard (B20) |
| 0b | Owner answers §5's open questions | nothing | owner | read §5 | done 2026-11-17, bar copyright | none | |
| 0c | Send `erratum_1.md` to the Maxim session | nothing | owner | paste it | sent 2026-11-18 | none | |
| 0d | Tile spec: `tile_and_client.md` (world) and `client_rendering.md` (Godot), each ≤ 6,000 words (O31) | nothing | this line | draft it | its review folded and accepted | Bio-faithful, Client, Physics | |
| 1 | The merge line, per `docs/merge_notes.md` on `phase1/realtime-design`: act-validation into realtime-design, then standards, then design-v2; merge, never rebase (O21). Until it lands, `phase1/standards:CLAUDE.md` governs. This line's items: `checklists.md` | 0a | owner merges; each session does its branch's items | read the notes | CI's `prepush` passes on each merge commit; `main` carries the four branches | per merge | |
| 2 | Godot skeleton in `client/`: 4.7.2 pinned, typed GDScript, warnings as errors, `godot_check.py` in the gate, a Linux CI golden job | 1 (PR #1 on `main`) | this line | `client/project.godot` | deletion fixtures go red; the golden job passes | Client and rendering | B6 |
| 3a | `phase1/boundaries`, structure only: the engine package `simcore`, 3–4 layers (O24), import contracts | 1 | this line | split `scripts/lint_standards.py` into one module per check first | no behaviour change; import-linter in the gate | Determinism | B19 (1), B19 (4) |
| 3b | `phase1/gates`, scoped to what the tile calls: frames as copies, validating constructors, the gate registry, the write window as a dev check (O8) | 3a | this line | `simcore` gate registry | every gate's rejection paths tested | Trust boundary, Determinism | |
| 4 | `phase1/verify`, slim: refine space and time separately; heat retrofitted; the resolution rule becomes the verification rule (D20) | 3b | this line | the harness | heat's order-of-accuracy test passes for the right reason | Physics and resolution | |
| 5a | `phase1/sim-clock` (O34): `Simulation`, tick (T3), 0.1 m truth, law list, field registry, intent log | 4, 3b | this line | a composition note | bit-identical replay; CPU time measured | Physics, Determinism, Performance | B2, B5 |
| 5b | `phase1/bodies`: bodies, `move`/`move_to`, vocabulary v1 | 5a | this line | the actor table | replay of a movement script | Determinism, Wire | |
| 6 | Fire (D30, T13): 6a open-air loss, 6b skin, 6c porous bed, 6d char oxidation; constants cited, never fitted | 5b | this line | flip `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating` red-first | tile §6.3 passes at three grids, or fails to the owner | Physics, Determinism | fire burnout gap |
| 7 | `phase1/protocol` v0: versioned `welcome`, `intent_result`, `regions`; WebSocket on 127.0.0.1 with the token and `Origin` refusal; golden fixtures read by Python and Godot; the guest-join red gate | 5b, 2, 0d | this line | `tests/fixtures/wire/` | both readers pass the fixtures | Wire, Trust, Concurrency, Determinism | B3, B14 |
| 8 | The tile: the alley, movement, the client drawing snapshots, one crack-and-glow shader (never colour alone), golden screenshots per tier | 6, 7, 0d | this line | the alley scene | the exit scenario passes automatically, then a playtest | Client and rendering, Physics | B7 |
| 9 | Save v0: grid, scene, actor and pilots tables | 8 | this line | save fixture | round trip, golden save | Wire, Determinism | B4 |
| 10 | Grey-box heat-debt prototype (D28), then the clinic (D27) | 8 | this line | a one-page design note | a playtest verdict: fun or not, and why | Client and rendering | |

**In parallel, off the path:**
- **The LLM spike (O20):** a throwaway `spikes/llm/` script, no Maxim: latency, tokens, cost, NPCs per local
  model, into `docs/design/research/llm_spike.md`.
- **The agent line, as tests (O19),** against the scripted double behind the real worker channel, after steps 5a and 7: types,
  codec, `data/agents/` gates; the worker channel; `AgentPort`, the double, the membrane. Red-first tests:
  1. a hash probe in the worker's first frame (`-I` ignores `PYTHONHASHSEED`);
  2. the worker's `HOME`, `XDG_*`, `TMPDIR`, `HF_HOME` under the agent home, probed, with a planted real-home read;
  3. the codec refuses a pickle;
  4. resume at the modelled landing tick, with a state digest that can go red;
  5. credit shares at two step rates, a strict red gate against pymaxim;
  6. a tool's duration comes from the host in world time, never `tool_dispatch.py:1419`'s wall clock.

  It owns the thinking lane (npcs §6.2) and stays in Phase 1 (O19, against S-S1). Checklist: `checklists.md`.
- **Real NPCs** wait for Maxim's stepped `think` (O15a, O29).

**Deferred to Phase 2 (D26, D29):** zones and vents, combustion per zone, pyrolysis, phase change, CSG, the lab. Save with agents: Phase 4 (roadmap). The clinic: §5.

## 3. Maxim (`origin/main` f0b1cea4)

**Done there:** the candidates doc (`docs/plans/overdrive_refactor_candidates.md`, #1688); #1684 (OD-I1), #1685
(OD-I3, absorbing OD-A13), #1686 (OD-I4); OD-I5 a private advisory; #1687 closed (real NPCs on macOS and
Linux only); #1396 (O18's guards). OD-I2
stays a nit.

**Exchanged:** `erratum_1.md` sent 2026-11-18 (OD-A20, OD-A21; OD-A19 withdrawn). Maxim's answer
(`response_4.md`): 1.4.0 planned March–May 2027; the world-seam front gate accepted. Its plan review of O35's draft: SOUND WITH CONDITIONS (2026-11-19); v4 folds it, v5 its delta review.

**Phase 3 ids, by where Maxim put them** (detail: `docs/plans/reviews/maxim_side.md` §1):
- Tier A: OD-A1 (#1361), OD-A20 (declined), OD-A21 (#1361 Q1), OD-A2, OD-A3, OD-A4, OD-A8 (A3); OD-A5 (split with #1361); OD-A7 (A2, a gate item after 1.4.0); OD-A12 (A1,
  with #984); OD-A11, OD-A17 (A4, behind the front gate).
- Tier B: OD-A10, OD-A14, OD-A15 (B1, B3); OD-A16, OD-A18 (B2, #1150).
- Tier C: OD-H2 (C2), OD-H4 and OD-H5 (C5), OD-H6 (C3, disagreeing), OD-H1, OD-HX1, OD-HX5 (cautions).
- Not in it yet: OD-C11 (proposed, tile §9), OD-A6, OD-A9, OD-H3, OD-X1, OD-X2; OD-B1, OD-B2, OD-B3, OD-B4, OD-B5, OD-B6, OD-B7 (Exp 64a's
  prerequisites), OD-B8, OD-B9, OD-B10, OD-B11, OD-B12, OD-B13; OD-C1, OD-C2, OD-C3, OD-C4, OD-C5, OD-C6, OD-C7,
  OD-C8, OD-C9, OD-C10.
- Exit tests: OD-WC1, OD-EA4, OD-EA5, OD-EA6, OD-EA7, OD-EA9, OD-EA10, OD-EA11, OD-EA12, OD-EA14, OD-EA15.

## 4. Decisions

**boundaries §0:**

| Id | Decision |
|---|---|
| O1 | One repository, an enforced engine/game boundary, a written split trigger |
| O2 | Superseded by O6 |
| O8 | The write window is a dev check; correctness rests on structure |
| O21 | Merge, never rebase; PR #1 targets `main` |
| O22 | Word budget: design docs don't grow; new ≤ 6,000; plan ≤ 2,500; review ≤ 3,000 |
| O23 | boundaries §12 answered as recommended |
| O24 | Three or four layers, splitting at the tripwire |
| O25 | Reviewers set fold status |
| O32 | Lock every dependency; a scheduled drift job |
| O33 | Python 3.12+ |
| O34 | Step 5 splits into 5a and 5b |
| O41 | Roadmap exempt |
| O42 | Checklists exempt from O22 |

**both §0:**

| Id | Decision |
|---|---|
| O3 | The substrate outside the sealed core behind `AgentPort`, in ticks; refined by O6, O6a |
| O4 | Three clocks; no time field reaches cognition; thought cost modelled in world time; late thoughts dilate; thinking couples to fatigue `[engineering]` |
| O5 | Refining SEM is in scope, through Maxim's process, additive first |
| O6 | A host-driven embeddable agent contract; mechanism corrected by O6a |
| O7 | World half proceeds, agent half parked; its condition is met (O7a) |
| O7a | The agent half unparked for one revision; a worker process per real agent |

**npcs §0:**

| Id | Decision |
|---|---|
| O6a | `think` host-called, resumable, returning model requests as values |
| O9 | A reply's content may only make it land later, never earlier |
| O10 | No real Maxim before tier A, except in strict red gates |
| O11 | End state: live play holds the floor rather than dilating; amended by O11a; until OD-H5, O16 applies |
| O11a | Filler, then an account (onset 600–1000 ms), then a yield after 1 s of silence; per world, *to verify* |
| O12 | Processing speed is a per-NPC trait in world time, never the hardware's |
| O13 | A worker process per real agent is the trust boundary (§6.6: subprocess, socketpair, env allowlist) |
| O14 | Guest sessions wait for five gates (sixth: O18) |
| O15 | Engineering seams accepted on engineering grounds |
| O15a | The stepped `think`: after 1.4.0 and the decomposition slice, in the 1.5 hybrid src phase |
| O16 | Until OD-H5, in both modes: dilate in single-player, silent late landing in co-op, an explicit exception to O4 and O12 |
| O17 | Guests' speech purged on request, never in a bug report |
| O18 | Guest sessions use a local model by default; remote needs the guest's informed consent |
| O19 | The agent half frozen at v3.1; its findings become red-first tests (§2) |
| O20 | The LLM spike is allowed, without Maxim |
| O26 | A purge leaves redaction records; replay exact to the first redacted reply |
| O27 | Co-op listeners perceive lateness (a known gap) |
| O28 | Co-op in Phase 5 or later; no more co-op rounds |
| O29 | A minimal tier-A subset, a 1.4.0 date range, a second candidates round |
| O30 | §12.1's rest answered; sandbox and slow tail deferred by name |
| O35 | Send the agent draft to Maxim |
| O36 | Maxim's review reopens the agent |
| O37 | Bridge NPC after the tile |
| O38 | Maxim's §A.1b.5 staleness |
| O39 | `apply` merged into `settle`: three host calls |
| O40 | `make_agent_rng` plus a stream argument |
| OA1 | A thought's kind from the agent's policy, a closed vocabulary; a logged host table sets cost |
| OA2 | Dilation shown on a three-handed clock |
| OA3 | No conversational repertoire of our own; proposed to Maxim as OD-H5 |
| OA4 | Speech stamped per syllable |
| OA5 | One mental-fatigue drive feeding sleep pressure `[engineering]` |

**world_model §0:**

| Id | Decision |
|---|---|
| D20 | One simulation truth, 0.1 m cells; rigs are rendering tiers |
| D21 | Resolution follows the world, not the machine |
| D22 | Rubble and collapse in Phase 2, foundations now |
| D23 | Amended by D26: the lab is Phase 2's benchmark tile |
| D24 | Three design documents, each reviewed |
| D25 | Reconstruct, decide at the point, integrate upward |
| D26 | Tile first; the exit as above; lab fires to Phase 2 |
| D27 | The clinic after the exit; §12 answered |
| D28 | A grey-box heat-debt prototype before more physics |
| D29 | Step 6 adds open-air loss, the surface skin, sub-cell recession |

**tile §0:**

| Id | Decision |
|---|---|
| T1 | Isometric 3/4 camera |
| T2 | Click-to-move and WASD, both validated intents |
| T3 | Tick 0.1 s, physics every 0.5 s |
| T4 | `kindle`, power from a held item |
| T5 | A body heat state from Phase 1 |
| T6 | File OD-C11 |
| T7 | Walk direction an integer vector, canonical |
| T8 | Compatibility renderer |
| T9 | No client prediction |
| T10 | Elevation 40° |
| T11 | Walls-down with stumps |
| T12 | Goldens gated in Linux CI |
| T13 | Tile spec frozen at v3 |

Unnumbered (npcs §0): the thought-cost unit as fine as useful; test per Maxim tier. New standards on
`phase1/standards`: separation of concerns, size tripwires, concurrent agents, search Maxim first, the push rule.

## 5. Open questions

### Open: boundaries §12
1. O23 (`simcore`).
2. O23.
3. O23.
4. O23.
5. O23.

### Open: world_model §12
1. D27.
2. D27.
3. D27.

### Open: npcs_and_sem §12.1
1. O14; the OS sandbox deferred to before guest sessions (O30).
2. O18.
3. O30.
4. O30.
5. O30; the slow tail and filler propensity after the LLM spike.
6. O16.
7. O17, with O26's mechanism.

### Open: tile §9
1. Flame radiation into bodies: yes.
2. 20 mm slats at φ 0.25: yes.
3. v0 freezes only sent kinds: yes.

### Open: client §10
None (T8–T12).

### Open: roadmap
1. Turn length: settle in the tile spec (0d).
2. The world server as a pip dependency of Maxim: Phase 3.
3. Copyright holder: still the owner's call.

**Still open elsewhere:** Windows NPCs before Phase 8 (`checklists.md`); the guest-text gate's ZWNJ and ZWJ rule
(step 7); whether F-S9's exit-test line is Phase 3's checklist (`fold.md`).

## 6. Risks

- **Designing forever:** about 372,000 words against under 1,700 lines of code (`reviews/skeptic.md`). Answer:
  O22, tile first, O19.
- **Timing on a shared machine:** load passes 20 with concurrent sessions, so budgets gate CPU time, the minimum
  of N runs, never wall time (SEQ-S10).
