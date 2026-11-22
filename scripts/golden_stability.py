"""The stick-stability measure (client_objects.md §7.2), with step 8's checklist's parameters, fixed before measuring.

A thin stick drawn by a renderer crawls when its covered area per length changes as the camera moves by less than a
pixel. This measures that crawl the same way for a rendered frame and for an ideal anti-aliased line drawn here at the
same projected geometry, so a renderer is judged against what a perfect one achieves, not against a round number.

- Bins are fixed in world space along the stick's axis: each spans the length that projects to ``BIN_PX`` output
  pixels, measured from the stick's projected start, and ``END_BINS`` at each end are dropped (the caps).
- A bin's coverage is the summed coverage (0 to 1) of the pixels whose centres project into it, within the stick's
  half-width plus ``WINDOW_PX`` of its axis.
- Its spread is (max - min) / mean over the camera offsets; the statistic is the 95th percentile over bins.
- The ideal line is a rectangle of the drawn width, rasterised at exact area coverage by ``SUPERSAMPLE`` x
  ``SUPERSAMPLE`` samples per pixel. The bar is the renderer's statistic at most ``BAR_RATIO`` times the ideal's.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import golden_compare
import numpy as np
from numpy.typing import NDArray

BIN_PX = 4.0
END_BINS = 2
WINDOW_PX = 3.0
SUPERSAMPLE = 16
PERCENTILE = 95.0
BAR_RATIO = 2.0
# What stability_check.tscn draws (its TIERS, PX_PER_M and OFFSETS; test_golden_stability holds them together):
# every key must be measured, so a run that measured nothing can't pass.
KEYS = ("laptop-30", "laptop-72", "rig-30", "rig-72")
OFFSETS = 8

Floats = NDArray[np.float64]


@dataclass(frozen=True)
class Axis:
    """The stick's projected axis in output pixels, start to end, for one frame."""

    ax: float
    ay: float
    bx: float
    by: float

    def unit(self) -> tuple[float, float, float]:
        dx, dy = self.bx - self.ax, self.by - self.ay
        length = float(np.hypot(dx, dy))
        return dx / length, dy / length, length


def _along_across(shape: tuple[int, int], axis: Axis, xs: Floats, ys: Floats) -> tuple[Floats, Floats]:
    ux, uy, _ = axis.unit()
    px, py = xs - axis.ax, ys - axis.ay
    return px * ux + py * uy, np.abs(-px * uy + py * ux)


def bin_coverage(coverage: Floats, axis: Axis, width_px: float) -> Floats:
    """Summed coverage per bin along the axis, end bins dropped."""
    h, w = coverage.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64) + 0.5
    along, across = _along_across((h, w), axis, xs, ys)
    _, _, length = axis.unit()
    bins = int(length // BIN_PX)
    near = (across <= width_px / 2.0 + WINDOW_PX) & (along >= 0.0) & (along < bins * BIN_PX)
    index = (along[near] // BIN_PX).astype(np.int64)
    sums = np.bincount(index, weights=coverage[near], minlength=bins)
    return sums[END_BINS : bins - END_BINS]


def ideal_coverage(shape: tuple[int, int], axis: Axis, width_px: float) -> Floats:
    """A rectangle of ``width_px`` along the axis at exact area coverage, by SUPERSAMPLE^2 samples per pixel. Only a
    window around the axis is sampled; everything else is 0."""
    h, w = shape
    out = np.zeros(shape, dtype=np.float64)
    x0 = max(int(min(axis.ax, axis.bx) - width_px - 2), 0)
    x1 = min(int(max(axis.ax, axis.bx) + width_px + 2), w)
    y0 = max(int(min(axis.ay, axis.by) - width_px - 2), 0)
    y1 = min(int(max(axis.ay, axis.by) + width_px + 2), h)
    offsets = (np.arange(SUPERSAMPLE) + 0.5) / SUPERSAMPLE
    _, _, length = axis.unit()
    for oy in offsets:
        for ox in offsets:
            ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float64)
            along, across = _along_across(shape, axis, xs + ox, ys + oy)
            inside = (across <= width_px / 2.0) & (along >= 0.0) & (along <= length)
            out[y0:y1, x0:x1] += inside
    return out / SUPERSAMPLE**2


def spread_statistic(per_offset: list[Floats]) -> float:
    """The PERCENTILE over bins of (max - min) / mean across offsets."""
    stack = np.vstack(per_offset)
    mean = stack.mean(axis=0)
    spread = (stack.max(axis=0) - stack.min(axis=0)) / np.where(mean > 0.0, mean, np.inf)
    return float(np.percentile(spread, PERCENTILE))


def stability(frames: list[Floats], axes: list[Axis], width_px: float) -> tuple[float, float]:
    """The renderer's statistic over ``frames`` (coverage images, one per offset, with their axes), and the ideal
    line's at the same geometry."""
    shape = (int(frames[0].shape[0]), int(frames[0].shape[1]))
    rendered = [bin_coverage(f, a, width_px) for f, a in zip(frames, axes, strict=True)]
    ideal = [bin_coverage(ideal_coverage(shape, a, width_px), a, width_px) for a in axes]
    return spread_statistic(rendered), spread_statistic(ideal)


def passes(rendered: float, ideal: float) -> bool:
    return rendered <= BAR_RATIO * ideal


def findings(frames: Path) -> list[str]:
    """The stick-stability check (client_objects.md §7.2) on stability_check.tscn's frames: each tier and zoom within
    BAR_RATIO of an ideal line at the same geometry. A missing record or frame is a finding."""
    record = frames / "stability.json"
    if not record.is_file():
        return [f"stick stability: no {record}"]
    meta = json.loads(record.read_text())
    if tuple(sorted(meta)) != KEYS:
        return [f"stick stability: measured {sorted(meta)}, not {list(KEYS)}"]
    found = []
    for key, entry in sorted(meta.items()):
        pngs = [frames / f"stab-{key}-{k}.png" for k in range(len(entry["ends"]))]
        missing = [p.name for p in pngs if not p.is_file()]
        if len(pngs) != OFFSETS or missing:
            found.append(f"stick stability ({key}): {len(pngs)} offsets, missing {missing}")
            continue
        images = [golden_compare.load_rgb(p)[..., 0].astype(np.float64) / 255.0 for p in pngs]
        axes = [Axis(*ends) for ends in entry["ends"]]
        rendered, ideal = stability(images, axes, entry["drawn_px"])
        if not passes(rendered, ideal):
            ratio = f"{rendered / ideal:.2f}x the ideal line" if ideal > 0 else f"{rendered:.3f} against an ideal of 0"
            found.append(f"stick stability ({key}): {ratio}, past {BAR_RATIO}x")
    return found
