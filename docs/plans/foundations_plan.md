# Foundations plan: from here to the first visible tile

For the owner and any session starting cold: where things stand, what comes next, what is open. Paths are on
`phase1/design-v2` unless a branch is named. `scripts/check_plan.py` fails if this drops a decision, a Phase 3 id or an
open question, or passes 2,500 words; it checks presence, not truth. Source: the review in `docs/plans/reviews/`;
`reviews/fold.md` maps each finding to where it went and keys the ids; `checklists.md` holds the steps' items.

## 1. Status, as of 2026-11-17

| PR | Branch (worktree) | Base | Head (local / origin) | Owner |
|---|---|---|---|---|
| #1 | `phase1/standards` (`.worktrees/standards`) | `main` (retargeted) | `87593fe` / `87593fe` | this line |
| #2 | `phase1/act-validation` (`.worktrees/act-validation`) | `phase1/standards` | `0480ab6` / `0480ab6` | the other session |
| #3 | `phase1/realtime-design` (`.worktrees/realtime-design`) | `phase1/standards` | `6291fd0` / `6291fd0` | the other session |
| #4 | `phase1/design-v2` (`.worktrees/design-v2`) | `phase1/standards` | ahead / `72bf36c` | this line |

"This line" works in `.worktrees/standards` and `.worktrees/design-v2`; "the other session" in the other two. The
main checkout is the owner's, on `main`. Nothing has merged to `main` yet.

**Security gate.** Private since 2026-11-17. `phase1/design-v2`'s history and PR #4 hold an advisory's details
(OD-I5). Before going public, the owner decides on history: an approved force-push, plus GitHub support for PR #4's
refs. Security findings go to private notes.

## 2. The order: tile first (D26)

Phase 1's exit (`docs/roadmap.md`): walk into the alley, set a crate on fire, watch it crack, glow and burn away by a
fuel-mass law, the same apart from detail at each rendering tier.

| # | Step | Blocked by | Owner | First action | Done when | Lenses beyond the three always run | Closes |
|---|---|---|---|---|---|---|---|
| 0a | A `.venv` per worktree | nothing | each session | `python3 -m venv .venv && .venv/bin/pip install -e '.[dev,maxim]'`; record `pip show pymaxim` | the gate runs with no `PYTHON=` | none | shared-venv hazard (B20) |
| 0b | Owner answers §4's open questions | nothing | owner | read §4 | each answered or deferred by name | none | |
| 0c | Send `docs/design/reviews/maxim_response_1/erratum_1.md` (answering `response_3.md`) to the Maxim design session | nothing | owner | paste it there | Maxim acknowledges | none | |
| 0d | Tile spec, `docs/design/tile_and_client.md` (≤ 6,000 words): the alley in metres, player movement, camera, the exit scenario, snapshot channels to 3-D textures, one shader, the golden-screenshot method | nothing | this line | draft it | its design review is folded and accepted | Bio-faithful, Client and rendering, Physics | |
| 1 | The merge line, per `docs/merge_notes.md` on `phase1/realtime-design`: act-validation into realtime-design, then standards, then design-v2; merge, never rebase (O21). Until it lands, `phase1/standards:CLAUDE.md` governs. This line's items: `checklists.md` | 0a | owner merges; each session does its branch's items | read the notes | CI's `prepush` passes on each merge commit; `main` carries the four branches | per merge | |
| 2 | Godot skeleton in `client/`: 4.7.2 pinned, typed GDScript, warnings as errors, a headless check in the gate and CI, one golden frame | 1 (PR #1 on `main`) | this line | `client/project.godot` | the gate runs Godot headless and passes | Client and rendering | B6 |
| 3a | `phase1/boundaries`, structure only: the engine package (`simcore`, proposed), the layers, import contracts | 1, 0b (Q1, Q2) | this line | split `scripts/lint_standards.py` into one module per check first | no behaviour change; import-linter in the gate | Determinism | B19 (1), B19 (4) |
| 3b | `phase1/gates`, scoped to what the tile calls: frames as copies, validating constructors, the gate registry, the write window as a dev check (O8) | 3a | this line | `simcore` gate registry | every gate's rejection paths tested | Trust boundary, Determinism | |
| 4 | `phase1/verify`, slim: refine space and time separately; heat retrofitted; the resolution rule becomes the verification rule (D20) | 3b | this line | the harness | heat's order-of-accuracy test passes for the right reason | Physics and resolution | |
| 5 | `phase1/sim-clock`: `Simulation`, integer tick, 0.1 m truth, preallocated buffers, the intent log and a replay test | 4, 0d (turn length) | this line | `Simulation` | bit-identical replay; turn time measured on a quiet machine | Physics, Determinism, Performance | B2, B5 |
| 6 | Fuel by mass: fuel by volume overlap, a burn law, burnout, material table v1 with provenance | 5 | this line | flip `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating` red-first | closed-form and verification tests pass; the gap closes | Physics, Determinism | fire burnout gap |
| 7 | `phase1/protocol` v0: versioned `welcome`, `act_result`, `error`; WebSocket on 127.0.0.1 with the token and the `Origin` refusal; golden wire fixtures read by Python and Godot; the lane skeleton; the guest-join red gate | 5, 2, 0d | this line | `tests/fixtures/wire/` | both readers pass the fixtures | Wire, Trust, Concurrency, Determinism | B3, B14 |
| 8 | The tile: the alley, movement, the client drawing snapshots, one crack-and-glow shader (never colour alone), golden screenshots per tier | 6, 7, 0d | this line | the alley scene | the exit scenario passes automatically, then a playtest | Client and rendering, Physics | B7 |
| 9 | Save v0: grid plus scene spec | 8 | this line | save fixture | round trip, golden save | Wire, Determinism | B4 |

**In parallel, off the path:**
- **The LLM spike (O20):** a throwaway `spikes/llm/` script, raw model calls, no Maxim, on a quiet machine: latency,
  tokens, cost, NPCs per local model. Results in `docs/design/research/llm_spike.md`.
- **The agent line, as tests (O19),** against the scripted double behind the real worker channel, after steps 5 and 7: types,
  codec, `data/agents/` gates; the worker channel; `AgentPort`, the double, the membrane. Red-first tests:
  1. a hash probe in the worker's first frame, so a worker started with `-I` (which ignores `PYTHONHASHSEED`) fails;
  2. the worker's `HOME`, `XDG_*`, `TMPDIR`, `HF_HOME` under the agent home, probed, with a planted real-home read;
  3. the codec refuses a pickle;
  4. resume at the modelled landing tick, with a state digest folding the double's steps and staleness, so it can go red;
  5. credit shares at two step rates: a strict red gate against pymaxim, not a test the double can turn green;
  6. a tool's duration comes from the host in world time, never `tool_dispatch.py:1343`'s wall clock.

  It owns the thinking lane (npcs §6.2). It stays in Phase 1 against S-S1: O19 chose tests over paper. Its PR
  checklist, reopen triggers included, is in `checklists.md`.
- **Real NPCs** wait for Maxim's stepped `think` (cand. B1; O15a), not only 1.4.0.

**Deferred to Phase 2 (D26):** zones and vents, combustion per zone, fuel recession and pyrolysis, phase change, the
CSG footprints, the lab. Save with agents: Phase 4 (roadmap). The clinic: §5.

## 3. Maxim, as of `origin/main` 6fee7377

**Done there:** the candidates doc (`docs/plans/overdrive_refactor_candidates.md`, #1688); #1684 (OD-I1), #1685
(OD-I3, absorbing OD-A13), #1686 (OD-I4); OD-I5 a private advisory; #1687 closed (the latch refuses off POSIX, so
real NPCs are macOS and Linux only); #1396 (routers ask before a download; O18 must guard a silent cloud fallback and
a blocking prompt). OD-I2 stays a nit.

