# SEM stimulus design, delta round 2: Physics and resolution

Reader: Physics and resolution lens. Design `docs/design/sem_stimuli.md` v3 at `77e24bb`; my delta-1 report
(`reviews/sem_stimuli/delta1/physics.md`); the author's `delta1/fold.md`; L3 (`research/sem_stimuli/3_world_side.md`)
and its column (`_durable/sem_research/scratch/skin.py`); `tile_and_client.md` §2.1; `world_model.md` §2 and §8.
Statuses are read from the v3 text, not from the fold table. Tags: **V** read here, **M** memory, **D** my derivation
or measurement. My scripts are in `_durable/sem_review_delta2/scratch_physics/` (`rest_core.py`, `rest_sink.py`,
`submesh.py`), run with the fire-research venv.

**Counts: 13 fixed, 0 deferred, 0 rejected, 1 open. New: 1 BLOCKER, 3 SHOULD-FIX, 3 NIT.** The fold table proposes
no deferral or rejection under this lens, so I have none to rule on. Round-1 deferrals (S2, S6, S8) still carry their
conditions in §11.2 and Q4.

## Status of delta-1 findings

| Id | Status | Reason |
|---|---|---|
| N1 (r1) | fixed | §8 states the basis once (58 points, 0.1 m tier, light load, one emitter), and the visibility row reads 73–90 ms. I checked the refresh arithmetic: 1,160 pair refreshes per world second at 10 NPCs; c = 63–78 µs; K = 116 gives 73–90 ms and ⌈580/116⌉ = 5 ticks; K = 290 gives 183–226 ms and 2 ticks; every tick is 365–452 ms. All consistent. |
| N5 (r1) | fixed | §3.1 books perfusion as a skin–core exchange and metabolism into the core, and makes only the ambient a reservoir. Which ambient that is turns out to be undefined (new S1). |
| S1 | fixed | §2.3's occluder row names primitives in metres for intact geometry and volume-fraction transmittance after B28. §11.1 puts B28 first, and the grid-only march is the planted red case. The transmittance law itself is undefined (new N2). |
| S2 | fixed | §2.3 has an outer boundary (convection plus radiation, immersion per point) and the steady-profile closed form. I reproduced the 32.4 °C rest on L3's column (32.38 °C, `rest_core.py`). Two new problems sit inside it: the sink (new S1) and the core it rests on (new S2). |
| S3 | fixed | §2.3 and §4.5 start join and restart at the steady profile, by a direct solve. I didn't rerun the author's 1,060 s; it's in line with my ~1,200 s estimate. The no-drift test I asked for is missing (new N3). |
| S4 | fixed | §2.3 picks (b): no face contact or face emission in v1, strict red gates on both (§7.4), a Known gap with P1's number, and face skins named as the fix (Q3). |
| S5 | **open** | v3 adds the object-side sub-mesh but doesn't say it persists, and §7.1 runs contact "against the solid's last published state". I measured both readings that rebuild the sub-mesh, and both flip the outcome class on hot wood. That's worse than the coarse mesh S5 complained of. See new B1. |
| S6 | fixed | §8 costs motion refresh (365–450 ms every tick). The capped schedule bounds cost at 10·K·c and staleness at ⌈P/K⌉. Acceptability is an outcome measurement (the step from behind a wall into 20 kW/m², pain at 1.1 s), and D12 is re-ruled on it before the law's code. The tolerance comes from outcomes, not from the budget, which is what I asked. Plainly, K = 116 gives up to 0.5 s staleness against a 1.1 s time to pain, so I expect it to fail. §8 names the failure paths. |
| S7 | fixed | §2.3 interpolates contact onset and release between poses, and radiation keeps the one-tick hold. |
| N1 (new) | fixed | §2.3 derives the K tolerance from an Ω error, and §5 puts both in the header. The per-K numbers carry two small errors (new N1). |
| N2 | fixed | §11.2 tags Weaver–Stoll's 0.9 per K as **M**. |
| N3 | fixed | As N5 (r1). |
| N4 | fixed | §6.3 adds the fingertip test, to land with a pain path; until then a build check refuses a mean on `noci_heat`, and §3.2's worker refuses a mean on a pain path. |
| N5 (new) | fixed | §11.2 defines the spread as the maximum over the emitter's quadrature points. |

