"""Score the spec generator spike's runs (plan.md §5, §6, §7). Throwaway spike code, never imported by ``src/``.

Every verdict is re-derived from each sample's last attempt (``protocol.classify``), not read from the record, and a
disagreement with what generate.py recorded is counted. One seeded Generator (seed 0) makes every draw: the labelling
sets first, then the blinding, then each bootstrap in a fixed order, so scoring the same files gives the same bytes.

    python spikes/specgen/score.py --runs spikes/specgen/runs/*.jsonl --out results.json \
        [--labelling-dir spikes/specgen/labelling] [--labels spikes/specgen/labels.jsonl] [--m3] [--m5] [--check]

Without ``--labels``, ``--labelling-dir`` receives the owner's blind sheet, renders and key; with it, the labels are
joined through that directory's key and §6's decision is computed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geometry
import labelling
import numpy as np
import protocol

from simcore.core.imagination import SpecRejected, place
from simcore.core.scene import Primitive

SEED, RESAMPLES, P_BAR = 0, 10_000, 0.8  # plan §5 (rates) and §2 (the product bar)
Key = tuple[str, str]  # (model, arm)


@dataclass
class Sample:
    """One scored sample: its identity, its prompt's tags, the re-derived verdict and what it cost."""

    prompt_id: str
    stratum: str
    model: str
    arm: str
    seed: int
    verdict: protocol.Verdict
    spec: dict[str, Any] | None
    prims: tuple[Primitive, ...] | None
    stored_class: str
    tokens: int
    wall_s: float
    meta: Mapping[str, Any] = field(default_factory=dict)

    @property
    def degenerate(self) -> dict[str, bool]:
        """Plan §5 M2, for a spec passing M1: (a) one primitive where one isn't right, (b) one material where two or
        more are expected, (c) a floating part."""
        prims = self.prims or ()
        mats = {p.material for p in prims}
        return {
            "a_single": len(prims) == 1 and not self.meta.get("single_ok", False),
            "b_one_material": len(self.meta.get("expect", [])) >= 2 and len(mats) == 1,
            "c_floating": geometry.components(prims) > 1,
        }


def prompt_meta() -> dict[str, dict[str, Any]]:
    return {p["id"]: p for split in protocol.SPLITS for p in protocol.load_prompts(split)}


def load(paths: Iterable[Path], arms: Mapping[str, Any]) -> list[Sample]:
    meta = prompt_meta()
    out = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("kind") == "sample":
                out.append(from_record(rec, arms, meta[rec["prompt_id"]]))
    return sorted(out, key=lambda s: (s.model, s.arm, s.prompt_id, s.seed))


def from_record(rec: Mapping[str, Any], arms: Mapping[str, Any], meta: Mapping[str, Any]) -> Sample:
    last = rec["attempts"][-1]
    finish = "length" if last.get("context_overflow") else last["finish"]
    verdict, spec = protocol.classify(last["raw"], finish, rec["arm"], arms)
    prims = protocol.authored(spec) if spec is not None else None
    tokens = sum(a.get("completion_tokens") or 0 for a in rec["attempts"])
    wall = sum(a.get("wall_s") or 0.0 for a in rec["attempts"])
    return Sample(
        rec["prompt_id"],
        rec["stratum"],
        rec["model"],
        rec["arm"],
        rec["seed"],
        verdict,
        spec,
        prims,
        last["klass"],
        tokens,
        wall,
        meta,
    )


def cluster_rate(by_prompt: Mapping[str, Sequence[float]], rng: np.random.Generator) -> dict[str, Any]:
    """A rate with its prompt-clustered percentile bootstrap: 95%, 10,000 resamples of whole prompts."""
    keys = sorted(by_prompt)
    sums = np.array([sum(by_prompt[k]) for k in keys], dtype=float)
    counts = np.array([len(by_prompt[k]) for k in keys], dtype=float)
    if not keys or counts.sum() == 0:
        return {"rate": None, "lo": None, "hi": None, "n": 0, "prompts": 0}
    idx = rng.integers(0, len(keys), size=(RESAMPLES, len(keys)))
    rates = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return {
        "rate": float(sums.sum() / counts.sum()),
        "lo": float(lo),
        "hi": float(hi),
        "n": int(counts.sum()),
        "prompts": len(keys),
    }


