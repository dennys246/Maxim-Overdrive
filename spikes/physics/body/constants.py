"""Q5 constants, each with provenance (preregistration.md: value, units, source, verified or from memory).

Throwaway spike code (spikes/physics/), never imported by src/. Where the literature gives a range, both ends
are listed and the run covers both. Nothing here was tuned against criterion 5b.
"""

from __future__ import annotations

SIGMA = 5.670374419e-8  # W/m^2K^4, CODATA 2018 (exact SI-derived), verified

T_AMB_C = 20.0  # degC, preregistration.md "open air at 20 degC" (scenario, not a constant)

# --- the fire (tile_and_client.md §5.1, §5.3: derived there, both ends of q''_f) ---------------------------
Q_FLAMING_KW = {"q_f=25": 777.0, "q_f=15": 402.0}  # kW, tile spec §5.3 (derived from from-memory constants)
FLAMING_DURATION_S = {"q_f=25": 390.0, "q_f=15": 750.0}  # s, tile spec §5.3
CHI_R = 0.30  # -, tile spec §5.1 (from memory); NUREG-1805 ch.5 gives 0.15-0.60 across fuels (verified)
CRATE_SIDE_M = 0.6  # m, tile spec §1 / preregistration (geometry)
# Ember phase: tile spec §5.3 derives ~550 degC (bare char face) and ~920 degC (envelope ember); both ends run.
T_EMBER_C = {"550C": 550.0, "920C": 920.0}
EMBER_DURATION_S = 1750.0  # s, tile spec §5.3 (derived)
Q_EMBER_KW = 150.0  # kW, tile spec §5.3 (derived): an energy cap on what the embers can radiate
EPS_CHAR = 0.9  # -, tile spec §5.1 surface emissivity (from memory)

# Flame height: Heskestad, Hf = 0.235 Q^(2/5) - 1.02 D (Q in kW, D in m). NUREG-1805 ch.5 eq 5-8, citing
# Heskestad (1995), SFPE Handbook. Verified (PDHonline M312 reproduction of NUREG-1805 ch.5, p.5-9).
HESKESTAD_A = 0.235
HESKESTAD_B = 1.02
# Solid-flame emissive power, Shokri & Beyler (1989): E = 58 * 10^(-0.00823 D) kW/m^2 (pool fires).
# NUREG-1805 ch.5 eq 5-6, verified (p.5-7). Upper end; the energy-consistent E = chi_r Q / A_flame is the lower.
SB_E0_KW = 58.0
SB_K = 0.00823

# --- the body (tile_and_client.md §2.1, T5) ---------------------------------------------------------------
BODY_HEIGHT_M = 1.8  # m, tile spec §2.1 [engineering]
BODY_MASS_KG = 70.0  # kg, tile spec §2.1 (from memory)
# Whole-body specific heat: 3.47 kJ/kgK is the conventional value; Xu, Rioux & Castellani (2022, Temperature,
# PMC10274559) recompute ~2.98 kJ/kgK. Both ends run. Verified (search summary of PMC10274559).
BODY_C = {"c=3470": 3470.0, "c=2980": 2980.0}
BODY_H_CONV = 10.0  # W/m^2K, tile spec §2.1 (from memory)
BODY_AREA_M2 = 1.9  # m^2, tile spec §2.1 (from memory)
BODY_PROJ_AREA_M2 = 0.5  # m^2 toward a source, tile spec §2.1 (from memory)
BODY_EPS = 0.95  # -, tile spec §2.1 (from memory); also used as skin absorptance for fire radiation
T_CORE_C = 37.0  # degC

