# The torch's Phase 1 pilot (design, 2026-11-22; rounds 1 and 2 folded; ruled)

**Scope.** The question that blocks step 8's exit scenario (`docs/plans/checklists.md` step 6, "Added by D-B2"): how
a `kindle` ignites a slab when Phase 1 has no flame object. Phase 1's exit is the roadmap's (Phase 1, "Exit"). Flame
objects, and with them fire_model §5.4's flame-object pilot, are 6.2's, in Phase 2 (`client_objects.md` §1). Both
rounds' reports and folds are in `reviews/torch_pilot/`; the owner's rulings, TP1–TP11, in `decisions/torch_pilot.md`.

**What this document owns** (one owner per contract):
- the pilot record (§2);
- `kindle`'s target rule, whole (§3), taken from fire_model §5.4 and tile §3.2, whose copies become links (§10);
- the deposit, its clock and the pilot condition (§4, §5);
- the torch's physical data and `kindle`'s physics ceiling (§6);
- the slab exit's beats, bands and controls (§9). This takes D-S2 for Phase 1. Tile §6 stays the Phase 2 crate's, and
  fire_solid §7's D-S2 row and `client_objects.md` §7.3 become links here (§10).

It links to the rest:
- `kindle`'s vocabulary, stage-1 checks, lifecycle codes and receipt: `tile_and_client.md` §3.2;
- the solid, flash, extinction, the ledger and the fuel view: `fire_solid.md` §4.4, §5.4, §5.6;
- the flow, the registry, the digest and caches: `sim_core.md` §5.1, §6, §7, §9;
- the agent receipt: `sem_stimuli.md` §6.2; the fuel tables and the Phase 1 flame: `client_objects.md` §3, §5.3.

Tags as in `fire_solid.md` (V, S, M, D); D numbers are `reviews/torch_pilot/numbers.md`'s.

## 0. The answer

1. **In Phase 1 the torch is the alley's cone heater, made local, and its pilot, made conditional.** It imposes a
   prescribed surface flux on the fuel segments under its footprint. While it is live, the footprint is the only
   pilot. No flame object, no `HeatSource`, and nothing heats an air cell (`fire_solid.md` §3.1).
2. **The pilot is state:** a record keyed by its intent's id, saved and digested. It is never a flame. 6.2's held-flame
   design (fire_model §12) replaces it and defines what becomes of a saved one.
3. **The target is the nearest authored surface within 50 mm,** from one geometry query that every `kindle`
   producer's stage 2 calls. No term in the target or the deposit depends on dx.
4. **The deposit is exact area overlap** of the footprint disc with each segment part, delivered on the solid's
   physics step in proportion to the ticks the pilot covers.
5. **The torch's flux and radius can't be cited today,** so they are `[engineering]` values (§6, TP3). Nothing is
   fitted to make the exit pass.
6. **No `ignite` red gate flips by being rewritten.** Each goes only with the mechanism it guards, deleted at 6.1b
   with 5b's interim sphere `kindle`, its last producer (TP6). The exit gains its own gates, each of which a deletion
   turns red (§9).
7. **The 6.1 solid's limits show here and are named:** a strip's single profile smears a narrow footprint (a strict
   red gate), and nothing spreads beyond the strips the torch heats (§7).

## 1. What this rests on (read at origin/main 2586ed7)

- The cone case, its pilot and its hysteresis: `fire_solid.md` §4.4. The non-uniform heater test, the pattern for a
  footprint along a slab: `fire_solid.md` §6.
- Strips, whole-strip flash and the one segmented face of a slab: `fire_solid.md` §1.1–§1.2.
- Unpiloted ignition refused; no cited pilot distance: `fire_model.md` §3.2, P2-N1.
- The tick schedule (DC-N6) and the lifecycle codes: tile §3.2. The clock's config, `tick_us` and `physics_every`:
  `src/simcore/core/simulation.py::SimConfig`.
