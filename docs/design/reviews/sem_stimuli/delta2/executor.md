# Executor, delta round 2: `docs/design/sem_stimuli.md` v3

**Revisions read.** Overdrive `phase1/sem-stimulus` at **77e24bb** (v3, `delta1/fold.md`, my delta-1 report). Maxim by
`git show origin/main:` at **043eab8f**, not fetched, no working tree read. import-linter's source from the
`fire-research` venv. Two measurements: the author's `v3/plant.py`, rerun, and my
`scratch_executor/t16.py`, both on L3's column (`_durable/sem_research/scratch/skin.py`), threads pinned to 1.

## Status of my open and new delta-1 findings

| Id | Status | Reason (read from v3) |
|---|---|---|
| B1 | fixed | §5: a 10⁻¹² relative plant (rerun: first differing tick 0 at 0, 2 and 20 kW/m²; one ulp none at zero flux, 152 and 120, as the fold says); the test finds the first differing tick and requires the per-tick lanes to name it; the order plant is inside `reduce.py` with `join` unchanged; events get a plant with their first producer. The plant's scenario and size have new gaps (Y5, Y7) |
| S6 | fixed | §3.3 names `overdrive_world`; every affordance on it goes to the outbox. The backend's `world_owned_sensors` is still unstated (Y8) |
| S8 | fixed | §6.3 T9: one fixed intent stream, divisors 1–50 |
| N8 | fixed | §4.2: writable arrays refused, and arrays whose base chain doesn't end in `bytes` |
| X1 | **open** | the value check runs only between the push and the body step, where nothing else in the worker runs; no plant for it; and it fires on every clamp (Y2) |
| X2 | fixed | `AGENTS_SURFACE` and the equality test; protected contracts allow `simcore.adapters` wholesale, narrowed by skip-layer; a test that every allowed importer exists. Setting `allow_indirect_imports = false` creates a new problem (Y4) |
| X3 | fixed | §3.2: `Binding` in `core/stimuli/schema.py`, validated when `join` applies, refused before any reduction; replay reads `join` through the same gate |
| X4 | fixed | §6.3: the table renders; "T2 merged into T1 in v2" |
| X5 | **open** | §4.1 cites "`npcs_and_sem.md` §9's lane minimum refuses equality". §9 (`npcs_and_sem.md:1043-1054`) states no minimum, and its apply rule gives `apply_tick = observed_tick` for `L_us = 0` ("a stamp exactly on a boundary applies at that tick") |
| X6 | fixed | §8: the skin row is one substep per tick; +30 ms near a fire; contact unmeasured |
| X7 | fixed | §11.1: schema, frame, reduce, contracts, §7.4's checks and §6.3's gates land together with `tissue_temperature`. But the step table now orders a codec before its type and a gate before its law (Y1, Y3) |
| N3 | deferred (unchanged) | trigger Q1, still recorded in §11.2 |

**Counts:** 9 fixed, 1 deferred (carried), 0 rejected, 2 open. No deferral or rejection is proposed in the Executor
rows of `fold.md`, so I have nothing to rule on there.

### X1, open: what is missing

1. **Where the check sits.** §4.4: "before the body step the worker compares each bound sensor with what it pushed".
   The worker pushes and then steps the body, in one thread, with the thread set frozen at every park. Nothing can
   write between the two calls except a thread, which the thread check already catches. The writers §4.4 names run
   elsewhere: `cerebellum_modulator.py:260` during cognition, after the body step; `body.py:674-682`'s legacy drift
   inside `tick_vital_drift`, called from `evaluate_failures` (`body.py:293-297`), that is, inside the body step.
   Tick T+1's push overwrites whatever they wrote before the check looks. **So the check as placed can't go red.**
   **Correction of my own delta-1 advice:** I asked for a check "before the body step, and again after it". The
   second one also misses cognition-time writers. **Fix:** check before each push, against the value the worker
   recorded after the previous push. That window covers the body step, cognition and any narrator write. The body
   step itself (`drift_rate: 0`, no `drive:`) shouldn't move a bound sensor, so a difference is a second writer.
   Not verified on code (none exists); reasoned from the call order above.
2. **A plant.** §4.4 plants the thread check ("at the third step") but not the value check. **Fix:** a stub
   modulator that writes `vital_metrics[bound]` during cognition. It must be red under the pre-push check, and it is
   green under v3's placement, which is the demonstration that the placement matters.
