"""Which tests count, by §2's tables: every cone file becomes a record with its features and the reasons it is left
out of each set (a reason scoped "all", "mass", "per_lab" or "envelope")."""

from __future__ import annotations

import copy
import math
import re
import statistics
from dataclasses import dataclass, field
from pathlib import PurePosixPath

import features
import fetch
import pins
import tables

PMMA_NAME = re.compile(r"^(?P<lab>.+)_Cone_(?P<flux>\d+)kW(?:_(?P<rep>\d+))?$")
WOOD_NAME = re.compile(r"^(?P<lab>[^_]+)_Wood_Cone_(?P<flux>\d+)kW_hor(?:_(?P<orient>[A-Za-z]+))?_R(?P<rep>\d+)$")


@dataclass
class Test:
    """One cone test: where it came from, its area and features, and why it is left out of which set."""

    name: str
    path: str
    lab: str
    flux: int
    area: float
    feats: dict[str, float | bool | None]
    excluded: dict[str, list[str]] = field(default_factory=dict)

    def exclude(self, scope: str, reason: str) -> None:
        self.excluded.setdefault(scope, []).append(reason)

    def counts(self, scope: str, feature: str) -> bool:
        """Whether this test's `feature` enters the set `scope` ("per_lab" or "envelope")."""
        if "all" in self.excluded or scope in self.excluded:
            return False
        if feature in pins.MASS_FEATURES and "mass" in self.excluded:
            return False
        v = self.feats.get(feature)
        return isinstance(v, float) and math.isfinite(v)


def _stem(path: str) -> str:
    return PurePosixPath(path).name.rsplit(".", 1)[0]


def pmma_area(name: str, lab: str) -> float:
    return pins.DBI_ROUND_AREA if name in pins.DBI_ROUND else pins.PMMA_AREA.get(lab, pins.PMMA_AREA_DEFAULT)


def load_pmma(paths: list[str]) -> list[Test]:
    """Every PMMA cone file at 25, 50 or 65 kW/m², with §2's exclusions marked."""
    tests = []
    for path in paths:
        name = _stem(path)
        mo = PMMA_NAME.match(name)
        if mo is None:
            raise ValueError(f"unrecognised PMMA cone file name {path}")
        lab, flux = mo["lab"], int(mo["flux"])
        if flux not in pins.PMMA_FLUXES:
            continue
        area = pmma_area(name, lab)
        t, m, q = tables.cone_columns(fetch.cache_path(path))
        test = Test(name, path, lab, flux, area, dict(features.pmma_features(t, m, q, area)))
        if lab != pins.PMMA_FIT_LAB:
            test.exclude("per_lab", "not the per-lab band's lab")
        if name in pins.DBI_ROUND:
            test.exclude("per_lab", "round sample: another holder and area (§2, P1 per lab)")
        _dhc_rule(test)
        tests.append(test)
    _artefact_rule(tests, "peak", ("per_lab", "envelope"))
    return tests


def _dhc_rule(test: Test) -> None:
    """MaCFP-2's outlier rule, per test, for the envelope: ΔH_c within 23.5 ± 2.5 kJ/g; a test whose ΔH_c can't be
    computed (no ignition, or no mass signal) fails it too."""
    centre, half = pins.DHC_RULE
    v = test.feats.get("dhc")
    if not (isinstance(v, float) and math.isfinite(v)):
        test.exclude("envelope", "MaCFP-2 outlier rule: ΔH_c not computable")
    elif abs(v - centre) > half:
        test.exclude("envelope", f"MaCFP-2 outlier rule: ΔH_c {v:.2f} kJ/g outside {centre} ± {half}")


def _artefact_rule(tests: list[Test], peak: str, scopes: tuple[str, ...]) -> None:
    """§2.1's artefact rule, per set: a test whose peak exceeds twice its lab's median at that flux (over the tests
    still in that set) leaves the whole set."""
    for scope in scopes:
        groups: dict[tuple[str, int], list[Test]] = {}
        for t in tests:
            if t.counts(scope, peak):
                groups.setdefault((t.lab, t.flux), []).append(t)
        for group in groups.values():
            med = statistics.median(float(t.feats[peak]) for t in group)  # type: ignore[arg-type]
            for t in group:
                if float(t.feats[peak]) > pins.ARTEFACT_FACTOR * med:  # type: ignore[arg-type]
                    t.exclude(scope, f"artefact rule: {peak} {t.feats[peak]:.1f} > 2 x lab median {med:.1f}")


def load_pine(paths: list[str]) -> list[Test]:
    """Every parallel-grain wood cone file of a §2 lab at its flux, with §2's exclusions marked."""
    tests = []
    for path in paths:
        name = _stem(path)
        mo = WOOD_NAME.match(name)
        if mo is None:
            raise ValueError(f"unrecognised wood cone file name {path}")
        if (mo["orient"] or "").lower() == "perpendicular":
            continue
        lab, flux = mo["lab"], int(mo["flux"])
        area = pins.WOOD_AREA.get(lab, math.nan)
        test = Test(name, path, lab, flux, area, {})
        _wood_exclusions(test)
        if "all" not in test.excluded:
            t, m, q = tables.cone_columns(fetch.cache_path(path))
            test.feats = dict(features.pine_features(t, m, q, area))
        tests.append(test)
    _artefact_rule(tests, "first_peak", ("envelope",))
    return tests


def _wood_exclusions(test: Test) -> None:
    if test.lab in pins.WOOD_EXCLUDED_LABS:
        test.exclude("all", pins.WOOD_EXCLUDED_LABS[test.lab])
    if test.name in pins.WOOD_EXCLUDED_TESTS:
        test.exclude("all", pins.WOOD_EXCLUDED_TESTS[test.name])
    if test.lab not in pins.PINE_LABS.get(test.flux, ()) and "all" not in test.excluded:
        test.exclude("all", "lab not listed at this flux in §2")
    if test.name in pins.WOOD_NO_MASS:
        test.exclude("mass", pins.WOOD_NO_MASS[test.name])


def without_artefact_rule(tests: list[Test]) -> list[Test]:
    """Copies of the tests with the artefact rule's exclusions lifted: for a reported-only sensitivity, never a band."""
    out = []
    for t in tests:
        c = copy.deepcopy(t)
        c.excluded = {
            k: kept for k, v in c.excluded.items() if (kept := [r for r in v if not r.startswith("artefact")])
        }
        out.append(c)
    return out