- Findings routed here by fire_solid §7: N-S2, N-N2, NN5, NS8, D-S5, A-S2.

## 2. The pilot record

<!-- contract: pilot.fields: actor_id seq target_kind object_id region_id face centre_m radius_m flux_w_m2 apply_tick end_tick -->
| Field | dtype | Meaning |
|---|---|---|
| `actor_id` | u32 | key, with `seq`: the intent's id, tile §3.1's `cause` |
| `seq` | u32 | key |
| `target_kind` | u8 | 0 a fuel object, 1 a solid cell region |
| `object_id` | u32 | the fuel object; 0 and unread when `target_kind` is 1 |
| `region_id` | u16 | the target's region |
| `face` | u8 | the face holding the nearest point (§3) |
| `centre_m` | 3 × f64 | the footprint's centre: the nearest point on the resolved `face`, in metres |
| `radius_m` | f64 | the item's footprint radius |
| `flux_w_m2` | f64 | the item's gauge flux (§4.2) |
| `apply_tick`, `end_tick` | u64, u64 | the covered ticks, [apply, end) |

- **The face enum, per target kind:** a slab's 0 top (its segmented face, fire_solid §1.1), 1 bottom, 2–5 the sides
  at −length, +length, −width and +width; a rod's 0 lateral (segmented), 1 its axis's start, 2 its end; 255 for a cell
  region, which takes no deposit in Phase 1 (§4.1).
- **Saved and digested** in key order: an input in `sim_core.md` §6 and a new member of its §9 digest, at a position
  sim_core's edit assigns. An empty member still hashes its name, dtype and shape, so 6.1b changes every tick digest: a
  recorded break under `sim_core.md` §12 (§10). Overlaps are derived (§4.3), neither saved nor digested.
- **Load refuses** a record whose end tick isn't after its apply tick, whose actor has two live records, whose object
  or region doesn't exist, whose object id isn't 0 for a cell target, whose face isn't in its kind's enum, or whose
  flux or radius lies outside the ceiling (§6). That is step 9's save requirement, with a round trip and a golden. Until then the 6.1b
  test is fire_solid §5.5's: the digest after a rebuild from the tables equals the running digest.