**We owe:** `erratum_1.md`, our reply to Maxim's answer to `correction_1.md`: it splits the planted-render test,
brings evidence to Maxim's #1361 question on anchor similarity (OD-A20), argues τ_elig against #1361 Q1 (OD-A21),
discloses OD-I5's exposure, and answers the front gate (why the 1.1.4 seam can't serve Overdrive). OD-A19 is withdrawn.

**Phase 3 ids, by where Maxim put them** (detail: `docs/plans/reviews/maxim_side.md` §1):
- Tier A: OD-A1 (#1361), OD-A20, OD-A21 (#1361 questions), OD-A2, OD-A3, OD-A4, OD-A8 (A3); OD-A5 (split with #1361); OD-A7 (A2, #1305); OD-A12 (A1,
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
| O3 | The substrate outside the sealed core behind `AgentPort`, in ticks; refined by O6, O6a | both §0 |
| O4 | Three clocks; no time field reaches cognition; thought cost modelled in world time; late thoughts dilate; thinking couples to fatigue `[engineering]` | both §0 |
| O5 | Refining SEM is in scope, through Maxim's process, additive first | both §0 |
| O6 | A host-driven embeddable agent contract; mechanism corrected by O6a | both §0 |
| O6a | `think` host-called, resumable, returning model requests as values | npcs §0 |
| O7 | World half proceeds, agent half parked; its condition is met (O7a) | both §0 |
| O7a | The agent half unparked for one revision; a worker process per real agent | both §0 |
| O8 | The write window is a dev check; correctness rests on structure | boundaries §0 |
| O9 | A reply's content may only make it land later, never earlier | npcs §0 |
| O10 | No real Maxim before tier A, except in strict red gates | npcs §0 |
| O11 | End state: live play holds the floor rather than dilating; amended by O11a; until OD-H5, O16 applies | npcs §0 |
| O11a | Filler, then an account (onset 600–1000 ms), then a yield after 1 s of silence; per world, *to verify* | npcs §0 |
| O12 | Processing speed is a per-NPC trait in world time, never the hardware's | npcs §0 |
| O13 | A worker process per real agent is the trust boundary (§6.6: subprocess, socketpair, env allowlist) | npcs §0, §6.6 |
| O14 | Guest sessions wait for five gates (sixth: O18) | npcs §0 |
| O15 | Engineering seams accepted on engineering grounds | npcs §0 |
| O15a | The stepped `think`: after 1.4.0 and the decomposition slice, in the 1.5 hybrid src phase | npcs §0 |
| O16 | Until OD-H5, in both modes: dilate in single-player, silent late landing in co-op, an explicit exception to O4 and O12 | npcs §0 |
| O17 | Guests' speech purged on request, never in a bug report | npcs §0 |
| O18 | Guest sessions use a local model by default; remote needs the guest's informed consent | npcs §0 |
| O19 | The agent half frozen at v3.1; its findings become red-first tests (§2) | npcs §0 |
| O20 | The LLM spike is allowed, without Maxim | npcs §0 |
| O21 | Merge, never rebase; PR #1 targets `main` | boundaries §0 |
| O22 | Word budget: design docs don't grow; new ≤ 6,000; plan ≤ 2,500; review ≤ 3,000 (proposed) | boundaries §0 |
| OA1 | A thought's kind from the agent's policy, a closed vocabulary; a logged host table sets cost | npcs §0 |
| OA2 | Dilation shown on a three-handed clock | npcs §0 |
| OA3 | No conversational repertoire of our own; proposed to Maxim as OD-H5 | npcs §0 |
| OA4 | Speech stamped per syllable | npcs §0 |
| OA5 | One mental-fatigue drive feeding sleep pressure `[engineering]` | npcs §0 |
| D20 | One simulation truth, 0.1 m cells; rigs are rendering tiers | world_model §0 |
| D21 | Resolution follows the world, not the machine | world_model §0 |
| D22 | Rubble and collapse in Phase 2, foundations now | world_model §0 |
| D23 | Amended by D26: the lab is Phase 2's benchmark tile | world_model §0 |
| D24 | Three design documents, each reviewed | world_model §0 |
| D25 | Reconstruct, decide at the point, integrate upward | world_model §0 |
| D26 | Tile first; the exit as above; lab fires to Phase 2 | world_model §0 |

Unnumbered (npcs §0): the thought-cost unit as fine as useful; test per Maxim tier. New standards on
`phase1/standards`: separation of concerns, size tripwires, concurrent agents, search Maxim first, the push rule.

## 5. Open questions, with recommendations

### Open: boundaries §12
1. Engine package name: `simcore` (proposed).
2. Structure, then behaviour: yes (3a, 3b).
3. Abandon `phase1/transport` and `foundations/world-server-v0`: yes, `phase1/standards` contains both.
4. Imagination budgets: engine mechanism, per-actor values in game data: yes.
5. Frames on change, not per tick: yes.

### Open: world_model §12
1. Truth at 0.1 m: yes.
2. The band gate for binary outcomes: yes.
3. CSG: Phase 2.

### Open: npcs_and_sem §12.1
1. Decided (O14); the OS sandbox for guest workers is open: decide before guest sessions.
2. Decided (O18).
3. OD-A16 gates Phase 4: yes.
4. `speak` text out of bug reports by default: yes.
5. The speed trait: take the age shift, the general-plus-domain factor, the weak gap loading; the slow tail and
   filler propensity after the LLM spike.
6. Decided (O16).
7. Decided (O17).

### Open: new in the fold
1. Purge versus replay (O17; TB-B3): guests' words sit in stores, continuation bodies, cache, saves and the log.
   Redaction records, or refuse replaying a purged session? Before the codec's kinds freeze (`purge` is one).
   Recommend redaction records.
2. Co-op lateness (O16; DB-S5): listeners perceive it (a Known gap), or it is hidden (an oracle). Phase 4; recommend
   perceive.
3. The clinic: the roadmap's tile names it; this plan builds the alley. Recommend it after the exit.
4. Skeptic S-S4 to S-S7, all recommended yes: 3–4 boundary layers; co-op in Phase 5+; a minimal tier-A subset and
   a 1.4.0 date range from Maxim; a grey-box heat-debt prototype after the tile.
5. Phase 3 items the candidates doc lacks (MS-S9): a second candidates round after tier A.

### Open: roadmap
1. Turn length: settle in the tile spec (0d).
2. The world server as a pip dependency of Maxim: Phase 3.
3. Copyright holder: owner's call.

**Also open:** reviewers, not authors, set fold status? Recommend yes.

## 6. Risks

- **Designing forever.** About 372,000 words of design and review against under 1,700 lines of code
  (`reviews/skeptic.md`). The answer: O22, tile first, the agent half frozen (O19) with errata only.
- **Fold tables overstated five times;** a reviewer set this round's (`fold.md`).
- **Timing on a shared machine:** load passes 20 with concurrent sessions, so budgets gate CPU time, the minimum
  of N runs, never wall time (SEQ-S10).
