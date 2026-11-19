# Executor lens, delta round 1: real time, lanes and co-op (design v1)

Reviewed `docs/design/realtime_lanes_coop.md` v1 and `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md` at 02338ef,
against this repo's code and Maxim at 4b773ef8. Scope: (1) did v1 fold X1 to X8 and the NITs correctly; (2) the
factual claims v1 makes that v0 didn't. Quick checks ran with `.venv/bin/python` on the crate scene from
`tests/test_cross_tier.py` and the steel bar from `tests/test_heat.py`. The scripts are not committed.

No BLOCKER. Five SHOULD-FIX, five NIT.

## Fold status of round 1

| Finding | Folded? | Note |
|---|---|---|
| X1 cost table | Partly | The table is now CP-1's tile numbers, quoted correctly. But §2.3's title "at no extra cost" and §1's "4 to 14 times" don't match those numbers (DX1). |
| X2 rig field | Partly | It's an integer now, but what it means for an advance that isn't one physics period is undefined, and "re-derive the closed-form error figures" was dropped (DX2). |
| X3 second clock | Mostly | `grid.time_s`, `turn` and `turn_seconds` go. The sensor and snapshot consumers aren't named, and `seconds` isn't made required (DX7). |
| X4 experience driver | Yes | §3.3 and item 12. |
| X5 TemporalSignature | Mostly | Local time and 86,400 are in §3.2. The SHAPE-FROZEN constraint and the `memory.timestamp` / `BoundedBin.add` stamps are missing from item 10 (DX10). |
| X6 hybrid runtime and DN | Yes, with a NIT | Deferred status is cited (item 17); "every DN timer" covers the throttlers; the non-visual channel and suppression are listed as work to do. Decision 1 still talks about the hybrid runtime in the present tense (DX6). |
| X7 modulator validation | Yes | PR 1. I reconfirmed that a NaN `ignite` returns `success=True`, and that after one `advance(0.5)` 100% of cells are NaN (§1's claim is true). |
| X8 live tick assignment | Yes | §4.2. |
| N1 to N4 | Yes | 51.2 MB/s is no longer quoted; the axis order is in §7; the integer clock is in §2.2; the stale docs are under "Supersedes". |

## SHOULD-FIX

### DX1. "Physics on a period, at no extra cost" is false by v1's own table. The caching fix doesn't remove the 3x / 1.5x / 1.125x substep increase.

- **Location:** §2.3, the heading and the cost table; §1, the third bullet ("about 4 to 14 times dearer").
- **What happens:**
  - With `substeps_per_physics_step` 1 / 2 / 6 at a 0.5 s step, a 6 s world interval takes 12 / 24 / 72 substeps,
    against today's 4 / 16 / 64. The caching fix removes the per-call `_power_field` and `stable_dt` work. It
    doesn't remove the substeps, which are the cost that remains.
  - The table leaves out CP-1's "today" row: about 600x / 21x / 0.8x. Next to it, the "with the caching fix" column
    (300x / 20x / 0.75x) is half today's headroom on the laptop, and slightly below today's on rig and max. So
    physics is dearer even after the fix.
  - "4 to 14 times dearer": CP-1's tile gives 13.5x, 4.3x and 1.8x (laptop, rig, max). Round 1's crate run gave 9.9x,
    5.7x and 2.6x. The low end is about 2x, not 4x.
- **Failure:** a reader takes "no extra cost" and budgets the laptop profile at today's headroom. B5's first rows
  in PR 2 then show the laptop at half that, with no root cause left to find. Precision-equal and cost-equal can't
  both hold at a 0.5 s step, because 4/12, 16/12 and 64/12 aren't integers. The period is world config, so it
  can't vary by rig without breaking the resolution rule.
- **Fix:** retitle §2.3 to something like "the root fix comes first". Add today's column to the table. Say that
  finer substeps cost 3x / 1.5x / 1.125x per world second and that this is accepted. Change §1 to "about 2 to 14
  times".

### DX2. `substeps_per_physics_step` has no defined meaning for an advance of any other length, and two tests v1 names depend on that.

- **Location:** §2.3, the first and third bullets. In code: `world/world.py::World.advance`,
  `world/heat.py::step` (`n = max(min_substeps, ceil(seconds / stable_dt))`), `tests/test_heat.py::_error` and
  `test_insulated_world_conserves_heat`, and the closed-form figures in `docs/architecture.md` ("1% / 0.1% / 0.01%").
- **What happens:**
  - `heat.step` applies its substep count to whatever `seconds` it is given. §2.1 keeps `World.advance(seconds)`.
  - **The period-split cross-tier test** ("one 6 s run against twelve 0.5 s steps"): if the field is passed
    through as `min_substeps`, the 6 s leg takes 1 / 2 / 6 substeps of 6 / 3 / 1 s. That is far coarser than
    today's 1.5 / 0.375 / 0.094 s. The test then compares two different solvers, not one physics split two ways.
  - **The closed-form test.** I ran it with the new values passed to the 3600 s step. On the laptop, stability now
    binds at 3 substeps where `min_substeps` used to force 4, and the error rises from **0.99% to 1.84%**. The test
    bound is 2%. Rig and max don't change (stability binds there anyway: 21 and 125 substeps). The `test_heat.py`
    rewrite would pass by a margin of 0.16 percentage points, and the architecture doc's "1%" would become false.
  - "Precision is never coarser than today at any rig" is true on the physics-period path. It is not true for any
    caller that passes a longer interval.
  - Round 1's X2 fix asked for re-derived error figures. v1 dropped that. v1 also doesn't list
    `tests/test_validation.py` (lines 31 and 202 use `min_substeps_per_turn`), or `test_heat.py:77`'s hard-coded
    `min_substeps=4` for a 6 s step.
- **Failure:** either the cross-tier test is weaker than it looks, or the closed-form test quietly loses half its
  margin. Neither change is visible in the diff.
- **Fix:** define the field as a step length, `dt = physics_step / substeps_per_physics_step`, and make the solver
  take `max_dt`. Then any interval gets `ceil(seconds / max_dt)` substeps, with the stability limit on top. As an
  alternative, `World.advance` could take a count of physics steps rather than seconds. Say which in §2.3. Have
  `test_heat.py` use the same `max_dt`. Re-derive and restate the closed-form figures. List the
  `test_validation.py` sites.

### DX3. The cache's invalidation list misses `paint`, and sources are a bare dict with no place to hook a version bump.

- **Location:** §2.3, the second bullet ("a version counter that adding a source, removing one and `destroy` all
  bump"). In code: `world/grid.py::MaterialGrid.paint`, called by `imagination/spec.py::place` (line 95);
  `sem_env/bridge.py::StructureModulator.execute`, which writes `self._world.sources[...] = HeatSource(...)` and
  `.pop(...)` directly (lines 151 and 156).
- **What happens:**
  - `stable_dt` depends on each cell's material. The power weighting uses `frac * grid.solid`.
  - `imagination.spec.place` turns air into solid through `paint`, which isn't on the list. A crate imagined into
    a burning fire's sphere would leave the cached weights depositing power on the old cells, and would leave
    `stable_dt` stale.
  - `World.sources` is a plain `dict`. Writing to it directly can't bump anything. Re-igniting a region also
    *replaces* a source under the same key, which is neither an add nor a remove.
- **Failure:** the cached power field goes stale after an imagined object is placed. The heat goes to cells that
  are no longer the solid ones in the sphere, and how far off it is depends on the rig. The closed-form cache test
  that §2.3 promises would only cover the change kinds it was listed with.
- **Fix:** route every material write (`paint`, `destroy`) through one version on the grid, and every source
  change through `World` methods (`set_source`, `remove_source`) that bump it. Then make `sources` read-only from
  outside. The "cached equals fresh" test should cover each writer: place, destroy, strike, a source added,
  replaced and removed.

### DX4. Item 17 cites the wrong revive trigger, and leaves out that Maxim's owner has already declined this re-key.

- **Location:** §6 item 17, decision 9, §9 Q3, and the 1.5 draft ("This line would revive that plan, on a
  simulated body"). In Maxim: `docs/plans/outstanding.md` M76,
  `docs/plans/deferred/hybrid_substrate_reflex_runtime.md` (header), and `docs/plans/grounding.md` (G4, lines 65,
  720 and 813).
- **What happens:**
  - M76 is the tripwire for `deferred/second_body_staging.md` and `deferred/microduck_intent_layer.md`. The hybrid
    plan's trigger sits in its own header: "a second robot body physically exists".
  - That header carries **owner decision G4 (2026-10-07): "this trigger is NOT re-keyed"**. It also says that
    re-reading the gate "is a question at GL3's start". `grounding.md:720` and `:813` place that question at
    GL3.B0.
  - v1 proposes the re-key without naming the decision it reverses, and without naming the route Maxim already set
    for reconsidering it.
- **Failure:** under decision 10 ("push back through Maxim's own process"), the issue lands in Maxim citing M76.
  Maxim's reviewers then find a standing owner decision that the proposal doesn't mention, and send it back.
- **Fix:** cite the plan header and G4. Frame item 17 as an input to the GL3.B0 question, with the game's evidence
  (a controllable simulated body) as the argument for re-reading it. Drop M76, or cite it only as the tripwire for
  the Microduck plans. Make the same correction in the 1.5 draft.

### DX5. Decision 10's pushback on `experience_clock_decay.md` §(g) covers only the SCN row, but item 11 contradicts another row of §(g) too.

- **Location:** §6 items 10 and 11. In Maxim: `docs/plans/experience_clock_decay.md` §(g).
- **What happens:**
  - §(g) keeps several things on the wall clock "on purpose". One is the SCN phase row, which v1 does name. Another
    is **"PainBus refractory, reflex cooldowns: motor/IO rate limits; hardware safety"**.
  - Item 11 asks for "every DN timer on the injected clock". On a dialled world, a wall-clock reflex cooldown means
    a different number of reflexes per world second at each dial setting, and replays come out timing-dependent.
- **Failure:** item 11 reaches Maxim contradicting a by-design row it doesn't cite. Or Maxim builds item 11 with the
  cooldowns kept on the wall clock, as §(g) says, and tier 1 replays with real agents never become bit-identical.
- **Fix:** name the cooldown and refractory row in item 11's pushback, with the distinction that resolves it: a
  physical robot's IO rate limit stays on the wall clock, while a simulated body's cooldown is world time.

## NIT

- **DX6, ids that collide and a present tense (§6 item 11; decision 1).**
  - Item 11 cites "the hybrid plan's BL-2, A3, A4, SF-1, SF-2". In that plan, A3 is NAc isolation (BL-4) and A4 is
    bearing IOR (BL-5). Item 11's text mentions neither.
  - Line 6 of v1 also says that ids like A3 point into Overdrive's review files, where A3 means agent state written
    during LLM calls.
  - Fix: write them as "hybrid plan A3 (BL-4), A4 (BL-5)", and add those two to the item's text. Also, decision 1
    still says "Maxim's hybrid runtime puts a fast substrate loop…" in the present tense; add "(deferred; X6)".
- **DX7, X3's consumers (§1, §2.1, Supersedes).**
  - `grid.time_s` feeds `sem_env/bridge.py::RegionSensor.read` (`timestamp=`) and `world.py::snapshot`
    (`"time_s"`). The tests that read it are `tests/test_snapshot.py:23` and `tests/test_determinism.py:60`, and
    `tests/test_validation.py:136` asserts `w.turn == 1`.
  - §2.1 says `World` has no clock, but `RegionSensor` holds only a `World`. Say where the sensor gets the tick.
  - Say that `World.advance`'s interval becomes required (keyword-only), since `turn_seconds` goes. List these
    sites under "Supersedes".
- **DX8, "O(cells x 64) work per call regardless of whether anything changed" (§2.3).**
  - The overlap cost is per source: 64 passes for each source. With no sources it is zero, because `_power_field`
    returns `None`. `stable_dt` adds another O(cells) per call.
  - Measured on the crate: `advance(0.5)` takes 0.44 ms with no source and 1.03 ms with one (laptop), and 7.9 ms
    against 10.3 ms (rig).
  - Fix: write "O(sources x cells x 64), plus O(cells) for the stability limit, on every call".
- **DX9, "Maxim's SCN has no intrinsic period apart from the clock it's given" (§3.4).**
  - `time/oscillator.py` has `_NATURAL_FREQUENCIES` (1 cycle per day, then per 7, 30 and 365.25 days). Bio-7 named
    those as the oscillator's ω.
  - The accurate claim is that ω is defined in the clock's day units, and that `observe` soft-resets the phase
    toward the signature's phase (blend >= 0.1). That is why it entrains perfectly.
  - Fix: reword. The conclusion still holds: a real experiment needs ω separate from the world's day.
- **DX10, small Maxim descriptions (§3.3, §6).**
  - "Most decay in Maxim still runs on the wall clock": per #1361's own audit, NAc decay is paced by loop passes,
    and only the windows and body drift run on the wall clock. Say "on loop passes and the wall clock".
  - "`AgentPool`, which has no body, drives or DN": the pool holds whole instances, but its `run_turn` path touches
    only `hippocampus` and `nac`. Say "whose turn path steps no body, drives or DN".
  - Item 10 should add X5's points that v1 dropped. `TemporalSignature` is SHAPE-FROZEN, so only defaulted
    trailing fields can be added. Memories are stamped from `memory.timestamp`, and `BoundedBin.add` stamps with
    `time.time()`.

## Checked and found correct

- **The rig values.** 1 / 2 / 6 at a 0.5 s step give 0.5 / 0.25 / 0.083 s substeps, all finer than today's 1.5 /
  0.375 / 0.094 s on the physics-period path. Stability doesn't bind on the crate (`stable_dt` is 240 / 60 / 15 s).
  There are exactly two `test_heat.py` calls passing the rig field (lines 23 and 44).
- **The cost table.** CP-1's numbers are quoted as measured: about 44x / 5x / 0.4x as designed, and 300x / 20x /
  0.75x with the fix. CP-1 gives no method for the fix row, so "estimated" is the honest label. The tile is
  16x10x4 m, as stated. CP-9's 100 ms and 1.2 s figures are quoted correctly, and so is CP-10's "24x not reachable
  on rig even fixed" (about 20x).
- **The sphere overlap.** `sphere_overlap` is 64 passes over the whole grid, and `_power_field` calls it once per
  source per `power()` call. `stable_dt` depends only on materials, so caching it behind a materials version is
  sound. `finite_vector` exists in `world/scene.py`.
- **NaN `ignite`.** A NaN `ignite` makes every cell NaN after one advance (measured, 100%), because NaN times a
  zero weight is NaN.
- **The experience clock (§3.3).** `ExperienceClockDriver` takes the duck-typed `experience_turns()` and a positive
  int `experience_us_per_turn`. In the turns kind, a world with no new ticks gains no experience. The driver
  advances only in `on_live_pass`.
- **#1361.** It exists as `docs/plans/experience_clock_decay.md`, PROPOSED, with owner decisions from 2026-10-17.
  Its scope is NAc decay, eligibility and the temporal windows, `Embodiment.advance` and `decay_all`, as v1 says.
  §(g) lists "SCN phases, `TemporalSignature` similarity: host calendar by design".
- **`NAc.recommend_action`.** It is keyword-only and returns `None` when no tool clears `min_confidence` (default
  0.3), with no random fallback.
- **`AgentPool.run_turn`.** Its docstring says it "does NOT run the full agent loop". It writes `hippocampus`
  before the LLM and `nac` after it.
- **The hybrid plan.** It is DEFERRED 2026-09-19 with the physical second-body trigger, and BL-1 to BL-5, SF-1 and
  SF-2 exist as the 1.5 draft says.
- **Item 15's evidence.** The global `random` appears in DN (`gaze_manager.py`, `movement_utils.py`), and
  `uuid4` / `time.time()` in `memory/hippocampus.py`.
- **The 1.5 draft's references.** Items 11, 12, 13, 15 and 16 map to the prerequisites it names. Its references to
  1.4's grounding line and to Reachy and the Microduck resolve.
- **The finding ids v1 cites.** I checked every id from my lens and a sample from the others (X1 to X8, X-N2 to
  X-N4, CP-1, CP-9, CP-10, Bio-7, TB-1): each says what v1 attributes to it, except the DX6 collision. The README's
  Executor counts (1 / 7 / 4) are right.
