"""Score the spec generator spike's runs (plan.md §5, §6, §7). Throwaway spike code, never imported by ``src/``.

Every verdict is re-derived from each sample's last attempt (``protocol.classify``), not read from the record, and a
disagreement with what generate.py recorded is counted. The labelling sets are drawn first from
``numpy.random.default_rng(0)``; every other draw (the blinding, each bootstrap) has a generator of its own, seeded by
seed 0 and the statistic's name (errata E10), so an interval never depends on what else was scored.

    python spikes/specgen/score.py --split dev --runs runs/*-dev.jsonl --out results.json \\
        [--labelling-dir labelling] [--labels labels.jsonl] [--m3] [--m5] [--allow-partial] [--check]

The runs are read with their headers: each must be of ``--split``, carry the frozen files' and data's current hashes,
and hold each (model, arm, prompt, seed) once. A cell missing samples is refused unless ``--allow-partial`` (for
watching a run, never for a result), and §6's decision is refused whenever its paired set or a label is missing
(errata E13). Without ``--labels``, ``--labelling-dir`` receives the owner's blind sheet, renders and key; with it, the
labels are joined through that key.
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
SampleKey = tuple[str, str, str, int]  # (model, arm, prompt, seed)


class ScoreRefused(ValueError):
    """The runs can't be scored as asked: a header, split, duplicate, missing sample or missing label."""


