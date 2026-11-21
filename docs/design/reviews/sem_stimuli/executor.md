# Executor review: `docs/design/sem_stimuli.md` (design v1)

**Revisions read.** Overdrive `phase1/sem-stimulus` at **3357439** (its diff from 5ff1b7c is docs only, so `src/` is
the design's stated 5ff1b7c). Maxim by `git show origin/main:` at **043eab8f79ea** (2026-11-20 20:23 -0700, PR #1718).
Nothing was fetched, no working tree was read, and no repository was edited. Scratch measurements were re-run from
`_durable/sem_research/scratch/` with threads at 1 (`geom.py contact_dt`, `skin.py cost`).

**Counts:** 1 BLOCKER, 8 SHOULD-FIX, 9 NIT.

---

## BLOCKER

### B1. `sem_stimuli.md::§5 "The test"`: the one-ulp plant is caught by the header check, so the per-tick digest is never tested
**Claim.** "Replay with `maxim` blocked, compare digests tick by tick, then plant a one-ulp change in a tissue constant
and watch it go red on the first exposed tick."
**What is true.** The same section puts "the registry with each row's `derivation_version`, the site tables and **the
tissue constants**" into the header, and says "a registry mismatch refuses a tier-1 replay". A planted tissue constant
therefore changes the header, and the replay is refused at load, before tick 0. The test goes red, but not on the first
exposed tick and not through `stimulus_digest`. The per-tick digest, the thing the test exists to prove ("catches
stimulus-path changes the world digest can't see"), is never exercised. Second hole: if the plant is a Henriques
constant (P or ΔE/R), the only delivered row it touches is `burned_area_fraction`, a share of points with Ω ≥ 1. A
one-ulp change moves Ω by about one ulp, which changes no point's Ω ≥ 1 test on the first exposed tick, and usually
never does. That plant cannot turn the stimulus digest red at all.
**Failure scenario.** A later change makes the host canonicaliser drop the `events` field from the digested bytes. The
test as written still passes, because the planted constant is refused at the header and never reaches the digest.
**Fix.** Plant below the header: change the constant in the law's code while leaving the recorded header as it was, or
bypass the header check in the test. Plant something that changes a delivered value on the first exposed tick (for
example a surface conductance, which moves `tissue_temperature` at once). Add a second plant on the stimulus path
alone, such as the binding order or an event, with the world unchanged.

---

## SHOULD-FIX

### S1. `sem_stimuli.md::§0 "Where it runs"`: "the skip-layer contract keeps adapters from reading cells" is false
**What is true.** `skip-layer` (pyproject.toml) forbids direct imports of `damage, grid, heat, imagination, readonly,
scene` only, with `allow_indirect_imports = true`. Its own comment says: "reaching the cells through the world is the
point of the public surface". `tests/test_tooling_config.py::test_the_skip_layer_contract_…` asserts this, commented
"the public surface reaches the cells; a direct import may not". `frames.Frame` has a public `cells: CellFrame` field
(frames.py:104-107), and `simcore.core.world` is on `CORE_PUBLIC_SURFACE`. The `Observation` protocol hides `cells`
from mypy, but that is a type, not a contract. Only `membrane-reads-frames` drops `world`, and only for
`simcore.adapters.sem`. The new `simcore.adapters.agents` gets just `agents-no-materials` (§7.3).
**Failure scenario.** A Phase 4 binding helper in `adapters/agents` imports `simcore.core.world` and computes a "skin
temperature" from `world`'s cells. No import contract fails. That is a second heat path, the very thing T1/T2 guard
against.
**Fix.** Correct the sentence. Give `adapters.agents` the membrane's whole forbidden list, `world` included (an
`agents-reads-stimulus-frames` contract), not just `materials`.

### S2. `sem_stimuli.md::§7.3`: subpackages escape the core-module classification test
**What is true.** `tests/test_tooling_config.py::_core_modules` is `(src/simcore/core).glob("*.py")`, which does not
recurse. The skip-layer and membrane tests compare forbidden lists against that flat set. The design adds the
subpackages `core/stimuli/` and `core/body/` (`tissue.py`, `store.py`, `geometry.py`, `sites.py`). §7.3 adds only
`stimuli.schema` and `stimuli.frame` to the surfaces. Adding those breaks `_core_modules() >= CORE_PUBLIC_SURFACE`
visibly. But `simcore.core.body.tissue`, `body.store`, `stimuli.registry`, `stimuli.run` and `stimuli.models.*` never
appear in `_core_modules()`, so nothing demands they be forbidden to adapters. The skip-layer comment also lists
"geometry" as off-limits, yet the binding must check site names, which live in `core/body/geometry.py`. The design
doesn't say which side that falls on.
**Failure scenario.** An adapter imports `simcore.core.body.tissue` (a law, with write access to tissue state). The
skip-layer contract doesn't list it, and the classification test doesn't notice it exists.
**Fix.** Make `_core_modules` recurse (`rglob`, dotted names) in the PR that creates the first subpackage. Classify
every `core/body/*` and `core/stimuli/*` module in §7.3. Decide whether adapters reach site names through `stimuli.schema` or `body.geometry`.

### S3. `sem_stimuli.md::§2.4`: "0.1 s is within 3% everywhere" is false for contact pain
**What is true.** Re-ran `geom.py contact_dt` (70 °C steel held in the hand). Time to pain is 0.249 s at Δt = 0.005 and
**0.298 s at Δt = 0.1, which is 20% late**; at 0.5 s it is 0.459 s (84% late). The burn is 2.3% late at 0.1 s
(2.994 against 2.927), as L3 says. L3 §1.3 reports only the burn. The design generalised "within 3%" to pain as well.
The radiant table holds: worst case +2.8% at 20 kW/m², 0.1 s (`convergence.json`, recomputed).
**Failure scenario.** The tick-rate tissue step is adopted as "within 3%". The contact cross-tier or Δt gate, written to
3%, then fails on steel at 70 °C. The temptation is to loosen it, which CLAUDE.md forbids.
**Fix.** State it: contact pain at 0.1 s is about 50 ms (20%) late, less than one tick. Either accept that with a
named tolerance, or substep contact more finely (Δt = 0.05 is still 10% late).

### S4. `sem_stimuli.md::§8 "Allowed, because bit-identical by construction"`: item 4 isn't bit-identical, and N has no owner
**What is true.** L5 §6's list has four items (schedule, reuse, cutoffs, parallelism). The design adds "staggered
occlusion (NPC i on steps ≡ i mod N)". Held occlusion at N = 4 differs from N = 1 whenever anything moves. The design
says so in the same item ("staleness measured and gated before any N > 1"). It is deterministic and independent of the
observer, but it is not bit-identical. Item 3 (cutoffs) is also not bit-identical to having no cutoff. More
importantly, §2.4 makes the tissue step "a truth constant, never a rig field", but N is not given the same status.
**Failure scenario.** N lands in a rig profile or `data/` as a performance knob. A laptop at N = 4 and a rig at N = 1
burn the same NPC at different ticks: the D20 failure §2.4 rules out for the tissue step.
**Fix.** Retitle the list "deterministic and independent of the observer". Make N, the near-emitter rule and the cutoff
floor truth constants in the header, with the same "never a rig field" sentence.

### S5. `sem_stimuli.md::§7.1` row `BodyFrame`: "one `stimuli` part of `Frame`" conflicts with frame cadence and per-NPC isolation
**What is true.** `boundaries.md` §4.2 publishes a `Frame` "after each physics step (0.5 s) and after each tick that
applied an intent", not per tick, and per-tick full publication is costed there as 13–16 GB/s. `tick`-cadence rows
(§2.3) are evaluated at each step tick, at that tick's pose, so they can't ride a `Frame` that isn't published that tick.
Also, a `Frame` carrying every NPC's stimuli hands any `FrameSource` holder (the membrane, `RegionInstrument`)
NPC B's tissue. That is the leak T12 plants. L5 §1/§7 put the `BodyFrame` *beside* `Frame` ("published beside Frame,
one per stepping NPC").
**Failure scenario.** Built as written, either tick rows go stale between publications (a 0.5 s hold on a 0.1 s
quantity, which §2.4's 12.1% figure says is too coarse), or `Frame` is published per tick.
**Fix.** Take L5's wording: a separate per-NPC value published by the simulation lane at each step tick, never a field
of `Frame`.

### S6. `sem_stimuli.md::§4.2` third bullet: being in `live_world_set_sensors` does more than guard writes
**What is true (origin/main).** The design treats membership as the write guard. In Maxim it also:
- filters the modelled `self_effect` on those keys and withholds drive credit for any affordance whose declared effect
  touches them (`embodiment/tool_bridge.py:548-560`, `:620-640`: "the consumer must NOT fall through to the flat +1
  tool-success floor");
- can be filled only by a **modulator** backend (`runtime/bootstrap.py:552-561`). An attached modulator backend also
  takes over that modulator's `execute` (`embodiment/spec.py:1136-1139`: `if self._backend is not None: return
  self._backend.execute(...)`).

So "Overdrive ships one" means the flat body needs a modulator to host it, and that modulator's affordances are routed
to Overdrive's backend.
**Failure scenario.** The first body's `rest` or `cool_off` affordance declares `self_effect` on a skin sensor. Its
credit is silently withheld from then on. If the backend is hung on, say, the `torso` modulator, every `torso`
affordance goes to a backend that only meant to declare world ownership.
**Fix.** List these effects in §4.2. Name which modulator hosts the backend and what its `execute` does (it must
delegate to the membrane or refuse). Add a build test that a bound sensor's affordances still book credit through the
intended path.

### S7. `sem_stimuli.md::§9 M2`: miscategorised; an existing plan owns it, and Maxim recorded the workaround as equivalent
**What is true (origin/main).** The encoder's "plan decision D1" is answered by `docs/plans/deferred/setpoint_aware_neutral.md`.
It was DEFERRED on 2026-09-16 after a four-lens review returned DO-NOT-BUILD, and it states a revive trigger ("a roadmap
want that STRUCTURALLY needs a small, same-side move of one graded sensor to separate"). `docs/plans/archive/world_channel_weighting.md:222`
records that a "static set-point-aware neutral" is "numerically identical to the range declaration already used". That
is exactly the design's workaround (centre the skin range on 33 °C). By §9's own definitions this is a **Question** to
an existing plan's revive trigger, not a Pushback. The motivating need may already be met by the range. A4's neutral
applies only when `gain_exponent` is set (`encoder.py:596`; `None` is the default).
**Failure scenario.** Filed as a pushback against D1, it reopens a review Maxim closed with measurements, without
citing it. This is the stale-read failure memory warns about.
**Fix.** Re-file M2 as a Question to `setpoint_aware_neutral.md`'s revive trigger. Cite world_channel_weighting:222.
Say whether a skin case needs more than a centred range.

### S8. `sem_stimuli.md::§6.2 T9`: "one history at different step sizes … one stream" has no defined oracle
**What is true.** Agents step "at an integer divisor of the tick" and get the frame at their step tick, with events
batched since the last step (§4.4). Two runs at divisors 1 and 5 send different numbers of `BodyFrame`s, sampled at
different ticks, with events batched differently. `stimulus_digest` covers "each stepping NPC", so it differs too. A
byte-level "one stream" cannot pass. A loose one (values at common ticks) passes even if a model reads the step size.
**Failure scenario.** As a byte test, T9 is red by construction, and the fold loosens it until it can't fail.
**Fix.** Define it: at every tick both runs step, the frames are byte-identical; and the union of events across the
coarse run's frames equals the fine run's. The planted leak is a model that reads `dt_ticks`.

---

## NIT

- **N1. `§0`, `§6.2`:** "fourteen tests, each shown red on a planted leak" includes T6, "an experiment, not the gate",
  and the review-rule half of T1/T2. Say "twelve gates, a probe and a review rule". The §1 leak tests are also named T1,
  T2, which collides with test rows T1, T2.
- **N2. `§6.2 T12`:** "Plant: bind B's site to A" can't be written. `Binding` has no `npc_key` and A's frame holds only
  A's sites. The plant belongs in the runner (copy B's value into A's frame).
- **N3. `§3` vs `§8`:** the body is 58 points but the cost table uses 48 (L3 §2 says so). At 58 the skin is ×1.21:
  ~6 ms and ~55 ms. "18 regions": L3's table gives 17 (5 single + 6 paired). Its 6% buttocks share (0.111 m²) is not
  what `geom.py body` computes (5%, 0.0924, total 99%).
- **N4. `§7.2`:** "`prepare` then `kernel` (O34's per-law split)". O34 (boundaries.md:59) doesn't say that. The split is
  `docs/plans/checklists.md:103`. The misattribution is inherited from L7.
- **N5. `§10 D1`:** "O13 already rules out the world frame (a `CellFrame` is 64–80 MB…)". O13 is the worker process. The
  64–80 MB figure and "agents get reductions, not grids" are in `boundaries.md` §4.2.
- **N6. `§2.3`:** "vestibular thresholds are flat at 1–5 Hz" holds for yaw only (0.74–0.84 °/s). L1 quotes vertical
  translation at 0.61 cm/s at 5 Hz against 1.67 at 1 Hz.
- **N7. `§9 M3, M4`:** OD-C9 is "a written version rule for the SEM vocabulary" and OD-A10 is "the embedded entry point
  on AgentFactory" (roadmap.md:239, :182). Neither is about unit vocabularies or post-push evaluation, so these are
  loose homes. Say "new, nearest home".
- **N8. `§4.1` `BodyFrame`:** a `frozen=True` dataclass holding `NDArray`s isn't frozen deep (`boundaries.md` §5.1:
  "numpy arrays read-only at the owner"). Say the arrays are made read-only through `readonly.py`. "Only
  `simcore.core.stimuli` writes a `BodyFrame`" (§6.1) needs a check (a constructor scan, as `test_ownership` does).
- **N9. `§7.4` "No central switch":** binding code and the build handshake's name maps use row names as dict keys by
  design. The lint's exemption list (own module, data file, schema) must also name `adapters/agents`, or it fires on
  the shipped path.

---

## Checked and true

**Overdrive code (3357439).**
- `RegionInstrument` is at `adapters/sem/bridge.py:48`, and L5's `:715` is wrong, as §11.1 says.
- `reading_schema`'s name test is at `bridge.py:72-75`; a fifth quantity gets `[-273, 6000]`.
- `QUANTITIES` has four entries (frames.py:30-32).
- `skip-layer` allows `materials`, and `membrane-reads-frames` forbids it to `adapters.sem`.
- `importlib` is banned in `sealed-core`.
- `CORE_PUBLIC_SURFACE` and `MEMBRANE_SURFACE` exist in `tests/test_tooling_config.py`.
- `maxim-through-adapters` lists only `simcore.adapters.sem`.

**Overdrive docs.**
- `realtime_lanes_coop.md` §2.2: 0.1 s tick and 0.5 s physics step (`tick_us` 100,000, `physics_every_ticks` 5); §2.3
  has `substeps_per_physics_step`.
- `npcs_and_sem.md`: §2.1 "Multi-rate is allowed; thinning is not"; §6.6 has the strict closed-schema codec,
  `agent_failed(… protocol)` and 50–200 µs per round trip; §7.3 pins the frame.
- `boundaries.md`: §9.1 has `parse_constant` refusing NaN/Infinity and "in-code field registry is primary"; §7.1 has
  the barrier.
- `fire_model.md` §5.1 has "~0.1 mm" and the root-sensor stopgap ANALOG; §5.4 has the NPC builder exclusions; §8.3 has
  40 ns per (flame, point), so 10×48×10×40 ns = 0.19 ms ✓.
- Lessons 4, 11 and 24 exist with the quoted titles; bio_faithful S4 exists.
- OD-C2, C8, C9, C10 and A10 exist.
- The Henriques and Torvi & Dale values match `physics_spike/body.md` (S, as tagged).

**Maxim (origin/main 043eab8f), each read at the cited line.**
- `audio_localization.py`: world_set_axis root-only (727-762); dotted name returns False; the clamp at 749-761; raw
  write with no range; `owner=` "SELF-DECLARATION … not an ACL" (720-721).
- `max(lo, min(hi, nan))` is `hi`, confirmed by running it; ±inf clamp likewise.
- `spec.py`: `:556` raises on sub-sensor `modality:`; `:290` default `drift_rate` 0.001; `:820-823` backend read;
  `:837` `time.time()` stamp; C5 derived health.
- `sem.py:278-281` pain formula. `bootstrap.py:552-561` is the only filler of `live_world_set_sensors` (grep of
  `src/`). `body.py:293-295` wall-clock drift.
- `pain_bus.py:196` `time.monotonic()`, 0.5 s per `(entity, failure_mode)`. `nac.py:425` fear allowlist, `:439` 300 s.
- `encoder.py:572-584` quote. `sensory_streams.py:68` `{AUDIO_TAG, WORLD_TAG}`, with `WORLD_TAG = "world"`.
- `base_humanoid.yaml:57-62` weights; no `drive:health`. `minecraft_player.yaml` units `hp`, `points`.
- `thalamic_relay.md:2123`: TR23's "one kind-taking setter" is GL3.B3, confirming §11.1's correction of L2.
- `autonomic_layer.md:233-234` "a burn is **not** added"; GL2b not started (header).
- `experience_clock_decay.md` PROPOSED, S4, §(g)'s PainBus row; `temporal_window_us` planned (:211).
- The Minecraft backend pushes through `world_set_axis(owner=…)`.

**Numbers.**
- `convergence.json` recomputed: +12.1% pain at 20 kW/m², Δt = 0.5; ≤ +2.8% at 0.1 s; 45 nodes (44 cells).
- `contact_dt` re-run, bit-for-bit the same: burn 3.262 against 2.927 s (+11%).
- `mean_vs_points.txt`: 6.20 s against 11.80 s.
- Flame puffing 1.5/√0.1 = 4.74 Hz. Nyquist 5 Hz and 1 Hz.
- Skin cost: interpolation from `cost.json` gives 4.95 and 45.3 ms. Re-run at load 2.7 (against 5.6–7.8): 0.44 and
  3.3 ms at 1 substep, 4.4 and 34 ms at 10. That is 2.2–2.7× faster, which confirms the "pessimistic" caveat. Subset
  bit-identity is true.
- Occlusion 76 and 818 ms; 9 rays × 10 flames gives ~14 ms and ~143 ms, and ÷4 gives ~4 and ~38 ✓.
- M6's arithmetic: 0.5 s world at 20× is 25 ms wall ✓.
