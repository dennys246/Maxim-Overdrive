# The torch's Phase 1 pilot (design, 2026-11-22, for review)

**Scope.** The one question that blocks step 8's exit scenario (`docs/plans/checklists.md` step 6, "Added by D-B2"):
how a `kindle` ignites a slab when Phase 1 has no flame object. Phase 1's exit is the roadmap's (Phase 1, "Exit"): a
slab lit with the torch, which chars, burns and flames out. Flame objects, and with them fire_model §5.4's "the
torch's pilot is a flame object", are 6.2's, in Phase 2 (`client_objects.md` §1).

**What this document owns** (one owner per contract): the pilot record (§2), the deposit and its clock (§4), the
pilot condition (§5), the torch's physical data and `kindle`'s physics ceiling (§6), and what the slab exit observes
(§9). That last answers D-S2 for Phase 1: tile §6 is the Phase 2 crate's, so the slab's beats had no owner
(`client_objects.md` §7.3). It links to the rest:
- `kindle`'s vocabulary, stage-1 checks, tick schedule, lifecycle and receipt: `tile_and_client.md` §3.2;
- the target rule: `fire_model.md` §5.4;
- the solid, flash, extinction, the ledger and the fuel view: `fire_solid.md` §4.4, §5.4, §5.6;
- the flow (inputs, one resolver per input kind) and the field registry: `sim_core.md` §5.1, §6;
- the fuel tables on the wire and the Phase 1 flame: `client_objects.md` §3, §5.3.

Tags as in `fire_solid.md`: **V** primary source read, **S** secondhand, **M** memory (verify before it enters
`data/` or `content/`), **D** derived (`reviews/torch_pilot/numbers.md`).

## 0. The answer

1. **In Phase 1 the torch is the alley's cone heater and spark in one.** It imposes a prescribed surface flux on the
   fuel segments under its footprint, and while it is live that footprint is the pilot. That is `fire_solid.md` §4.4's
   cone case with the heater made local and the spark made conditional. No flame object, no `HeatSource`, and nothing
   heats an air cell.
2. **The pilot is state:** a record keyed by its intent's id, saved and digested. It is never a flame and never
   clusters. 6.2 replaces it with fire_model §5.4's flame object through a save migration.
3. **The target comes from fire_model §5.4's nearest-surface rule,** evaluated in integer micrometres on authored
   geometry, at stage 2, in one core function. A player's `kindle` and an NPC's run the same function on the same
   record kind.
4. **The deposit is exact area overlap** of the footprint disc with each segment part, delivered on the solid's
   physics step in proportion to the ticks the pilot covers. No term in it depends on dx.
5. **The torch's flux and radius can't be cited today.** A search found no measured hand-torch flux. The owner chooses
   between a bench measurement and `[engineering]` values inside the solid's graded range (§11, Q3). Nothing is fitted
   to make the exit pass.
6. **Two limits of the 6.1 solid show here, and they are named instead of hidden.** First, a strip's single profile
   smears a narrow footprint across the strip's width: a strict red gate and a Known gap, fixed in 6.2 (§7). Second,
   the torch heats no structural cell (§7).

## 1. What this rests on (read at origin/main 2586ed7)

- **The cone case** (`fire_solid.md` §4.4): flash at m''_flash, a prescribed q''_fl while flaming with convective loss
  off, extinction below m''_ext, at most one flash per part. The spark is present by definition, and the heater is
  uniform.
- **Strips** (`fire_solid.md` §1.2): a 0.02 m strip spans a slab's whole width with one profile per part, and it flips
  whole at flash. A slab's segments lie on one face only (§1.1).
- **Unpiloted ignition is refused** (`fire_model.md` §3.2). The cited pilot distance doesn't exist (P2-N1).
- **The ambient rule** (`fire_solid.md` §3.1): nothing an object loses enters an air cell, and a test holds it to that.
- **The tick schedule** (tile §3.2, DC-N6): the pilot covers ticks [apply_tick, apply_tick + D), and the physics step
  at tick t covers (t − 5, t]. That is T3: a 0.1 s tick, physics every 5 ticks.