## New findings

### BLOCKER

**B1. As written, the contact sub-mesh is rebuilt from the coarse object state each tick. That flips "hot wood is
painless" into a burn: the cure is worse than S5's disease.**
`sem_stimuli.md::§2.3` (contact row: "an object-side sub-mesh refined to the substep's penetration depth, remapped
back conservatively"), `::§7.1` (contact "at step 3, against the solid's last published state"), `::§5` (the save's
"contact state").

v3 says nothing about the sub-mesh living longer than a tick. §7.1 pins the object side to the last published solid
state, and §2.2's zero-order hold refreshes that once per 0.5 s physics step. Two readings follow, and both rebuild
the sub-mesh:
- **reinit:** each tick, the sub-mesh is remapped conservatively onto the object's coarse nodes, then rebuilt from
  them, piecewise constant;
- **stale:** each tick, the sub-mesh is rebuilt from the state published at the last physics step.

**Measured** (`submesh.py`, **D**):
- Setup: a finite-volume skin column on L3's layers (70 cells), a 20 mm object in perfect contact, backward Euler at
  2 ms.
- Object meshes: the coarse one uses fire_solid's first-cell rule, √(α·1 s): 0.39 mm for wood, 2.0 mm for steel. The
  reference sub-mesh starts at √(α·0.1 s)/8 and persists.
- Pain: basal ≥ 44.8 °C, L3's threshold.

