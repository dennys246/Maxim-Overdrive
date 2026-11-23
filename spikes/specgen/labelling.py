"""The owner's labelling sets and their renders (plan.md §5, M6 and M8). Throwaway spike code.

The sets are drawn first from the scorer's one seeded Generator (seed 0), before any bootstrap, so they are the same
whatever is scored after them. Renders are drawn from the authored primitives, never from voxels, so M6 judges the
generator: three orthographic views and one isometric view, each primitive filled with its material's ``color_rgb``.
The owner sees only anonymous ids; the key that maps an id to its sample is written apart, under ``key/``.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from maxim_overdrive.data import materials
from simcore.core.scene import Box, Cylinder, Primitive

POSSIBLE = ("furniture", "barriers", "glass", "mixed")  # the four possible strata, in a fixed order
PAIRED_PROMPTS, PAIRED_SEEDS = 30, (0, 1, 2, 3)
TREND_PROMPTS, TREND_SEEDS, TREND_ARMS = 10, (0, 1), ("A0", "A1", "A2")
M8_PROMPTS, M8_SEEDS = 10, (0, 1)


@dataclass(frozen=True)
class Draws:
    """The labelling sets' prompts: paired (M6, §6), trend (M6) and closest-fit (M8)."""

    paired: tuple[str, ...]
    trend: tuple[str, ...]
    m8: tuple[str, ...]


def quotas(counts: Mapping[str, int], total: int) -> dict[str, int]:
    """Proportional allocation of ``total`` over the strata, by largest remainder, ties broken in POSSIBLE order."""
    n = sum(counts.values())
    exact = {s: total * counts[s] / n for s in POSSIBLE}
    out = {s: math.floor(v) for s, v in exact.items()}
    by_remainder = sorted(POSSIBLE, key=lambda s: (-(exact[s] - out[s]), POSSIBLE.index(s)))
    for s in by_remainder[: total - sum(out.values())]:
        out[s] += 1
    return out


def draw(rng: np.random.Generator, dev: Sequence[Mapping[str, Any]]) -> Draws:
    """The three sets, in file order within each stratum, drawn in this fixed order from ``rng``."""
    by = {s: [p["id"] for p in dev if p["stratum"] == s] for s in POSSIBLE}
    q = quotas({s: len(v) for s, v in by.items()}, PAIRED_PROMPTS)
    paired: list[str] = []
    for s in POSSIBLE:
        picked = set(rng.permutation(len(by[s]))[: q[s]].tolist())
        paired += [pid for i, pid in enumerate(by[s]) if i in picked]
    trend_idx = set(rng.permutation(len(paired))[:TREND_PROMPTS].tolist())
    impossible = [p["id"] for p in dev if p["stratum"] == "impossible"]
    m8_idx = set(rng.permutation(len(impossible))[:M8_PROMPTS].tolist())
    return Draws(
        tuple(paired),
        tuple(pid for i, pid in enumerate(paired) if i in trend_idx),
        tuple(pid for i, pid in enumerate(impossible) if i in m8_idx),
    )


def items(d: Draws) -> list[dict[str, Any]]:
    """Every (set, prompt, model, arm, seed) the owner labels, before blinding."""
    out = [
        {"set": "paired", "prompt_id": p, "model": m, "arm": "A3", "seed": s}
        for p in d.paired
        for m in ("S", "R")
        for s in PAIRED_SEEDS
    ]
    out += [
        {"set": "trend", "prompt_id": p, "model": "S", "arm": a, "seed": s}
        for p in d.trend
        for a in TREND_ARMS
        for s in TREND_SEEDS
    ]
    out += [{"set": "m8", "prompt_id": p, "model": "S", "arm": "A3", "seed": s} for p in d.m8 for s in M8_SEEDS]
    return out


# --- rendering -------------------------------------------------------------------------------------------------------

PANEL = 240.0
_COS30, _SIN30 = math.cos(math.pi / 6), 0.5


def _colour(material: str) -> str:
    table = materials()
    rgb = table[material].color_rgb if material in table else (255, 0, 255)
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def _ortho_rects(p: Primitive, view: str) -> tuple[list[tuple[float, float]], float]:
    """A primitive's outline in one orthographic view (front: x-z, side: y-z, top: x-y), and its draw depth."""
    (x0, y0, z0), (x1, y1, z1) = p.bounds_m
    if view == "top" and isinstance(p, Cylinder):
        cx, cy = p.center_xy_m
        n = 24
        pts = [
            (cx + p.radius_m * math.cos(2 * math.pi * k / n), cy + p.radius_m * math.sin(2 * math.pi * k / n))
            for k in range(n)
        ]
        return pts, z1
    if view == "front":
        return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], -y0
    if view == "side":
        return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], -x0
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1


def _iso(x: float, y: float, z: float) -> tuple[float, float]:
    return (x - y) * _COS30, (x + y) * _SIN30 - z