- **Open findings routed here** (`fire_solid.md` §7, "6.4, with `kindle`'s pilot"): N-S2 (the pilot is state), N-N2
  and NN5 (the target rule), and NS8, D-S5, A-S2 (the `ignite` red gates). §2, §3 and §9.4 answer them.

## 2. The pilot record

<!-- contract: pilot.fields: actor_id seq object_id face centre_um radius_um flux_w_m2 apply_tick end_tick -->
| Field | dtype | Meaning |
|---|---|---|
| `actor_id` | u32 | key, with `seq`: the intent's id (tile §3.1's `cause`) |
| `seq` | u32 | key |
| `object_id` | u32 | the fuel target; the null id 2³² − 1 for a cell target (§4.4) |
| `face` | u8 | which of the target's faces holds the footprint (§4.1) |
| `centre_um` | 3 × i64 | the footprint's centre, the nearest surface point (§3), in whole micrometres |
| `radius_um` | i64 | the item's footprint radius |
| `flux_w_m2` | f64 | the item's gauge flux (§4.2) |
| `apply_tick`, `end_tick` | u64, u64 | the covered ticks, [apply, end) |

- **Keyed by (`actor_id`, `seq`)** (N-S2). One live pilot per actor is tile §3.2's `pilot_live`, unchanged.
- **Saved and digested,** in key order. A save mid-pilot that is then loaded continues bit for bit (§9.3). It is step
  9's save requirement.
- **The overlaps are derived** (§4.3): rebuilt from the record and the immutable geometry (`fire_solid.md` §1.1),
  never saved, never digested, and equal bit for bit to a rebuild.