| Object | reference: persistent sub-mesh | coarse, no sub-mesh (S5's case) | reinit each tick | stale published state |
|---|---|---|---|---|
| wood 90 °C | no pain in 10 s (basal 42.9 °C) | no pain (42.8) | **pain 2.35 s** (47.2 at 10 s) | **pain 0.40 s** (55.5) |
| wood 120 °C | pain 0.76 s | 0.94 s (+24%) | 0.33 s (−56%) | 0.23 s (−70%) |
| steel 60 °C | 0.326 s | 0.348 s (+7%) | 0.302 s | 0.274 s |
| steel 70 °C | 0.164 s | 0.182 s (+11%) | 0.158 s | 0.154 s |

What the numbers say:
- **The mechanism.** Rebuilding piecewise constant from 0.39 mm cells erases the cooled boundary layer under the hand
  every 0.1 s. Each tick re-presents nearly full-temperature wood, and the low-effusivity protection is lost.
- **The outcome class flips.** On wood at 90 °C, painless becomes painful.
- **The stale reading also breaks the ledger.** It discards the cooling contact already wrote to the object, extracts
  that heat again, and debits the object twice.
- **S5's original error is now measured.** The coarse mesh without a sub-mesh errs by +7% to +24% on time to pain
  and keeps the class. The sub-mesh is worth building only if it persists.

The resolution rule applies here in spirit. The object's mesh is set by the solid law's step size, not by dx, but a
mesh choice that changes the outcome class is the same failure.

**Fix:**
- The sub-mesh is carried state for the life of a contact: initialised once at onset from the object's profile, kept
  across ticks, and saved under §5's "contact state".
- Each physics step, the solid law reads it through a conservative remap. The solid's own step then hands its
  interior change back to the sub-mesh as a boundary or source, never by overwriting it.
- Replace "against the solid's last published state" with "against the contact's own carried sub-mesh".
- Release remaps the sub-mesh onto the object once.
- Add a §2.3 convergence row against the persistent reference: rebuild interval × object-node count, on wood at 90 and
  120 °C, with "painless stays painless" as an outcome gate. Plant the per-tick rebuild as its red case.

**Verified:** only that the persistent sub-mesh is the reference here, by construction, and that both rebuild
readings flip the class. **Not verified:** the two-way coupling of a persistent sub-mesh with an object stepping
coarsely at 0.5 s. That needs its own convergence measurement before the contact law's PR.

### SHOULD-FIX

**S1. "The local ambient" is three different sinks in three documents, and the rest state depends on which one.**
`sem_stimuli.md::§2.3` (outer boundary row: "convection and linearised radiation to the local ambient"), `::§3.1`
("tile §2.1's exchange volume now meets the skin … Only the ambient is a reservoir"), against
`tile_and_client.md::§2.1` and `world_model.md::§2`.

The candidates:
- **L3 §1.2** (and its column, `T_INF = 293.15` fixed): Phase 1 air has no gas in cells, so the body loses to a fixed
  ambient reservoir.
- **Tile §2.1** (**V**): T_env is the volume-overlap mean of the exchange volume's cells, and those cells are debited.
  They hold 1.53 kJ/K and reach body temperature in about 80 s.
- **world_model §2** (**V**): gas lives in zones, read only through `gas.at(zone)` and `gas.over(mask)`, and a
  two-layer smoke zone is the planned swap behind that interface.

v3 cites both of the first two and defines neither.

**Failure scenarios:**
- **Rest moves.** If the tile's exchange volume is the convective sink, it warms to skin temperature within minutes
  and convection collapses. L3's column with h_conv = 0 rests at **34.69 °C** against 32.38 (`rest_sink.py`, **D**).
  That moves the A4-centred rest by 2.3 K. The steady-profile join and its closed-form test assume a sink nobody
  specified.
- **One value for the whole body.** A body-wide T_env (the tile's single mean) gives head and feet the same gas
  temperature. Under the two-layer smoke zone that world_model already plans, a 200 °C upper layer at head height
  would be averaged with 20 °C floor air before a non-linear damage law. That is averaging then thresholding, on the
  classic head-burn scenario.
- **The radiative sink.** It's unnamed. If it's air or zone temperature, cold walls radiate as if they were the gas,
  and hot gas radiates with the skin's ε. If it's a fixed 20 °C, a hot layer contributes nothing.
- **"Linearised".** With a fixed coefficient taken at rest, this is low by 28% at a 100 °C sink and by 2.2× at 200 °C
  (575 against 416 W/m², and 2,230 against 1,030; **D**). L3's column actually uses the exact secant coefficient
  εσ(T_s² + T_a²)(T_s + T_a), lagged one step, so v3's word is looser than its own evidence.

**Fix:** §2.3 should state that each point's convective sink is read per point (per region at least) through
`gas.at`/`gas.over` over a volume in metres around that point, debited on the ledger. Under Phase 1's still air that
is a fixed reservoir, which keeps the 32.4 °C rest and its closed form true. Also:
- either supersede tile §2.1's exchange-volume T_env by name, or state why both hold;
- name the radiative sink (v1: the fixed ambient, with "hot surroundings don't radiate except as emitters" folded
  into S4's Known gap) and the exact secant form;
- add a test in which a two-region body, one region in a hot zone and one not, burns only the hot region.

**Verified:** the two rest temperatures and the linearisation errors. The per-point zone read is design, not
measured.

**S2. The skin rests on a free core that cools 3.5–4.7 K per hour, so neither "rest" nor the steady-profile join is a
steady state.**
`sem_stimuli.md::§3.1` ("The tile's 245 kJ/K store is the core node"; "metabolism into the core"), `::§2.3` ("a
column on a 37 °C core rests at 32.4 °C"), `::§4.5`.

L3's column holds its base at 37 °C as a Dirichlet condition. That's what makes 32.4 °C a rest. v3 replaces it with
the tile's free store.

**Measured on L3's column** (`rest_core.py`, **D**): at rest the surface loses 170.6 W/m² (99.0 convective, 71.6
radiative). Of that, 2.9 W/m² is column metabolism; the core supplies the rest, 121.3 by perfusion and 46.4 by
conduction. Over the tile's 1.9 m² that's 319 W drawn from the core: 4.7 K/h on 245 kJ/K, or 3.5 K/h with an assumed
80 W core metabolism (**M**). v3 gives metabolism no value, and tile §2.1 says Phase 1 has none.

**Failure scenario:** an idle NPC in a 20 °C room reaches a 35 °C core in 35–45 minutes of world time. Its skin rest
slides off the §3.3 midpoint. `core_temperature`, once bound, reports hypothermia for a body nobody harmed. Every
time to pain after the first half hour then depends on how long the NPC has existed, a scene-authoring accident, the
same class of error as delta-1's S3.

**Fix:** state v1's core law. Either:
- (a) hold the core node at 37 °C as a boundary, booking the supplied power on `bodies` as a named source, "basal
  thermoregulation, ANALOG", and supersede tile §2.1's free relaxation test (τ = 12,900 s) by name. The core goes
  free when vasomotor and shivering output arrive as logged intent kinds, as breathing does (§4.5); keeping the set
  point Maxim's preserves §1's split. Or:
- (b) keep the core free and enter the drift as a Known gap with the 3.5–4.7 K/h number, making the join solve
  explicitly quasi-steady.

(a) is what L3's evidence assumed; I verified only that a held core gives the 32.38 °C rest, not any controller.

**S3. Immersion convection is a binary inside/outside switch on a flame shape that comes from cell-computed power,
with no cross-tier test, and the plume outside the flame heats nothing.**
`sem_stimuli.md::§2.3` (outer boundary: "immersion convection per point inside a flame, against its shape in
metres"), `::§7.4` (cross-tier couplings: occlusion, face emission, face contact, zone gas; immersion is absent).

- **The switch.** A point just inside gets h(d)·(T_f − T_s). A limb in flame gas at h of order 20–50 W/m²K and
  T_f ≈ 800 °C gives 15–40 kW/m² (**M** on h, **D** on the product). A point just outside gets the 20 °C ambient. The
  flame's height follows Q, and Q is computed from cells, so it differs across tiers within the fire model's margin.
  Points within that margin of the flame edge flip between about 0 and tens of kW/m². That's a binary outcome without
  a band, which CLAUDE.md requires to be gated with an outcome margin. §2.3's immersion convergence is in time step,
  not grid.
- **The plume.** A hand 0.3 m above the flame tip sits in plume gas at hundreds of °C (McCaffrey/Heskestad plume
  correlations, **M**) and gets ambient convection. That is an unrecorded physics gap, in a scenario players will
  try.

**Fix:**
- Replace the switch with a gas-temperature field in metres around each flame: flame, intermittent and plume regions
  from a cited correlation, continuous across the flame edge. Evaluate h(d)·(T_gas(x) − T_s) per point.
- Add "immersion and plume" to §7.4's cross-tier couplings, at the three offsets, with an outcome margin on burned
  area for a hand at the flame edge.
- Until the field lands, enter "plume gas doesn't heat" as a Known gap with a number.

**Not verified:** the flux numbers rest on **M** values for h and the plume. The finding stands on the switch's
structure alone.

### NITs

- **N1.** `::§2.3`: "Ω's rate moves 0.50–0.54 per K under Henriques, so 0.1 K basal is 5–9%." Under 0.50–0.54 per K,
  0.1 K is 5.1–5.5%. The 9% came from my Weaver–Stoll figure (0.92 per K), not from Henriques. The 0.50–0.54 also
  rests on L3's ΔE/R = 55,000 K (`skin.py`, P = 1.43×10⁷²). My memory of Henriques is P ≈ 3.1×10⁹⁸ and ΔE/R ≈ 75,500
  K, which gives 0.68–0.75 per K (**M**, **D**). Tag the sensitivity as conditional on §11.2's constant trace, and fix
  the 9%.
- **N2.** `::§2.3` (occluders): "volume-fraction transmittance" doesn't say how fraction becomes transmittance. Taken
  per cell crossed, a ray grazing along a wall whose face sits mid-cell multiplies 0.5 per cell and is opaque after a
  few cells, while a ray 1 mm higher passes. That puts the knife edge back on a coarse cell. Define it per path
  length (an extinction coefficient of fraction/λ along the ray's chord) or by sub-cell surface reconstruction, and
  include a grazing ray in §7.4's wall-edge case. Unmeasured.
- **N3.** `::§2.3`/`::§4.5`: delta-1 S3 asked for a test that a joined NPC's tissue doesn't change in its first second
  at ambient. v3 has only the closed-form steady profile. Add it. It's the test that catches a join solved on a
  different mesh or a different sink than the law runs on, and it goes red under S2's free core unless S2 (b) is
  chosen.
