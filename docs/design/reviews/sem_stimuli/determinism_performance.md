# Design review: SEM stimuli, Determinism, replay and Performance lens

Design: `docs/design/sem_stimuli.md` at `3357439`, with research L3 (`3_world_side.md`) and L5 (`5_contract.md`), read
against the charter, CLAUDE.md and the cited sections of `world_model.md`, `realtime_lanes_coop.md`,
`boundaries.md`, `npcs_and_sem.md` and B5.

Measurements are mine, in `_durable/sem_review/scratch/` (scripts and `.json` beside them), run with the
fire-research venv: numpy 2.5.5, BLAS Accelerate, threads at 1 (OMP/OpenBLAS/vecLib), Apple Silicon with 8 cores.
**Load average 2.5–3.2.** Times are order-of-magnitude; bit-identity results don't depend on load.

**Counts: 2 BLOCKER, 8 SHOULD-FIX, 5 NIT.**

---

## BLOCKER

### DP-B1. The tier-1 claim "what did the NPC sense at tick T" is false as specified: the digest depends on inputs that are not in the tier-1 header or log

`sem_stimuli.md::5` ("Digested every tick", "In the header", "In the rerun manifest", "Reserve now") and
`::4.1` ("Ids come from name maps in the agent's build handshake").

`stimulus_digest` is `SHA-256(canonical(BodyFrame) for each stepping NPC, in npc_key order)` over the bytes sent.
Three things fix those bytes, and the design records none of them where a tier-1 replay (scene, header, log;
`boundaries.md` §6.3) can read them:

1. **Which NPCs step at T.** That is each actor's rate divisor and phase, which `boundaries.md` §7.3 puts in
   `data/agents/`. `data/agents/` digests sit in the **rerun manifest** (tier 2), not the header.
2. **The `stimulus_id` and `site_id` integers.** They come from "name maps in the agent's build handshake", which is
   an exchange with the worker that is not logged. If the map is built by iterating a set or dict of names, the ids
   follow `PYTHONHASHSEED`, and the worker's seed is pinned per run.
3. **Which rows and sites a frame holds.** "An NPC binds only what its body declares", and the body YAML digest is
   in the rerun manifest. The header's "site tables" may or may not mean the per-NPC body instances; the design
   doesn't say.

**Failure scenario.** A bug report is replayed at tier 1, from the scene, header and log alone, with `maxim` blocked
as §5 requires. The replayer can't know that NPC `npc_0007` steps on ticks ≡ 3 (mod 5). So it digests a different
set of frames, and the replay goes red on the first tick while the world is bit-identical. Or a second run with
another `PYTHONHASHSEED` assigns `site_id`s in another order: the values are the same, the bytes differ, and the
digest goes red.

**Fix.**
- Make the frame's identity a pure function of tier-1 content:
  - ids assigned by sorted name from the registry and the body instance;
  - each NPC's body instance (site sets and areas) and its step schedule (divisor, phase) in the header, or in its
    `join` record;
  - the handshake only *checks* the map against the header and never assigns it.
- Reserve these slots alongside `stimulus_digest`.

### DP-B2. Batched kernels are not batch-invariant: §8's parallel evaluation makes the bits depend on the host's worker count, and an NPC joining changes another NPC's bits (measured)

`sem_stimuli.md::8` item 5 ("Parallel evaluation … fixed-order reductions", listed as "bit-identical by
construction"); `::6.2` T11. The claim "a subset solved alone gave the same bits as the batch" (L3 §5) is the basis.

L3's subset test covers the Thomas skin solve, which is elementwise across columns, so its invariance is trivial.
View factors are not elementwise: L3's quadrature is a (point × patch) kernel, and its natural numpy form is a
matrix-vector product. I measured NPC A's 48 points against 160 emitter patches (`matvec_threshold.py`,
`batch_invariance.py`):

| Form | A computed alone vs stacked with others |
|---|---|
| `big @ w` (Accelerate dgemv) | identical with up to 8 others. **With 9 or more others (≥ 480 rows), 19 of A's 48 values change by 1 ulp.** Repeatable at a fixed size; A first or last gives the same result |
| `A @ W` (matrix-matrix, 3 columns) | identical at every size tested |
| per-NPC loop at a fixed shape (`[blk @ w for blk in …]`) | identical |
| `np.add.reduce(big * w, axis=1)` | identical, but differs from `A @ w` |
| `np.einsum("pk,k->p")` | differs from `A @ w`; `optimize=True` differs again |
| `np.bincount(weights=…)` | each bin is independent of the other bins: identical |
| `exp`, `log`, `sin`, `** 0.25`, `** 4` over lengths 1–64, offsets 0–15, strided views | 0 mismatches in 4,296 cases |