3. **Clamps:** Y2.

### X5, open
**Fix:** state the minimum in this design's own words, since §9 doesn't: every agent intent has `L_us ≥ 1`, so
`apply_tick ≥ observed_tick + 1` under §9's ceiling rule. Add a refusal test planted with `L_us = 0`. Checked: with
`L_us = 0`, `ceil(observed·tick_us / tick_us) = observed`.

## New findings in v3

**1 BLOCKER, 5 SHOULD-FIX, 3 NIT.**

### Y1 (BLOCKER). `sem_stimuli.md::§4.6, §6.3 T16, §11.1`: T16 can't be red under D14, and it lands before its law

**What is true.** T16 says that "a 0.2 s contact between steps at divisor 10 must change the agent's body state",
held strict red while delivery runs at the cognition rate. I measured it (`scratch_executor/t16.py`: 70 °C steel,
perfect contact, the coupled column, Δt 5 ms; the cognition steps at t = 0 and 1.0 s; the contact at three onsets).
At the next cognition step the basal (0.1 mm) value is **38.16 °C (onset 0.0 s), 40.00 (0.4 s) and 43.26 (0.7 s)**,
against a rest value of 32.45 °C. That is 5.7–10.8 K high, and the push at the cognition rate carries it. So:
- If "body state" means the bound sensor's value, T16 **passes under D14**. A strict xfail then XPASSes, and the gate
  goes red the day it lands, for no defect. The pressure is then to reword or loosen it.
- If it means pain or failure state, no body has a pain path (§0), so it can't change under either delivery rate.
  T16 then can't tell D14 from every-tick delivery, and it "flips when a pain path lands" for the wrong reason.

§4.6's Known gap text is also false as written: "a contact shorter than a cognition step reaches tissue, not the
agent". The residue does reach the agent. What is lost is the time course: the agent never sees the values of the
ticks inside the contact window, and for an early contact it sees a value 5 K below the peak (43.18 °C, onset
0.0 s).

**Second defect.** §11.1 puts "T16 and D14's Known gap" in `phase1/agents`, which is Phase 1 ("Phase 1 has no NPCs",
`roadmap.md:26`). The contact law and `tissue_temperature` land later, "before Phase 4". A strict xfail with no
`raises=` counts any exception as the expected failure. So T16 written in `phase1/agents` fails on the missing
contact law (an `ImportError` or `NameError`) and reports "xfailed", green, while guarding nothing.

**Failure scenario.** The tissue PR lands. T16 XPASSes under D14 and the strict gate is red. The fix chosen under
pressure is to assert on pain state, which no body has. The gate now can't fail until a pain path exists, so the
only guard on D14's Known gap guards nothing.

**Fix.** (a) T16 asserts tick-resolved delivery: for every tick inside the contact window, the agent's bound sensor
holds that tick's `BoundFrame` value, read from a per-tick push log the stub records. Under D14 no push happens at
those ticks, so the test is red; with every-tick delivery it is green. (b) Land T16 with the contact law, as
`xfail(strict=True, raises=AssertionError)`, so a missing law is an error, not an xfail. (c) Reword the Known gap:
"the agent sees only the values at cognition ticks; inside-window values and their timing are lost (measured: at the
next step the basal value is 5.7–10.8 K above rest, against a 43.2 °C peak)". Verified: the measurement above. That
pytest's `raises=` reports other exceptions as ordinary failures is documented pytest behaviour; I didn't run a
fixture for it.

### Y2 (SHOULD-FIX). `sem_stimuli.md::§4.4 "One writer"` vs `§2.1`: every clamp kills the agent

