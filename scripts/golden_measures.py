"""The rendered checks that measure a property rather than match a picture (client_rendering.md §2, §6.3, §6.4; B7).

Unlike a golden, none of these depends on the build that drew the frames: a ratio of a body's pixels, or a brightness
difference over a mask, comes out the same on any correct renderer. So they run wherever the frames are drawn, and
fail on the owner's Mac as they would in CI.

- **The cut-away** (§2): the player's ID-colour pixels with the walls the rule left standing, divided by the same with
  every flagged wall cut away (the crate and floor still drawn), must be at least 95% at every sample position and
  yaw, and every expected (sample, yaw) pair must be there. The reference keeps the never-cut crate, so its honest
  occlusion counts on both sides and the ratio measures only what the walls hide (owner decision, 2026-11-21).
- **Never colour alone** (§6.4, CLAUDE.md), at every tier: measured in CIE L*, lightness, which is what a viewer with
  no colour vision still sees. Over the cells a crack mask marks, the cracked frame must differ from the cold one by a
  mean of at least 8 L* and have at least twice its Sobel edge density (crack changes *shape*). Over the glow mask,
  the glowing frame must be at least 15 L* brighter (glow changes *brightness*). The masks come from the shader's own
  debug passes, so they mark exactly the pixels whose first drawn cell is cracked or glowing.
- **No speckle:** on the cold frames (laptop's averaged 2 x 2, since it draws at half scale), no pixel may differ
  sharply from eight neighbours that agree with each other. A cold frame has no cracks, so such a pixel is a
  traversal defect (a missed or mis-shaded cell): the walk's brick jump once put 52 in each cold rig frame (47 in its
  fire golden), and the golden ΔE judge passed them.
- **Same apart from detail** (§6.3): each tier's frame, box-filtered to 160 x 90, against the rig tier's: mean ΔE at
  most 3 and the 99th percentile at most 10. (§6.3's ID-mask areas are not measured yet.)

scripts/golden_run.py draws the frames and calls these.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from golden_compare import Rgb, delta_e76, load_rgb, srgb_to_lab
from numpy.typing import NDArray
from scipy import ndimage

CUTAWAY_MIN = 0.95
CRACK_MIN_L = 8.0
CRACK_MIN_EDGE_RATIO = 2.0
GLOW_MIN_L = 15.0
AGREE_SIZE = (160, 90)
AGREE_MEAN_MAX = 3.0
AGREE_P99_MAX = 10.0
# A Sobel gradient magnitude above this many L* per pixel is an edge: a few just-noticeable differences (ΔE about 1).
# 20 was tried first and refused every edge on the dark crate, whose whole cold range is about 16 L*.
EDGE_L = 5.0
# Speckle: a pixel whose RGB sum is this far from its neighbours' median, where the neighbours span at most FLAT_SPAN.
SPECKLE_DIFF = 30
FLAT_SPAN = 6
# laptop draws at half scale, so a defect there is a 2 x 2 block: it is judged on the frame averaged down 2 x 2.
SPECKLE_TIERS = {"laptop": 2, "rig": 1, "max": 1}
CUT_FRAME = re.compile(r"^cut-(?P<sample>.+)-k(?P<k>[0-3])-with\.png$")
# client/tests/cutaway_check.gd::SAMPLES, which tests/test_golden_measures.py holds to this list.
CUTAWAY_SAMPLES = (
    "south-2", "south-4", "south-7.5", "south-10.5", "north-2", "north-4", "north-7.5", "north-10.5", "end",
    "crate-kindle", "crate-south", "crate-east", "pavement-spawn", "pavement-south", "pavement-north",
    "pavement-strip-south", "pavement-strip-north",
)  # fmt: skip
TIERS = ("laptop", "rig", "max")

Mask = NDArray[np.bool_]
Floats = NDArray[np.float64]


def lightness(rgb: Rgb) -> Floats:
    out: Floats = srgb_to_lab(rgb)[..., 0]
    return out


def body_pixels(rgb: Rgb) -> int:
    """Pixels in the body's ID colour, pure red, thresholded at half so filtering at the silhouette doesn't count."""
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    return int(np.count_nonzero((r > 127) & (g < 128) & (b < 128)))


def mask_of(rgb: Rgb) -> Mask:
    out: Mask = rgb.astype(np.int32).sum(axis=-1) > 3 * 127
    return out


def cutaway_findings(frames: Path) -> list[str]:
    """Findings for the cut-<sample>-k<k>-with.png / -without.png pairs in ``frames``: a missing, extra or half pair,
    and a pair below CUTAWAY_MIN."""
    found: list[str] = []
    seen = {(m["sample"], int(m["k"])): p for p in frames.iterdir() if (m := CUT_FRAME.match(p.name))}
    expected = {(sample, k) for sample in CUTAWAY_SAMPLES for k in range(4)}
    found += [f"cutaway: no frames for {s} at step {k}" for s, k in sorted(expected - seen.keys())]
    found += [f"cutaway: frames for {s} at step {k}, which is not a sample" for s, k in sorted(seen.keys() - expected)]
    for pair in sorted(expected & seen.keys()):
        line = _pair_finding(seen[pair])
        if line is not None:
            found.append(line)
    return found


def _pair_finding(with_path: Path) -> str | None:
    without_path = with_path.with_name(with_path.name.replace("-with.png", "-without.png"))
    if not without_path.is_file():
        return f"cutaway: {with_path.name} has no -without.png beside it"
    without = body_pixels(load_rgb(without_path))
    if without == 0:
        return f"cutaway: {with_path.name}: the body draws no pixels even with the volume hidden"
    ratio = body_pixels(load_rgb(with_path)) / without
    if ratio < CUTAWAY_MIN:
        return f"cutaway: {with_path.name}: {ratio:.1%} of the body visible, below {CUTAWAY_MIN:.0%}"
    return None


def edge_density(lstar: Floats, mask: Mask) -> float:
    """The fraction of ``mask``'s pixels where the L* gradient (Sobel) exceeds EDGE_L."""
    magnitude = np.hypot(ndimage.sobel(lstar, axis=0), ndimage.sobel(lstar, axis=1)) / 8.0
    return float(np.count_nonzero((magnitude > EDGE_L) & mask)) / max(1, int(np.count_nonzero(mask)))