**Failure scenarios.**
- **(a) Parallel evaluation, a BLOCKER.** §8 item 5 lets NPCs be evaluated in parallel. The natural split is a chunk
  per worker thread, and the chunk size is a host property (core count, a server setting) that isn't hashed into the
  header. With a dgemv view-factor kernel, the tenth NPC in a chunk changes the first NPC's flux by 1 ulp. That
  changes its tissue nodes, then its Ω, then the world digest. Run the same log on 4 workers and on 8, on one
  machine, and the two diverge. That breaks the Determinism lens's "whatever the thread scheduling". Fixed-order
  assembly in `npc_key` order doesn't help, because the values differ before assembly.
- **(b) Joining.** The tenth NPC entering the tile changes NPC A's tissue bits through the batched kernel. Replay
  still holds, since the join is logged. But "adding an NPC leaves every other NPC's draws bit-identical" holds for
  noise (`npcs_and_sem.md` §3.4) and not for stimuli. T11 would miss it, because it doesn't vary NPC count (DP-S8).

**Fix.**
- Make batch invariance part of the stimulus contract: each NPC's value is computed at a shape fixed by its own body,
  never by the batch. Use per-NPC fixed-shape calls, row-wise `add.reduce`, or `bincount`. The per-NPC loop costs
  0.13 ms against 0.04 ms batched at 100 NPCs (`batch_vs_loop.json`), which is negligible.
- Ban BLAS matrix-vector calls and `einsum` over a batch axis in `core/stimuli` and `core/body` by lint.
- Add a T11 perturbation: B joins or leaves far away, and A's frame and tissue stay bit-identical. Show it red with a
  planted batched `@`.
- Move item 5 out of the "by construction" list until that test exists.

---

## SHOULD-FIX

### DP-S1. Events are ordered by `(apply_us, id)` across ticks, but `apply_us` is the offset within a tick

`sem_stimuli.md::4.1` (`events: … by (apply_us, id)`), `::2.3` ("stamped in integer µs within the tick");
`boundaries.md` §6.2 defines `apply_us` as "the integer world-microsecond offset within the tick".

**Failure scenario.** An NPC steps every 5 ticks. Sound A arrives at tick 101 with `apply_us` 90,000, and sound B at
tick 103 with `apply_us` 10. The frame lists B before A. That is deterministic and wrong: a learner gets reversed
causality, and an onset-ordering test gated on ticks passes by luck at divisor 1.

`StimulusEvent` is also undefined in a frozen contract. Its `id` must be a world-assigned integer, never the opaque
agent pid (`npcs_and_sem.md` §6.6 `caused_by`), and never insertion order.

**Fix.** Order by `(apply_tick, apply_us, kind_rank, world_event_id)`. Define `StimulusEvent`'s fields, with
`caused_by` as data, not as a key.

### DP-S2. Where the frame sits in the tick, and what it was derived from, are not pinned

`sem_stimuli.md::4.1` step 1 ("after every law at tick T") against `realtime_lanes_coop.md` §2.1 (D10: apply records,
**then step agents, then physics**). Also `basis_sequence` ("the Frame it was derived from") against
`boundaries.md` §4.2: frames are published only after physics steps and intent ticks, while tissue changes every
tick.

**Failure scenario.** At physics tick 10 a source ignites. Under D10 the agents stepping at tick 10 see pre-physics
fields. Under §4.1 they see post-physics fields. Either is deterministic, but a frozen row's meaning shifts by one
physics step depending on which order the code picks. Fixing it later means regenerating every golden and bumping a
derivation version on every row.

At a non-physics tick, the frame's tissue values come from the body store at T, which is in no published `Frame`.
So `basis_sequence` doesn't identify the input, and a save or load check can't name what to recompute from.

**Fix.**
- Pin the order: apply records, move poses, run the tissue substep, run physics on physics ticks, build stimuli,
  then step agents. Amend D10 in one place.
- Add the body store's publication sequence to the header beside `basis_sequence`.

### DP-S3. The flux that heats the tissue is unplaced and uncosted per tick, and one reading makes world state depend on agent cadence

`sem_stimuli.md::2.4` ("integrates every tick … whether or not its agent steps"), `::7.1` (no module for flux,
view factors or occlusion), `::7.3` (`laws-blind-to-senses`, `stimuli-read-only`), `::8` item 1 and the cost table.
Against L3 §4, which computes view factors "every step" (per physics step).

The tissue law needs incident flux at the pose of every tick for every body. The design never says where flux and
occlusion are computed, and §8 bills occlusion to "stimuli's B5 line". If they live on the stimulus side:
- `laws-blind-to-senses` forbids the tissue law from reading them;
- or, if they're computed "only at step ticks" (item 1), the tissue's input changes with the NPC's rate divisor,
  which lives in `data/agents/` (the rerun manifest).

