"""Constants for the accelerant spike: the bed spike's Params plus kerosene, each with a provenance row.

Pre-registered in docs/design/research/accelerant_spike/preregistration.md (commit 40d79a6). Status values as in
the bed spike: V verified on a page read, S secondhand or a snippet, M memory, D derived.
Throwaway spike code: never imported by src/. Run with PYTHONPATH including ../bed (launch.sh does).
"""

from __future__ import annotations

from dataclasses import dataclass

from constants import Params


@dataclass(frozen=True)
class AccParams(Params):
    # the scenario (preregistration §2) ------------------------------------
    loading_wood: float = 64.0  # kg of liquid per m^3 of wood (cold soak 32-96, FPL-GTR-190 ch.15)
    distribution: str = "uniform"  # "uniform" | "surface" (saturated from the face inward)
    void_wood: float = 0.61  # wood internal void fraction, 1 - 600/1530
    # kerosene (preregistration §1) ----------------------------------------
    t_b_c: float = 230.0
    l_v: float = 250e3  # J/kg
    c_l: float = 2360.0  # J/kg K
    rho_l: float = 800.0  # kg/m^3
    dh_k: float = 43.1e6  # J/kg
    crit_form: str = "energy"  # "energy" | "mass" (kerosene counted kg for kg against m_crit)
    # numerics ------------------------------------------------------------
    sub_mult: int = 1  # E5: substeps multiplied by this

    @property
    def t_b(self) -> float:
        return self.t_b_c + 273.15

    @property
    def liquid_per_area(self) -> float:
        """kg of liquid per m^2 of slat surface: loading x wood volume per m^2 (half slat)."""
        return self.loading_wood * self.slat_b_m / 2.0


NOMINAL = AccParams()

# value, units, source, status (final, after the pre-run verification pass on 2026-11-20) -----------------------
PROVENANCE: list[tuple[str, str, str, str]] = [
    ("flash point", ">= 38 C", "USCG CHRIS Kerosene (KRS) 4.1; NIOSH NPG 0366: 100-162 F (page read)", "V"),
    ("T_b", "230 C (175; 325)", "CHRIS 9.3: 200-260 C; NIOSH NPG 0366: 347-617 F (page read)", "V"),
    ("L_v", "250 kJ/kg", "CHRIS 9.12", "V"),
    ("c_L", "2.36 kJ/kgK", "CHRIS 9.21 linear in T, mean over 20-230 C (extrapolated above 99 C)", "V/D"),
    ("rho_L", "800 kg/m3", "CHRIS 9.7 (NIOSH 0.81)", "V"),
    ("dh_c kerosene", "43.1 MJ/kg", "CHRIS 9.13", "V"),
    ("q''_crit", "m_crit x 12.4 MJ/kg (energy form)", "Lyon & Quintiere 2007 form: full text not reached", "D/M"),
    ("chi_r end 0.35", "0.35", "Hamins et al. 1991 C&F 86:223, range 0.16-0.35 over 8 fuels; fuels not listed", "S"),
    ("wood void", "0.61", "cell wall SG ~1.53-1.54 (ASTM D2395, FPL snippets)", "S"),
    ("loading", "64 (32-96) kg/m3 wood", "FPL-GTR-190 ch.15 Cold Soaking (PDF read)", "V"),
    (
        "kerosene vs No.2 fuel oil",
        "thinner, so uptake no smaller",
        "Penn State FSc 430 'Typical Analyses': No.1 31 SSU / SG 0.825, No.2 35 SSU / SG 0.865 at 100 F (page read; "
        "original publisher unnamed)",
        "S",
    ),
    ("drying-model form", "node capped at T_b, excess evaporates at L_v", "memory", "M"),
]