def crack_findings(cold: Rgb, cracked: Rgb, mask: Mask) -> list[str]:
    if not mask.any():
        return ["crack: the crack mask marks no pixels"]
    l_cold, l_cracked = lightness(cold), lightness(cracked)
    out = []
    change = float(np.abs(l_cracked - l_cold)[mask].mean())
    if change < CRACK_MIN_L:
        out.append(f"crack: mean |ΔL*| over cracked cells is {change:.1f}, below {CRACK_MIN_L}")
    before, after = edge_density(l_cold, mask), edge_density(l_cracked, mask)
    if after < CRACK_MIN_EDGE_RATIO * before or after == 0.0:
        out.append(f"crack: edge density {after:.3f} is not {CRACK_MIN_EDGE_RATIO}x the cold frame's {before:.3f}")
    return out


def glow_findings(cold: Rgb, glowing: Rgb, mask: Mask) -> list[str]:
    if not mask.any():
        return ["glow: the glow mask marks no pixels"]
    gain = float((lightness(glowing) - lightness(cold))[mask].mean())
    return [] if gain >= GLOW_MIN_L else [f"glow: glowing cells are {gain:.1f} L* brighter, below {GLOW_MIN_L}"]


def box_filter(rgb: Rgb, size: tuple[int, int] = AGREE_SIZE) -> Rgb:
    """``rgb`` averaged over equal blocks down to ``size`` (width, height); the frame must divide evenly."""
    h, w = rgb.shape[:2]
    bw, bh = w // size[0], h // size[1]
    if bw * size[0] != w or bh * size[1] != h:
        raise ValueError(f"a {w}x{h} frame doesn't divide into {size[0]}x{size[1]} blocks")
    blocks = rgb.reshape(size[1], bh, size[0], bw, 3).astype(np.float64).mean(axis=(1, 3))
    out: Rgb = np.round(blocks).astype(np.uint8)
    return out


def agreement_findings(name: str, tier: Rgb, rig: Rgb) -> list[str]:
    de = delta_e76(box_filter(tier), box_filter(rig))
    mean, p99 = float(de.mean()), float(np.percentile(de, 99))
    out = []
    if mean > AGREE_MEAN_MAX:
        out.append(f"tiers: {name} against rig: mean ΔE {mean:.2f} > {AGREE_MEAN_MAX}")
    if p99 > AGREE_P99_MAX:
        out.append(f"tiers: {name} against rig: 99th percentile ΔE {p99:.2f} > {AGREE_P99_MAX}")
    return out


def speckle(rgb: Rgb) -> list[tuple[int, int]]:
    """(row, column) of every interior pixel that differs by more than SPECKLE_DIFF (RGB sum) from the median of
    eight neighbours spanning at most FLAT_SPAN."""
    total = rgb.astype(np.int32).sum(axis=-1)
    h, w = total.shape
    ring = np.stack(
        [
            total[1 + dy : h - 1 + dy, 1 + dx : w - 1 + dx]
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0)
        ]
    )
    flat = (ring.max(axis=0) - ring.min(axis=0)) <= FLAT_SPAN
    odd = np.abs(total[1:-1, 1:-1] - np.median(ring, axis=0)) > SPECKLE_DIFF
    return [(int(r) + 1, int(c) + 1) for r, c in zip(*np.nonzero(flat & odd), strict=True)]


def speckle_findings(frames: Path) -> list[str]:
    found = []
    for tier, block in SPECKLE_TIERS.items():
        rgb = load_rgb(frames / f"cold-{tier}.png")
        h, w = rgb.shape[:2]
        dots = speckle(box_filter(rgb, (w // block, h // block)) if block > 1 else rgb)
        if dots:
            found.append(f"{tier}: speckle: {len(dots)} isolated pixel(s) on flat faces, first at {dots[:3]}")
    return found


def colour_alone_findings(frames: Path, tier: str) -> list[str]:
    """§6.4 at ``tier`` over the frames golden_run.py names: cold and fire, and the fire fixture's two masks."""
    cold, fire = load_rgb(frames / f"cold-{tier}.png"), load_rgb(frames / f"fire-{tier}.png")
    found = crack_findings(cold, fire, mask_of(load_rgb(frames / f"fire-{tier}-crack_mask.png")))
    found += glow_findings(cold, fire, mask_of(load_rgb(frames / f"fire-{tier}-glow_mask.png")))
    return [f"{tier}: {f}" for f in found]
