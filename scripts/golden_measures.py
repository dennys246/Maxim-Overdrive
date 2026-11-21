"""The rendered checks that measure a property rather than match a picture (client_rendering.md §2, §6.3, §6.4; B7).

Unlike a golden, none of these depends on the build that drew the frames: a ratio of a body's pixels, or a brightness
difference over a mask, comes out the same on any correct renderer. So they run wherever the frames are drawn, and
fail on the owner's Mac as they would in CI.

- **The cut-away** (§2): the player's ID-colour pixels with the cell volume drawn, divided by the same with it
  hidden, at every sample position and yaw, must be at least 95%. Two samples are reported, not gated: a body pressed
  against the crate's south or east face is hidden by the crate itself (86.7% measured), which §2 never cuts; the
  conflict is the owner's to settle, and every run prints the numbers.
- **Never colour alone** (§6.4, CLAUDE.md): measured in CIE L*, lightness, which is what a viewer with no colour
  vision still sees. Over the cells a crack mask marks, the cracked frame must differ from the cold one by a mean
  of at least 8 L* and have at least twice its Sobel edge density (crack changes *shape*). Over the glow mask, the
  glowing frame must be at least 15 L* brighter (glow changes *brightness*). The masks come from the shader's own
  debug passes, so they mark exactly the pixels whose first drawn cell is cracked or glowing.
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
CUT_FRAME = re.compile(r"^cut-(?P<sample>.+)-k(?P<k>[0-3])-with\.png$")
# Samples where the never-cut crate stands between camera and body at two yaws (§2 "never cut"): reported only.
CUTAWAY_ADVISORY = frozenset({"crate-south", "crate-east"})

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


def cutaway_report(frames: Path) -> tuple[list[str], list[str]]:
    """(findings, notes) for the cut-<sample>-k<k>-with.png / -without.png pairs in ``frames``: a gated sample below
    CUTAWAY_MIN is a finding, an advisory one a note."""
    pairs = sorted(p for p in frames.iterdir() if CUT_FRAME.match(p.name))
    if not pairs:
        return [f"cutaway: no cut-*-with.png frames in {frames}"], []
    found: list[str] = []
    notes: list[str] = []
    for with_path in pairs:
        match = CUT_FRAME.match(with_path.name)
        assert match is not None
        without = body_pixels(load_rgb(with_path.with_name(with_path.name.replace("-with.png", "-without.png"))))
        if without == 0:
            found.append(f"cutaway: {with_path.name}: the body draws no pixels even with the volume hidden")
            continue
        ratio = body_pixels(load_rgb(with_path)) / without
        line = f"cutaway: {with_path.name}: {ratio:.1%} of the body visible, below {CUTAWAY_MIN:.0%}"
        if ratio < CUTAWAY_MIN:
            (notes if match["sample"] in CUTAWAY_ADVISORY else found).append(line)
    return found, notes


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


def colour_alone_findings(frames: Path) -> list[str]:
    """§6.4 over the frames golden_run.py names: cold and fire at the rig tier, and the fire fixture's two masks."""
    cold, fire = load_rgb(frames / "cold-rig.png"), load_rgb(frames / "fire-rig.png")
    found = crack_findings(cold, fire, mask_of(load_rgb(frames / "fire-rig-crack_mask.png")))
    return found + glow_findings(cold, fire, mask_of(load_rgb(frames / "fire-rig-glow_mask.png")))
