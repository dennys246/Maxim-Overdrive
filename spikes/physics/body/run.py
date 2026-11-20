"""Q5 of the physics spike: what a body near the crate fire feels. Run: .venv/bin/python spikes/physics/body/run.py

Computes incident flux (point source and solid flame / view factor) at 1, 2, 3 m, skin time to pain (bare and two
clothed cases), the burn integral, and the T5 lumped core's warming rate. Runs everything twice and asserts the two
result payloads are bit-identical (preregistration: each script is deterministic). Writes results/ next to itself.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import constants as C  # noqa: E402
import flux as F  # noqa: E402
import skin as S  # noqa: E402

DISTANCES = (1.0, 2.0, 3.0)
Z_BODY = np.round(np.arange(1, 37) * 0.05, 10)  # 0.05 .. 1.80 m, the body's front
DT = 0.01


def flux_profiles(dist_axis: float) -> dict:
    """Every (phase, case, model) -> incident flux kW/m^2 at each body height."""
    d_eq = F.equivalent_diameter(C.CRATE_SIDE_M)
    out = {}
    for qname, q in C.Q_FLAMING_KW.items():
        hf = F.heskestad_height(q, d_eq)
        e_sb = F.emissive_power_shokri_beyler(d_eq)
        e_en = F.emissive_power_energy(q, hf, d_eq)
        vf = [F.cylinder_vf_closed(0.0, hf, dist_axis, d_eq, z) for z in Z_BODY]
        out[("flaming", qname, "point")] = [F.point_source(q, hf, dist_axis, z) for z in Z_BODY]
        out[("flaming", qname, "solid E=chi_rQ/A")] = [e_en * f for f in vf]
        out[("flaming", qname, "solid E=Shokri-Beyler")] = [e_sb * f for f in vf]
    for tname, tc in C.T_EMBER_C.items():
        e = F.ember_emission(tc)
        vfs = [F.faces_vf_quadrature(dist_axis, z, C.CRATE_SIDE_M, n=400) for z in Z_BODY]
        out[("ember", tname, "point")] = [F.ember_point(dist_axis, z, C.CRATE_SIDE_M, e) for z in Z_BODY]
        out[("ember", tname, "view factor")] = [e * (a + b) for a, b in vfs]
    return out


def core_rates(q_mean_kw: float) -> dict:
    """T5 lumped body at 37 degC in 20 degC air: gross absorbed-radiation rate and net of the spec's losses (K/min)."""
    tb, ta = C.T_CORE_C + 273.15, C.T_AMB_C + 273.15
    absorbed = C.BODY_EPS * q_mean_kw * 1000.0 * C.BODY_PROJ_AREA_M2
    losses = C.BODY_H_CONV * C.BODY_AREA_M2 * (tb - ta) + C.BODY_EPS * C.SIGMA * C.BODY_AREA_M2 * (tb**4 - ta**4)
    res = {"absorbed_W": absorbed, "losses_W": losses}
    for cname, c in C.BODY_C.items():
        mc = C.BODY_MASS_KG * c
        res[f"gross_K_per_min[{cname}]"] = absorbed / mc * 60.0
        res[f"net_K_per_min[{cname}]"] = (absorbed - losses) / mc * 60.0
    return res


def clothing_cases() -> dict:
    cases = {"bare": None}
    for name, (m, gap) in C.CLOTH_CASES.items():
        cases[name] = S.Clothing(m, gap)
    return cases


