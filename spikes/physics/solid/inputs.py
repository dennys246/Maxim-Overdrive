"""The pinned MaCFP inputs the model reads (FDS input files, material-property JSON), fetched and parsed.

Files come from MaCFP matl-db at the pre-registration's pinned commit, through stage 0's verified tree: each must
hash to the tree's git blob SHA-1, and its SHA-256 goes into results.json. They are untrusted data: written only
under `out/cache/`, parsed by the narrow readers below (a value they don't expect is refused), never executed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE / "stage0"))
import fetch as stage0_fetch  # noqa: E402
import pins as stage0_pins  # noqa: E402

CACHE = HERE / "out" / "cache"
FDS_DIR = "PMMA/Validation_Results/NIST-StMU-FSRI/FDS_Input_Files/"
FDS_CASES = ("25R1", "25R2", "25R3", "R3", "R4", "R5", "T1", "T2", "T3", "T4", "T5")
PMMA_SET = "PMMA/Material_Properties/2023/MaCFP_PMMA_NIST-StMU.json"
PINE_SET = "Wood/Material_Properties/Wood_UMD_FSRI-DM.json"
FILES = tuple(f"{FDS_DIR}macfp_black_pmma_nist_stmu_fsri_{c}.fds" for c in FDS_CASES) + (PMMA_SET, PINE_SET)


def _cache_path(path: str) -> Path:
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts or rel.suffix not in (".fds", ".json"):
        raise ValueError(f"refusing repository path {path!r}")
    return CACHE.joinpath(*rel.parts)


def fetch_all() -> dict[str, str]:
    """Fetch (once) and verify every model input; returns {path: SHA-256}."""
    tree = stage0_fetch.load_tree()
    out: dict[str, str] = {}
    for path in FILES:
        want = str(tree[path]["sha"])
        dest = _cache_path(path)
        if not (dest.exists() and stage0_fetch.git_blob_sha1(dest.read_bytes()) == want):
            url = f"https://raw.githubusercontent.com/{stage0_pins.REPO}/{stage0_pins.COMMIT}/{urllib.parse.quote(path)}"
            with urllib.request.urlopen(url, timeout=60) as resp:  # a fixed https URL at the pinned commit
                data: bytes = resp.read()
            if stage0_fetch.git_blob_sha1(data) != want:
                raise RuntimeError(f"{path}: bytes do not match the pinned tree's blob {want}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        out[path] = hashlib.sha256(dest.read_bytes()).hexdigest()
    return out


def fds_path(case: str) -> Path:
    return _cache_path(f"{FDS_DIR}macfp_black_pmma_nist_stmu_fsri_{case}.fds")


def load_json(path: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(_cache_path(path).read_text(encoding="utf-8"))
    return loaded


# ----- FDS namelist reader (just what these inputs use) -----
_GROUP = re.compile(r"&(\w+)(.*?)/", re.S)
_KEY = re.compile(r"([A-Z_]+(?:\([0-9:,]+\))?)\s*=")


def _values(text: str) -> list[str]:
    out: list[str] = []
    for tok in re.findall(r"'[^']*'|[^,\s]+", text):
        out.append(tok)
    return out


def parse_fds(text: str) -> list[tuple[str, dict[str, list[str]]]]:
    """Namelist groups in order: (name, {KEY: [raw values]}). Strings keep their quotes stripped."""
    groups: list[tuple[str, dict[str, list[str]]]] = []
    for name, body in _GROUP.findall(text):
        keys = list(_KEY.finditer(body))
        fields: dict[str, list[str]] = {}
        for i, k in enumerate(keys):
            end = keys[i + 1].start() if i + 1 < len(keys) else len(body)
            fields[k.group(1)] = [v.strip("'") for v in _values(body[k.end() : end])]
        groups.append((name, fields))
    return groups


def fds_case(case: str) -> dict[str, Any]:
    """The physics an input sets: TMPA (K), T_END, DT, flux (W/m²), h, layer thicknesses, materials, ramps."""
    groups = parse_fds(fds_path(case).read_text(encoding="utf-8"))
    misc = next(f for n, f in groups if n == "MISC")
    time = next(f for n, f in groups if n == "TIME")
    surf = next(f for n, f in groups if n == "SURF")
    if misc["SOLID_PHASE_ONLY"] != ["T"] or surf["STRETCH_FACTOR"] != ["1", "1", "1"]:
        raise ValueError(f"{case}: not the solid-phase-only, unstretched input the pre-registration describes")
    matl = {f["ID"][0]: f for n, f in groups if n == "MATL"}
    ramps: dict[str, list[tuple[float, float]]] = {}
    for n, f in groups:
        if n == "RAMP":
            ramps.setdefault(f["ID"][0], []).append((float(f["T"][0]), float(f["F"][0])))
    return {
        "case": case,
        "tmpa_k": float(misc["TMPA"][0]) + 273.15,
        "t_end": float(time["T_END"][0]),
        "dt": float(time["DT"][0]),
        "flux_w": float(surf["EXTERNAL_FLUX"][0]) * 1000.0,
        "h": float(surf["HEAT_TRANSFER_COEFFICIENT"][0]),
        "thickness": [float(x) for x in surf["THICKNESS"]],
        "mass_fraction": [float(x) for x in surf["MATL_MASS_FRACTION(1,1:3)"]],
        "matl": matl,
        "ramps": ramps,
    }