def rng_for(name: str) -> np.random.Generator:
    """One statistic's own generator: seed 0 and the statistic's name (errata E10)."""
    words = np.frombuffer(hashlib.sha256(name.encode("utf-8")).digest()[:16], dtype="<u4").tolist()
    return np.random.default_rng([SEED, *words])


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
    prompt_tokens: int
    completion_tokens: int
    wall_s: float
    meta: Mapping[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> SampleKey:
        return (self.model, self.arm, self.prompt_id, self.seed)

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


def _current_data() -> dict[str, str]:
    data = protocol.ROOT / "data"
    return {p: protocol.sha256_file(data / p) for p in ("materials/core.yaml", "world/actions.yaml")}


def read_run(path: Path, split: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """One run file's header and sample records, refused unless the header is of ``split`` and of the current frozen
    files and data."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ScoreRefused(f"{path} is empty")
    rows = [json.loads(line) for line in lines]
    head = rows[0]
    if head.get("kind") != "header":
        raise ScoreRefused(f"{path} has no header")
    if head.get("split") != split:
        raise ScoreRefused(f"{path} is of split {head.get('split')!r}, not {split!r}")
    if head.get("frozen") != protocol.check_frozen():
        raise ScoreRefused(f"{path} was run on other frozen files than this tree's")
    if head.get("data_sha256") != _current_data():
        raise ScoreRefused(f"{path} was run on other data than this tree's")
    return head, [r for r in rows[1:] if r.get("kind") == "sample"]


def load(paths: Iterable[Path], arms: Mapping[str, Any], split: str) -> list[Sample]:
    meta = prompt_meta()
    out: dict[SampleKey, Sample] = {}
    for path in paths:
        _, records = read_run(path, split)
        for rec in records:
            if rec.get("split", split) != split:
                raise ScoreRefused(f"{path} holds a sample of split {rec.get('split')!r}")
            s = from_record(rec, arms, meta[rec["prompt_id"]])
            if s.key in out:
                raise ScoreRefused(f"{s.key} appears twice")
            out[s.key] = s
    return sorted(out.values(), key=lambda s: s.key)


def completeness(samples: Sequence[Sample], split: str, arms: Mapping[str, Any]) -> dict[str, Any]:
    """Each (model, arm) cell's missing (prompt, seed) pairs against the split's prompts and arms.yaml's seeds."""
    want = {(p["id"], s) for p in protocol.load_prompts(split) for s in arms["sampling"]["seeds"]}
    have: dict[Key, set[tuple[str, int]]] = defaultdict(set)
    for s in samples:
        have[(s.model, s.arm)].add((s.prompt_id, s.seed))
    return {"/".join(k): {"expected": len(want), "missing": len(want - have[k])} for k in sorted(have)}


def from_record(rec: Mapping[str, Any], arms: Mapping[str, Any], meta: Mapping[str, Any]) -> Sample:
    last = rec["attempts"][-1]
    finish = "length" if last.get("context_overflow") else last["finish"]
    verdict, spec = protocol.classify(last["raw"], finish, rec["arm"], arms)
    prims = protocol.authored(spec) if spec is not None else None
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
        sum(a.get("prompt_tokens") or 0 for a in rec["attempts"]),
        sum(a.get("completion_tokens") or 0 for a in rec["attempts"]),
        sum(a.get("wall_s") or 0.0 for a in rec["attempts"]),
        meta,
    )


def cluster_rate(by_prompt: Mapping[str, Sequence[float]], name: str) -> dict[str, Any]:
    """A rate with its prompt-clustered percentile bootstrap: 95%, 10,000 resamples of whole prompts, drawn from the
    statistic's own generator."""
    keys = sorted(by_prompt)
    sums = np.array([sum(by_prompt[k]) for k in keys], dtype=float)
    counts = np.array([len(by_prompt[k]) for k in keys], dtype=float)
    if not keys or counts.sum() == 0:
        return {"rate": None, "lo": None, "hi": None, "n": 0, "prompts": 0}
    idx = rng_for(name).integers(0, len(keys), size=(RESAMPLES, len(keys)))
    rates_ = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.percentile(rates_, [2.5, 97.5])
    return {
        "rate": float(sums.sum() / counts.sum()),
        "lo": float(lo),
        "hi": float(hi),
        "n": int(counts.sum()),
        "prompts": len(keys),
    }


def paired_delta(h: Mapping[str, Sequence[float]], low: Mapping[str, Sequence[float]], name: str) -> dict[str, Any]:
    """Δ = H - L with a paired bootstrap over the prompts both share."""
    keys = sorted(set(h) & set(low))
    if not keys:
        raise ScoreRefused("Δ needs at least one prompt both models share")
    hs, hc = (np.array([f(h[k]) for k in keys], dtype=float) for f in (sum, len))
    ls, lc = (np.array([f(low[k]) for k in keys], dtype=float) for f in (sum, len))
    idx = rng_for(name).integers(0, len(keys), size=(RESAMPLES, len(keys)))
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


def rates(groups: Mapping[tuple[str, ...], Mapping[str, Sequence[float]]], name: str) -> dict[str, Any]:
    return {"/".join(k): cluster_rate(groups[k], f"{name}/{'/'.join(k)}") for k in sorted(groups)}


def m1(samples: list[Sample]) -> dict[str, Any]:
    """M1: the acceptance rate per model, arm and stratum, and the breakdown of every other class."""
    breakdown: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in samples:
        v = s.verdict
        label = v.klass if v.klass != protocol.REFUSED else f"refused:{v.code}" + (f":{v.field}" if v.field else "")
        breakdown[f"{s.model}/{s.arm}"][label] += 1
    possible = [s for s in samples if s.stratum != "impossible"]
    return {
        "rate": rates(grouped(possible, lambda s: s.verdict.m1_pass), "m1.rate"),
        "rate_by_stratum": rates(grouped(samples, lambda s: s.verdict.m1_pass, by_stratum=True), "m1.by_stratum"),
        "classes": {k: dict(sorted(v.items())) for k, v in sorted(breakdown.items())},
        "recorded_class_disagrees": sum(s.verdict.klass != s.stored_class for s in samples),
    }


def m2_m4(samples: list[Sample]) -> dict[str, Any]:
    passing = [s for s in samples if s.verdict.m1_pass and s.stratum != "impossible" and s.prims]
    flags = {
        f: rates(grouped(passing, lambda s, f=f: s.degenerate[f]), f"m2.{f}")
        for f in ("a_single", "b_one_material", "c_floating")
    }
    return {
        "m2_degenerate": rates(grouped(passing, lambda s: any(s.degenerate.values())), "m2.degenerate"),
        "m2_flags": flags,
        "m2_thin_fraction_mean_of_specs": {
            "/".join(k): float(np.mean([v for vs in g.values() for v in vs]))
            for k, g in sorted(grouped(passing, lambda s: geometry.thin_fraction(s.prims or ())).items())
        },
        "m4_material_fit": rates(grouped([s for s in passing if s.meta.get("expect")], _has_expected), "m4"),
    }


def _has_expected(s: Sample) -> bool:
    return set(s.meta["expect"]) <= {p.material for p in s.prims or ()}


def m3(samples: list[Sample]) -> dict[str, Any]:
    """M3 (reported only): voxelized over authored volume at the scene offset and half a cell on, and acceptance at
    0.2 m, for every spec passing M1. A spec place refuses at an offset counts 0 there and is counted apart."""
    half = [c + protocol.TRUTH_DX_M / 2 for c in protocol.OFFSET_M]
    rows: dict[str, list[tuple[float, float, bool, int]]] = defaultdict(list)
    for s in samples:
        if s.verdict.m1_pass and s.spec is not None and s.prims:
            authored_m3 = sum(p.volume_m3 for p in s.prims)
            got = [_voxel_m3(s.spec, o, protocol.TRUTH_DX_M) for o in (protocol.OFFSET_M, half)]
            refused = sum(g is None for g in got)
            at = [(g or 0.0) / authored_m3 for g in got]
            coarse = protocol.place_verdict(s.spec, protocol.OFFSET_M, 0.2).klass == protocol.ACCEPTED
            rows[f"{s.model}/{s.arm}"].append((at[0], at[1], coarse, refused))
    return {
        k: {
            "ratio_offset": float(np.mean([r[0] for r in v])),
            "ratio_half_cell": float(np.mean([r[1] for r in v])),
            "accepted_at_0.2m": float(np.mean([r[2] for r in v])),
            "refused_at_an_offset": sum(r[3] for r in v),
            "n": len(v),
        }
        for k, v in sorted(rows.items())
    }


def _voxel_m3(spec: Mapping[str, Any], offset: Sequence[float], dx_m: float) -> float | None:
    """The placed cells' volume, or None when place refuses the spec at this offset."""
    grid = protocol.empty_grid(dx_m)
    try:
        place(grid, dict(spec), tuple(offset))
    except SpecRejected:
        return None
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


def m8(samples: list[Sample]) -> dict[str, Any]:
    impossible = [s for s in samples if s.stratum == "impossible"]
    return {
        "accepted": rates(grouped(impossible, lambda s: s.verdict.m1_pass), "m8.accepted"),
        "accepted_by_breaks": {
            b: rates(
                grouped([s for s in impossible if s.meta.get("breaks") == b], lambda s: s.verdict.m1_pass),
                f"m8.accepted.{b}",
            )
            for b in ("extent", "mass", "primitives")
        },
    }


def m9(samples: list[Sample], good: Mapping[SampleKey, bool] | None) -> dict[str, Any]:
    """M9 cost per cell: prompt and completion tokens and wall time, in total, per sample and per M1 pass; and per good
    spec on the labelled set only (errata E8, E17)."""
    out = {}
    for key in sorted({(s.model, s.arm) for s in samples}):
        cell = [s for s in samples if (s.model, s.arm) == key]
        passing = sum(s.verdict.m1_pass for s in cell)
        tokens = sum(s.prompt_tokens + s.completion_tokens for s in cell)
        wall = sum(s.wall_s for s in cell)
        row: dict[str, Any] = {
            "prompt_tokens": sum(s.prompt_tokens for s in cell),
            "completion_tokens": sum(s.completion_tokens for s in cell),
            "wall_s": wall,
            "samples": len(cell),
            "m1_pass": passing,
            "per_sample": {"tokens": tokens / len(cell), "wall_s": wall / len(cell)},
            "per_m1_pass": {"tokens": tokens / passing, "wall_s": wall / passing} if passing else None,
        }
        if good is not None:
            labelled = [s for s in cell if s.key in good]
            n_good = sum(good[s.key] for s in labelled)
            row["per_good_spec_labelled_set"] = (
                {
                    "tokens": sum(s.prompt_tokens + s.completion_tokens for s in labelled) / n_good,
                    "wall_s": sum(s.wall_s for s in labelled) / n_good,
                }
                if n_good
                else None
            )
        out["/".join(key)] = row
    return out


@dataclass(frozen=True)
class Labels:
    """The owner's labels, joined through the key: each labelled sample's label, and the set it was drawn for."""

    label: Mapping[SampleKey, str]
    sets: Mapping[SampleKey, str]


def _require_paired(index: Mapping[SampleKey, Sample], draws: labelling.Draws, labels: Labels) -> None:
    """Plan §6 is computed only on complete data: every paired sample once, and a label for each one passing M1."""
    missing, unlabelled = [], []
    for model in ("S", "R"):
        for p in draws.paired:
            for seed in labelling.PAIRED_SEEDS:
                k = (model, "A3", p, seed)
                s = index.get(k)
                if s is None:
                    missing.append(k)
                elif s.verdict.m1_pass and k not in labels.label:
                    unlabelled.append(k)
    if missing or unlabelled:
        raise ScoreRefused(
            f"§6 needs the whole paired set: {len(missing)} samples missing (e.g. {missing[:2]}), "
            f"{len(unlabelled)} passing M1 unlabelled (e.g. {unlabelled[:2]})"
        )


def decision(samples: list[Sample], draws: labelling.Draws, labels: Labels) -> dict[str, Any]:
    """Plan §6 on the paired set: L and H with prompt-clustered intervals, Δ paired, and the first rule that holds;
    then the same rates without prompts tagged `template`, as a diagnostic only."""
    index = {s.key: s for s in samples}
    _require_paired(index, draws, labels)

    def good(model: str, prompts: Sequence[str]) -> dict[str, list[float]]:
        return {
            p: [
                float(_is_good(index[(model, "A3", p, seed)], labels.label.get((model, "A3", p, seed))))
                for seed in labelling.PAIRED_SEEDS
            ]
            for p in prompts
        }

    low, high = good("S", draws.paired), good("R", draws.paired)
    l_rate, h_rate = cluster_rate(low, "decision.L"), cluster_rate(high, "decision.H")
    d = paired_delta(high, low, "decision.delta")
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
            "L": cluster_rate(good("S", plain), "decision.without_template.L"),
            "H": cluster_rate(good("R", plain), "decision.without_template.H"),
        },
    }


