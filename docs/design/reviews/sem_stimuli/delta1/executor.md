# Executor, delta round 1: `docs/design/sem_stimuli.md` v2

**Revisions read.** Overdrive `phase1/sem-stimulus` at **3e97ac9** (v2, `fold.md`, my round-1 report). Maxim by
`git show origin/main:` at **043eab8f**, not fetched, no working tree read. One scratch measurement, run from the
session scratchpad against `_durable/sem_research/scratch/skin.py` (L3's column, 45 nodes), threads unpinned
(the result is a rounding question, not a timing one).

**Correction of my own round-1 advice, first.** B1's fix told the author to plant "a surface conductance, which moves
`tissue_temperature` at once". v2 took that, as "one ulp on the surface conductance". Measured, it is false: a one-ulp
change to `H_CONV` changes **no node of the column in 100 ticks at 2 kW/m²**, and the first change at 20 kW/m² is
**tick 42** (Δt = 0.1 s, backward Euler from steady state). The ulp of 8.0 is lost when it is added to the radiative
coefficient and to C/Δt. A 10⁻¹² relative change differs at tick 0 (2 kW/m²) and tick 1 (20 kW/m²). So v2's test, as
written on my advice, can stay green on the very mechanism it targets. Details under B1.

## Status of my round-1 findings

| Id | Status | Reason (read from v2) |
|---|---|---|
| B1 | **open** | plant moved below a bypassed header (right), but "one ulp … moves `tissue_temperature` on the first exposed tick" is false (measured above); the binding-order plant's location is ambiguous |
| S1 | fixed | §7.3 corrects the sentence; `agents-reads-body-frames` forbids `world`. Its fail-open shape is new finding X2 |
| S2 | fixed | §7.3 and §11.1: `_core_modules` recursive in 5a, every module and `__init__` classified, site names as handshake data |
| S3 | fixed | §2.4 states the 20%, moves accuracy to kelvin, error-controlled substeps; convergence before the law ships |
| S4 | fixed | §8 list retitled; staggered occlusion gone; tolerance, refresh, clustering and cutoff floors are header truth constants (§5), "never a rig field" (§2.4) |
| S5 | fixed | §4.2: `BodyFrameFeed` beside `Frame`, keyed by `npc_key`, `FrameView` never reaches it |
| S6 | **open** | effects stated in §4.4, but "one named modulator" is never named, and §3.3's first body declares sensors only, so nothing exists to host the backend |
| S7 | fixed | §9 M2 withdrawn, citing `setpoint_aware_neutral.md` and `world_channel_weighting.md:222` |
| S8 | **open** | oracle defined (byte-identical frames each tick), but the intent stream isn't held fixed, so the test is red by construction with live agents (below) |
| N1 | fixed | "twelve gates and a probe" matches §6.3's rows (T6 the probe); leak tests renamed. T2's gap and a broken table header are X5 |
| N2 | fixed | T12 plants are in the core (A built from B's store) and the channel (misroute) |
| N3 | deferred | accepted: 17 regions and 58 points used throughout §8; the buttocks share waits for Q1's convergence run (trigger: Q1), which §11.2 Q1 records |
| N4 | fixed | cited to `checklists.md:103`, which does say "each law split into `prepare` and an array-only kernel" |
| N5 | fixed | figure dropped from D1 |
| N6 | fixed | "yaw thresholds" |
| N7 | fixed | M4 "New, nearest home OD-A10"; M3 dropped |
| N8 | **open** | "refuses writable **or non-owning** arrays, as `CellFrame` does": `CellFrame.__post_init__` checks only `flags.writeable` (frames.py:49-53), and every array `readonly.frozen` makes is non-owning (below) |
| N9 | fixed | §7.4 exemptions name `adapters/agents` |

**Counts:** 13 fixed, 1 deferred, 0 rejected, 4 open.

### B1, open: what is still missing

1. **The plant's size.** A one-ulp perturbation of a coefficient that is summed with larger terms is absorbed by
   rounding. Scenario: the harness plants one ulp on `h`, the digest stays green for 100 ticks at 2 kW/m², and the
   test either fails for the wrong reason (no divergence at "the first exposed tick") or gets "fixed" by moving the
   assertion later, at which point it no longer pins the first-bad-tick bisection. **Fix:** don't predict the tick.
   The test runs the law twice (planted and clean), finds the first tick at which any raw `BodyFrame` value differs,
   asserts that one exists inside the run, and asserts the digest chain's bisection names that same tick. Plant a
   change big enough to survive rounding (10⁻¹² relative did, at tick 0–1), or a structural one.
2. **Where the binding-order plant goes.** "Reverses binding order with the world unchanged" can be read as reversing
   the binding table in the `join` record. That is a logged input change, so a red digest proves nothing about the
   stimulus path. **Fix:** say the plant reverses the order inside the core's reduction (`frame.py`), with the `join`
   record unchanged.
3. **Events.** Neither plant touches `events`; my round-1 scenario (the canonicaliser drops `events`) is still
   uncaught. Acceptable for v1 because a gate holds `events` empty (§4.2). I accept it as deferred, trigger: the
   first event producer (sound), which must add an event plant. Say so in §5 in one clause.

### S6, open
§4.4: "Overdrive's backend hangs on one named modulator, and its `execute` *is* the outbox path." The modulator is not
named, and §3.3's flat body lists root sensors and no modulator. `bootstrap.py:552-561` (read here) fills
`live_world_set_sensors` only by walking `ent.modulators` for a `SpecModulator` whose `_backend` is set. A body with no
modulator gets no owned sensors, and the "build test that credit flows through settle" has nothing to build on.
**Fix:** §3.3 names the modulator (an Overdrive-only one, say `overdrive_world`), its affordances (or none), and states
that every affordance on it goes to the outbox.

### S8, open
T9: "frames byte-identical every tick at cognition divisors 1–50". `dt_ticks` reaches only the worker
(`npcs_and_sem.md` §9, `step(now_tick, dt_ticks, frame)`), so a core frame can differ across divisors only through the
agents' intents. With live agents, cognition at divisor 50 issues different posture, gaze and movement intents
(§4.5: they are intent kinds), bodies move differently, and frames differ legitimately. Scenario: T9 is red on its
first honest run and gets loosened. **Fix:** T9 drives both runs from one fixed intent stream (scripted, or one run's
logged records fed to the other), varying only the divisor; the `dt_ticks` plant then shows the only path left.

### N8, open
`readonly.frozen` returns `np.frombuffer(arr.tobytes(), …).reshape(…)`. Checked: such an array has
`flags.owndata == False`, `writeable == False`, base chain ending in `bytes`. A `__post_init__` that refuses
non-owning arrays refuses every array built the sanctioned way, and no other way gives an array nothing can make
writable. **Fix:** refuse writable arrays (as `CellFrame` does), and, if more is wanted, refuse an array whose base
chain doesn't end in an immutable `bytes`. Correct "as `CellFrame` does", which checks only the first.

## New findings in v2

**0 BLOCKER, 3 SHOULD-FIX, 4 NIT.**

### X1 (SHOULD-FIX). `sem_stimuli.md::§4.4 "One writer"`: "bound sensors have only Overdrive's owners" can't be checked
**What is true (origin/main).** `world_set_axis`'s `owner` is used for one test only, refusing an anonymous write to a
live-owned sensor (`audio_localization.py:733-745`), then `vm[sensor_name] = v`. The owner is never stored. Other
writers bypass it and write `vital_metrics` directly (`body.py:674-682` legacy drift, `cerebellum_modulator.py:260`,
`spec.py:1061`), or call `world_set_azimuth` with no owner (`loop_perception.py:460, :480`). Maxim has no record of who wrote a sensor, so "after Maxim builds, the worker checks that …
bound sensors have only Overdrive's owners" has nothing to read. The thread half is also a one-time check after build;
a thread started lazily on the first step escapes it.
**Failure scenario.** The worker ships the check as written; it inspects nothing and passes. A narrator write to
`skin_hand_left_temp` between push and step goes unseen, and the "planted red" demonstration can only be faked.
**Fix.** Check by value: after each push, before the body step, and again after it, the worker compares each bound
sensor's `vital_metrics` value with what it pushed; any difference before the body's own update is a second writer,
reported as `agent_failed(protocol)`. Run the thread check after build and after the first step. If Maxim must
record writers instead, file it as a Question with M18.

### X2 (SHOULD-FIX). `sem_stimuli.md::§7.3`: the agents contract is a denylist with no classification test, and two contracts can't be written as stated
**What is true.** §7.3 opens "Denylists fail open (a law born under a new name escapes them)", then makes
`agents-reads-body-frames` a list of seven forbidden modules. The skip-layer and membrane contracts don't fail open
only because `tests/test_tooling_config.py:274-288` asserts their lists equal `_core_modules()` minus a surface set.
v2 names no `AGENTS_SURFACE` and no such assertion, so "every new module … is classified" has no test holding the
agents contract. Separately: `stimuli-protected` allows "the simulation composition", and `body-protected` "the
composition", which are not module names (§7.1's table has no composition module); and import-linter 2.6's
`protected` contract takes only `protected_modules` and `allowed_importers` (read in its source), so "adapters'
`schema`/`frame` imports" needs `ignore_imports`, whose default unmatched alerting is `error`. In 5a, where
`schema.py` lands and `adapters/agents` doesn't exist yet, that ignore matches nothing and the contract errors.
**Failure scenario.** Step 6 adds `simcore.core.sound` (a field module). `adapters.agents` imports it, reads the
pressure field and computes an eardrum level: a second stimulus path, and no contract or test fails.
**Fix.** Define `AGENTS_SURFACE` (`stimuli.schema`, `stimuli.frame`, `intents`, `limits`, `checks`) and assert the
agents contract's list equals `_core_modules() - AGENTS_SURFACE` plus `adapters.sem.bridge`, as the membrane's test
does. Name the composition module. Write the protected contracts as `protected_modules` over
`simcore.core.stimuli` with `ignore_imports` for the two adapter imports, added in the PR that creates the importer.

### X3 (SHOULD-FIX). `sem_stimuli.md::§3.2` vs `§7.1`: the core reduces by bindings that only the worker checks
**What is true.** §3.2: "a binding reduces, in the core"; the core reduces after building the `BodyFrame`, and
§4.5's table digests a body's frames from the `join` tick, inert or refused. §7.1 puts "Binding check" in
`adapters/agents/ (worker)`. The `join` record carries the bindings (§5); the core reads them before any worker check
has run, and for a refused build, the bindings are invalid by definition.
**Failure scenario.** A `join` record binds a site not in the body. The core indexes by it at tick T's step 4: an
`IndexError` in the simulation lane (§4.3 treats a core error as a world bug and stops the server), or, with
`bincount`, a silent zero-weight bin. One bad NPC definition stops the world, or a `BoundFrame` with a meaningless value
is digested into every replay.
**Fix.** The core validates the binding table when it applies the `join` record (§3.2's checks are pure, so they
belong in `core/stimuli`), refuses it as a logged `agent_failed(build)` before any reduction, and digests only the
`BodyFrame` for a refused body. The worker may re-check; it isn't the gate. Put the check's module in §7.1.

### X4 (NIT). `sem_stimuli.md::§6.3`: the table is malformed and T2 is missing
The table has a three-column header (`| # | Gate | Catches |`, `|---|---|---|`) followed by a second two-column header
as data rows; it renders as junk. v1's row was "T1, T2" (ownership); v2 keeps only "T1", so rows go T1, T3, T4 with
no note. Fix the header; say T2 is merged into T1, or renumber.

### X5 (NIT). `sem_stimuli.md::§4.1`: the overlap's premise needs its refusal named
"Physics at T doesn't depend on agent outputs at T (intents apply at `observed_tick + L`)". Under
`npcs_and_sem.md` §9's rule, `apply_tick = ceil((observed_tick·tick_us + L_us)/tick_us)`, an `L_us` of 0 gives
`apply_tick = T`, which the overlap can't honour. §9 refuses an `L_bio` below "the lane's minimum" without stating it.
Say the overlap requires `apply_tick > observed_tick` for every agent intent, and that the refusal enforces it.

### X6 (NIT). `sem_stimuli.md::§8` totals: the skin row is at one substep per tick
"skin … ~50 ms" at 10 NPCs is L3's 4.95 ms per physics step at one substep, times ten ticks. §2.4 now asks for
error-controlled substeps, and contact needs far more than one (Δt = 0.05 s is still 10% late on 70 °C steel). Say the
row is the floor at one substep, and give the contact multiplier when the law's convergence run measures it.

### X7 (NIT). `sem_stimuli.md::§11.1`: each gate should land with what it guards
The step table assigns "§6.3's gates" wholesale to "before Phase 4", but 5a ships `stimuli/schema.py` and `frame.py`.
T10, T14, the `BodyFrame` constructor-site scan and the `__post_init__` refusal guard those files, and CLAUDE.md wants
tests in the same commit. List them under 5a.

## Checked and true in v2

- Weights 0.034 at 45 °C and 0.39 at 60 °C over [−4, 70] centred at 33 °C: (0.6622−0.5)·2 = 0.324, cubed 0.0341;
  (0.8649−0.5)·2 = 0.730, cubed 0.389.
- `bootstrap.py:538-561` and the backend loop at origin/main, as §4.4 cites; `world_set_axis` returns True after a
  clamp, so the worker must count bites itself, as §2.1 says.
- §2.4's 1.25 K and +87% are Physics review's table (`physics.md:90`); §7.2's dgemv 19-of-48 and 0.13/0.04 ms are
  `determinism_performance.md:61, :83`.
- `checklists.md:103`; `npcs_and_sem.md` §9's apply rule, as quoted above.
- `skip-layer` and `membrane-reads-frames` in `pyproject.toml`, and their equality tests, as quoted in X2.