# --- skin (Pennes three-layer model) -------------------------------------------------------------------------
# All from Torvi & Dale (1994), "A finite element model of skin subjected to a flash fire", J. Mech. Eng. 116,
# as tabulated in Jasinski (2003), Sci. Res. Inst. Math. Comput. Sci. 2(1):45-54, section 4. Verified against
# Jasinski's text (amcm.pcz.pl/2003_1/art_07.pdf).
SKIN_LAYERS = (
    # name, thickness m, k W/mK, rho*c J/m^3K, perfusion G (m^3 blood/s)/m^3 tissue, metabolic W/m^3
    ("epidermis", 0.0001, 0.235, 4.3068e6, 0.0, 0.0),
    ("dermis", 0.002, 0.445, 3.96e6, 0.00125, 245.0),
    ("subcutaneous", 0.01, 0.185, 2.674e6, 0.00125, 245.0),
)
RHO_C_BLOOD = 3.9962e6  # J/m^3K, same source, verified
T_BLOOD_C = 37.0  # degC, same source, verified
H_SKIN_AIR = 8.0  # W/m^2K, same source (Jasinski's surface coefficient), verified
# Henriques burn integral at the basal layer: P = 1.43e72 1/s for Tb >= 317 K, dE/R = 55,000 K; first degree
# at Ib = 0.53, second at Ib = 1. Jasinski (2003) citing Torvi & Dale (1994) and Henriques (1947). Verified.
HENRIQUES_P = 1.43e72
HENRIQUES_DE_R = 55000.0
HENRIQUES_T_ON_K = 317.0

# Pain: a temperature at the pain-receptor depth. Buettner (1951), J. Appl. Physiol. 3(12):703-713: threshold
# 44.8 degC at 0.1 mm (verified from abstract via search summary; the author attribution is from memory).
# Havenith & Daanen (2013) give 43-45 degC; EN ISO 9886 (2004) uses 43 degC (both as quoted by IFV/Heus 2016,
# "Maximum allowable exposure to different heat radiation levels", verified). Run at both ends: 43.0 and 44.8.
PAIN_DEPTH_M = 0.0001
PAIN_T_C = {"43.0C": 43.0, "44.8C": 44.8}

# --- clothing: one cotton layer over an air gap -------------------------------------------------------------
# Cotton specific heat 1340 J/kgK: Engineering ToolBox, "Solids - specific heats" (verified via search summary).
# Areal mass 120-220 g/m^2: Printful "T-shirt weight guide" gives cotton 119-220 g/m^2 (vendor source, verified
# via search summary). Air gap: 6.4 mm is the ASTM F1939/F2700 spacer (from memory); ~25 mm is the mean air gap
# of fit protective clothing, Lu et al. (2013), 3D Body Scanning proc. (verified via search snippet).
# Fabric absorptance/emissivity 0.9 (from memory); air k = 0.026 W/mK (from memory).
CLOTH_C = 1340.0
CLOTH_CASES = {
    # name: (areal mass kg/m^2, air gap m): the two ends bracket fastest and slowest skin heating
    "light shirt, 6.4 mm gap": (0.120, 0.0064),
    "heavy shirt, 25 mm gap": (0.220, 0.025),
}
CLOTH_ALPHA = 0.9
CLOTH_EPS = 0.9
K_AIR = 0.026
H_CLOTH_AIR = 10.0  # W/m^2K outer convection: the tile spec's body h (from memory)

# --- empirical anchors (cross-checks, never fitted to) -------------------------------------------------------
# Bare skin, incident flux kW/m^2 -> seconds to pain:
BARE_ANCHORS = (
    (4.0, 15.0, "Hoschke (1981) diagram, as quoted by IFV/Heus (2016): verified"),
    (6.3, 8.0, "API 521 example via brojowesi blog (2009): secondary, unverified against API 521"),
    (9.45, 6.0, "API RP 521 (1997) 'approx. six seconds', via the same blog: secondary"),
)
# Clothed (RadMan manikin, operator ensembles, time to 43 degC skin), IFV/Heus (2016) Table V, verified:
# flux kW/m^2: (min, max) seconds over standing/walking and short/long sleeve.
CLOTHED_ANCHORS = {3.0: (33.0, 88.0), 4.6: (20.0, 58.0), 6.3: (18.0, 68.0), 10.0: (13.0, 20.0)}