def _is_good(s: Sample | None, label: str | None) -> bool:
    """Plan §5's composite: passes M1, is not degenerate, and the owner labelled it "yes"."""
    return s is not None and s.verdict.m1_pass and not any(s.degenerate.values()) and label == "yes"


def m6_m8_labels(samples: list[Sample], labels: Labels) -> dict[str, Any]:
    """M6's label rates per set (paired per model, trend per arm), with `hard: shape` prompts apart; and M8's
    closest-fit rate, the share of its labelled specs marked "yes" (errata E16)."""
    index = {s.key: s for s in samples}
    groups: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for k in sorted(labels.label):
        s, lab, which = index.get(k), labels.label[k], labels.sets[k]
        if s is None:
            raise ScoreRefused(f"label for {k}, which no run holds")
        part = "hard_shape" if s.meta.get("hard") == "shape" else "plain"
        name = f"{which}/{s.model}" if which == "paired" else f"{which}/{s.arm}" if which == "trend" else which
        groups[f"{name}/{part}"][s.prompt_id].append(float(lab == "yes"))
        counts[f"{name}/{part}"][lab] += 1
    rates_ = {k: cluster_rate(groups[k], f"m6.{k}") for k in sorted(groups)}
    return {
        "m6": {k: {"yes_rate": rates_[k], "counts": dict(sorted(counts[k].items()))} for k in rates_ if k[:2] != "m8"},
        "m8_closest_fit": {
            k: {"yes_rate": rates_[k], "counts": dict(sorted(counts[k].items()))} for k in rates_ if k[:2] == "m8"
        },
    }


