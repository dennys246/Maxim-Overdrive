# Tile and client spec, design review: Physics and resolution

Target: `docs/design/tile_and_client.md` at f6afd66 (branch `phase1/tile-spec`). Lens: Physics and resolution
(`docs/code_review.md`), read against CLAUDE.md's resolution/verification rule and D25, `world_model.md` (D20, D21,
D25, D26, §1, §3, §9, §11), `architecture.md` Known gaps, `src/maxim_overdrive/world/*.py`,
`data/materials/core.yaml` and `tests/test_cross_tier.py`.

**Counts:** 3 BLOCKER, 7 SHOULD-FIX, 5 NIT.

**What I recomputed** (scratch script building the alley from the spec's boxes with the worktree's `Scene`, run on
the shared venv with `PYTHONPATH=src`):
- grid shapes and cell counts: 60×20×24 = 28,800; 120×40×48 = 230,400; 240×80×96 = 1,843,200;
- solids at 0.1 m: 59,312 (floor 19,200, sides 17,280 each, end 5,120, crates 216 each), 25.7%;
- memory, 23–29 MB;
- 2.68 m between the crates, 993 mm for the `move_to`, x = 5,080 mm at tick 42, 98.99 mm diagonals;
- glow codes 3 and 23 for 538 and 613 °C;
- `stable_dt` 187 / 46.9 / 11.7 s at 0.2 / 0.1 / 0.05 m;
- today's uncached `heat.substep` on the alley: 0.59 / 4.5 / 38.3 ms (CPU time, minimum of 20 / 20 / 5 runs);
- the energy budget, floor uptake, cell-mean bias, Wien ratio and controls arithmetic below.

