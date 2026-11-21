# Executor review: `docs/design/fire_solid.md` (fire 6.0–6.1), 2026-11-20

Lens: are the design's claims about code, data and tools true, and can each test fail? Code read at `gates` 396ae10 (read-only). MaCFP read from `MaCFP/matl-db` `master` via `gh api`. FDS 6.11.1 run
on copies in `_durable/fire_solid_review/scratch/executor/` (`env -i`, one thread).

**Counts:** 5 BLOCKER, 9 SHOULD-FIX, 5 NIT.

## BLOCKER

### EX-B1. The MaCFP PMMA FDS inputs are not cone inputs. They are anaerobic gasification runs with no flame, and none exists at 65 kW/m²
`fire_solid.md::intro` ("MaCFP ships FDS cone inputs for black PMMA"), `§6` FDS-verification row ("at 25, 50 and 65 kW/m²").
- **Claim:** MaCFP ships FDS *cone* inputs, and FDS verification runs at 25, 50 and 65 kW/m².
- **True:** All 15 `PMMA/Validation_Results/**.fds` files (NIST-StMU-FSRI 25R1–3, R3–R5, T1–T5; Aalto-I/II 25 and
  50) have `SOLID_PHASE_ONLY=T` and a constant `EXTERNAL_FLUX` of 25 or 50 only. They have no flame and no
  `RAMP_EF`. Aalto's title is `'N2 cone calorimeter'`. `PMMA/README.md` says Validation_Data is "anaerobic
  gasification of PMMA", and its folder is `NIST_Gasification_Apparatus`, with q25 and q50 only. So, to the
  brief's question: **no, the MaCFP PMMA inputs do not model the flame's heat feedback.** Their h is 13 W/m²K,
  calibrated to the gasification device.
- **What still holds:** these inputs are a fair *numerics* reference for the non-flaming solid. They verify
  nothing about q''_fl, flash or extinction, and nothing at 65 kW/m² until we write that input ourselves.
- **Failure scenario:** a builder reads "FDS's boundary conditions" as cone conditions, adds q''_fl or compares
  against cone MLR, and the gate fails for a reason that isn't numerics. Fix: call them gasification inputs, verify at 25 and 50 (plus a hand-written 65 marked
  as ours), and say the flaming phase has no FDS reference.

### EX-B2. The FDS-verification gate can't pass with the solver §4.1 specifies: MaCFP's PMMA has in-depth absorption
`§4.1` ("one linearisation of εσT⁴ at the front"), `§6` FDS row ("MaCFP's NIST-StMU-FSRI PMMA parameters", "peak MLR within 2%, its time within 5 s").
- **Claim:** our solver with MaCFP's parameters reproduces FDS's curves to about 2% and 5 s.
- **True:** every PMMA MATL in the NIST-StMU-FSRI input has `ABSORPTION_COEFFICIENT=2620` (Aalto: 3421), so FDS
  absorbs radiation in depth. §4.1's solver absorbs it at the surface. I measured the difference by deleting the
  absorption coefficient from `nsf_R3.fds` (50 kW/m²). Peak BR went from **31.99 to 30.02 g/m²s (−6.2%)**, and the
  peak time from **346 to 388 s (+42 s)**. That is three times the example tolerance on the rate and eight times on the time.
- **Failure scenario:** a correct implementation of §4.1 fails the pre-registered gate. The builder then either
  loosens the tolerance or quietly edits the reference, which is the band-aid CLAUDE.md forbids. Fix: one of the
  following, stated before the run:
  - (a) implement in-depth absorption;
  - (b) verify against an FDS copy with the coefficient removed, recorded as a model-form difference;
  - (c) restrict verification to surface-absorbing parameter sets.