def read_labels(labelling_dir: Path, labels_path: Path) -> Labels:
    key = {r["id"]: r for r in map(json.loads, (labelling_dir / "key" / "key.jsonl").read_text().splitlines())}
    label: dict[SampleKey, str] = {}
    sets: dict[SampleKey, str] = {}
    for row in map(json.loads, labels_path.read_text(encoding="utf-8").splitlines()):
        k = key[row["id"]]
        if row["label"] not in ("yes", "partly", "no"):
            raise ScoreRefused(f"label {row['label']!r} for {row['id']} is not yes, partly or no")
        sk = (k["model"], k["arm"], k["prompt_id"], k["seed"])
        if sk in label:
            raise ScoreRefused(f"{row['id']} is labelled twice")
        label[sk], sets[sk] = row["label"], k["set"]
    return Labels(label, sets)


def score(args: argparse.Namespace) -> dict[str, Any]:
    arms = protocol.load_arms()
    samples = load([Path(p) for p in args.runs], arms, args.split)
    complete = completeness(samples, args.split, arms)
    short = {k: v for k, v in complete.items() if v["missing"]}
    if short and not args.allow_partial:
        raise ScoreRefused(f"cells missing samples: {short} (--allow-partial only to watch a run)")
    dev = protocol.load_prompts("dev")
    draws = labelling.draw(np.random.default_rng(SEED), dev)  # the labelling sets: errata E6, E7
    labels = read_labels(Path(args.labelling_dir), Path(args.labels)) if args.labels else None
    if args.labelling_dir and not args.labels:
        _emit_labelling(Path(args.labelling_dir), draws, samples, {p["id"]: p["text"] for p in dev})
    result: dict[str, Any] = {
        "split": args.split,
        "completeness": complete,
        "partial": bool(short),
        "m1": m1(samples),
        **m2_m4(samples),
        "m7": m7(samples),
        "m8": m8(samples),
        "draws": {"paired": draws.paired, "trend": draws.trend, "m8": draws.m8},
    }
    if args.m3:
        result["m3"] = m3(samples)
    if args.m5:
        import burn  # noqa: PLC0415 - heavy, and only on request

        result["m5"] = burn.m5(samples)
    good = None
    if labels is not None:
        if args.split != "dev" or short:
            raise ScoreRefused("§6's decision is computed on the complete dev split only")
        result["decision"] = decision(samples, draws, labels)
        result.update(m6_m8_labels(samples, labels))
        index = {s.key: s for s in samples}
        good = {k: _is_good(index.get(k), v) for k, v in labels.label.items()}
    result["m9"] = m9(samples, good)
    return result