**Failure scenario.** An NPC's step divisor is raised from 1 to 5 in `data/agents/`. Its tissue then sees flux
refreshed a fifth as often, so world state differs, and a tier-1 replay that lacks the agent data can't reproduce
it.

The other reading, view factors once per physics step (L3 §4), reintroduces the end-pose averaging §2.4 forbids.

**Fix.**
- Place flux, view factors, contact and occlusion in the tissue law (`core/body/`), run every tick for every body.
  Stimulus models read tissue state only.
- Cost it per tick. The analytic flame row is about ×5, from ~1.9 to ~9.5 ms per physics step at 100 NPCs.
- Held occlusion goes stale within a physics step for a moving NPC even at N = 1. Say so in the staleness
  measurement.

### DP-S4. Staggered occlusion and physical cutoffs change values, and their constants are not in the header

`sem_stimuli.md::8` items 3–4, listed under "Allowed, because bit-identical by construction"; `::5` "In the header"
(which names the registry, site tables and tissue constants only).

Stale held occlusion at N = 4 is not equal to N = 1. The design itself requires that halving a cutoff floor "must
change values within tolerance". So these are law choices, deterministic but value-changing. They aren't
cost-only.

**Failure scenario.** A later commit changes N from 4 to 2, or the near-emitter radius, without bumping a
`derivation_version`. The header still matches, so an old log replays, goes red at the first stale tick, and is
reported as a determinism bug.

Separately, "NPC i" is unspecified. If i is the actor allocator's integer, a roster reorder shifts every later NPC's
occlusion phase. If it is `hash(npc_key)`, it breaks the no-`hash()` rule.

**Fix.**
- Move items 3–4 into §2.4 as law parameters.
- Put N, the radius in metres, the phase rule, the floors and `substeps_per_physics_step` for tissue in the header
  as truth constants.
- Take the phase from the first bytes of `SHA-256(npc_key)`.

### DP-S5. The cost model omits the dominant per-NPC rows and the worst case, and there is no budget figure or gate

`sem_stimuli.md::8` (the table, "Stimuli get their own B5 line, with work counters as the gate").

What's missing:
- **The worst case.** The N = 1 rule near emitters means staggering saves nothing when everyone is near the fire (a
  crowd fleeing it), which is the case that matters. Then occlusion at 100 NPCs is L3's unstaggered ~150 ms per
  physics step, not 38.
- **Delivery.** I measured a 250-row frame: 58 points × 3 depths, plus exposure and 18 burned regions, about 6 KB of
  canonical JSON. Per NPC per step (`frame_cost.json`):

  | Operation | Time per NPC per step |
  |---|---|
  | encode | 99 µs |
  | strict decode | 67 µs |
  | SHA-256 | 3 µs |
  | park round trip | 50–200 µs (`npcs_and_sem.md` §6.6) |

  With all 100 NPCs stepping every tick, which is D5(c), the recommended target, host-serial delivery costs
  10–30 ms per tick: **0.15–0.30 s per world second** before any physics.
- **Points.** The table uses 48 points per body. L3's body has 58 (+21%), and Q1's convergence test may raise it.

**My totals, per world second** (2 physics steps, 10 ticks; L3's kernels, which are pessimistic under load, plus
the rows above):

| | 10 NPCs | 100 NPCs |
|---|---|---|
| kernels (skin, flux per tick, occlusion N = 4 … N = 1) | ~20–45 ms | ~190–410 ms |
| delivery, every NPC stepping every tick | ~15–30 ms | ~150–300 ms |
| **total** | **~35–75 ms** | **~0.34–0.71 s** |

The heat law alone is already 1.4× slower than real time at 1.92×10⁶ cells (B5 row). So 10 NPCs cost about 3–5% on
top of that, which is affordable. 100 NPCs at a fire make the world run at roughly 1.7–2.1 wall seconds per world
second or worse. Dilation allows it; the design should say so.

The design sets no number, and B5 is still an open backlog row, so "a gate" doesn't exist yet.

**Fix.**
- Put this totals table in §8.
- Set a budget, for example stimuli plus delivery ≤ 10% of the physics step's time at 10 NPCs, with the 100-NPC
  figure stated as a dilation forecast.
- Gate on deterministic work counters: column substeps, ray samples, frames and bytes encoded, parks per tick. These
  are integers that replay exactly, so a regression gate on them can't flake.
- Add a wall-time p99 meter as an advisory.

### DP-S6. "Over the bytes sent" against "canonical(BodyFrame)", and the binding reduction happens after the digest