def paired_delta(
    h: Mapping[str, Sequence[float]], low: Mapping[str, Sequence[float]], rng: np.random.Generator
) -> dict[str, Any]:
    """Δ = H - L with a paired bootstrap over the prompts both share."""
    keys = sorted(set(h) & set(low))
    hs, hc = (np.array([f(h[k]) for k in keys], dtype=float) for f in (sum, len))
    ls, lc = (np.array([f(low[k]) for k in keys], dtype=float) for f in (sum, len))
    idx = rng.integers(0, len(keys), size=(RESAMPLES, len(keys)))
    deltas = hs[idx].sum(1) / hc[idx].sum(1) - ls[idx].sum(1) / lc[idx].sum(1)
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return {"delta": float(hs.sum() / hc.sum() - ls.sum() / lc.sum()), "lo": float(lo), "hi": float(hi)}


def grouped(
    samples: Iterable[Sample], value: Any, by_stratum: bool = False
) -> dict[tuple[str, ...], dict[str, list[float]]]:
    """``value(sample)`` (None to skip) per (model, arm[, stratum]) and prompt."""
    out: dict[tuple[str, ...], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for s in samples:
        v = value(s)
        if v is not None:
            key = (s.model, s.arm, s.stratum) if by_stratum else (s.model, s.arm)
            out[key][s.prompt_id].append(float(v))
    return out


def rates(groups: Mapping[tuple[str, ...], Mapping[str, Sequence[float]]], rng: np.random.Generator) -> dict[str, Any]:
    return {"/".join(k): cluster_rate(groups[k], rng) for k in sorted(groups)}


def m1(samples: list[Sample], rng: np.random.Generator) -> dict[str, Any]:
    """M1: the acceptance rate per model, arm and stratum, and the breakdown of every other class."""
    breakdown: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in samples:
        v = s.verdict
        label = v.klass if v.klass != protocol.REFUSED else f"refused:{v.code}" + (f":{v.field}" if v.field else "")
        breakdown[f"{s.model}/{s.arm}"][label] += 1
    possible = [s for s in samples if s.stratum != "impossible"]
    return {
        "rate": rates(grouped(possible, lambda s: s.verdict.m1_pass), rng),
        "rate_by_stratum": rates(grouped(samples, lambda s: s.verdict.m1_pass, by_stratum=True), rng),
        "classes": {k: dict(sorted(v.items())) for k, v in sorted(breakdown.items())},
        "recorded_class_disagrees": sum(s.verdict.klass != s.stored_class for s in samples),
    }


def m2_m4(samples: list[Sample], rng: np.random.Generator) -> dict[str, Any]:
    passing = [s for s in samples if s.verdict.m1_pass and s.stratum != "impossible" and s.prims]
    flags = {
        f: rates(grouped(passing, lambda s, f=f: s.degenerate[f]), rng)
        for f in ("a_single", "b_one_material", "c_floating")
    }
    return {
        "m2_degenerate": rates(grouped(passing, lambda s: any(s.degenerate.values())), rng),
        "m2_flags": flags,
        "m2_thin_fraction": {
            "/".join(k): float(np.mean([v for vs in g.values() for v in vs]))
            for k, g in sorted(grouped(passing, lambda s: geometry.thin_fraction(s.prims or ())).items())
        },
        "m4_material_fit": rates(grouped([s for s in passing if s.meta.get("expect")], _has_expected), rng),
    }


def _has_expected(s: Sample) -> bool:
    return set(s.meta["expect"]) <= {p.material for p in s.prims or ()}


def m3(samples: list[Sample]) -> dict[str, Any]:
    """M3 (reported only): voxelized over authored volume at the scene offset and half a cell on, and acceptance at
    0.2 m, for every spec passing M1."""
    half = [c + protocol.TRUTH_DX_M / 2 for c in protocol.OFFSET_M]
    rows: dict[str, list[tuple[float, float, bool]]] = defaultdict(list)
    for s in samples:
        if s.verdict.m1_pass and s.spec is not None and s.prims:
            authored_m3 = sum(p.volume_m3 for p in s.prims)
            at = [_voxel_m3(s.spec, o, protocol.TRUTH_DX_M) / authored_m3 for o in (protocol.OFFSET_M, half)]
            coarse = protocol.place_verdict(s.spec, protocol.OFFSET_M, 0.2).klass == protocol.ACCEPTED
            rows[f"{s.model}/{s.arm}"].append((at[0], at[1], coarse))
    return {
        k: {
            "ratio_offset": float(np.mean([r[0] for r in v])),
            "ratio_half_cell": float(np.mean([r[1] for r in v])),
            "accepted_at_0.2m": float(np.mean([r[2] for r in v])),
            "n": len(v),
        }
        for k, v in sorted(rows.items())
    }


def _voxel_m3(spec: Mapping[str, Any], offset: Sequence[float], dx_m: float) -> float:
    grid = protocol.empty_grid(dx_m)
    try:
        place(grid, dict(spec), tuple(offset))
    except SpecRejected:
        return 0.0
    return float(np.count_nonzero(grid.regions[spec["name"]].cells)) * dx_m**3


def m7(samples: list[Sample]) -> dict[str, Any]:
    """M7: distinct SpecIds and the Vendi score per prompt, over samples passing M1; prompts with fewer than 2 are
    counted, not scored."""
    cells: dict[Key, dict[str, list[Sample]]] = defaultdict(lambda: defaultdict(list))
    for s in samples:
        if s.verdict.m1_pass and s.spec is not None and s.prims:
            cells[(s.model, s.arm)][s.prompt_id].append(s)
    out = {}
    for key in sorted(cells):
        scored = [g for g in cells[key].values() if len(g) >= 2]
        ids = [len({geometry.spec_id(s.spec or {}) for s in g}) for g in scored]
        vs = [geometry.vendi([geometry.raster(s.prims or ()) for s in g]) for g in scored]
        out["/".join(key)] = {
            "prompts_scored": len(scored),
            "prompts_under_2": len(cells[key]) - len(scored),
            "distinct_spec_ids_mean": float(np.mean(ids)) if ids else None,
            "vendi_half_mean": float(np.mean([v[0] for v in vs])) if vs else None,
            "vendi_inf_mean": float(np.mean([v[1] for v in vs])) if vs else None,
        }
    return out


def m8(samples: list[Sample], rng: np.random.Generator) -> dict[str, Any]:
    impossible = [s for s in samples if s.stratum == "impossible"]
    return {
        "accepted": rates(grouped(impossible, lambda s: s.verdict.m1_pass), rng),
        "accepted_by_breaks": {
            b: rates(grouped([s for s in impossible if s.meta.get("breaks") == b], lambda s: s.verdict.m1_pass), rng)
            for b in ("extent", "mass", "primitives")
        },
    }


def m9(samples: list[Sample], good: Mapping[tuple[str, str, str, int], bool] | None) -> dict[str, Any]:
    out = {}
    for key in sorted({(s.model, s.arm) for s in samples}):
        cell = [s for s in samples if (s.model, s.arm) == key]
        passing = sum(s.verdict.m1_pass for s in cell)
        row: dict[str, Any] = {
            "tokens": sum(s.tokens for s in cell),
            "wall_s": sum(s.wall_s for s in cell),
            "samples": len(cell),
            "m1_pass": passing,
        }
        if good is not None:
            labelled = [s for s in cell if (s.model, s.arm, s.prompt_id, s.seed) in good]
            n_good = sum(good[(s.model, s.arm, s.prompt_id, s.seed)] for s in labelled)
            row["per_good_spec_labelled_set"] = (
                {"tokens": sum(s.tokens for s in labelled) / n_good, "wall_s": sum(s.wall_s for s in labelled) / n_good}
                if n_good
                else None
            )
        out["/".join(key)] = row
    return out


def decision(
    samples: list[Sample],
    draws: labelling.Draws,
    labels: Mapping[tuple[str, str, str, int], str],
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Plan §6 on the paired set: L and H with prompt-clustered intervals, Δ paired, and the first rule that holds;
    then the same rates without prompts tagged `template`, as a diagnostic only."""
    index = {(s.model, s.arm, s.prompt_id, s.seed): s for s in samples}

    def good(model: str, prompts: Sequence[str]) -> dict[str, list[float]]:
        out: dict[str, list[float]] = {}
        for p in prompts:
            out[p] = [
                float(_is_good(index.get((model, "A3", p, seed)), labels.get((model, "A3", p, seed))))
                for seed in labelling.PAIRED_SEEDS
            ]
        return out

    low, high = good("S", draws.paired), good("R", draws.paired)
    l_rate, h_rate, d = cluster_rate(low, rng), cluster_rate(high, rng), paired_delta(high, low, rng)
    rule = 3
    if l_rate["lo"] >= P_BAR:
        rule = 1
    elif h_rate["lo"] >= P_BAR and d["lo"] > 0:
        rule = 2
    meta = prompt_meta()
    plain = [p for p in draws.paired if not meta[p].get("template")]
    return {
        "L": l_rate,
        "H": h_rate,
        "delta": d,
        "rule": rule,
        "P": P_BAR,
        "without_template": {
            "prompts": len(plain),
            "L": cluster_rate(good("S", plain), rng),
            "H": cluster_rate(good("R", plain), rng),
        },
    }


def _is_good(s: Sample | None, label: str | None) -> bool:
    """Plan §5's composite: passes M1, is not degenerate, and the owner labelled it "yes"."""
    return s is not None and s.verdict.m1_pass and not any(s.degenerate.values()) and label == "yes"


def read_labels(labelling_dir: Path, labels_path: Path) -> dict[tuple[str, str, str, int], str]:
    key = {r["id"]: r for r in map(json.loads, (labelling_dir / "key" / "key.jsonl").read_text().splitlines())}
    out = {}
    for row in map(json.loads, labels_path.read_text(encoding="utf-8").splitlines()):
        k = key[row["id"]]
        if row["label"] not in ("yes", "partly", "no"):
            raise ValueError(f"label {row['label']!r} for {row['id']} is not yes, partly or no")
        out[(k["model"], k["arm"], k["prompt_id"], k["seed"])] = row["label"]
    return out


def score(args: argparse.Namespace) -> dict[str, Any]:
    arms = protocol.load_arms()
    samples = load([Path(p) for p in args.runs], arms)
    rng = np.random.default_rng(SEED)
    dev = protocol.load_prompts("dev")
    draws = labelling.draw(rng, dev)  # first, always, so the sets never depend on what else is scored
    labels = read_labels(Path(args.labelling_dir), Path(args.labels)) if args.labels else None
    if args.labelling_dir and not args.labels:
        _emit_labelling(Path(args.labelling_dir), draws, samples, rng, {p["id"]: p["text"] for p in dev})
    result: dict[str, Any] = {
        "m1": m1(samples, rng),
        **m2_m4(samples, rng),
        "m7": m7(samples),
        "m8": m8(samples, rng),
        "draws": {"paired": draws.paired, "trend": draws.trend, "m8": draws.m8},
    }
    if args.m3:
        result["m3"] = m3(samples)
    if args.m5:
        import burn  # noqa: PLC0415 - heavy, and only on request

        result["m5"] = burn.m5(samples)
    good = None
    if labels is not None:
        result["decision"] = decision(samples, draws, labels, rng)
        good = {
            k: _is_good(next((s for s in samples if (s.model, s.arm, s.prompt_id, s.seed) == k), None), v)
            for k, v in labels.items()
        }
    result["m9"] = m9(samples, good)
    return result


def _emit_labelling(
    out_dir: Path, draws: labelling.Draws, samples: list[Sample], rng: np.random.Generator, texts: Mapping[str, str]
) -> None:
    index = {(s.model, s.arm, s.prompt_id, s.seed): s for s in samples}
    entries = []
    for item in labelling.items(draws):
        s = index.get((item["model"], item["arm"], item["prompt_id"], item["seed"]))
        entries.append({"item": item, "m1_pass": bool(s and s.verdict.m1_pass), "prims": s.prims if s else None})
    labelling.write_sets(out_dir, rng, entries, texts)


def check(argv: list[str]) -> int:
    """plan §7: score in two processes with different PYTHONHASHSEED and compare the outputs' digests."""
    out_raw = argv[argv.index("--out") + 1]
    out = Path(out_raw)
    rest = [a for a in argv if a != "--check"]
    digests = []
    with tempfile.TemporaryDirectory(dir=out.resolve().parent) as tmp:
        for hs in ("1", "2"):
            target = Path(tmp) / f"out{hs}.json"
            cmd = [sys.executable, __file__, *[str(target) if a == out_raw else a for a in rest]]
            subprocess.run(cmd, check=True, env={**os.environ, "PYTHONHASHSEED": hs})
            digests.append(hashlib.sha256(target.read_bytes()).hexdigest())
    print(f"score --check: {'PASS' if digests[0] == digests[1] else 'FAIL'} {digests}")
    return 0 if digests[0] == digests[1] else 1


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labelling-dir")
    ap.add_argument("--labels")
    ap.add_argument("--m3", action="store_true")
    ap.add_argument("--m5", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.labels and not args.labelling_dir:
        ap.error("--labels needs --labelling-dir, whose key joins them")
    return args


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    args = parse_args(raw)
    if args.check:
        return check(raw)
    Path(args.out).write_text(json.dumps(score(args), sort_keys=True, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