def _iso_faces(p: Primitive) -> list[list[tuple[float, float]]]:
    """The visible faces (top, +x, +y) of a box, or a 24-sided prism standing for a cylinder."""
    if isinstance(p, Box):
        (x0, y0, z0), (x1, y1, z1) = p.min_m, p.max_m
        return [
            [_iso(x0, y0, z1), _iso(x1, y0, z1), _iso(x1, y1, z1), _iso(x0, y1, z1)],
            [_iso(x1, y0, z0), _iso(x1, y1, z0), _iso(x1, y1, z1), _iso(x1, y0, z1)],
            [_iso(x0, y1, z0), _iso(x1, y1, z0), _iso(x1, y1, z1), _iso(x0, y1, z1)],
        ]
    assert isinstance(p, Cylinder)
    (cx, cy), r, (z0, z1), n = p.center_xy_m, p.radius_m, p.z_m, 24
    ring = [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    sides = [
        [_iso(*ring[k], z0), _iso(*ring[(k + 1) % n], z0), _iso(*ring[(k + 1) % n], z1), _iso(*ring[k], z1)]
        for k in range(n)
        if ring[k][0] + ring[k][1] + ring[(k + 1) % n][0] + ring[(k + 1) % n][1] >= 2 * (cx + cy)
    ]
    return [*sides, [_iso(x, y, z1) for x, y in ring]]


def _fit(polys: list[tuple[list[tuple[float, float]], str]], ox: float, oy: float, flip_y: bool) -> list[str]:
    xs = [x for pts, _ in polys for x, _ in pts]
    ys = [y for pts, _ in polys for _, y in pts]
    if not xs:
        return []
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
    scale = (PANEL - 20) / span
    out = []
    for pts, fill in polys:
        coords = []
        for x, y in pts:
            sx = ox + 10 + (x - min(xs)) * scale
            sy = oy + 10 + ((max(ys) - y) if flip_y else (y - min(ys))) * scale
            coords.append(f"{sx:.1f},{sy:.1f}")
        out.append(f'<polygon points="{" ".join(coords)}" fill="{fill}" stroke="black" stroke-width="0.8"/>')
    return out


def svg(prims: Sequence[Primitive]) -> str:
    """The four views of one spec, as an SVG document."""
    body: list[str] = []
    for k, view in enumerate(("front", "side", "top")):
        drawn = sorted(((*_ortho_rects(p, view), _colour(p.material)) for p in prims), key=lambda t: t[1])
        body += _fit([(pts, fill) for pts, _, fill in drawn], (k % 2) * PANEL, (k // 2) * PANEL, flip_y=True)
        body.append(f'<text x="{(k % 2) * PANEL + 12}" y="{(k // 2) * PANEL + 16}" font-size="12">{view}</text>')
    iso = sorted(prims, key=lambda p: sum(p.centroid_m))
    faces = [(face, _colour(p.material)) for p in iso for face in _iso_faces(p)]
    body += _fit(faces, PANEL, PANEL, flip_y=False)
    body.append(f'<text x="{PANEL + 12}" y="{PANEL + 16}" font-size="12">isometric</text>')
    size = 2 * PANEL
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size:g}" height="{size:g}" '
        f'viewBox="0 0 {size:g} {size:g}"><rect width="100%" height="100%" fill="white"/>{"".join(body)}</svg>\n'
    )


def write_sets(out_dir: Path, rng: np.random.Generator, entries: list[dict[str, Any]], texts: Mapping[str, str]) -> int:
    """Blind the entries with ``rng``, write each passing spec's render and the owner's sheet, and the key apart.
    Each entry carries its item, `m1_pass` and `prims` (authored primitives, or None). Returns the renders written."""
    for existing in (out_dir / "sheet.jsonl", out_dir / "key" / "key.jsonl"):
        if existing.exists():  # the owner may be labelling this sheet: never rewrite it
            raise FileExistsError(f"{existing} exists; label it, or move it aside to draw a new sheet")
    order = rng.permutation(len(entries)).tolist()
    (out_dir / "renders").mkdir(parents=True, exist_ok=True)
    (out_dir / "key").mkdir(parents=True, exist_ok=True)
    sheet, key, rendered = [], [], 0
    for rank, i in enumerate(order):
        e, rid = entries[i], f"r{rank + 1:03d}"
        key.append({"id": rid, **e["item"], "m1_pass": e["m1_pass"]})
        if e["m1_pass"] and e["prims"]:
            (out_dir / "renders" / f"{rid}.svg").write_text(svg(e["prims"]), encoding="utf-8")
            row: dict[str, Any] = {"id": rid, "prompt": texts[e["item"]["prompt_id"]], "label": None}
            if e["item"]["set"] == "m8":  # M8 asks a different question: is this the closest object that fits?
                row["question"] = "closest fit"
            sheet.append(row)
            rendered += 1
    _jsonl(out_dir / "sheet.jsonl", sheet)
    _jsonl(out_dir / "key" / "key.jsonl", key)
    return rendered


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