`sem_stimuli.md::5` (the digest), `::3` (a binding reduces by area mean or maximum), `::4.1` step 3 (the worker
pushes).

The area-mean reduction runs in the worker, after the digest. So the scalar Maxim actually receives is never
digested, and a change in the worker's summation order (a Python `sum` becoming numpy's pairwise sum) goes
unnoticed at tier 1 and tier 2.

Digesting the wire bytes also ties the digest to the codec. Frame deltas, which `npcs_and_sem.md` §6.6 names as a
barrier lever, change every digest with no stimulus change. Under deltas, a frame's bytes also depend on the
previous frame.

JSON floats round-trip exactly (measured), so the codec is not the risk. Format coupling is.

**Fix.**
- Digest the canonical values through the one canonicaliser.
- Do binding reductions host-side in a fixed order (`bincount` or ordered `fsum`), so the digest covers the pushed
  scalars. Or have `step_output` return a digest of the worker's `world_set_axis` writes, checked at tier 2.
- Keep a separate codec round-trip golden.

### DP-S7. T9 tests the half that is wall-clock-free by construction and can't see where the wall clock enters

`sem_stimuli.md::6.2` T9 ("Δt and wall-time invariance … one stream"), `::9` M5, M6 and M8.

The frame is built host-side from world state, so T9 passes by construction. Wall time enters after the push:
- `SensorReading.timestamp=time.time()` (M8);
- the PainBus refractory on `time.monotonic()` (M6);
- drift on `time.time()` (M5).

Under the barrier, wall time follows host load, so even a tier-2 rerun with the response cache gives different pain
events and then different intents.

**Fix.**
- Give T9 a worker half: `vital_metrics` writes and pain events at 1× and 20×, and under two seeded wall-delay
  schedules, compared value for value with the timestamp exempt.
- Make it a strict red gate until M6 and M8 land.
- State in §5 that real-Maxim tier-2 reruns aren't bit-identical until then.

### DP-S8. Which perturbations of NPC B must leave A unchanged is undefined (T11 against the radiation ledger)

`sem_stimuli.md::6.2` T11 ("another NPC's internals"), `::11.2` Q4; L3 §1.2 ("bodies are receivers in
Q_rad,view, so the ledger gains Δ(bodies)").

If bodies take energy from the view-factor budget, B's position and clothing change wall heating, and through that
A's stimuli. That is a legitimate physical path, so T11 must allow it. If bodies are ledger-only, the ledger isn't
conservative, and the number should be stated.

As written, T11 neither forbids nor permits B's body physics, and it doesn't vary NPC count, so DP-B2 passes it.

**Fix.**
- Rule the v1 choice: bodies are ledger-only, an ANALOG, with the non-conservation figure.
- Define T11's perturbation set: B's agent state, B's join or leave far away, and allocation order. B's body is a
  physical path only within line of sight.

---

## NIT

- **DP-N1** (`::8` item 2). The reuse key includes "tissue version", which changes every tick for every body, so
  the cache never hits for any v1 row. Scope it to physics-cadence rows, or drop it until B5 shows a need.
- **DP-N2** (`::5`). "Digested every tick" against log v0's "every N ticks a state digest"
  (`realtime_lanes_coop.md` §7). Say whether the log stores 32 B per tick (about 1.15 MB per world hour) or a
  chained hash, which still finds the first bad tick by bisection.
- **DP-N3** (`::2.3`). Floor sound arrival µs once, as `npcs_and_sem.md` §2.1 does for crossings.
- **DP-N4** (`::5`). Length-prefix each NPC's bytes in the concatenated digest.
- **DP-N5** (`::4.3`). After a `False` gives `agent_failed(protocol)`, state the record's apply tick (in tick T's
  merge, canonical order) and whether the inert NPC's frames are still built and digested. Its tissue goes on either
  way (`npcs_and_sem.md` §6.6).

---

## Checked, no finding

- **The dial and latency.** Frames are built host-side, before the send, at a fixed schedule tick, so neither
  worker scheduling nor the dial can reach them (`::4.4`).
- **Forbidden interest keys.** Player distance, the wall clock, host load and the dial are all excluded (`::8`).
  The netcode distinction between replication and simulation interest is drawn correctly.
- **Noise.** None in v1. When it comes, the keyed `(npc, stream, tick, sensor)` Philox stream is order-free.
- **Floats and reductions (measured).** JSON float64 round-trips exactly; `bincount` and elementwise
  transcendentals are invariant to batch, length and stride on this build.
- **Hung workers.** A hung worker is detected by a wall ceiling, but the result is logged and flagged tier 3, so
  tier 1 is unaffected.
