"""The rules stage 0 applies, each one cited to the pre-registration.

`docs/design/research/solid_spike/preregistration.md` (committed in 65ee7d6) is the source of every number here; a
section sign (§) below means a section of that document. Nothing in this file is tuned: a value that disagrees with
the data is reported by `reference.py`, never adjusted here.
"""

from __future__ import annotations

# §2: MaCFP matl-db, pinned.
REPO = "MaCFP/matl-db"
COMMIT = "9986be8d285c70b51d59262468199a3e63e41fe0"

# The files stage 0 reads. Cone files are matched by name inside these folders; the rest are named exactly.
PMMA_CONE_DIR = "PMMA/Calibration_Data/"
WOOD_CONE_DIR = "Wood/Calibration_Data/"
GASIF_DIR = "PMMA/Validation_Data/NIST_Gasification_Apparatus/"
READMES = (
    "PMMA/Calibration_Data/README.md",  # MaCFP-2's outlier rule (ΔH_c = 23.5 ± 2.5 kJ/g)
    "PMMA/Calibration_Data/DBI_Lund/README.md",  # DBI's round-sample area, 0.00387 m²
    "Wood/Calibration_Data/Aalto/README.md",  # flame-out times (§2.1, m''_ext)
    "Wood/Calibration_Data/UQ/README.md",  # flame-out times (§2.1, m''_ext)
)

# §2.1: t_ig is the first sample with Q'' >= 24 kW/m² (MaCFP-4's rule).
Q_IGN = 24.0  # kW/m²
MLR10_HALF_WINDOW = 5.0  # s: m''_10 is the five-point difference averaged over ±5 s
MLR60_HALF_SPAN = 30.0  # s: m''_60 = (m(t - 30) - m(t + 30)) / (60 A)
PINE_FIRST_PEAK_SPAN = 200.0  # s after t_ig
PINE_PLATEAU = (250.0, 450.0)  # s after t_ig
PINE_WINDOW_END_MLR = 2.7  # g/m²s: the window ends at the first m''_60 below this after the first peak
ARTEFACT_FACTOR = 2.0  # a test whose peak exceeds twice its lab's median at that flux is excluded
M_EXT_FALLBACK = 1.17  # g/m²s, used (and named as a leak) only if no fit-flux flame-out can be read

# §2, P1 envelope: MaCFP-2's outlier rule, applied per test.
DHC_RULE = (23.5, 2.5)  # kJ/g, centre and half-width

# §2.2: the V tolerance that widens every band (times in s; rates and masses relative).
TOL_TIME = 3.0
TOL_REL = 0.025

# §2, "Areas" (m²). PMMA: README values; Edinburgh 0.095². DBI's round samples: its README (0.00387, average).
PMMA_AREA = {
    "Edinburgh": 0.095 * 0.095,
    "TIFP": 0.0084,
    "UClan": 0.0088,
    "UDRI": 0.00884,
    "UQ": 0.00884,
}
PMMA_AREA_DEFAULT = 0.01
DBI_ROUND_AREA = 0.00387
DBI_ROUND = ("DBI_Lund_Cone_25kW_4", "DBI_Lund_Cone_25kW_5", "DBI_Lund_Cone_25kW_6")

# Wood: MaCFP-4's get_cone_area (Scripts/MaCFP-4/Cone_analysis.py); any other lab has no area.
WOOD_AREA = {lab: 0.01 for lab in ("Aalto", "FSRI", "FZJ", "UDRI", "UQ")} | {
    lab: 0.00884 for lab in ("FPL", "IMT", "TUBS", "UMET")
}

# §2, P1 fluxes; P2 labs per flux (fit, graded, cross-check).
PMMA_FLUXES = (25, 50, 65)
PMMA_FIT_LAB = "DBI_Lund"
PINE_LABS = {
    25: ("FSRI", "IMT"),
    30: ("Aalto", "FZJ", "TUBS", "UDRI"),
    45: ("Aalto",),
    50: ("FPL", "FSRI", "IMT"),
    60: ("Aalto", "FZJ", "UDRI", "UQ"),
    75: ("FSRI", "FZJ", "IMT"),
}
PINE_ROLE = {25: "graded", 30: "fit", 45: "cross-check", 50: "graded", 60: "fit", 75: "graded"}
PINE_FIT_FLUXES = (30, 60)

# §2, P2 exclusions: MaCFP-4's own, then the pre-registration's.
WOOD_EXCLUDED_LABS = {
    "UMET": "MaCFP-4: HRR from a mass-loss cone, not oxygen consumption",
    "BUWfd": "MaCFP-4 has no area for it; L1 §1.3 flagged its 2-4 s ignitions",
}
WOOD_EXCLUDED_TESTS = {
    "IMT_Wood_Cone_25kW_hor_R2": "MaCFP-4: ignition time far from the others",
    "IMT_Wood_Cone_25kW_hor_R5": "MaCFP-4: ignition time far from the others",
    "BUWfd_Wood_Cone_50kW_hor_R1": "MaCFP-4: non-physical mass signal",
}
WOOD_NO_MASS = {"FZJ_Wood_Cone_75kW_hor_parallel_R1": "no mass signal: excluded from mass features only"}

# §2.1, m''_ext: the labs whose README records flame-out times at the fit fluxes.
FLAMEOUT_READMES = {"Aalto": "Wood/Calibration_Data/Aalto/README.md", "UQ": "Wood/Calibration_Data/UQ/README.md"}

# Features, and which kind of tolerance widens each (§2.2).
PMMA_FEATURES = {"t_ig": "time", "peak": "rel", "t_peak": "time", "mass_lost": "rel"}
PINE_FEATURES = {"t_ig": "time", "first_peak": "rel", "plateau": "rel"}
MASS_FEATURES = frozenset({"peak", "t_peak", "mass_lost", "first_peak", "t_first_peak", "plateau", "dhc"})

# §5 P0: the NIST gasification repeats and the V tolerance of each feature. Peak time's is V2's 8 s; the half-mass
# time and back-temperature crossings have no V row, so they take §2.2's 3 s on times (disclosed in bands.md).
GASIF_MLR = (("50", "R3"), ("50", "R4"), ("50", "R5"))
GASIF_TEMP = (("25", "R1"), ("25", "R2"), ("25", "R3"), *(("50", f"R{i}") for i in range(1, 6)))
GASIF_TOL = {
    "peak_mlr": ("rel", TOL_REL),
    "t_peak": ("time", 8.0),
    "t_mlr_1": ("time", TOL_TIME),
    "t_mlr_2.7": ("time", TOL_TIME),
    "t_half_peak": ("time", TOL_TIME),
    "t_half_mass": ("time", TOL_TIME),
    "t_back_100C": ("time", TOL_TIME),
    "t_back_200C": ("time", TOL_TIME),
    "t_back_300C": ("time", TOL_TIME),
}
BACK_T_CROSSINGS = (100.0, 200.0, 300.0)  # °C
KELVIN = 273.15

# Unit-label errata, each with its evidence: (file stem, column) -> (the unit the values are in, the label it carries,
# why). Only these exact labels on these exact files are read as the corrected unit; any other surprise is refused.
UNIT_ERRATA = {
    ("Edinburgh_Cone_65kW_6", 2): (
        "kw/m2",
        "kw",
        "its five siblings label Q'' kW/m2, and its values match theirs (peak 1,351 against 65kW_5's 1,383; an "
        "absolute kW over 0.009 m² would be about 0.01 of that), so the label is a typo",
    ),
}