- **The lifecycle, in tick order** (`sem_stimuli.md` §4.1's steps):
  - **Appended** by the applier at stage 2, in step 1. It is the record's one appender.
  - **Live** at tick τ when apply tick ≤ τ < end tick. Tile §3.2's `pilot_live` reads that interval, never the
    record's presence, so a `kindle` at the end tick applies.
  - **Cut short** only on `leave`: the applier sets the end tick to the `leave`'s tick, in that tick's step 1. Nothing
    else ends a pilot early. A burnt-out object's row stays (`fire_solid.md` §1.1), and a cell target takes no deposit,
    so a pilot whose target burns out or is destroyed runs to its end tick, fruitless. Tile §3.2's "when its region is
    gone" is dropped (§10).
  - **Removed** by `Simulation` at the end of the first physics step at a tick ≥ the end tick − 1, or at the cut itself
    when every covered tick has already been integrated. No law deletes its own input.
- **Not perceivable:** the record, the pilots table and `pilot_ended` (`sem_stimuli.md` §7.4).
- **Its one resolver is the solid law** (`sim_core.md` §5.1).

## 3. The target

**The rule:** the candidate whose authored surface is nearest the point, within 50 mm. A second candidate less than
1 mm farther than the nearest makes it `ambiguous_point`. With no candidate within 50 mm (a point deep inside a
solid, or far from everything), the act is `not_on_surface`.
- **Candidates:**
  - every row of the object table, live or burnt out, as of the start of stage 2 (`pending` is excluded,
    `fire_solid.md` §1.4);
  - every solid cell region, by its authored solid primitives, minus carved air once world_model §5's CSG lands. It
    is never measured by its cells, whose faces move with dx, nor by `scene.py::footprint_of`'s bounding box.
  - A cell region is a candidate until authored geometry (a later paint) has taken every cell, as the applier's
    "gone" is (TP10). Destruction never removes one, nor is a crater seen: the authored primitives stand (§7), which is
    fruitless in Phase 1, since cells take no deposit.
  - When the sub-cell solids design lands, its objects of every role join, by its own states (TP1).
- **Distances** are f64 point-to-geometry distances in metres, from `point_mm` ÷ 1000 and the authored geometry
  (fire_solid §1.1 holds it in f64), by one fixed formula per kind. `centre_m` is stored unrounded.
- **Faces:** of one object's faces, those less than 1 mm farther than its nearest (an edge, a corner) resolve to the
  segmented face if it is among them, else to the lowest `face` value `[engineering]`. `centre_m` is the nearest
  point on the resolved face.
- **A slab on the floor doesn't tie:** a point on its top face is 0 from the slab and its thickness from the floor. A
  point on the contact line ties, and is refused. A slab no thicker than the tie band could never be kindled from
  above, so the catalogue refuses a slab recipe whose minimum thickness is ≤ 2 mm (§10).
- **One query, two policies.** The geometry layer returns candidates ranked by distance. `kindle`'s stage 2 applies
  this tie rule, and the sub-cell design's `strike` its own.
- **Every producer calls the same stage 2:** the client's intent and, from Phase 4, an NPC's body act (tile §3.2). Both
  log the same record kind with `target: null`, and replay recomputes the target from the logged point. In Phase 1 the
  client is the only producer, so the one-call-site test covers that path alone.
- **The receipt's effect value** (tile §3.3) is the derived target (its kind, object and region), never a deposit. An
  agent's receipt is `sem_stimuli.md` §6.2's `accepted` in every case.
- Porous `bed` objects need their own inside rule: 6.2's.

## 4. The deposit

### 4.1 The footprint

- **A disc** of radius `radius_m`, centred on `centre_m`, in the plane of the target's `face` (on a rod, the tangent
  plane there).
- **It deposits only on segment parts of that face.** On any other face it deposits nothing and the act still succeeds
  (fire_model §5.4). Any disc area beyond the face reaches nothing, as the cone heater's flux beside a sample doesn't,
  and is not on the ledger.

### 4.2 What it deposits

- **A uniform gauge flux q''_t over the disc** `[engineering]`: an impinging torch's profile is uncited.
- **Absorbed whole at the surface node** `[engineering]`: a torch heats mostly by convection (M), so neither ε nor
  in-depth absorption applies.
- **Losses are the cone's before flash:** convective and radiative loss stay on under the footprint, as under the cone
  heater. After flash the part is fire_solid §4.4's.
- **Per part, contributions sum in a fixed order:** pilots in key order, then the flame flux q''_fl (TP2).

### 4.3 Overlap, in metres

- **Per segment part:** A_ov = |disc ∩ the part's face region|, in closed form. A strip's face region is a rectangle
  on a slab, and on a rod the band's silhouette, 2R × ℓ, in the tangent plane.
- **Conservation:** Σ A_ov over a face equals |disc ∩ face| to 10⁻¹² relative `[engineering, as fire_solid §6's
  straddle test]`.
- **Computed per pilot by scalar functions** (`math`, not vectorised numpy), in segment key order, in one call shape at
  apply and on load. So a rebuild is bit-identical to the running value whatever other pilots exist (D1-S9's offset
  problem).
- **A cache keyed by the record's values,** built when the record is appended and on load, and evicted on removal and
  on rollback (`sim_core.md` §7).

## 5. The clock and the pilot condition

- **Time** is `Simulation.step`'s integer tick. The solid runs once per physics step (`fire_solid.md` §4.3).
- **The energy into part p** at the physics step ending at tick t:
  E_p,t = q''_t · A_ov,p · (`tick_us` ÷ 10⁶ s) · n_t,
  where n_t counts the pilot's ticks in (t − `physics_every`, t] (tile §3.2's schedule).
  - It is one named expression. The ledger books it, and the solve takes E_p,t ÷ (A_p · step length) as its step-mean
    surface flux.
  - It is booked as `fire_solid.md` §5.4's `incident_absorbed`, whose suppliers gain the torch (§10).
