"""Every fixed number the solid spike's model and harness use, each with its source.

`docs/design/research/solid_spike/preregistration.md` (65ee7d6) governs; a section sign (§) below is a section of
it. "wall.f90" etc. are FDS 6.11.1's sources at tag FDS-6.11.1 (commit c6c06da5), read before this code was written.
Values marked CHOICE are not fixed by the pre-registration; each was set before any model run and is listed in
results.md as a disclosed choice. Nothing here is tuned: no value was changed after a run.
"""

from __future__ import annotations

# Physical constants: FDS's own (cons.f90 / func.f90), so V compares like with like.
SIGMA = 5.670373e-8  # W/m²K⁴, FDS SIGMA
R_GAS = 8.314472  # J/molK, FDS R0 = 8314.472 J/kmolK with E in J/kmol
KELVIN = 273.15

# §3: kinetics cutoff. T_cut is where A·exp(-E/RT_cut) = 1e-9 1/s; below it the rate is exactly 0.
K_CUT = 1e-9  # 1/s
# §3 / fire_solid §4.3: regression when the surface node falls below 1% of its initial thickness.
REGRESS_FRACTION = 0.01

# §2 / fire_solid §4.6: the V tolerances (also §2.2's band widening).
TOL_TIME = 3.0  # s
TOL_PEAK_TIME = 8.0  # s, V2
TOL_REL = 0.025
TOL_FRONT_T = 12.0  # K
V_STEPS = (0.01, 0.5)  # s, V3: the inputs' DT and the shipped step

# §5 N1/N2.
N1_STEPS = (0.5, 0.25, 0.125)
N1_TIG_ABS = 0.5  # s
N1_TIG_REL = 0.03
N1_PEAK_REL = 0.025
N5_TOL = 1e-9
N6_TOL = 1e-9
S1_MARGIN = 1.1

# FDS's node-count rule (func.f90 GET_N_LAYER_CELLS, read.f90 line 9803): the fewest uniform cells with
# thickness/N < CELL_SIZE_FACTOR·sqrt(min diffusivity at TMPA), CELL_SIZE_FACTOR 1 (default), STRETCH_FACTOR 1.
CELL_SIZE_FACTOR = 1.0
# FDS's default ABSORPTION_COEFFICIENT for a MATL without one (read.f90 line 7466): 5e4 1/m.
KAPPA_DEFAULT = 5.0e4

# Cone harness. CHOICE: the convective coefficient before flaming is the gasification inputs' 13 W/m²K (the only h
# in any pre-registered input; fire_solid §4.6); ambient, initial and radiative-surroundings T 20 °C; heater flux
# exactly nominal and uniform. While flaming, convection is off (§3) and q''_fl is added to the incident flux.
CONE_H = 13.0  # W/m²K
CONE_T_AMB = 293.15  # K
DT_SHIPPED = 0.5  # s

# §3 PMMA geometry: DBI's mean thickness per flux (README "Sample Thickness", square samples 1-3).
DBI_THICKNESS_MM = {25: (6.16, 6.17, 6.08), 50: (6.24, 6.25, 6.14), 65: (6.18, 6.23, 6.16)}
# §3 PMMA backing: DBI's 2 x 13 mm Superwool SW Plus, rho 64; k from DBI's HFM table (README), linear above 70 °C
# (CHOICE of extrapolation: the table's least-squares slope); c 1,000 J/kgK; adiabatic beneath.
SUPERWOOL_RHO = 64.0
SUPERWOOL_C = 1000.0
SUPERWOOL_LAYER_M = 0.013
SUPERWOOL_LAYERS = 2
SUPERWOOL_K_TABLE_C = (25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.5, 60.0, 65.0, 70.0)
SUPERWOOL_K_TABLE = (0.03364, 0.03437, 0.03520, 0.03618, 0.03721, 0.03795, 0.03854, 0.03920, 0.04003, 0.04088)
SUPERWOOL_K_TOP_C = 1200.0  # end of the extrapolated table (well above any backing temperature reached)
# §5 N9 range ends for the PMMA backing.
N9_BACKING_K_CONST = 0.041
N9_BACKING_C = (800.0, 1200.0)

