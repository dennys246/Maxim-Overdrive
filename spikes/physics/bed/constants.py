"""Constants for the porous-bed spike, each with a provenance row.

Status values: V = verified on a page read during this spike; S = found only secondhand
(the secondary source is named); M = from memory, unverified; D = derived here from other rows;
E = [engineering] content value from the tile spec (not a physical constant).
Throwaway spike code: never imported by src/.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

SIGMA_SB = 5.670374419e-8  # W/m^2 K^4, CODATA exact-defined value


@dataclass(frozen=True)
class Params:
    # geometry (tile spec §1.1, T15) ---------------------------------------
    box_m: float = 0.6
    phi: float = 0.25
    slat_b_m: float = 0.020
    sigma_v: float = 25.0  # m^2/m^3 = 2 phi / b
    rho_wood: float = 600.0  # kg/m^3, gives 32.4 kg (spec)
    t_amb_c: float = 20.0  # pre-registration: open air at 20 C
    # pilot (tile spec §3.2: 2 kW over a 0.2 m disc, 15.9 kW/m^2) ---------
    pilot_w: float = 2000.0
    pilot_r_m: float = 0.2
    pilot_centre_yz_m: tuple[float, float] = (0.325, 0.325)  # (2.925-2.6, 0.725-0.4) on the x- face
    # wood thermal --------------------------------------------------------
    c_wood: float = 1700.0  # J/kg K
    k_wood: float = 0.12  # W/m K
    skin_m: float = 0.001  # tile spec 6b, 1 mm
    n_slab: int = 10  # nodes over the half-slat (10 mm): 1 mm each
    # pyrolysis / flaming -------------------------------------------------
    t_p_c: float = 380.0
    l_g: float = 1.8e6  # J/kg volatiles
    chi_char: float = 0.25
    dh_vol: float = 12.4e6  # J/kg volatiles
    q_f: float = 25e3  # W/m^2 of burning surface
    m_crit: float = 3.7e-3  # kg/m^2 s volatiles, flaming extinction
    chi_r: float = 0.30
    huggett: float = 13.1e6  # J per kg O2
    # surfaces ------------------------------------------------------------
    eps: float = 0.9
    h_env: float = 10.0  # W/m^2 K, natural convection on the crate's outer faces
    # char ----------------------------------------------------------------
    c_char: float = 1260.0
    ks_a: float = 430.0  # m/s, surface reaction velocity pre-exponential
    ks_ta: float = 9000.0  # K
    kinetics: bool = True  # False = diffusion-limited only (tile spec 6d)
    product: str = "arthur"  # "arthur" | "co2"
    co_burns_in_bed: bool = False
    ignite_base_m: float = 0.0  # conditional scenario: bottom fuel ignited at t = 0
    flame_in_bed: bool = False  # bounding end: flame radiation emitted inside the bed
    feedback_mode: str = "split"  # "split" (direct (1-chi_r), P1 chi_r) | "p1"
    char_floor: float = 0.1  # kg/m^2, numerical capacity floor (energy booked)
    # gas -----------------------------------------------------------------
    cp_air: float = 1100.0
    y_o2: float = 0.233
    pr: float = 0.70
    k_minor: float = 1.5  # entrance + exit loss, dynamic heads
    # numerics ------------------------------------------------------------
    dt_phys: float = 0.5
    cap_s: float = 5400.0
    m_sub: int = 6  # reconstruction samples per cell axis (ignition)
    face_sample_m: float = 0.01  # metric sampling of envelope faces (glow/crack area)

    @property
    def t_amb(self) -> float:
        return self.t_amb_c + 273.15

    @property
    def t_p(self) -> float:
        return self.t_p_c + 273.15

    @property
    def w0(self) -> float:  # wood per m^2 of fuel surface (half slat)
        return self.rho_wood * self.slat_b_m / 2.0

    def with_(self, **kw: object) -> Params:
        return replace(self, **kw)  # type: ignore[arg-type]


NOMINAL = Params()

# value, units, source, status -------------------------------------------
PROVENANCE: list[tuple[str, str, str, str, str]] = [
    ("phi, slat b, sigma_v", "0.25, 20 mm, 25 m2/m3", "tile spec §1.1, T15 (content value)", "E"),
    ("rho_wood", "600 kg/m3", "tile spec §1.1 (32.4 kg); dry softwood 500-600 is memory", "E/M"),
    ("pilot", "2 kW over r=0.2 m, 15.9 kW/m2", "tile spec §3.2 ('of order 2 kW', from memory)", "E/M"),
    (
        "c_wood",
        "1700 J/kgK (ends 1236, 2630)",
        (
            "Wood Handbook FPL-GTR-190 ch.4 Eq.4-16a c=0.1031+0.003867T kJ/kgK: 1236 at 293 K, 2630 at 653 K; 1700 "
            "at 413 K"
        ),
        "V",
    ),
    (
        "k_wood",
        "0.12 W/mK (ends 0.106, 0.15)",
        "Wood Handbook FPL-GTR-190 ch.4: 0.106 at G=0.45, 0.116 at G=0.5 oven-dry; 0.15 is tile spec/PH",
        "V (0.106-0.116); M (0.15)",
    ),
    ("skin depth", "1 mm", "tile spec 6b [engineering]", "E"),
    (
        "T_p",
        "380 C (cited range 300-364)",
        (
            "tile spec 380 (memory); Babrauskas, 'Ignition of Wood' slides (cfitrainer.net 2005_CCAI): 300-310 C low "
            "flux, 349-364 C flaming softwoods; review: Babrauskas 2002 J. Fire Prot. Eng. 12(3):163"
        ),
        "V (range); M (380)",
    ),
    ("L_g", "1.8 MJ/kg", "Tewarson, SFPE Handbook (Douglas fir 1.81) - not found online", "M"),
    (
        "char yield chi",
        "0.25 (ends 0.20, 0.30)",
        "Baker 1983 FPL 'Wood fuel properties...': ~25% charcoal yield; 0.2-0.3 range is memory",
        "V (0.25); M (range)",
    ),
    ("dH_c,eff volatiles", "12.4 MJ/kg", "tile spec / world_model §11; not found online", "M"),
    (
        "q''_f",
        "25 kW/m2 (ends 15, 35)",
        (
            "Spearpoint & Quintiere (softwoods 16-17, redwood/oak ~35), Tewarson & Pion Douglas fir 23.8 - search "
            "snippets only"
        ),
        "S",
    ),
    (
        "m''_crit (flaming extinction)",
        "3.7 g/m2s (ends 2.5, 3.93)",
        (
            "Emberley et al. 2017 Fire Safety J. 91:327 (3.7+-0.2, radiata pine CLT, PDF read); 3.93 spruce "
            "Arnorsson et al. 2020 (snippet); 2.5 Bamford 1946 (ignition) via M. Nelson review page"
        ),
        "V (3.7); S (others)",
    ),
    ("chi_r", "0.30 (ends 0.27, 0.33)", "Johnsson et al., NIST TN 2327 (2025): 0.30+-0.03 dry Douglas-fir trees", "V"),
    ("Huggett", "13.1 MJ/kg O2", "Huggett 1980 Fire Mater. 4:61, via NIST SP 958 (Steckler)", "V"),
    (
        "epsilon (wood, char)",
        "0.9 (ends 0.85, 0.95)",
        "0.9 straw char, Chem. Eng. Trans. 94 (2022) citing Zhou 2005; 0.85-0.95 is FPH review/memory",
        "V (0.9); M (range)",
    ),
    (
        "h_env",
        "10 W/m2K (ends 5, 10)",
        "tile spec 5.1 (memory); FPH review: 5-10 natural convection, 0.6 m face (Incropera)",
        "M",
    ),
    ("c_char", "1260 J/kgK", "Huang & Rein via Jayasuriya et al. 2022 arXiv:2206.03836 Table 2", "V"),
    (
        "char surface kinetics",
        "k_s = 430 exp(-9000/T) m/s, O2 flux = rho Y k_s",
        (
            "Mankame & Shotorban 2021 Front. Mech. Eng. 7:640979 Eq.23 (A=430 m/s, Ta=9000 K) citing Morvan & Dupuy "
            "2004; printed form dimensionally ambiguous, the rho*Y_O2*surface form is memory of Morvan & Dupuy"
        ),
        "V (numbers); M (form)",
    ),
    ("kinetics end", "diffusion-limited only", "tile spec 6d", "E"),
    (
        "CO/CO2 at the surface",
        "CO/CO2 = 2500 exp(-6240/T)",
        (
            "Arthur 1951 Trans. Faraday Soc. 47:164; exponent 12,400 cal/mol consistent with a Utah collections "
            "snippet; prefactor not verified"
        ),
        "S/M",
    ),
    ("product end", "CO2 only", "tile spec 6d assumption", "E"),
    ("dH C->CO2, C->CO, CO->CO2", "32.8, 9.20, 10.1 MJ/kg", "NIST WebBook dHf CO -110.53, CO2 -393.51 kJ/mol", "V/D"),
    ("char treated as carbon", "-", "char is ~85-90% C (memory); overstates char heat by ~10%", "M"),
    (
        "Ergun",
        "150, 1.75; d_eq = 6(1-eps_void)/a_v",
        "Ergun 1952 Chem. Eng. Prog. 48 (via Wikipedia); d_eq form memory",
        "V/M",
    ),
    ("minor loss", "K = 1.5 dynamic heads", "standard entrance+exit loss (memory)", "M"),
    (
        "Churchill-Bernstein",
        "cylinder crossflow, slat as d = b",
        "Churchill & Bernstein 1977 J. Heat Transfer 99:300 (via Wikipedia)",
        "V (form); M (slat as cylinder)",
    ),
    ("Churchill-Chu", "horizontal cylinder natural convection", "Churchill & Chu 1975 (search snippets)", "S"),
    ("Sutherland air mu, k", "1.716e-5, 273, 111; 0.0241, 273, 194", "White, Viscous Fluid Flow, via COMSOL docs", "V"),
    ("cp air, Pr", "1100 J/kgK, 0.70", "memory (cp 1005 at 300 K to 1180 at 1200 K)", "M"),
    ("Chilton-Colburn h_m = h/(rho cp), Le = 1", "-", "memory (FPH review uses it)", "M"),
    (
        "extinction beta = a_v/4",
        "-",
        "Cauchy mean projected area for random convex elements; Vaz et al. 2004 IJWF 13:65 (not opened)",
        "M",
    ),
    ("P1 + Marshak", "-", "Modest, Radiative Heat Transfer (not opened)", "M"),
]