- **The solid's time refinement is `tick_us`,** the only knob that reaches it (`substep_refine` doesn't,
  `fire_solid.md` §4.3). The time study runs at `tick_us`, ½ and ¼ at a fixed `physics_every`, from a script that
  states its apply times and holds in seconds (§9.1), which its loader converts to ticks. Each run starts with the
  actor in reach, so no movement, whose speed is per tick (tile §2.3), enters it.
- **A part is piloted at a step** when n_t ≥ 1 and A_ov,p > 0. Only then may it flash, by fire_solid §4.4's rule at
  that step. Nothing else pilots in Phase 1: a flaming segment pilots nothing (P2-N1).
- **An unpiloted crossing** is a part at or above m''_flash on a step where it isn't piloted, which the solid's lag
  can produce after `end_tick`. It stays unignited. A lab instrument under `tests/` counts it (`fire_solid.md` §2),
  not `WorkCounters`.
- **Extinction and hysteresis are fire_solid §4.4's.** The torch ending doesn't extinguish anything. A part that goes
  out may flash again, but only when piloted.
- **A beat's time is interpolated within its step:** linearly between the two physics steps that bracket the crossing
  of its quantity (a part's m'' through m''_flash or m''_ext, the residue share through 0.1). So times aren't
  quantised to the 0.5 s step.

## 6. The torch's numbers

| Quantity | Value | Basis |
|---|---|---|
| q''_t | ε_r · 37.5 kW/m²; about 34 kW/m² at ε 0.9 (M) | `[engineering]` (TP3): the centre of the graded 25–50 kW/m² window, cone-equivalent, so the exit sits inside it with room on both sides. Searched: no measured hand-torch impingement flux (fire fluxes of 10–134 kW/m² aren't a torch's; S) |
| r_t | 0.05 m | `[engineering]` (TP3): the least radius the exit's footprint row admits on a 0.1 m plank. Tile §3.2's 2 kW over a 0.2 m disc is M, from the retired sphere deposit |
| `kindle`'s flux ceiling | min over shipped recipes of ε_r · 50 kW/m²; about 45 kW/m² at ε 0.9 (M) | D: 50 kW/m² is graded on both rungs (`fire_solid.md` §4.5) and FDS-verified for PMMA (§4.6; pine is graded only). A cone heater at q delivers ε·q; the torch delivers q whole. ε_r is the least of the recipe's fixed, unfitted ε values (pine's fitted char ε is excluded). Computed from 6.1's committed sets, and a 6.1b test holds `actions.yaml`'s number to it |
| `kindle`'s radius floor | ℓ = 0.02 m | `[engineering]`: at least two strips across; the strip-halving control (§9.4) raises it if it fails, never lowers it |
| The exit's plank | white pine (R1's recipe), 0.1 m wide and 0.6 m long, kindled at its centre | Width, D: R1 grades pine on a 0.01 m² sample (fire_solid §4.4), and m''_ext depends on sample size (fire_model §4.3), so the burning patch is cone-sized. Length `[engineering]` (TP7): 7 × 43 px at the golden view. Thickness: MaCFP-4's (M; read V before `content/`) |
| The exit's footprint | r_t ≥ 0.05 m, the slab's half-width | D: at r = W/2 a disc centred on the slab's centreline lies on it, and its most-covered strip gets 0.973–0.993 of q''_t over all centre offsets |
| An NPC's holds (`brief`, `steady`, `long`) | Phase 4's body design (tile §3.2) | each must lie outside every shipped recipe's flash band under this item's flux and radius, measured when the holds are set; `torch.yaml` gains them then, with a version bump |

- **A q''_t below ε_r · 25 kW/m²** lies below both rungs' graded range (converted as the ceiling is). The exit then runs
  as an extrapolation and is reported as one, never tuned.
- **The 0.2 m radius floor retires** with the sphere deposit. It existed for the coarsest cell, and nothing here sees a
  cell.
- **The torch's values are fixed and committed before the first exit run.** D and the cap come from the band runs by
  §9.2's rule, and are committed before the graded run.

## 7. Known gaps (into `docs/known_gaps.md` with 6.1b's commit)

- **A strip's mean smears a narrow footprint across its width.** A flash decided on the strip mean is averaging, then
  thresholding (CLAUDE.md). D, over all centre offsets: the most-covered strip gets 0.195–0.199 of q''_t at r = 0.05 m
  on a 0.5 m-wide plank, and 0.662–0.666 at r = 0.1 m on 0.3 m. A rod's ring gets at most 1/π: 14.3 kW/m² at a 45 kW/m²
  ceiling, below every graded flux, so every rod `kindle` is an extrapolation.
  - **A strict red gate** (`raises=AssertionError`): a footprint of r = 0.05 m on a 0.5 m-wide plank flashes within
    max(e_dt, s_floor) (§9.2) of the same footprint on a 0.1 m slab. A never-flash case fails the assertion.
  - **Fixed in the 6.2 design,** which must choose the mechanism: profiles across the width, or a footprint-sized
    sub-profile. 6.2's partial transfer alone doesn't fix it (`fire_solid.md` §1.2). At §6's r ≥ W/2 the exit's
    first strip is diluted by at most 2.7%. The gap is reduced there, not absent.
- **Nothing spreads beyond the strips the torch heats.** Strips don't conduct to each other, and no flame heats or
  pilots its neighbours until 6.2. A torch on a long plank lights a footprint-sized patch, which then goes out.
- **The torch heats no structural cell, and no body.** D: at a 45 kW/m² ceiling for 60 s, a concrete face rises about
  190 K with re-radiation and convection (187 K by a march that reads 3% low; 208 K by the lossless closed form). A
  0.1 m cell's mean would read 12.8 K. With losses it reaches concrete's 300 °C onset after about 140 s (D). The fix is
  skins on structural faces (the 6.2 design, D-S3), and tissue under Phase 4's body.
- **The cold-gauge convention overstates a hot surface's gain** by (h_t − h_c)(T_s − T₀). h_c's part (3.3 kW/m² at a
  350 °C surface, M) is kept by §4.2. The impinging flame's h_t is uncited.
- **m''_flash is fitted under a spark and a radiant heater** (fire_solid §4.5). Applied under an impinging flame it is
  a validation gap, not a verified law.
- **Energy beyond the face is lost:** none at r = W/2, 22% at r = 0.075 m, and 39% at r = W (D).
- **A slab's sides and underside take no footprint** (one segmented face in 6.1).
- **The target rule doesn't see destruction:** a cell region is its authored primitives, craters and all (TP10).
- **The floor, not the cone's Kaowool, backs the exit slab,** so its back-face behaviour is a prediction.
- **A cone-fitted q''_fl applies to every flaming part** (TP2): an extrapolation beyond the cone.
- **Torch and flame fluxes add after flash** (§4.2), but two impinging flames share one boundary layer, so their gains
  don't add. The overstatement is bounded by q''_t · A_ov over [`t_flash`, `end_tick`).
- **PMMA under the torch is absorbed at the surface,** but its sets absorb in depth: fire_solid §4.1's −6.2% and
  +42 s on FDS's peak at 50 kW/m² is the size of that error.
- **A pine surface charred before flash** has char's ε, which is fitted, and may gain more than the ceiling's
  cone-equivalent. Its size is measured at 6.1b.

## 8. What the client may draw

- **The torch flame,** a purely visual effect, while a pilots row is live: an additive emissive cone from the actor's
  held item, aimed at the footprint centre the pilots row carries (tile §2.2, TP5). Its look is
  `[engineering]`, with flicker off in goldens. Engine why: a flame has no surface for a pass to hit, so it draws after
  opaque geometry, as `client_objects.md` §5.3's flames do. Never colour alone: it adds shape and brightness.
- **The surface's heating** is drawn only from the fuel tables (`client_objects.md` §5). The client never draws heat
  it computed.
- **A named asymmetry:** a torch flame is luminous, and no Phase 1 stimulus row carries it. It joins
  `client_objects.md` §5.4's divergences, OPEN against OD-C8.

## 9. What the exit observes

### 9.1 Beats, on logged server state

The script is `tests/scenarios/slab_exit.yaml`, v0 and versioned. It departs from tile §6.2's form in one way: apply
times and holds are in seconds (`hold_s`), which its loader converts to ticks by `tick_us` (§5). It holds one `kindle`
on the slab's top face, with a hold of D seconds, and the cap of §9.2. Beats read the record, the tables and the ledger.
The residue share is computed by fire_solid §5.6's definition from the store, never from pixels.
1. **Applied:** the receipt is `applied`, with the slab as the target.
2. **Pilot:** the pilots row is live over [apply_tick, end_tick), and `pilot_ended` fires once.
3. **Flash:** `t_flash` is the first flash's interpolated time (§5). Every flash falls on a step the pilot covers.
   Reflashes are counted and reported.
4. **Char:** `t_char` is the interpolated time at which some segment's residue share reaches 0.1 `[engineering]`.
5. **Burn:** the flaming area is above zero on every step in [`t_flash`, `t_out`).
6. **Flame out:** `t_out` is the interpolated time at which the last flaming part goes out, after the pilot's last
   covered step, before the cap.
7. **Order:** `t_flash` falls no later than the pilot's last covered physics step, and `t_char` < `t_out`.
8. **Out stays out:** from `t_out` to the cap, no part flames and no flame flux reaches any part. This carries the
   burned-fuel gate's meaning onto fuel objects. A flame flux applied to a part that isn't flaming turns it red.
9. **Reported, not gated:** the unpiloted-crossing count; `t_out` − `end_tick` (a prediction, fire_solid §4.5); the
   footprint's energy on partly covered strips and off the slab.

### 9.2 Gates (bars derived from their sources' error; rules written now, values at 6.1b)

- **Margin** (`world_model.md` §3): every binary beat (flash against D, char reached, out before the cap) is held from
  its threshold by at least max(its spread across the three grids and three steps, one quantum: a coarsest tick for
  D, a physics step for a time). The script's D lies above the band's highest measured upper edge by that margin,
  and the cap lies past the latest `t_out` by its margin.
- **In time:** `t_flash`, `t_char` and `t_out` at `tick_us`, ½ and ¼ (0.5, 0.25 and 0.125 s steps), with
  |t(dt/2) − t(dt/4)| < |t(dt) − t(dt/2)|, or both zero. That checks convergence; the scheme's order is fire_solid §6's to verify.
  e_dt = |t(dt) − t(dt/2)| at 0.05 m is the shipped step's error.
- **Across grids:** every beat's class agrees at 0.2, 0.1 and 0.05 m, and each time lies within max(e_dt, s_floor)
  of 0.05 m's. The dx path is the slab's floor contact (`fire_solid.md` §3.2). s_floor is that path's own error
  carried to the beat: each time's change when, at 0.05 m, the contact exchange is scaled by the contact closed form's
  verified bound (`fire_solid.md` §6, 3%), up and down.
- **The ledger closes** (`fire_solid.md` §5.4), and **nothing heats air** (its §3.1 test, on the exit).

### 9.3 Determinism

Two stepped runs, the unpaced run and the replay are bit-identical at every physics tick (tile §6.3 item 9's form).
At 6.1b, the digest rebuilt from the tables and records equals the running digest at every step of the exit, with a
second pilot on the slab from another actor. Across machines, only the class is promised.

### 9.4 Controls, and the `ignite` red gates

| Control | Deletion that must turn it red |
|---|---|
| Flash needs the pilot | delete the pilot condition: a hold ending inside the band, where lag carries a part past m''_flash after the pilot's last step, then flashes |
| Flash needs the deposit | delete the deposit: beat 3 fails |
| Only the segmented face takes it | project the disc into the segmented face's plane: a point on the slab's side, more than 1 mm below its top edge, then lights it |
| Exact overlap | centre sampling: per-strip A_ov against fine quadrature, at centre offsets 0.13ℓ and 0.71ℓ and r = 0.051 m (2r/ℓ not whole) |
| Segment independence (a refinement, not a deletion) | strips halved: the interpolated times to 25, 50 and 75% of the final flaming area agree within max(e_dt, s_floor) |
| The ledger line | drop the torch's `incident_absorbed` |
| Out stays out | apply q''_fl to a part that isn't flaming: beat 8 |

**None of the four `ignite` red gates is rewritten onto this design** (NS8, D-S5, A-S2):
- `test_a_fire_that_has_burned_its_fuel_stops_heating` guards `core/deposit.py::Deposit`'s fallback into air.
- `test_the_fiercest_allowed_fire_…` reads cell integrity.
- `test_a_fire_on_a_region_carved_hollow_…` guards the centroid rule.
- `test_the_crate_is_badly_burned_at_the_same_time_at_every_rig`, whose trigger is Phase 2's.

The pilot touches none of them. At 5b, when `ignite` leaves the vocabulary, their precondition moves to 5b's sphere
`kindle` on a cell region, which uses the same `HeatSource` path, so each stays red on its own subject. At 6.1b the
sphere deposit, its last producer, goes, and with it `HeatSource`, `sources`, `source_exposure` and `Deposit`:
one recorded digest break with the pilots member (§2). Each gate and Known gap then closes by that deletion, recorded.
That is TP6, under which fire on structural cells leaves Phase 1. Today's `douse` removes a source, so it loses its
subject too: until 6.2's water sink (D-N3), a `douse` is applied and fruitless, a Known gap. It has no wire message in
v0 (T16), and Phase 1 has no NPCs.

## 10. What this changes elsewhere (TP9)

Documents marked † were edited on this branch; the rest are 6.1b's, with its code.

| Document or file | Change |
|---|---|
| † `tile_and_client.md` §3.2, §6.4 | the target sentence, the deposit bullet, the item's fields, `actions.yaml`'s `max_power_w` and the 0.2 m floor become links here; the lifecycle drops "when its region is gone"; the red-gate sentence ("rewritten to use `kindle`") links §9.4; the sphere band-aid's removal names 6.1b; 5b's interim target rule stays there, for cell regions only; §6.4's burned-fuel control closes with its gate |
| † `tile_and_client.md` §2.2 | TP5's columns, with `seq` for `cause` |
| † `fire_model.md` §5.4, §10.2, §12 | the target rule becomes a link; the flame-object pilot is Phase 2's; 6.1b joins the plan; the red-gate bullet links §9.4 |
| † `fire_solid.md` §1.3, §2, §4.4, §5.1, §5.4, §5.5, §7 | 6.1b uses no `holds_fuel`; `kindle` is excepted from the object-only refusal (TP1); q''_fl moves into the solid law (TP2) and its row says 6.1b; on the shipped path the pilot is §5's; the catalogue refuses slabs ≤ 2 mm; `incident_absorbed` gains the torch; the record joins the save list; the D-S2 row links §9 |
| † `client_objects.md` §5.4, §7.3 | the torch flame's divergence; the beats link §9, and step 8 maps G1–G5 onto them |
| † `sim_core.md` §6, §9 | the pilot input and its resolver; its digest member |
| `sim_core.md` §1, §3, §6, §9; `boundaries.md` §5's writer table | at 6.1b, `sources` and `source_exposure` retire (digest members 2 and 3) with `ignite`'s and `douse`'s writer rows; 6.1b's commit records the one break (§12's rule) |
| `sem_stimuli.md` §6.2's T11 sweep | 6.1b's tests include the off-face and cell-target `applied`-with-no-deposit cases (§4.1) |
| `data/world/actions.yaml` | `kindle`'s `max_flux_w_m2`, `max_duration_s`, `min_radius_m`; a version bump over 5b's v1, with a refusal test |
| `content/items/torch.yaml` | the version after 5b's sphere-era file: `flux_w_m2`, `radius_m`, `max_duration_s`, `restrike_s`; its loader checks them against the ceiling at load, with a gate-registry row |
| `tests/test_act_validation.py` | `test_every_verification_grid_is_at_least_as_fine_as_the_smallest_action`'s 0.2 m floor gives way to §6's two-strip floor |
| `tests/test_cross_tier.py`, `test_determinism.py`, `test_exposure.py`, `test_deposit.py` | the heat-source tests that drive `ignite` or `sources` are deleted with them or rehomed on the pilot, each named in 6.1b's commit |
| † `docs/roadmap.md` | 6.1b in Phase 1; Phase 1's "must flip the strict red gate" sentences follow §9.4 and TP6; the Phase 0 claim "fire outcomes agree across rigs" is retired for structure (TP6). At 6.1b, Phase 2 lists `core/solid.py` for the `TEMPORARY(phase2/6.2)` markers on the pilot deposit and, under TP2, q''_fl, and the strip-width red gate |
| `docs/known_gaps.md` | §7's entries; the four gates' gaps closed by deletion at 6.1b |
| † `docs/standards_backlog.md` B30 | tile §6.3 item 7's 2× margin listed (TP8) |
| † `docs/plans/checklists.md` steps 5b, 6, 8, 9 | 5b moves the four gates' precondition to the sphere `kindle` and names 6.1b for its removal; 6.1b's tests; step 8 maps G1–G5 onto §9.1's beats; the record in save v0 |

**The build step is 6.1b,** after 6.1 and 5b's vocabulary v1, before step 8's exit script. Placement:
- the ranked-candidate query and the overlap in `core/fuel_geometry.py` (layer 2);
- the record, stage 2 and the tie rule in `core/applier.py` (6);
- the deposit in `core/solid.py` (4);
- removal in `core/simulation.py`.

## 11. Rulings

The owner ruled §11's questions on 2026-11-22 (TP1–TP9, `decisions/torch_pilot.md`). Each ruling's contract is
stated above, at its owner section. The sub-cell solids session was told of TP1's conflict with its S0.

## 12. Maxim

Nothing here asks Maxim for anything. Phase 1 has no NPCs, and an NPC's `kindle` is tile §3.2's body act. OD-A16's
route is the roadmap's row (Phase 3, OD-A16), not this note's. Searched Maxim `origin/main` b98954f7 (`kindle`,
`torch`, `igniter`, `held item`, `delayed credit`, `eligibility`, `call window`); what bears on it:
- `docs/plans/tool_failure_credit.md`, lines 76–80: retiring at invocation end removes the 300 s pending window, and
  "R4 delayed credit must not assume the window";
- `docs/plans/roadmap_1_4.md`, R4: relief after a call returns credits the next call;
- `src/maxim/decisions/nac.py`: two paths reach past a call. The `tool:kindle` eligibility trace starts at 0.3,
  decays ×0.9 per loop iteration (not per second), is pruned below 0.01, and credits the 0.20-capped `_reward_bias`
  (`docs/plans/lookback_primitive.md`, "What exists"). The anchor tier has a 300 s window, read on `time.time()`
  (OD-A20).

**The evidence 6.1b hands OD-A16 is two delays:**
- from `kindle` to `t_flash`, physics, measured;
- from the receipt to the first change in a declared stimulus row: none in Phase 1, since no row carries flame
  (`client_objects.md` §5.4, OD-C8).

Lesson 38 records why this matters. The roadmap's OD-A16 row cites it, and the step 6 checklist records both delays
at 6.1b.
