"""Constants for the hot-surface spike: the accelerant spike's AccParams plus the char layer and the flame gas.

Pre-registered in docs/design/research/hot_surface_spike/preregistration.md (commit 1c58b75). Status values as in
the parents: V verified on a page read, S secondhand or a snippet, M memory, D derived.
Throwaway spike code: never imported by src/. Run with PYTHONPATH=../bed:../accelerant (launch.sh does).

The defaults are arm H1 (char-layer surface, flame-gas cap, no in-cell contact). The zero-change arm sets
surface_mode=pinned gas_cap=tp, which routes every override to the parents' code.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from acc_constants import AccParams

# EN 1995-1-2 Annex B apparent conductivity of softwood and char (Cachim & Franssen 2009, Table II, read).
EC5_T_C = np.array([20.0, 99.0, 120.0, 200.0, 250.0, 300.0, 350.0, 400.0, 500.0, 600.0, 800.0, 1200.0])
EC5_K = np.array([0.120, 0.133, 0.136, 0.150, 0.123, 0.097, 0.070, 0.077, 0.090, 0.176, 0.350, 1.500])


@dataclass(frozen=True)
class HotParams(AccParams):
    # switches (preregistration §1.4) -------------------------------------
    surface_mode: str = "char"  # "pinned" (6c, the parents) | "char" (§1.1)
    gas_cap: str = "flame"  # "tp" (the parents) | "flame" (§1.2) | "mccaffrey_z" (the Mz end)
    incell_contact: bool = False  # H2 (§1.3)
    # the char layer (§1.1) -------------------------------------------------
    t_f_c: float = 300.0  # pyrolysis-front temperature (ends 288, 380)
    k_c: float = 0.10  # W/m K (end 0.07)
    k_c_mode: str = "const"  # "const" | "ec5" (apparent k(T) at the layer mean, linear interpolation)
    rho_c: float = 150.0  # kg/m^3 (end 200)
    # the flame gas (§1.2) --------------------------------------------------
    t_fl_c: float = 873.0  # C (ends 520, 1027); deviation run 817 (McCaffrey Table 1, measured)
    mcc_c: float = 0.9  # McCaffrey's C, as registered

    @property
    def t_f(self) -> float:
        return self.t_f_c + 273.15

    @property
    def t_fl(self) -> float:
        return self.t_fl_c + 273.15

    def k_char(self, t_mean: np.ndarray) -> np.ndarray:
        """Char conductivity at the layer's mean temperature (K)."""
        if self.k_c_mode == "ec5":
            return np.interp(t_mean - 273.15, EC5_T_C, EC5_K)
        return np.full_like(t_mean, self.k_c)


NOMINAL = HotParams()

# McCaffrey 1979 (NBSIR 79-1910 p. 8): (kappa, eta, upper bound of z/Q^(2/5) in m/kW^(2/5)) per region.
MCC_REGIONS = ((6.8, 0.5, 0.08), (1.9, 0.0, 0.20), (1.1, -1.0 / 3.0, np.inf))


def mccaffrey_dt(x: np.ndarray, t0: float, c: float, g: float = 9.81) -> np.ndarray:
    """Centre-line excess temperature (K) at z/Q^(2/5) = x: 2g dT/T0 = (kappa/C)^2 x^(2 eta - 1)."""
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    lo = 0.0
    for kappa, eta, hi in MCC_REGIONS:
        m = (x >= lo) & (x < hi)
        xs = np.where(m, np.maximum(x, 1e-12), 1.0)
        out = np.where(m, t0 * (kappa / c) ** 2 / (2 * g) * xs ** (2 * eta - 1), out)
        lo = hi
    return out


# value, units, source, status (final, after the §6 verification pass on 2026-11-20) ---------------------------
PROVENANCE: list[tuple[str, str, str, str]] = [
    ("T_f", "300 C (288; 380)", "White & Dietenberger 2010, FPL-GTR-190 ch.18 (PDF read); EC5 char line", "V"),
    ("k_c", "0.10 W/mK (0.07; EC5 k(T))", "Correa 2023 T1 via char_oxidation.md; EC5 via Cachim & Franssen T.II", "V"),
    ("rho_c", "150 kg/m3 (200)", "chi*rho_wood; EC5 density ratio 0.33 x 600", "D"),
    ("T_fl", "873 C (520; 1027)", "McCaffrey 1979 pp.5-8: kappa 6.8, C 0.9 -> dT 853 K", "V/D"),
    ("T_fl measured", "817 C (deviation run)", "McCaffrey 1979 Table 1: flame dT 790-807, weighted 797 C", "V"),
    ("T_fl low", "520 C", "Heskestad 1997 FSS 5:427: mean flame height at a 500 K rise (PDF read)", "V"),
    ("McCaffrey burner", "0.30 m square, natural gas, 14.4-57.5 kW", "NBSIR 79-1910 pp.3, 27", "V"),
    ("crib gas (cross-check)", "650 C crib top to 900 C peak", "Mukunda et al. 2022 quoting Fons et al.", "V/S"),
]