def _emit_labelling(out_dir: Path, draws: labelling.Draws, samples: list[Sample], texts: Mapping[str, str]) -> None:
    index = {s.key: s for s in samples}
    entries = []
    for item in labelling.items(draws):
        s = index.get((item["model"], item["arm"], item["prompt_id"], item["seed"]))
        entries.append({"item": item, "m1_pass": bool(s and s.verdict.m1_pass), "prims": s.prims if s else None})
    labelling.write_sets(out_dir, rng_for("labelling.blind"), entries, texts)


def check(args: argparse.Namespace, argv: list[str]) -> int:
    """plan §7: score in two processes with different PYTHONHASHSEED and compare the outputs' digests. Each process
    writes its own output and labelling directory, under a temporary directory beside ``--out``."""
    out = Path(args.out)
    digests = []
    with tempfile.TemporaryDirectory(dir=out.resolve().parent) as tmp:
        for hs in ("1", "2"):
            run = parse_args(argv)
            run.check, run.out = False, str(Path(tmp) / f"out{hs}.json")
            if run.labelling_dir and not run.labels:
                run.labelling_dir = str(Path(tmp) / f"labelling{hs}")
            cmd = [sys.executable, __file__, *_argv(run)]
            subprocess.run(cmd, check=True, env={**os.environ, "PYTHONHASHSEED": hs})
            digests.append(hashlib.sha256(Path(run.out).read_bytes()).hexdigest())
    print(f"score --check: {'PASS' if digests[0] == digests[1] else 'FAIL'} {digests}")
    return 0 if digests[0] == digests[1] else 1


def _argv(a: argparse.Namespace) -> list[str]:
    out = ["--split", a.split, "--runs", *a.runs, "--out", a.out]
    for flag, value in (("--labelling-dir", a.labelling_dir), ("--labels", a.labels)):
        if value:
            out += [flag, value]
    out += [f for f, on in (("--m3", a.m3), ("--m5", a.m5), ("--allow-partial", a.allow_partial)) if on]
    return out


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", required=True, choices=tuple(protocol.SPLITS))
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labelling-dir")
    ap.add_argument("--labels")
    ap.add_argument("--m3", action="store_true")
    ap.add_argument("--m5", action="store_true")
    ap.add_argument(
        "--allow-partial", action="store_true", help="score incomplete cells (to watch a run, never a result)"
    )
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.labels and not args.labelling_dir:
        ap.error("--labels needs --labelling-dir, whose key joins them")
    return args


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    args = parse_args(raw)
    if args.check:
        return check(args, raw)
    try:
        result = score(args)
    except ScoreRefused as exc:
        print(f"score: refused: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