**What is true (origin/main).** `world_set_axis` stores `max(lo, min(hi, v))` and returns `True`
(`audio_localization.py:748-762`, read). §2.1 treats a clamp as normal and counts the bites. §4.4 compares "each bound
sensor with what it pushed; a difference is `agent_failed(protocol)`". After a clamp the stored value is the bound,
not the pushed value.
**Failure scenario.** An NPC's hand is immersed in a flame, and the surface node passes the YAML's upper bound
(70 °C in §3.3's example range). The comparison sees 70.0 against, say, 74.3. The agent is ended as a protocol
failure on the tick its body is most stimulated.
**Fix.** Before the push, the worker computes the expected stored value with the sensor's declared range, which it
already validates at build (§3.2). It records that value, counts a bite when it differs from the pushed value, and
compares the next check (X1's placement) against the recorded value. Verified by reading the clamp. No code exists to
run against.

### Y3 (SHOULD-FIX). `sem_stimuli.md::§11.1`: a codec lands before its type

**What is true.** §11.1 assigns to `phase1/agents` the "binding format, `BoundFrame` codec, receipt and goldens", the
`bindings_digest` check and the `agents-reads-body-frames` contract, whose `AGENTS_SURFACE` names `stimuli.schema` and
`stimuli.frame`. It assigns `schema.py` (where `Binding` lives) and `frame.py` (where `BoundFrame` lives) to "with
`tissue_temperature`, before Phase 4". By `roadmap.md:26` and `foundations_plan.md:43`, `phase1/agents` is the earlier
step. A2-S4's rule, "the frozen types land with their caller", says the same: the codec is their first caller.
**Failure scenario.** The `phase1/agents` engineer must encode a type that doesn't exist and record goldens for it. In
practice they define a local `BoundFrame`, and the tissue PR's `frame.py` becomes a second definition. Meanwhile the
contract's surface names modules that aren't in the graph.
**Fix.** Move `Binding`'s spec and checks, and `frame.py`'s types (no laws, no `reduce.py`), into `phase1/agents`. Keep
the laws and the protected contracts with the tissue PR. Or move the codec, the binding format and its goldens to the
tissue PR. The first fits §6.1 (the builder's capabilities are agents-step data); I haven't checked either against
`foundations_plan.md`'s word budget.

### Y4 (SHOULD-FIX). `sem_stimuli.md::§7.3 agents-reads-body-frames`: red on its first honest import chain

**What is true.** In import-linter 2.6, `forbidden` checks indirect chains when `allow_indirect_imports` is false,
which is also the default (`contracts/forbidden.py:23, :47, :96`, read). Type-checking imports count unless
`exclude_type_checking_imports` is set (`adapters/building.py:17`). Both existing forbidden contracts set
`allow_indirect_imports = true` (`pyproject.toml`, `skip-layer` and `membrane-reads-frames`), and the reason is
exactly this. v3 lists as forbidden every core module outside `AGENTS_SURFACE`. But `schema.py` holds the
`StimulusModel` protocol, whose signature names the field-reader type (§7.3's model allowlist lists it as a separate
module). It also holds `Binding`'s checks, which test "sites lie in its site set and the body", so it reads
`body.spec`. Neither module is in `AGENTS_SURFACE`.
**Failure scenario.** `adapters.agents` imports `stimuli.schema` (allowed). The chain `agents → schema → body.spec`
breaks the contract, and the gate is red the day the worker lands. The quick fixes are bad: drop the type
annotations, or add `body.spec` to the surface ad hoc.
**Fix.** Keep `allow_indirect_imports = false`, and require `AGENTS_SURFACE` to be closed under imports: a grimp test
that every module the surface imports is in the surface. Then name the closure explicitly (likely `body.spec` and the
field-reader type join it), with each addition reviewed. Verified: the import-linter semantics, by reading its source.
`schema.py`'s imports are inferred from §3.2 and §7.3, since the file doesn't exist.

### Y5 (SHOULD-FIX). `sem_stimuli.md::§5 "The plant test"`: the order plant is green on a symmetric scene

**What is true.** Under uniform ambient every skin point starts at the same steady profile (§2.3; rerun:
surface 32.381 °C, basal 32.454 °C, one column type in v1). The first body's bindings are one sensor per region at
one depth. Reversing the binding order in `reduce.py` permutes equal float64 values, so the bytes are identical.
Reversing the summation order inside an area mean of equal values is identical too.
**Failure scenario.** The harness runs the plant on the join scene or a centred lamp. The bound lane stays green, and
the test fails on the plant, not the mechanism. Or, if the harness asserts only "lane red", someone picks a scene
until it goes red.
**Fix.** State the plant's scenario: one-sided exposure (a lamp to the body's left, 2 kW/m²). Before asserting the
digest, the test asserts that the permuted `BoundFrame` value array differs from the unpermuted one, as a
precondition. Reasoned from the measured rest profile. Not run against a reduction, since none exists.

### Y6 (SHOULD-FIX). `sem_stimuli.md::§4.1 "Its gate runs live"`, §6.3 T9: wall-delay schedules can't be built, and the plant depends on timing

**What is true.** The gate uses "two seeded wall-delay schedules", and so does T9's worker half. In `tests/`, the
determinism scan rejects `import time`, `time.sleep` and `perf_counter` (`tests/test_determinism.py`, the
`test_the_scan_catches` cases). CLAUDE.md bans sleeps in tests. Separately, the planted red ("a merge applying a
`step_output` during step 6") goes red only if some reply arrives while step 6 runs. Under wall delays, that depends
on host speed.
**Failure scenario.** On a fast CI host every stub reply arrives before step 6 starts, and on a slow one none does.
Either way the planted merge-during-step-6 changes nothing, and the plant passes green on one machine and red on
another.
**Fix.** Make the interleaving deterministic rather than timed. The test's pump holds each stub reply and releases it
at named points: before step 6, at a hook inside step 6 (a callback the physics step exposes only to tests, or a
barrier), and after the join. The two "schedules" become two fixed release orders. The plant releases one reply at
the in-step-6 point. Unverified: no code exists. The hook's placement in `Simulation.step` is the author's call.

### Y7 (NIT). `sem_stimuli.md::§5` vs `§2.1 valid`: size the 10⁻¹² plant against the row's rounding

The rerun shows the 10⁻¹² plant moves the column by at most **1.1×10⁻¹³ K**. §2.1's `valid` carries a "rounding
policy", and §4.2's `frame.py` owns "canonical values". If frame values are rounded before they are digested (say to
10⁻⁶ K), the plant never crosses a quantum, and the test's "first differing tick inside the run" fails red. That is
loud, not silent, but it lands in the tissue PR as a surprise. **Fix:** say the plant moves a digested value by at
least one rounding quantum at a declared depth, and size it once the rounding freezes (§2.2). Or say lanes hash the
values before rounding.

### Y8 (NIT). `sem_stimuli.md::§4.4 "The backend"`: name `world_owned_sensors`

`bootstrap.py:555-561` fills `live_world_set_sensors` only from the backend's `world_owned_sensors`. Only that set
makes `world_set_axis` refuse anonymous writes to a bound sensor (`audio_localization.py:733-745`). v3 doesn't say the
backend declares it. With no `drive:` on skin sensors, `tool_bridge`'s measured set (`self_effect ∩ live ∩
drive_specs`) is empty either way, so "a build test proves credit flows through settle" passes whether or not the set
is filled. **Fix:** say `world_owned_sensors` is the bound sensor set. The build test asserts
`live_world_set_sensors` equals it and that an anonymous `world_set_axis` on a bound sensor returns `False`, planted
with an empty tuple. Verified by reading both sites at origin/main.

### Y9 (NIT). `sem_stimuli.md::§2.3 "Accuracy is in kelvin"`: 5–9% doesn't follow

With `d ln(rate)/dT = ΔE/R / T² = 55,000/T²` (0.547 at 317 K, 0.505 at 330 K, matching "0.50–0.54 per K"), a 0.1 K
basal error moves the rate by e^0.050−1 to e^0.054−1, that is **5.1–5.5%**, not 5–9%. The header records this error,
so state the number, or show where 9% comes from (Weaver–Stoll's 0.9 per K gives 9.4%, but that is §11.2's
alternative, tagged **M**).

## Checked and true in v3

- §8: c = 73–90 ms / 1,160 = 63–78 µs (1,160 = 10 × 58 × 2 physics steps); at K = 116, 10·K·c = 73–90 ms, ⌈580/116⌉ =
  5 ticks; at K = 290, 182–225 ms and 2 ticks; 0.5 s × 4 m/s = 2 m; the stationary total is 109–152 ms; 2,000 parks
  per second at 20× and 10 NPCs.
- §2.3 and the fold: rest 32.4 °C and a 1,060 s join transient, reproduced exactly by rerunning `plant.py`.
- §4.4: `bootstrap.py:538-561`, `world_set_axis` storing no owner, and `evaluate_failures` drifting on `time.time()`
  (`body.py:293-297`), all at origin/main.
- §7.3: the `protected` and `forbidden` semantics in import-linter's source, as stated.