def compute() -> dict:
    grid = S.make_grid()
    cloth = clothing_cases()
    rows = []
    for ref in ("axis", "face"):
        for d in DISTANCES:
            dist_axis = d if ref == "axis" else d + C.CRATE_SIDE_M / 2.0
            profiles = flux_profiles(dist_axis)
            for (phase, case, model), prof in profiles.items():
                q_max = max(prof)
                q_mean = float(np.mean(prof))
                t_max = C.FLAMING_DURATION_S[case] if phase == "flaming" else C.EMBER_DURATION_S
                row = {
                    "ref": ref,
                    "d": d,
                    "phase": phase,
                    "case": case,
                    "model": model,
                    "q_max": q_max,
                    "z_at_max": float(Z_BODY[int(np.argmax(prof))]),
                    "q_mean": q_mean,
                    "core": core_rates(q_mean),
                    "phase_s": t_max,
                    "skin": {},
                }
                if ref == "axis" or phase == "flaming":
                    for cname, cl in cloth.items():
                        e = S.expose(grid, cl, q_max, t_max, DT)
                        row["skin"][cname] = {
                            "t_pain": e.t_pain,
                            "t_burn1": e.t_burn1,
                            "t_burn2": e.t_burn2,
                            "steady_receptor_C": e.steady_receptor_c,
                            "initial_receptor_C": e.initial_receptor_c,
                        }
                rows.append(row)
    return {"rows": rows}


def validations() -> dict:
    """Checks that do not depend on the scenario: closed forms vs quadrature, a published skin case, anchors,
    and grid/time-step sensitivity."""
    d_eq = F.equivalent_diameter(C.CRATE_SIDE_M)
    out: dict = {}
    worst = 0.0
    for q in C.Q_FLAMING_KW.values():
        hf = F.heskestad_height(q, d_eq)
        for d in DISTANCES:
            for z in (0.3, 1.0, 1.7):
                a = F.cylinder_vf_closed(0.0, hf, d, d_eq, z)
                b = F.cylinder_vf_quadrature(0.0, hf, d, d_eq, z)
                worst = max(worst, abs(a - b) / a)
    out["cylinder_vf_closed_vs_quadrature_max_rel"] = worst
    worst = 0.0
    for d in DISTANCES:
        for z in (0.3, 0.9, 1.5):
            a = F.front_face_vf_closed(d, z, C.CRATE_SIDE_M)
            b = F.faces_vf_quadrature(d, z, C.CRATE_SIDE_M, n=400)[0]
            worst = max(worst, abs(a - b) / a)
    out["face_vf_closed_vs_quadrature_max_rel"] = worst
    t1, t2 = S.jasinski_check(DT)
    out["jasinski_2003_example1"] = {"published_s": [16.25, 17.8], "this_model_s": [t1, t2]}
    grid = S.make_grid()
    out["bare_anchors"] = [
        {"q": q, "published_s": t, "src": src, "model_s": S.expose(grid, None, q, 600.0, DT).t_pain}
        for q, t, src in C.BARE_ANCHORS
    ]
    out["clothed_anchors"] = []
    for q, (lo, hi) in C.CLOTHED_ANCHORS.items():
        m = {
            name: S.expose(grid, cl, q, 900.0, DT).t_pain["43.0C"]
            for name, cl in clothing_cases().items()
            if cl is not None
        }
        out["clothed_anchors"].append({"q": q, "RadMan_43C_s": [lo, hi], "model_43C_s": m})
    fine = S.make_grid(40, 80, 100)
    sens = []
    for cl in (None, S.Clothing(0.12, 0.0064)):
        for q in (2.0, 12.0):
            base = S.expose(grid, cl, q, 900.0, DT).t_pain["44.8C"]
            half_dt = S.expose(grid, cl, q, 900.0, DT / 2).t_pain["44.8C"]
            dbl = S.expose(fine, cl, q, 900.0, DT).t_pain["44.8C"]
            sens.append(
                {
                    "clothed": cl is not None,
                    "q": q,
                    "base": base,
                    "dt_half_rel": (half_dt - base) / base,
                    "grid_x2_rel": (dbl - base) / base,
                }
            )
    out["numerics_sensitivity"] = sens
    return out


def digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=repr).encode()).hexdigest()


def main() -> None:
    first = {"results": compute(), "validations": validations()}
    second = {"results": compute(), "validations": validations()}
    h1, h2 = digest(first), digest(second)
    assert h1 == h2, f"non-deterministic: {h1} != {h2}"
    first["determinism"] = {"runs": 2, "sha256": h1, "bit_identical": True}
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(first, indent=1, sort_keys=True, default=repr) + "\n")
    print("determinism: two runs bit-identical, sha256", h1)


if __name__ == "__main__":
    main()