- **An input, not a field a law owns** (`sim_core.md` §5.1). The applier appends the record at stage 2. Its one
  resolver is the solid law, at its physics step. It ends at `end_tick`, or on leave or `region_gone`, as tile §3.2's
  lifecycle says. Its registry entry sits beside `sources` (`sim_core.md` §6). It is not perceivable
  (`sem_stimuli.md` §7.4's default).
- **The wire's pilots row stays tile §2.2's** (`actor_id`, `region_id`, `end_tick`). In 6.0–6.1 each fuel object is
  its own region (`fire_solid.md` §1.3), so the row names the object. Whether it gains a point is Q5.
- **Not a flame.** It has no Q, no cluster, no height and no merge weight. Burning segments never pull it into a
  cluster, because Phase 1 has no clusters. 6.2 migrates each saved record to a flame object, under a save version
  bump.

## 3. The target

**The rule is fire_model §5.4's:** the nearest surface within 50 mm, and a tie within 1 mm is `ambiguous_point`. This
section fixes only how that rule is evaluated.
- **Candidates:** every live fuel object, by its authored geometry (`fire_solid.md` §1.1's kinds), and every solid
  cell region, by its cells' faces on integer-micrometre edges (F13).
- **Distances** are exact point-to-geometry distances in whole micrometres, computed from `point_mm` × 1000 and the
  authored integers. A point inside a candidate has distance 0 and its depth is its distance to the nearest face. A
  depth over 50 mm is `not_on_surface`, which restores tile §3.2's depth bound that fire_model §5.4 dropped (N-N2).
- **A slab on the floor doesn't tie:** a point on its top face is 0 from the slab and the slab's thickness from the
  floor. A point on the contact line ties and is refused, as N-N2 says it must be. The thickness must exceed the 1 mm
  tie band, which every `slab` recipe's geometry range does (`fire_solid.md` §5.1).
- **One function, at stage 2, in the core,** called for every `kindle` record whatever produced it. The client's
  intent and an NPC's body act (tile §3.2: the body modulator, `hold` converted to ticks) both log the same record
  kind with `target: null`. Replay recomputes the target from the logged point. No producer names a target.
- **tile §3.2's restatement** ("two candidates is `ambiguous_point`") is the stale T4 rule that fire_model §10.1
  revised (NN5). It becomes a link here (§10).
- **Bed objects** (6.2) need a rule for a point inside porous fuel. That is 6.2's, as N-N2 notes.

## 4. The deposit

### 4.1 The footprint

- **A disc** of radius `radius_um`, centred on `centre_um`, lying in the plane of the target face that holds the
  nearest point. On a rod, it lies in the tangent plane there.
- **It deposits only on segment parts of that face.** A slab's segmented face is its top (`fire_solid.md` §1.1). A
  footprint on a side or the underside deposits nothing, and the act still succeeds (fire_model §5.4: "a fruitless act
  succeeds as an act"). A rod's lateral surface carries its segments, and its ends carry none.
- **The disc's area beyond the face** reaches nothing: the slab next to it, the floor under an overhang, the air. It
  never enters the world, so it is not on the ledger, just as the cone heater's flux outside the sample isn't.

### 4.2 What it deposits

- **A uniform gauge flux q''_t = `flux_w_m2` over the disc** `[engineering]`: the profile of an impinging torch is
  uncited (§6). It follows the convention of `fire_solid.md` §4.4's q''_fl, a flux as a cold gauge reads it.
- **It is absorbed at the surface node,** not through the in-depth absorption of §4.1 of fire_solid: a torch heats
  mostly by convection (M). For the exit's opaque pine (κ → ∞), the two are the same.
- **Over the covered share of a part, the convective loss is off,** because the torch's gas sits on the surface. That
  is the same rule as under the cone flame. Re-radiation stays.
- **It adds** to everything else the part receives: a flaming part gets q''_fl (Q2) and the torch together, as a cone
  sample gets heater and flame.

### 4.3 Overlap, in metres

- **Per segment part:** A_ov = |disc ∩ the part's face region|, exact, from the integer geometry. A strip's face
  region is a rectangle (slab), or the band's silhouette 2R × ℓ in the tangent plane (rod).
- **The covered share** f = A_ov ÷ A_part, with zero-area parts skipped (`fire_solid.md` §1.2's hygiene).
- **Conservation:** Σ A_ov over a face equals |disc ∩ face| to 10⁻¹² relative `[engineering, as the straddle test]`.
- **Centre sampling is forbidden** (CLAUDE.md, deposit by exact average). The build test moves the centre by ℓ/3 and
  2ℓ/3 (§9.4).

### 4.4 A cell target

A `kindle` whose target is a solid cell region is `applied`, records the null `object_id`, and deposits nothing in
Phase 1. A structural face has no skin unless it touches fuel (`fire_solid.md` §3.2). Depositing into the cell mean
would understate its face temperature by an amount set by dx (D: 75 kW/m² for 60 s raises a semi-infinite concrete
face about 346 K, but a 0.1 m cell's mean by 21 K). It is a Known gap (§7).

## 5. The clock and the pilot condition

- **Time** is `Simulation.step`'s integer tick. The solid runs once per 0.5 s physics step (`fire_solid.md` §4.3).
- **The energy into part p at the physics step ending at tick t** is q''_t · A_ov,p · 0.1 s · n_t, where n_t is the
  number of the pilot's ticks in (t − 5, t] (tile §3.2's schedule). The implicit solve sees that as a step-mean surface
  flux q''_t · f_p · n_t / 5, and it turns the convective loss off on the share f_p · n_t / 5. Ledger and solve use the
  same f64 expression.
- **Booked** as `fire_solid.md` §5.4's `incident_absorbed`, whose suppliers gain the torch (§10). The cone harness
  stays the other supplier.
- **A part is piloted at a step** when n_t ≥ 1 and A_ov,p > 0. Only then may it flash, by fire_solid §4.4's rule,
  evaluated at that step. The pilot is the only one Phase 1 has: a flaming segment pilots nothing, since no cited
  distance exists (P2-N1).
- **An unpiloted crossing** (a part at or above m''_flash that isn't piloted) stays unignited. It is counted in a work
  counter that the exit reports (§9.1). Phase 1 has no lateral conduction between strips, so only the torch can raise
  a strip that far.
- **Extinction, hysteresis and the one-flash cap are fire_solid §4.4's,** unchanged. The torch ending doesn't
  extinguish anything. Flaming parts go out when their own mass flux falls below m''_ext.

## 6. The torch's numbers

| Quantity | Value | Basis |
|---|---|---|
| q''_t | **open (Q3)** | searched: no measured hand-torch impingement flux found (DTIC wood and propane fire fluxes of 10–134 kW/m² are fires, not torches; S) |
| r_t | **open (Q3)** | as above; tile §3.2's 0.2 m disc and 2 kW are M and come from the retired sphere deposit |
| `kindle`'s flux ceiling | 65 kW/m² | D: the lower of the highest graded fluxes, PMMA's 65 and pine's 75 (`fire_solid.md` §4.5), so no `kindle` drives a shipped recipe past its graded range |
| `kindle`'s radius floor | ℓ = 0.02 m | `[engineering]`, by analogy with the two-cell rule: a footprint at least two strips across; the strip-halving test (§9.4) raises it if it fails, never lowers it |
| D, the hold | from the band (§9.2) | tile §6.3 item 7's rule: ≥ 2× the band's upper edge |
| The exit's slab | white pine (R1's recipe), 0.1 m wide | D: R1 grades pine on a 0.01 m² sample (`fire_solid.md` §4.4), and m''_ext depends on sample size (fire_model §4.3). Its thickness is MaCFP-4's (M; read V before `content/`) |
| The exit's footprint | r_t ≥ W | D: 84% of the footprint's energy lands in fully covered strips at W = r_t, and none at W = 2r_t (§7) |

- **A q''_t below 25 kW/m²** lies under both rungs' graded range, so the exit would run as an extrapolation of the
  solid. It is reported as one, never tuned.
- **The 0.2 m radius floor retires** with the sphere deposit (fire_model §5.4). It existed for the coarsest cell, and
  nothing here sees a cell.
- **Fixed before the first exit run** and committed, as fire_solid §4.5's fitter is pre-registered.

## 7. Known gaps (into `docs/architecture.md` with the build step's commit)

- **A strip's mean smears a narrow footprint across its width.** One profile per strip means a flash decided on the
  strip mean, which is averaging then thresholding (CLAUDE.md). D: the most-covered strip receives at most 0.195 of
  q''_t when r = 0.05 m on a 0.5 m plank, and 0.973 when r = 0.05 m on a 0.1 m slab. A rod's ring gets at most 1/π.
  Refinement across the width (6.2's partial transfer, `fire_solid.md` §1.2) is the verification: a **strict red gate**
  (`raises=AssertionError`) asserts that a footprint narrower than its slab flashes at the time the same peak flux
  gives on a slab it covers. It is fixed in 6.2. The exit stays clear of it by §6's W ≤ r_t.
- **The torch heats no structural cell** (§4.4). D: up to about 346 K of face rise at the ceiling for 60 s, past
  concrete's 300 °C degradation onset, is missed. The fix is skins on every structural face (the 6.2 design, D-S3).
- **The cold-gauge convention overstates a hot surface's convective gain** by h_t(T_s − T_0), where h_t, the
  impinging flame's coefficient, is uncited. The cone flame's q''_fl shares the convention.
- **A slab's sides and underside take no footprint,** since 6.1's slab has segments on one face.
- **The floor backs the exit slab, not the cone's Kaowool:** back-face behaviour is a prediction (`fire_solid.md` §4.5).

## 8. What the client may draw

- **The torch flame,** a purely visual effect (CLAUDE.md), while a pilots row is live: an additive emissive cone from
  the actor's held item towards the target, `[engineering]` in look, flicker off in goldens. Engine why: a flame has
  no surface, so it is drawn like `client_objects.md` §5.3's flames, after opaque geometry. Never colour alone: it adds
  shape (pixels where nothing was) and brightness.
- **Without a point on the wire** (Q5) the client aims at the target object's top face centre. With one, it aims at
  the footprint.
- **The surface's heating is drawn only from the fuel tables:** glow from the segment's surface temperature, the
  Phase 1 flame from `ignited_fraction` (`client_objects.md` §5). The client never draws a footprint's heat it
  computed.
- **A named asymmetry:** a torch flame is luminous, but no Phase 1 stimulus row carries it. It joins
  `client_objects.md` §5.4's divergences, OPEN against OD-C8.

## 9. What the exit observes

### 9.1 Beats, on logged server state (never pixels)

The script is step 8's `tests/scenarios/` file, in tile §6.2's form, with one `kindle` whose point is on the slab's top
face, and the cap of tile §6.2.
1. **Applied:** the receipt is `applied`, and its derived region is the slab's.
2. **Pilot:** a pilots row is live over [apply_tick, end_tick), and `pilot_ended` fires once.
3. **Flash:** `t_flash` is the first physics step with a flaming part. Every flash happens at a step the pilot covers.
4. **Char:** `t_char` is the first step at which some segment's residue share (`fire_solid.md` §5.6) is ≥ 0.1
   `[engineering, as tile §6.3 item 3's 10%]`.
5. **Burn:** the flaming area is > 0 on every step in [`t_flash`, `t_out`).
6. **Flame out:** `t_out` is the first step after `end_tick` with no flaming part, before the cap.
7. **Order:** `t_flash` < `end_tick` ≤ `t_out`, and `t_char` < `t_out`.
8. **Reported, not gated:** the unpiloted-crossing count; `t_out` − `end_tick` (fire_solid §4.5: with the heater
   removed it is a prediction); the share of the footprint's energy that landed in partly covered strips.

### 9.2 Gates

- **The band:** flash is binary, so its hold D is band-gated (`world_model.md` §3). The build step measures the band
  in D, q''_t fixed, at 0.2, 0.1 and 0.05 m and at the 0.5 and 0.25 s steps, and the script's D is ≥ 2× its upper
  edge (tile §6.3 item 7).
- **Across grids:** the class of every beat agrees on every grid, and `t_flash`, `t_char` and `t_out` agree by
  `verify_harness.md` §4's `agrees`. The gate names its dx path: the slab's contact with the floor (`fire_solid.md`
  §3.2), the only place dx enters (fire_model §6.1).
- **In time:** the same beats at dt and dt/2 within fire_solid §6's flash tolerance, max(0.5 s, 3%).
- **The ledger closes** (`fire_solid.md` §5.4), with the torch's `incident_absorbed`.
- **Nothing heats air** (`fire_solid.md` §3.1's test, run on the exit).

### 9.3 Determinism

Two stepped runs, the unpaced run and the replay are bit-identical at every physics tick (tile §6.3 item 9's form).
So is a save taken at a mid-pilot tick and loaded, against one continuous run. The pilot's inputs are integers plus a
digested data file's flux, and the overlaps are a fixed closed form summed in segment key order. Across machines only
the class is promised.

### 9.4 Controls, and the red gates

| Control | Deletion that must turn it red |
|---|---|
| Flash needs the pilot | flux on, pilot condition off: no flash, and a nonzero unpiloted count |
| Flash needs the flux | pilot on, q''_t = 0: no flash |
| The footprint lands only on segmented faces | a point on the slab's side: `applied`, zero deposit |
| Exact overlap | centre sampling: the ℓ/3 and 2ℓ/3 offsets' total deposit differs past 10⁻¹² |
| Segment independence | strips halved: a different class, or `t_flash` past max(0.5 s, 3%) |
| The ledger line | drop the torch's `incident_absorbed` |

The three `ignite` red gates (NS8, D-S5):
- `test_a_fire_that_has_burned_its_fuel_stops_heating` is rewritten on the exit slab with `kindle`. Its bar is
  unchanged in meaning: after `t_out` the world gains no heat from the fire. It flips, and its gate is removed.
- `test_the_fiercest_allowed_fire_…` is rewritten with `kindle` at §6's ceiling and the item's longest hold, keeping
  its bar (the same outcome on every grid at every physics step, integrity within 0.1).
- `test_a_fire_on_a_region_carved_hollow_…` tests the centroid rule that retires with `ignite`. It is replaced by a
  passing test that `kindle` on a hollow cell region heats no air, and its Known gap is closed by name, not deleted.

## 10. What this changes elsewhere (after the owner's rulings)

| Document | Change |
|---|---|
| `tile_and_client.md` §3.2 | the deposit bullet, the item's fields and the 0.2 m radius floor become links here; the target sentence becomes a link to fire_model §5.4 |
| `fire_solid.md` §2 | `kindle` is excepted from the object-only refusal (Q1) |
| `fire_solid.md` §5.4, §7 | `incident_absorbed` gains the torch as a supplier; q''_fl's placement (Q2) |
| `data/world/actions.yaml` v1, `content/items/torch.yaml` | `kindle`: `max_flux_w_m2`, `max_duration_s`, `min_radius_m` = 0.02; the item: `flux_w_m2`, `radius_m`, `max_duration_s`, `restrike_s`; each a version bump with a refusal test (repo-only formats) |
| `docs/design/contracts.md` | `pilot.fields` registered |
| `docs/plans/checklists.md` step 6 | the build sub-step and its tests |

**The build step** is 6.1b, after 6.1 and 5b's vocabulary v1, before step 8's exit script. Placement: the record and
the stage-2 target function in `core/applier.py`'s layer (6); the overlap geometry in `core/fuel_geometry.py` (2);
the deposit in the solid law, `core/solid.py` (4).

## 11. Open questions for the owner

- **Q1. `kindle` on a fuel slab is refused today.** `fire_solid.md` §2 refuses every act on an object-only region
  with `fuel_only_region`, and the exit's slab is one. The unmerged sub-cell solids design (S0) would rename that code
  `wrong_target`, and its acts table gives `kindle` to 6.4. Recommended: except `kindle` in fire_solid §2, linking
  here, and tell that session.
- **Q2. Nothing on the shipped path applies q''_fl.** `fire_solid.md` §7 places the prescribed flame flux in the cone
  harness under `tests/fire/`. Without it, the slab burns only while the torch is on it, and flames out as soon as the
  torch ends. Recommended: q''_fl, already one fitted constant per material (§4.5 of fire_solid), moves into the solid
  law as recipe data, flagged fitted in every result, and the harness keeps the heater and the spark.
- **Q3. The torch's flux and radius.** (a) Measure a real torch with a heat-flux gauge at stated standoffs, a
  pre-registered bench measurement like the starter's (fire_model §7). (b) Choose `[engineering]` values inside
  25–65 kW/m², and describe the item honestly as a game torch, not a cited propane torch. Recommended: (b) now and
  (a) when a gauge is available. Either way the values are fixed before any exit run.
- **Q4. The strip gap.** Accept §7's strict red gate, fixed in 6.2, with the exit slab authored at W ≤ r_t?
  Otherwise 6.2's partial transfer comes forward into Phase 1. Recommended: accept.
- **Q5. A point on the wire.** Add `point_mm` (3 × i32, 12 B) to tile §2.2's pilots row, so co-op and replay draw the
  torch where it heats, or keep 10 B and aim at the face centre. Recommended: add it, in step 7's freeze.
- **Q6. The edits of §10.** Make them on this branch once Q1–Q5 are ruled, so that no stale owner survives the merge.

## 12. Maxim

Nothing here asks Maxim for anything. Phase 1 has no NPCs, and an NPC's `kindle` is tile §3.2's body act. Searched
Maxim `origin/main` b98954f7 for `kindle`, `torch`, `igniter`, `held item`, `delayed credit`, `eligibility`. Delayed
credit is R4's, on `NAc._eligibility` (pruned after about 44 loop iterations, `docs/plans/lookback_primitive.md`,
shipped; `deferred/three_factor_credit_assignment.md`, revived with R4's build). So OD-A16 stays a question to R4.
The time from `kindle` to `t_flash`, measured at 6.1b, is its evidence.