### EX-B3. The coupling-frequency check in R1 can't fail: R0 and R1 have nothing to couple to
`§3` "Frequency" ("R1 compares that against a run coupled at every heat substep"), with `§3` ("R0 and R1 are otherwise grid-free") and `§4.1` "Back face" (MaCFP's insulation layers).
- **Claim:** R1 compares once-per-step coupling against coupling at every substep, and a class or time outside
  tolerance fails 6.1.
- **True:** in R1 the sample's backing is MaCFP's insulation, modelled as layers inside the 1D solid, and its losses
  go to ambient T∞ (§3). No cell touches it, so the "coupling" has no partner and both runs compute the same thing.
  "Tolerance" is also undefined, which repeats NN6 from delta round 1.
- **Failure scenario:** delete the coupling code entirely and the R1 comparison stays green. Fix: run the check on
  the straddle or the coupling-closed-form scene, where a slab touches concrete cells, with a stated tolerance.

### EX-B4. The segment-halving test can't fail on R0 and R1
`§1.1` "Segment size" ("halving it must keep R0's and R1's classes and graded times"), `§6` row "Segment size halved".
- **Claim:** halving the segment size tests segment-independence on R0 and R1.
- **True:** under a uniform heater and a uniform q''_fl, every segment of a cone sample is identical. Conduction is
  1D in depth with no lateral term (§4.1), and every segment flashes on the same step. Halving the size only changes
  how many identical copies are summed, and the front never moves in a cone test.
- **Failure scenario:** a bug in the front, in area transfer or in per-segment indexing passes, because no segment
  differs from another. Fix: grade segment size on a scene with a gradient along the object: a slab half-shadowed
  from the heater, or a rod heated at one end, with lateral spread or the front active.

### EX-B5. `World._power_field` is a missed occupancy consumer. Admitting object-only regions sends `ignite` power into air
`§2` consumer table ("Every consumer that asks 'is something here' … switches to an explicit rule").
- **Claim:** the table lists every consumer.
- **True:** `src/simcore/core/world.py::World._power_field` reads `on_solid = frac * self._grid.solid` and falls
  back to `weights = frac` (air cells) when the sphere touches no solid. The table doesn't list it. §2 changes
  `applier._check_region` to accept a region "with no solid cells" if it has objects, so `ignite` on such a region
  (a cardboard object alone in its region) is now accepted. Its power is then dumped into air cells. §3 says that
  heat has no Phase 1 sink and is set by dx, and fuel never receives it, because objects couple only to solid cells
  and to ambient.
- **Failure scenario:** an NPC calls `ignite box` on a fuel-only region. It was refused before 6.0 and is accepted
  after. The power heats air by an amount set by dx, and the cardboard stays at ambient: a success with no effect,
  and a resolution-rule violation. Fix: add the row, and refuse `ignite` on object-only regions until 6.4's
  `kindle`, or deposit on the object.

## SHOULD-FIX

### EX-S1. The pine m''_ext range is contradicted by the pine data the fit uses: flames persist down to about 1 g/m²s
`§4.2` ("m''_ext in 2.7–8.3 g/m²s (V7 1)"; "pins m''_ext ≤ 3.8").
- **True:** MaCFP's own flame-out times show flaming well below 2.7. I took the mass flux as a ±30 s difference of
  mass over a 0.01 m² area:

  | Test (25 kW/m², parallel) | Recorded flame-out | m'' at flame-out | m'' first < 2.7 |
  |---|---|---|---|
  | FSRI R1 | 2,279.75 s | 0.93 | 1,727 s |
  | FSRI R2 | 2,131.75 s | 1.17 | 1,828 s |
  | FSRI R3 | 2,050.25 s | 0.78 | 1,872 s |
  | IMT R1 | 2,301 s | 1.33 (≈ 1.5 over the 94 mm frame) | 2,050 s |
  | IMT R2 | 2,178 s | 1.17 (≈ 1.3) | 1,860 s |

  The 2.7–8.3 band (V7 1) is a step-down self-extinction band from CLT rigs. The constraint the heater-on cone data
  impose is m''_ext ≲ 1.2 g/m²s, not ≤ 3.8. HRR at flame-out is still 25–28 kW/m² at m'' ≈ 0.9, so char oxidation
  carries much of the late HRR, and §4.1 turns it off.
- **Failure scenario:** the bounded fit lands at 2.7, the edge, and the model still flames out 180–550 s early
  at 25 kW/m². The design forbids leaving the range, so R1 fails on a bound, not on physics. Fix: either derive the
  band from MaCFP-4's own flame-out data (heater on), or grade only up to a stated time before flame-out.
  Either way, say which.

### EX-S2. "Heater removed at a pre-registered time" is graded with no data
`§4.3` pine row ("Graded on … the heater removed at a pre-registered time").
- **True:** no MaCFP-4 cone test removes its heater. The READMEs I read (FSRI, Aalto, FZJ, IMT) record `t_ign` and
  `t_flameout` under a constant heater. Delta round 1's NN4 said this, and it is still open. The FSRI README also
  shows that pine flames under the heater for about 2,000 s, so "flames out when the heater goes" has no
  measurement to compare against.
- **Failure scenario:** the row grades a prediction against nothing. Fix: mark it "prediction, not graded", or cite
  a step-down dataset.

### EX-S3. "Q'' ≥ 24 kW/m² sustained" has no window, and the data show why it needs one
`§4.2` ("t_ig is graded at the data's own definition (Q'' ≥ 24 kW/m² sustained)").
- **True:** MaCFP-2's rule is "Q'' ≥ 24 kW/m²" (V7 12), with no "sustained". The pine labs record `t_ign` by hand:
  FSRI's operator pushes a button. In FSRI 25 kW R3, HRR crosses 24 at 27–30 s, drops to 6 kW/m² at 52 s, and
  rises again at 56 s. The recorded `t_ign` is 52.25 s.
- **Failure scenario:** three plausible readings of "sustained" give t_ig = 27, 52 or 57 s for one test. Fix: state
  the window (for example, ≥ 24 for 10 s) and which column is graded (the HRR rule or the lab's `t_ign`).

### EX-S4. The save validator refuses every save after pyrolysis starts
`§1.3` "Saves" ("inventories ≥ 0 that sum to the recipe's mass").
- **True:** pyrolysis removes mass, and `removed_with_mass` is a ledger line. A mid-burn object's inventories sum to
  less than its authored mass. §1.1 also holds inventories twice, as kg per object and as per-node density, with no
  stated invariant between them.
- **Failure scenario:** §6's "save and load at every step of a cone run" refuses the first save after flash.
  Weakening the validator to make it pass is a loosened check. Fix: the validator should check the following, and
  the double storage should become one source of truth or a checked invariant:
  - Σ(node density × node volume) equals the object's inventory;
  - the inventory is ≤ the authored mass;
  - the recipe's admitted components are the only ones present.

### EX-S5. Several formats and facilities the design calls "today's" don't exist at gates 396ae10
`§5.1` ("path and SHA-256, as today"; "registered `materials_v0_to_v1`"), `§5.2` ("migration from v1"), `§2` ("u16 `region` channel … unchanged"), `§1.1` ("field registry"), `§5.3` (snapshot tables, save).

| Claim | True at gates 396ae10 |
|---|---|
| A log header with each file's path and SHA-256 "as today" | No intent log exists. The step 5a checklist creates it. `boundaries.md` §6.3 specifies a digest "over a canonical serialisation of the loaded, typed value", not of the file, and a path in the header makes it machine-dependent |
| A registered migration `materials_v0_to_v1` | No migration registry exists. `checklists.md` (step 3b) limits migrations to "formats other people hold … Repo-only files get a version bump and a refusal test", and `core.yaml` is repo-only |
| Scene v2 migrates from v1 | `scene.py::SCENE_VERSION = 0`; scene v1 hasn't landed |
| A u16 `region` channel, "unchanged" | Regions are a dict of boolean masks (`CellStore._regions`, `name_region`), and `grid.py` has no id channel. `region_id` is step 5a's (world_model §5, O34) |
| A field registry, snapshot tables, a save | The field registry is step 5a's. `encoding.snapshot` returns a dict of arrays, and the table grammar (F2–F4) is step 7's. Save v0 is step 9's, after step 6 |

- **Failure scenario:** 6.0 can't be built in the order the plan gives. Either it silently builds pieces of 5a, 7
  and 9, or it extends formats that aren't there. Fix: list the dependencies (5a: log, registry, region ids; scene
  v1; step 7's table grammar; step 9's save, or a 6.0-local save with its own version) and use the digest form from
  boundaries §6.3.

### EX-S6. `surface_temperature_c` as u8 °C clips every ignited surface
`§5.3` snapshot table ("u8 | °C, display-quantised as `temperature_c` is").
- **True:** `encoding.snapshot` sends `temperature_c` as **f16**, clipped to [−273, 6000]. `client_rendering.md` §4.2
  also says f16. A u8 holds 0–255 °C. FDS's PMMA surface reaches 364 °C at 25 kW/m², and 404 °C at peak with 620 °C
  maximum at 50 kW/m² (my runs).
- **Failure scenario:** every flaming surface reads 255 °C. Fix: use f16, or a u8 with an offset and scale.

### EX-S7. The consumer table's "Today" column misdescribes three consumers and misses others
`§2` table.
- **Misdescribed:**
  - `StructureModulator.__init__` and `region_parts` don't use `cells.any()`. They call `frame.is_solid(region)`,
    which is `Region.solid`, a flag set once at `paint` (`solid=mid != AIR_ID`) or `True` for imagined objects.
  - `applier._on_region` doesn't refuse anything. It decides strike-point ownership from footprints and the other
    regions' `solid` flags.
  - `_check_region`'s second refusal (`not cells.any()`, "is gone") is a separate rule that the "After" column
    merges away.
- **Missing:**
  - `World._power_field` (EX-B5);
  - `CellFrame.solid` and `CellFrame.is_solid` (the `Observation` protocol the membrane reads);
  - `damage.thermal_degrade` (`grid.solid`);
  - `tests/test_determinism.py::digest`, which hashes `region.solid` and must hash the new tables.
- **Unspecified:** `damage.region_integrity` returns **0.0** for a region with no original solid cells, so an intact
  fuel-only region reads integrity 0 ("destroyed") to an NPC. The design leaves `damage.py` unchanged.
  `CellFrame.reading`'s "adds object reductions" doesn't say how a cell-volume mean and a segment-area mean are
  joined into one `temperature_mean`.
- **Failure scenario:** an NPC reads intact cardboard as integrity 0.

### EX-S8. Two tolerances are borrowed from places that don't define them
`§6` "Straddle" row ("within tile §6.3's tolerance"), `§3` and `§1.1` ("within tolerance").
- **True:** tile §6.3's tolerances are 15% and 10% on the times `t_crack`, `t_glow` and `t_gone`, with a convergence
  rule against a 0.05 m reference. They don't cover coupling totals or the floor's heating, and the straddle test
  has no 0.05 m reference rule.
- **Failure scenario:** with no number, any result passes. Fix: state each tolerance.

### EX-S9. The FDS tolerance example sits inside FDS's own discretisation spread, and our node rule isn't the inputs'
`§1.1` "Nodes" ("stretch 2 toward the core"), `§6` FDS row.
- **True:** the MaCFP inputs override FDS's default to `STRETCH_FACTOR=1` (NIST) or `CELL_SIZE_FACTOR=0.5` with
  stretch 1 (Aalto). On `nsf_R3` (50 kW/m²), as a percentage of the input's 31.99 g/m²s at 346 s:

  | Change | Peak | Peak time |
  |---|---|---|
  | Cells halved | −0.9% | +4 s |
  | Stretch 2 | −2.8% | −11 s |

- **Failure scenario:** our stretch-2 solver against FDS's stretch-1 input misses "2% and 5 s" on discretisation
  alone. Fix: verify on the same node layout as the FDS input, and set the tolerance from the spread measured here.
  Also note that at 25 kW/m² the input's `T_END=800` cuts the run before its peak: BR is still rising at 800 s,
  and with `T_END=1500` the peak is at 890 s. "Peak time" therefore needs a longer run.

## NIT

- **EX-N1** `§4.1`: "k(T), c(T) as RAMPs, as MaCFP's sets do". The PMMA sets this design uses (NIST-StMU-FSRI,
  Aalto) have constant k and c for PMMA. Only the Kaowool backing has RAMPs. Some wood sets (UCB-TDEP) are
  T-dependent.
- **EX-N2** `§4.1` "Residue: … none (PMMA)". The NIST-StMU-FSRI set carries an inert `PMMA3` at a mass fraction of
  0.01, and its CTRLs tare 0.43544 kg/m² of residue. Verification with that set needs a residue.
- **EX-N3** `§4.1` (b) "FDS's form r = A·ρ^n·e^(−E/RT)". FDS normalises by the layer's initial density,
  (ρ_s/ρ_s0)^n. The two agree only at n = 1, which holds for both PMMA sets here.
- **EX-N4** `§4.2` "In MaCFP practice … 15–30 kW/m² (V, L1 §2.3)". L1 §2.3's verified source is McKinnon's
  *cardboard* cone (17.2 at 20 kW/m², 29.9 at 60), not MaCFP. The 15–30 range itself is L1 §6's recommendation.
- **EX-N5** `§4.3`: lab and flux are confounded.
  - Pine's parallel-grain fit fluxes come from Aalto (30, 60) and FZJ (30, 60), and every held-out flux (25, 50, 75)
    from FSRI alone. IMT's orientation is "uncertain".
  - PMMA's 50 kW/m² cone data come from two labs only (DBI_Lund, ULSTER).
  - "Multi-lab" grading is one lab per held-out pine flux, so a lab offset reads as a flux error.
- **Also:** `foundations_plan.md` step 6 still says "constants cited, never fitted", but §4.3 fits seven
  parameters. The plan row wasn't revised after fire_model v2.

## Checked and found true

- **FDS runtime:** `macfp_black_pmma_nist_stmu_fsri_25R1.fds` ran in **12.9 s** wall time here ("13 s").
  `nsf_R3` took 7.5 s.
- **Paths:** `PMMA/Validation_Results/` holds NIST-StMU-FSRI and Aalto(-I, -II) FDS inputs (but see EX-B1).
- **Pine:** no `.fds` file exists anywhere under `Wood/` (all 32 in the repo are under PMMA and Verification), and
  `Wood/Material_Properties/` has 12 JSON property sets. "Pine has fitted property sets but no FDS inputs" is true.
- **FDS's node rule:** the PMMA layer in `nsf_R3.out` has 23 cells of **0.2722 mm**, against
  √(α·1 s) = √(0.20/(1177·2130)) = **0.2825 mm**. "First cell ≤ √(α·1 s)" matches. Stretch 2 is FDS's default,
  though these inputs use 1.
- **Pine at 25 kW/m²** sustains at about 3.8 g/m²s. My medians over 300–1,800 s for FSRI R1–R3 are 3.68, 3.73 and
  4.18.
- **Cone data exist** for PMMA at 25, 50 and 65 kW/m², and for pine parallel grain at 25–75 kW/m². The backing is
  documented per lab, so §4.1's "backing specified per dataset" is feasible.
- **DP-S1:** "the full form drifted on 200 of 200" matches `reviews/fire_model/determinism_performance.md` DP-S1
  (200 of 200 against 0 of 200). That test can fail.
- **The named symbols exist at 396ae10:** `Region.solid`, `applier._check_region` and `_on_region`,
  `StructureModulator.__init__`, `region_parts`, `CellFrame.reading`, `damage.strike` and `region_integrity`
  (breach is `region_breached`), `scene._check_no_solid_overlaps`, `imagination._within_world_rules` (box overlap),
  and `encoding.snapshot`'s `* frame.solid` masks.
- **`CellStore`** has a copy-on-open, rollback write window that can hold §1.1's tables.
- **Formats:** `core.yaml` is `version: 0`, so v1 is a real bump. Tile §1.3 plans `content/` for rights-reserved
  game content. `client_rendering.md` §4.2 lists `burning` as a planned u8 channel, and code has none, so
  "reserved" holds.
- **The other §6 tests can fail as stated:** the t_ig closed forms, erfc, delta-form equilibrium, the coupling
  closed form, the straddle mechanism, loader refusals and work counters. The identity test can fail only against a
  parent-commit digest taken on the same machine. No golden is committed (`test_determinism.py`), and step 5a's
  substep change resets every digest first, so say which digests "today's" means.
