"""Build the kernel's components, reactions and layers from the pinned inputs (§3's fixed sets, free parameters).

- **PMMA** (both uses): NIST-StMU, two first-order reactions plus 1% inert (PMMA1-3). The gasification runs read
  it from each FDS input as shipped; the cones from `MaCFP_PMMA_NIST-StMU.json`; `check_pmma_sets_agree` holds the
  two equal.
- **Backings:** Kaowool PM from the inputs' RAMPs (V, P0; and N9's range end), DBI's Superwool (cone, §3).
- **Pine:** `Wood_UMD_FSRI-DM.json`, the 5-step chain, per-component c(T), one k(T) for all components but char
  (k_c, free), ε per component interpolated linearly in heater flux and held at the table's ends outside it (char ε
  free), κ 5e4 for every component as published. Ash (0.4%) inert.
- Node counts follow FDS's rule (spec.CELL_SIZE_FACTOR); `refine` multiplies them (N2; rerun 1 §1 B's r).
- **Rerun 1** (spec.NUMERICS == "rerun1"; `preregistration_rerun1.md`): §1 A, a part uses surface absorption unless
  one of its materials has κ < spec.FDS_OPAQUE_KAPPA, as FDS decides per wall (`fds_internal_radiation`); §1 C, each
  reaction's cutoff is raised to its TGA onset (`onset_temperature`, `with_onsets`). In "run1" both are off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import inputs
import numpy as np
import spec
from kernel import Component, Layer, Reaction


@dataclass(frozen=True)
class Build:
    comps: list[Component]
    reactions: list[Reaction]
    layers: list[Layer]
    surface_absorption: bool = False  # rerun 1 §1 A: True when FDS would treat the wall as opaque


def fds_internal_radiation(comps: list[Component]) -> bool:
    """FDS 6.11.1 init.f90 line 4265: in-depth radiation is on for a wall if any of its materials has κ < 4.9e4."""
    return any(c.kappa < spec.FDS_OPAQUE_KAPPA for c in comps)


def finish(comps: list[Component], reactions: list[Reaction], layers: list[Layer], kinetics_rate_k_min: float) -> Build:
    """The Build under the active numerics: rerun 1 applies §1 A (opacity by FDS's rule) and §1 C (onset cutoffs)."""
    if spec.NUMERICS == "run1":
        return Build(comps, reactions, layers)
    if spec.NUMERICS != "rerun1":
        raise ValueError(f"unknown numerics {spec.NUMERICS!r}")
    return Build(comps, with_onsets(reactions, kinetics_rate_k_min), layers, not fds_internal_radiation(comps))


def onset_temperature(a: float, e: float, n: float, rate_k_min: float) -> float:
    """Rerun 1 §1 C: the T at which the reaction alone, from spec.T_ON_START heated at rate_k_min, reaches
    spec.ONSET_CONVERSION. Conversion solves y^(1-n) = 1 - (1-n)·∫k dt (n = 1: y = exp(-∫k dt)) with
    ∫k dt = ∫A·exp(-E/RT) dT / β, by the trapezoid rule on a spec.T_ON_DT grid, linear inside the crossing interval."""
    beta = rate_k_min / 60.0
    c = spec.ONSET_CONVERSION
    target = -math.log1p(-c) if n == 1.0 else (1.0 - (1.0 - c) ** (1.0 - n)) / (1.0 - n)
    temps = spec.T_ON_START + spec.T_ON_DT * np.arange(int(round(2000.0 / spec.T_ON_DT)) + 1)
    k = a * np.exp(-e / (spec.R_GAS * temps))
    cum = np.concatenate(([0.0], np.cumsum(0.5 * (k[1:] + k[:-1]) * spec.T_ON_DT))) / beta
    i = int(np.searchsorted(cum, target))
    if i == 0 or i >= cum.size:
        raise ValueError("onset not reached below T_ON_START + 2000 K")
    return float(temps[i - 1] + (target - cum[i - 1]) / (cum[i] - cum[i - 1]) * spec.T_ON_DT)


def with_onsets(reactions: list[Reaction], rate_k_min: float) -> list[Reaction]:
    return [replace(r, t_on=onset_temperature(r.a, r.e, r.n, rate_k_min)) for r in reactions]


def kinetics_rate(j: dict[str, Any]) -> float:
    """The slowest TGA heating rate (K/min) of the set's `Calibration` entry whose Scope is "Kinetics"."""
    blocks = [b for b in j["Calibration"] if b.get("Scope") == "Kinetics"]
    if len(blocks) != 1:
        raise ValueError("expected exactly one Kinetics calibration block")
    data = blocks[0]["Data"]
    rates = [float(d["Heating Rate"]) for d in (data if isinstance(data, list) else [data]) if d["Type"] == "TGA"]
    if not rates:
        raise ValueError("the Kinetics calibration names no TGA rate")
    return min(rates)


def fds_cells(thickness: float, diffusivity: float, refine: int = 1) -> int:
    """FDS GET_N_LAYER_CELLS with STRETCH_FACTOR 1: the fewest N with thickness/N < CSF·sqrt(diffusivity)."""
    s = spec.CELL_SIZE_FACTOR * math.sqrt(diffusivity)
    n = 1
    while thickness / n >= s:
        n += 1
    return n * refine


def _const(name: str, rho: float, c: float, k: float, eps: float, kappa: float) -> Component:
    return Component(name, rho, (300.0,), (c,), (300.0,), (k,), eps, kappa)


def _pmma_components(rho: float, c: float, k: float, eps: float, kappa: float) -> list[Component]:
    return [_const(f"PMMA{i}", rho, c, k, eps, kappa) for i in (1, 2, 3)]


def _ramp(points: list[tuple[float, float]], scale: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """An FDS RAMP over T in °C as (T in K, value·scale); FDS holds the ends outside the ramp."""
    return tuple(t + spec.KELVIN for t, _ in points), tuple(f * scale for _, f in points)


def kaowool(case: dict[str, Any]) -> Component:
    m = case["matl"]["KPM"]
    ct, cv = _ramp(case["ramps"][m["SPECIFIC_HEAT_RAMP"][0]], 1000.0)
    kt, kv = _ramp(case["ramps"][m["CONDUCTIVITY_RAMP"][0]], 1.0)
    return Component("KPM", float(m["DENSITY"][0]), ct, cv, kt, kv, float(m["EMISSIVITY"][0]), spec.KAPPA_DEFAULT)


def superwool(*, k_const: float | None = None, c: float = spec.SUPERWOOL_C, k_ramp: str | None = None) -> Component:
    """DBI's table (°C), continued above 70 °C with its least-squares slope to SUPERWOOL_K_TOP_C."""
    tc = np.array(spec.SUPERWOOL_K_TABLE_C)
    kv = np.array(spec.SUPERWOOL_K_TABLE)
    slope = float(np.polyfit(tc, kv, 1)[0])
    t_top = spec.SUPERWOOL_K_TOP_C
    k_top = float(kv[-1] + slope * (t_top - tc[-1]))
    kt_k = tuple(float(t) + spec.KELVIN for t in (*tc, t_top))
    kv_t = (*(float(x) for x in kv), k_top)
    if k_const is not None:
        kt_k, kv_t = (300.0,), (k_const,)
    if k_ramp == "kaowool":  # N9: Kaowool PM's k(T) from the inputs
        kp = kaowool(inputs.fds_case("R3"))
        kt_k, kv_t = kp.k_t, kp.k_v
    return Component("Superwool", spec.SUPERWOOL_RHO, (300.0,), (c,), kt_k, kv_t, 0.9, spec.KAPPA_DEFAULT)


def diffusivity_at(comp: Component, t: float) -> float:
    return float(np.interp(t, comp.k_t, comp.k_v)) / (float(np.interp(t, comp.c_t, comp.c_v)) * comp.rho)


def pmma_from_fds(case: dict[str, Any], *, refine: int = 1, fds_h_r: bool) -> Build:
    """A gasification input as shipped: PMMA layer and Kaowool, back insulated (§9: the aluminium is immaterial)."""
    mt = case["matl"]
    p1, p2, p3 = mt["PMMA1"], mt["PMMA2"], mt["PMMA3"]
    comps = _pmma_components(
        float(p1["DENSITY"][0]),
        float(p1["SPECIFIC_HEAT"][0]) * 1000.0,
        float(p1["CONDUCTIVITY"][0]),
        float(p1["EMISSIVITY"][0]),
        float(p1["ABSORPTION_COEFFICIENT"][0]),
    )
    for p in (p2, p3):
        if [p[k] for k in ("DENSITY", "SPECIFIC_HEAT", "CONDUCTIVITY", "EMISSIVITY", "ABSORPTION_COEFFICIENT")] != [
            p1[k] for k in ("DENSITY", "SPECIFIC_HEAT", "CONDUCTIVITY", "EMISSIVITY", "ABSORPTION_COEFFICIENT")
        ]:
            raise ValueError("PMMA components differ in thermal properties; the builder assumes they don't")
    comps.append(kaowool(case))
    reactions = [
        Reaction(i, None, 0.0, float(p["A(1)"][0]), float(p["E(1)"][0]), 1.0, float(p["HEAT_OF_REACTION(1)"][0]) * 1e3)
        for i, p in ((0, p1), (1, p2))
    ]
    if fds_h_r:
        reactions = [with_fds_h_r(r, comps[0].c_v[0], comps[0].rho) for r in reactions]
    tp, tk = case["thickness"][0], case["thickness"][1]
    t_a = case["tmpa_k"]
    f = case["mass_fraction"]
    layers = [
        Layer(tp, fds_cells(tp, diffusivity_at(comps[0], t_a), refine), comps[0].rho, (f[0], f[1], f[2], 0.0), True),
        Layer(tk, fds_cells(tk, diffusivity_at(comps[3], t_a), refine), comps[3].rho, (0.0, 0.0, 0.0, 1.0), False),
    ]
    return finish(comps, reactions, layers, kinetics_rate(pmma_json()))  # the inputs are NIST-StMU (check_pmma_sets_agree)


# FDS's temperature-dependent heat of reaction (ADJUST_H, default on; read.f90 lines 7700-7820). FDS fits each
# material's reference enthalpy so H_R(T_ref) equals the input, then H_R(T) = products' minus reactant's enthalpy:
# for PMMA (all gas, constant c_s) H_R(T) = H_in + (cp_gas - c_s)(T - T_ref). The gas is the inputs' user-defined
# SPEC 'MMA', FORMULA='C5H8O', which has no thermo data, so FDS gives it cp = R/MW·GAMMA/(GAMMA-1) with GAMMA 1.4
# (data.f90 THERMO_TABLE_GAS; cons.f90 GAMMA). T_ref is FDS GET_TMP_REF's peak-rate temperature in a 5 K/min TGA
# (func.f90 2812-2847; cons.f90 TGA_HEATING_RATE). FDS's own .out prints H_R at T_ref and T_ref ± 40 K, which
# `fds_h_r_check` compares with this.
FDS_GAMMA = 1.4
FDS_TGA_RATE = 5.0  # K/min
MW_C5H8O = 5 * 12.0107 + 8 * 1.00794 + 15.9994  # g/mol (FDS prints 84.11642)


def fds_tmp_ref(a: float, e: float, n: float, rho: float) -> float:
    """FDS GET_TMP_REF: step T by 0.01 K at 5 K/min from 0 K; the T of the largest rate."""
    dtmp = 0.01
    dt = dtmp / (FDS_TGA_RATE / 60.0)
    tmp, t_ref, rr_max, rho_s = 0.0, 0.0, 0.0, rho
    while int(tmp) < 5000:
        tmp += dtmp
        rate = a * rho_s**n * math.exp(-e / (spec.R_GAS * tmp))
        if rate > rr_max:
            t_ref, rr_max = tmp, rate
        rho_s -= rate * dt
        if rho_s < 1e-15:
            break
    return t_ref


def with_fds_h_r(r: Reaction, c_s: float, rho: float) -> Reaction:
    """The reaction with FDS's H_R(T) (all-gas products, constant c_s)."""
    cp_g = spec.R_GAS * 1000.0 / MW_C5H8O * FDS_GAMMA / (FDS_GAMMA - 1.0)
    t_ref = fds_tmp_ref(r.a, r.e, r.n, rho)
    return Reaction(r.reactant, r.product, r.nu, r.a, r.e, r.n, r.h, cp_g - c_s, t_ref)


def pmma_json() -> dict[str, Any]:
    return inputs.load_json(inputs.PMMA_SET)


def check_pmma_sets_agree() -> None:
    """The JSON set and the FDS inputs' MATLs must be the same numbers (both are NIST-StMU)."""
    j = pmma_json()
    case = inputs.fds_case("R3")
    p1, p2 = case["matl"]["PMMA1"], case["matl"]["PMMA2"]
    want = (
        j["Kinetics"]["Pre-exponential"],
        j["Kinetics"]["Activation Energy"],
        j["Thermodynamics"]["Heat of Pyrolysis"]["Value"],
        j["Composition"]["Initial Mass Fraction"],
    )
    got = (
        [float(p1["A(1)"][0]), float(p2["A(1)"][0])],
        [float(p1["E(1)"][0]), float(p2["E(1)"][0])],
        [float(p1["HEAT_OF_REACTION(1)"][0]) * 1e3, float(p2["HEAT_OF_REACTION(1)"][0]) * 1e3],
        case["mass_fraction"],
    )
    for w, g in zip(want, got, strict=True):
        if [float(x) for x in w] != [float(x) for x in g]:
            raise ValueError(f"NIST-StMU JSON and FDS input disagree: {w} vs {g}")


def pmma_cone(
    flux: int,
    *,
    refine: int = 1,
    backing: str = "superwool",
    backing_k: float | None = None,
    backing_c: float = spec.SUPERWOOL_C,
    backing_k_ramp: str | None = None,
    fds_h_r: bool,
) -> Build:
    """DBI's square sample at a flux: NIST-StMU on 2 x 13 mm Superwool (or N9's Kaowool PM ramps), adiabatic beneath."""
    j = pmma_json()
    th, tr = j["Thermodynamics"], j["Transport"]
    comps = _pmma_components(
        float(th["Density"]["Value"]),
        float(th["Heat Capacity"]["Value"]),
        float(tr["Conductivity"]["Value"]),
        float(tr["Emissivity"]["Value"]),
        float(tr["Absorption"]["Value"]),
    )
    kin = j["Kinetics"]
    reactions = [
        Reaction(
            i,
            None,
            0.0,
            float(kin["Pre-exponential"][i]),
            float(kin["Activation Energy"][i]),
            float(kin["Reaction Order"][i]),
            float(th["Heat of Pyrolysis"]["Value"][i]),
        )
        for i in (0, 1)
    ]
    if fds_h_r:
        reactions = [with_fds_h_r(r, comps[0].c_v[0], comps[0].rho) for r in reactions]
    if backing == "kaowool":
        comps.append(kaowool(inputs.fds_case("R3")))
    else:
        comps.append(superwool(k_const=backing_k, c=backing_c, k_ramp=backing_k_ramp))
    frac = tuple(float(x) for x in j["Composition"]["Initial Mass Fraction"])
    tp = float(np.mean(spec.DBI_THICKNESS_MM[flux])) / 1000.0
    t_a = spec.CONE_T_AMB
    layers = [Layer(tp, fds_cells(tp, diffusivity_at(comps[0], t_a), refine), comps[0].rho, (*frac, 0.0), True)]
    bk = comps[3]
    nb = fds_cells(spec.SUPERWOOL_LAYER_M, diffusivity_at(bk, t_a), refine)
    for _ in range(spec.SUPERWOOL_LAYERS):
        layers.append(Layer(spec.SUPERWOOL_LAYER_M, nb, bk.rho, (0.0, 0.0, 0.0, 1.0), False))
    return finish(comps, reactions, layers, kinetics_rate(j))


PINE_NAMES = ("Virgin", "Int1", "Int2", "Int3", "Int4", "Char", "Ash")


def pine_json() -> dict[str, Any]:
    return inputs.load_json(inputs.PINE_SET)


def pine_eps(table: dict[str, Any], flux_kw: float) -> float:
    """ε at a heater flux: linear in flux between the table's points, held at its ends outside (§10.7)."""
    return float(np.interp(flux_kw * 1000.0, table["Heat Flux"], table["Values"]))


def pine_cone(
    flux: int,
    *,
    k_c: float,
    eps_char: float,
    refine: int = 1,
    backing: str = "adiabatic",
) -> Build:
    """MaCFP-4 pine, 25.4 mm, parallel grain, on an adiabatic back (or N9's 25.4 mm Kaowool PM)."""
    j = pine_json()
    th, tr, kin = j["Thermodynamics"], j["Transport"], j["Kinetics"]
    kt = tuple(float(x) for x in tr["Conductivity"]["Temperature"])
    kv = tuple(float(x) for x in tr["Conductivity"]["Values"])
    comps: list[Component] = []
    for name in PINE_NAMES:
        ctab = th["Heat Capacity"]["Components"][name]
        ct = tuple(float(x) for x in ctab["Temperature"])
        cv = tuple(float(x) * 1000.0 for x in ctab["Values"])
        rho = float(th["Density"]["Components"][name])
        kappa = float(tr["Absorption Coefficient"]["Components"][name])
        if name == "Char":
            comps.append(Component(name, rho, ct, cv, (300.0,), (k_c,), eps_char, kappa))
        else:
            eps = pine_eps(tr["Emissivity"]["Components"][name], flux)
            comps.append(Component(name, rho, ct, cv, kt, kv, eps, kappa))
    reactions = []
    for i in range(5):
        if kin["Reactants"][i] != [i + 1] or kin["Products"][i] != [i + 2, 8]:
            raise ValueError("pine set: not the sequential chain the builder expects")
        reactions.append(
            Reaction(
                i,
                i + 1,
                float(kin["Solid Yield"][i]),
                float(kin["Pre-exponential"][i]),
                float(kin["Activation Energy"][i]),
                float(kin["Reaction Order"][i]),
                float(th["Heat of Pyrolysis"]["Value"][i]),
            )
        )
    f0 = j["Composition"]["Initial Mass Fraction"]
    frac = tuple(float(x) for x in f0[:7])
    rho0 = comps[0].rho
    t_a = spec.CONE_T_AMB
    d_min = min(diffusivity_at(c, t_a) for c, f in zip(comps, frac, strict=True) if f > 0)
    layers = [Layer(spec.PINE_THICKNESS, fds_cells(spec.PINE_THICKNESS, d_min, refine), rho0, frac, False)]
    if backing == "kaowool":
        kp = kaowool(inputs.fds_case("R3"))
        comps.append(kp)
        layers = [Layer(L.thickness, L.n_nodes, L.rho_bulk, (*L.fractions, 0.0), L.shrinks) for L in layers]
        layers.append(
            Layer(spec.PINE_THICKNESS, fds_cells(spec.PINE_THICKNESS, diffusivity_at(kp, t_a), refine), kp.rho, (0.0,) * 7 + (1.0,), False)
        )
    return finish(comps, reactions, layers, kinetics_rate(j))