# §3 pine: 25.4 mm, adiabatic back; density as published (360, virgin).
PINE_THICKNESS = 0.0254
PINE_FIT_FLUXES = (30, 60)
PINE_GRADED_FLUXES = (25, 50, 75)

# §3 free parameters and bounds.
QFL_BOUNDS = (15.0e3, 30.0e3)  # W/m²
MFLASH_UPPER = 2.5e-3  # kg/m²s
KC_BOUNDS = (0.04, 0.30)  # W/mK
EPS_CHAR_BOUNDS = (0.677, 0.833)
Q_IGN = 24.0  # kW/m², §2.1
FIT_SEEDS = (0, 1, 2, 3, 4)  # §4: seed 0 graded, 1-4 reported
FLAG_FRACTION = 0.01  # §4: within 1% of a bound's width is a flagged pass
FIT_NO_IGNITION_PENALTY = 1.0e6  # CHOICE: objective for a candidate whose run gives no value for a fit feature

# Run lengths (CHOICE, set before any run): PMMA cones run to burnout or the cap; pine fit runs to t_ig + 480 s
# (the plateau window ends at t_ig + 450 and m''_60 needs 30 s more); pine graded runs to the data window's end + 30 s.
PMMA_T_CAP = {25: 1200.0, 50: 700.0, 65: 600.0}
PINE_FIT_AFTER_TIG = 480.0
PINE_T_CAP = 3000.0
PINE_FIT_T_CAP = 1000.0  # CHOICE: a pine fit run that has not flashed by 1,000 s ends (its features score the penalty)

# ----- Rerun 1 (`preregistration_rerun1.md`, de2290d): the numerics fixes, nothing else -----
# Which numerics the builders apply. "rerun1" (the default from de2290d on) applies §1 A and C; "run1" is the first
# run as registered (65ee7d6) and recorded (9575a44): `run.py` sets it, so the first run's pipeline still rebuilds the
# model it graded. §1 B's node multiplier is not a mode: callers pass `refine`.
NUMERICS = "rerun1"
# §1 A: FDS 6.11.1 turns on in-depth (two-flux) radiation for a wall only if one of its materials has κ below this
# (init.f90 line 4265, `IF (MATERIAL(ONE_D%MATL_INDEX(NN))%KAPPA_S<4.9E4_EB) ONE_D%INTERNAL_RADIATION = .TRUE.`, read
# at tag FDS-6.11.1); otherwise the wall absorbs and emits at its face (wall.f90 2867-2876, 2922).
FDS_OPAQUE_KAPPA = 4.9e4  # 1/m
# §1 C: T_cut,i = max(T at K_CUT, T_on,i); T_on,i is where reaction i alone, from T_ON_START, heated at its source
# TGA's slowest calibration rate (the JSON's `Calibration` block with Scope "Kinetics", K/min), reaches
# ONSET_CONVERSION. [engineering], fixed by the rerun's pre-registration before any run.
ONSET_CONVERSION = 1e-3
T_ON_START = 293.15  # K
T_ON_DT = 1e-3  # K: the quadrature step for T_on (trapezoid; T_on converges to < 1e-4 K at this step)
# §1 B: the convergence probe's multipliers of FDS's node rule, and the largest r* allowed.
PROBE_REFINE = (1, 2, 4, 8, 16, 32)
R_STAR_MAX = 8
# Rerun 1's registered T_on estimates (preregistration_rerun1.md §1 C table, K); a code value more than 1 K away is
# disclosed, never substituted.
T_ON_REGISTERED = {"pmma": (349.0, 532.0), "pine": (372.0, 459.0, 517.0, 425.0, 311.0)}