**What I took on trust:**
- world_v2 P3 and S2's measured numbers, and world_model §9's 3.9 ms cached substep;
- ΔH_c,eff = 12.4 MJ/kg (world_model §11, *from memory*);
- a softwood charring rate of 0.65 mm/min (Eurocode 5's β₀, *from memory*, to verify);
- that llvmpipe's output depends on the LLVM version and the host's SIMD path (*from memory*).

The alley's geometry is legal: every coordinate is a multiple of 0.2 m, every solid and every air gap a test uses is
≥ 0.4 m (two coarse cells), and `MaterialGrid.empty` accepts the extent at all three grids. The findings are about
what the exit scenario asks of physics that Phase 1 doesn't have.

---

## BLOCKER

### PH-B1. Open air has no heat sink, so a conserving fuel law can't keep the crate under 2000 °C

`tile_and_client.md::§1.2 "Open air"`, `::§7.3 item 5`

§1.2 says open air means no O₂ limit, not an open heat boundary: "the fuel law decides burn-out; the tile's air stays
hot". That doesn't close the energy budget. Derived (recomputed):
- **Energy in.** The crate holds 0.216 m³ × 600 kg/m³ = 129.6 kg of wood. At 12.4 MJ/kg that is **1.61 GJ** to
  release. Burning out by the 3,600 s cap means at least **446 kW** on average.
- **The floor can take 92 MJ at most (5.7%).** Under the 0.36 m² footprint, a semi-infinite concrete slab held at
  2000 °C for the whole hour absorbs 2kΔT·√(t/πα)·A, with α = 1.7/(2400·880) = 8.05×10⁻⁷ m²/s.
- **The walls and the control take essentially nothing.** Heat reaches them only through air, k = 0.026, with a
  diffusion length √(αt) = 0.28 m in an hour.
- **Destroyed cells delete at most 437 MJ (27%),** even if every crate cell vanishes at 2000 °C (ρc·V·ΔT =
  1.02 MJ/m³K × 0.216 × 1985). That deletion is itself a Known gap ("destroying a cell removes its heat"), not a sink
  to rely on.
- **About 1.08 GJ (67%) has nowhere to go.** In the remaining wood (≤ 220 kJ/K) it means thousands of kelvin. In the
  air (206 kJ/K for the whole tile) it means about 5,000 K: the runaway the Known gap already records.

So item 5's "no cell ever exceeds 2000 °C" can only pass if step 6's law throws most of the heat release away, or
clamps temperature by deleting energy. Either would be an unrecorded band-aid that breaks the relative ledger
(world_model §4). In reality that heat leaves by convection and radiation, which D26 deferred to Phase 2 along with
the open boundary (§13). §1.2 also has the air backwards. Under Phase 1 physics the air barely heats, because no
source deposits into it after step 6 and conduction through air is negligible. It doesn't "stay hot".

**Failure scenario.** Step 6 implements burn rate × ΔH, deposited into the burning cells, with the ledger exact.
Item 5 goes red by about 3.6× (an adiabatic wood cell gains 7.44 GJ/m³ ÷ 1.02 MJ/m³K ≈ 7,300 K). The only ways to
turn it green are an unnamed loss factor or a clamp.

**Fix.** The spec must decide the Phase 1 open-air heat boundary explicitly, and the owner confirms it as a D26
amendment. Two candidates:
- (a) **An export term.** Heat release splits into a fixed flame-feedback flux per m² of burning area (world_model
  §3's S5 form) and the remainder, which is exported to open air as a named ledger line. It needs a closed-form test
  that release = feedback + export.
- (b) **Exposed-face losses in step 6.** Linear convection plus radiation on exposed faces (the surface skin of world_model
  §3, P1), with the domain's open faces as an ambient sink.

Recommendation: (a) for Phase 1. Record the gap with these numbers either way, and correct §1.2's "the tile's air
stays hot".

### PH-B2. "`t_gone` converges to the reference" depends on fuel recession, which D26 moved to Phase 2

`tile_and_client.md::§7.3 item 9`, `::§13`; `foundations_plan.md` §2 step 6

Item 9 requires `t_gone` at 0.2 m and 0.1 m to agree with 0.05 m. Step 6 is "fuel by volume overlap, a burn law,
burnout". D26 deferred "fuel recession and pyrolysis", which includes world_model §3's sub-box recession, the fix for
P3. The spec doesn't say which burn law step 6 uses. Both obvious Phase 1 choices are measured to fail convergence
(trusted numbers):
- **Per-face mass loss without sub-box recession (P3).** A 0.6 m box keeps 0.205 / 0.268 / 0.311 of its mass, against
  an exact 0.370. It burns out about 35% early at 0.2 m. On this crate at 0.2 m, 26 of 27 cells are face, edge or
  corner cells.
- **A volumetric burn per cell, lit when the cell's mean passes T_ig.** That is a threshold on a cell mean (D25's
  forbidden case). S2 measured a surface cell's mean reaching 350 °C at t ∝ dx: 1,350 s at 0.2 m and 340 s at
  0.05 m. The burning front, and so `t_gone`, inherits that.

**Failure scenario.** Step 6 ships either law. Item 9 fails at 0.2 m by about 35%, or by a factor tied to dx. The
spec's own rule ("never loosened to pass") then blocks the exit. The way out is a quiet "Known gap, not gated",
which the verification rule forbids for a gated outcome.

**Fix.** Bring sub-box recession into step 6 (P3's prototype gives 0.370 at every grid, measured), with reconstructed
ignition, and ask the owner to amend D26's deferral to say so. Or the spec states, before step 6 starts, that
`t_gone` convergence is not in the exit. Either way, §13 must name the dependency instead of "step 6: the burn law".

### PH-B3. `t_glow` thresholds the cell-mean temperature, which understates a surface by a factor that scales with dx

`tile_and_client.md::§5.1 glow`, `::§6.4`, `::§7.3 item 3`; `world.py::snapshot`

`glow` is round(255·clip((T − 525)/975)) of each cell's mean temperature. Item 3 is "≥ 8 crate surface cells at
glow ≥ 26". The visible thing is the surface, and the gradient that matters sits inside the surface cell. Derived for
wood (α = 0.15/(600·1700) = 1.47×10⁻⁷ m²/s), with a face held at 900 °C for 600 s: the thermal layer
2√(αt) ≈ 19 mm, and the surface cell's mean is
- **62 °C at 0.2 m,** 5.3% of the rise;
- **109 °C at 0.1 m,** 10.6%;
- **203 °C at 0.05 m,** 21.2%.

The read-out halves with every doubling of dx. That is the "average then threshold" error D25 forbids, and it is the
main reason §6.4's measured peaks (538 and 613 °C, glow 3 and 23) are low. It is not only the 250 °C degrade
threshold, which is itself a cell-mean threshold. The surface model that would fix this is the skin (world_model §3,
P1). World_model §10 scheduled skins in `phase1/zones`, and D26 deferred zones. Step 6's line in the plan doesn't
include skins. §6.4 assumes "step 6's surface law", which nothing schedules. And `t_glow` isn't in item 9's
convergence check at all.

**Failure scenario.** Step 6 adds char at, say, 700 °C on the face. At 0.1 m no cell's mean reaches 622.5 °C, so
`t_glow` doesn't exist and item 6 fails. Or it passes at 0.05 m and not at 0.1 m: the outcome class depends on the
grid.

**Fix.**
- Put the surface skin on fuel faces into step 6 explicitly, using the face table, keyed by (cell, face), that
  world_model §8 already reserves.
- Publish glow from the skin's surface temperature as a new channel, since a name is an identity (F1). `glow` stays
  cell-mean, or is retired.
- Restate item 3 as a glowing area in m² from that table, band-gated. Add `t_glow` to item 9.

---

## SHOULD-FIX

### PH-S1. The 3,600 s cap is about 8× faster than a solid 0.6 m wood block burns

`tile_and_client.md::§7.2` (cap), `::§1.1 crate`

The cross-tier crate is a solid block, and the thin-feature rule rules out a hollow crate (0.4 m walls leave no
cavity in 0.6 m). Wood chars at about 0.65 mm/min (Eurocode 5, from memory). Burning through 0.3 m from the sides
takes about 27,700 s (7.7 h, derived). Burning out within 3,600 s needs a burn rate about 7.7× faster than that, and
446 kW on average. Step 6's material table v1 promises provenance.

**Failure scenario.** A provenance-faithful rate times out at the cap. A calibrated one passes but contradicts the
provenance column, and nobody wrote the 7.7× down.

**Fix.** State the expected burn time from the cited rate in §7.2. Either set the cap from it (at 20×, 27,700 s is
23 minutes of play), or mark the rate as gameplay calibration in `data/` with the ratio. Don't leave the cap as an
unexplained `[engineering]` value.

### PH-S2. Crack and glow criteria count cells, so their meaning changes 64× across the grids

`tile_and_client.md::§7.3 items 2, 3`

"≥ 8 crate cells" means 0.064 / 0.008 / 0.001 m³ at 0.2 / 0.1 / 0.05 m (8 of 27 cells, 30% of the crate, at
0.2 m). "≥ 8 surface cells" means 0.32 / 0.08 / 0.02 m² of face. Item 9 compares outcome classes across these grids,
so the criterion itself is resolution-dependent.

**Fix.** Use volumes and areas in metres, from the region reduction or the face table (for example, cracked volume
≥ 0.008 m³, glowing area ≥ 0.08 m²), as the charter's "no consumer reads a cell" requires.

### PH-S3. The controls, and item 5's second clause, can't fail

`tile_and_client.md::§7.3 items 5, 7`

These are tests that cannot fail, which the charter treats as a BLOCKER. They are graded SHOULD-FIX here only because
each sits beside conditions that can fail. Recomputed:
- **Floor ≥ 0.95,** a mean over 19,200 cells. Failing needs 960 cells' worth of integrity lost (0.96 m³). The whole
  slab under the crate, 0.36 m² × 0.4 m, is 144 cells. Destroying all of it leaves 0.9925.
- **Walls ≥ 0.99.** The north wall has 17,280 cells, so failing needs 173 cells. The patch facing the crate, 0.6 ×
  0.6 m × 0.4 m thick, is 144 cells. Losing all of it leaves 0.9917.
- **`crate_control` ≥ 0.99.** Under conduction-only physics, nothing can reach it 2.68 m away through air (diffusion
  length 0.28 m in an hour). It guards only against a source placed in the wrong spot. It isn't a fire-spread control.
- **"From `t_gone` + 600 ticks the tile's maximum only falls."** The explicit scheme with STABILITY_SAFETY 0.9 is a
  convex combination of neighbours, so the discrete maximum principle guarantees this once sources stop.

**Fix.**
- Make the controls local and in metres: destroyed volume within 1 m of the crate ≤ X m³ per region, or the minimum
  integrity over a metric neighbourhood.
- Prove each one by deletion: plant a source at the control and watch it go red.
- Replace the max-only-falls clause with a ledger check: after `t_gone`, heat plus exported energy stays constant
  within the relative tolerance.
- Rename `crate_control` honestly, as a placement guard.

### PH-S4. The pilot lost its footprint, and "2× the reference's minimum energy" isn't a band gate

`tile_and_client.md::§2.3`, `::§4.3`, `::§12 Q3`

`ignite {point_m, power_w, duration_s}` drops `radius_m`, so the deposit has no size in metres. If it falls back to
today's "a source smaller than a cell heats one cell", the power density is P/dx³, 64× different between the grids
(Known gap). P2 showed footprint and position decide ignition outright: a 2 kW corner pilot lit at 0.05 m and never
at 0.2 m.

"≥ 2× the reference grid's minimum igniting energy" also misses two things:
1. **Ignition has a power axis.** Below the critical heat flux, no duration ignites, so "minimum energy" is undefined
   without fixing P.
2. **The truth's threshold isn't bounded.** The margin is taken from the reference alone. If 0.1 m's threshold is
   more than 2× the reference's, the scenario fails at the truth grid.

**Fix.**
- Put the footprint radius in metres in `data/world/player.yaml`, at least one coarse cell (≥ 0.2 m), deposited by
  face-area overlap with no single-cell fallback.
- Choose (P, D) outside the ignition band measured in (P, D) at all three grids, and record that band's width
  (world_model §3).
- Make `duration_s` a whole number of ticks, or deposit exactly P·D by time overlap across the 0.5 s physics steps.

### PH-S5. The band gate is applied to a continuous time and not to the binaries

`tile_and_client.md::§7.3 item 9`

The band gate (world_model §3, S4) is defined for binary outcomes: the width of the input range where truth and
reference disagree. Item 9 applies it to `t_gone`, a continuous quantity. The binaries here are ignited, burned away
before the cap, glow reached, and controls intact, and none of them is band-gated.

**Fix.** Give `t_gone`, `t_crack` and `t_glow` a convergence tolerance taken from measurement. Give each binary a band
gate over P, with the band recorded in Known gaps.

### PH-S6. "Identical on every machine" is promised where only the outcome class is

`tile_and_client.md::§2.2 Blocked`, `::§8.5`

§2.2 calls the collision reduction "identical on every machine (D20)". The test itself is integer, but it reads the
solid mask, which after a burn comes from float temperature and integrity histories. CLAUDE.md promises cross-machine
agreement only for the outcome class. A different BLAS or numpy SIMD path can destroy a cell one physics step apart.
§8.5 says llvmpipe is "identical across runners". From memory, its output depends on the Mesa and LLVM versions and on
the host ISA's code path.

**Failure scenario.** A replay on the owner's Mac of a CI-recorded log diverges in `move_result.path_mm` after the
burn, and someone treats it as a determinism bug.

**Fix.** Say "bit-identical on one machine; outcome class across machines". Pin the golden runner's container image
and Mesa version, and record them with the goldens.

### PH-S7. What drives `crack` under the fuel law is unspecified, and today's driver thresholds the cell mean

`tile_and_client.md::§5.1 crack`, `::§7.3 item 2`; `damage.py::thermal_degrade`

`crack` = 1 − integrity. Today integrity falls by `thermal_degrade`, a rate on the cell mean's excess over 250 °C. That
is a threshold plus a non-linear law on the mean, and it is the source of the Known gap where "a coarse cell degrades
as one block" (0.55 against 0.37). The spec doesn't say whether step 6 keeps it, replaces it with burned mass fraction,
or uses char depth in metres.

**Fix.** Name `crack`'s driver for wood under step 6, as burned fraction or char depth from the reconstructed profile,
and include `t_crack` in item 9.

---

## NIT

### PH-N1. glow ≥ 26 means T ≥ 622.5 °C, not 625 °C

`tile_and_client.md::§7.3 item 3`. The code rounds, so 26 starts at (T − 525)/975·255 ≥ 25.5.

### PH-N2. "Brightness ∝ T⁴ (Stefan–Boltzmann)" is total radiance, not visible radiance

`tile_and_client.md::§6.3`. At 650 nm, Wien's law gives a 525 °C to 1500 °C ratio of 2.4×10⁻⁷, against T⁴'s 0.041
(derived). It is visual only and acceptable as a stylisation, but it shouldn't be labelled as physics.

### PH-N3. The script's ignite point lies on cell boundaries at 0.1 m and 0.05 m

`tile_and_client.md::§7.2` (tick 70). y = 2.9 and z = 0.7 fall on cell edges, and in floats 2.9/0.1 =
28.999999999999996. Any `cell_of` fallback is then a float tie that varies by grid. Choose a point such as
(6.0, 2.925, 0.725), or forbid the fallback (PH-S4).

### PH-N4. "Arrival within 50 mm" can't be met if the path ends at a walk-grid node

`tile_and_client.md::§4.2`, `::§7.2` (tick 50). The target (5500, 2900) is a cell corner of the 0.1 m walk grid, and
the nearest node centre is 70.7 mm away. Either the last waypoint is the target itself, or the tolerance is larger.

### PH-N5. The substep figure is a projection, and the reference run's cost isn't stated

`tile_and_client.md::§1.4`, `::§10`.
- I measured today's uncached substep on the alley at **4.5 ms at 0.1 m** and **38.3 ms at 0.05 m**. That matches
  14 ms × 0.36. The 1.4 ms cached figure is a projection.
- With `stable_dt` at 46.9 s, every 0.5 s physics step is one substep, so the 0.05 m reference over a 3,600 s cap is
  7,200 substeps, about 276 s of heat alone per run.
- A band-gate sweep over P at three grids is therefore many minutes, and belongs behind the tier variable.

---

**Verdict:** the geometry is legal and the arithmetic holds, but the exit scenario as written can't pass on step 6's
fuel-mass law alone. It needs an open-air heat sink, sub-box recession and a surface skin for glow, all of which D26
deferred, so the spec must schedule them into step 6 or change the exit before code.
