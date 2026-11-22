"""The fuel checks (client_objects.md §7.2): burning, char, glow on fuel, burn-through, flame shape and tier agreement
per object, measured on the golden scene's fuel frames.

Each fuel shot writes ``<frame>.segments.json`` beside its PNG: every segment's centre line on screen and its drawn
half-width, from the camera that drew it (client/tests/support/fuel_footprints.gd). A segment's pixels are those inside
that strip which the fuel-ID mask marks, so a thin stick is measured on what it drew, not on the night beside it. The
segments' own values (ignited, charred, burnt, which object) come from the committed fixture (``segments``).
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import golden_compare
import golden_measures as gm
import numpy as np
from numpy.typing import NDArray

FUEL_MIN_L = gm.GLOW_MIN_L  # burning and glow on fuel: brightness, as the cells' glow check (§7.2)
CHAR_MIN_L = gm.CRACK_MIN_L  # char darkening: as the crack check's luminance half
FLAME_ABOVE_SHARE = 0.5  # most flame pixels sit above the segment they rise from
TIER_AREA_MAX = 0.15  # client_rendering.md §6.3's ID-mask areas
# The laptop tier draws at render scale 0.5 and is upscaled, which spreads a thin stick's coverage up to one of its
# pixels (2 output px) past the drawn edge: the area window reaches that far on every tier, so all tiers count alike.
AREA_WINDOW_PX = 2.0
# A live run's width may fall short of its drawn width by one output pixel: the pixel grid's quantization of its
# two edges, half a pixel each (written before measuring).
WIDTH_SLACK_PX = 1.0
HOT_C, COLD_C = 1000.0, 300.0
CHARRED = 230  # char_fraction counts at or above which a cold segment is the burnout check's reference (0.9)
# How far from a burnt-out or burnt-through object a flame pixel counts as its flame: twice FuelPass.FLAME_HEIGHT_M,
# since a segment's run along x and a flame's rise foreshorten differently on screen (test_golden_fuel holds the two).
FLAME_REACH_M = 0.4
# The fuel fixture the fuel shots draw, and the one container version this reader knows (scripts/fuel_fixtures.py
# writes it; a test holds the two together, since the golden image doesn't install the engine that script imports).
FIXTURE_NAME = "fuel_ramp"
FORMAT, VERSION = "overdrive-client-fuel-fixture", 0

Mask = NDArray[np.bool_]
Ints = NDArray[np.int64]


@dataclass(frozen=True)
class Segments:
    """Per segment row: its object's region name and kind, and its state as the fixture holds it."""

    region: list[str]
    kind: list[str]
    segment_m: NDArray[np.float64]
    temperature_c: NDArray[np.float64]
    ignited: Ints
    thickness: Ints
    char: Ints

    def rows(self, region: str, keep: Mask | None = None) -> Ints:
        picked = np.array([r == region for r in self.region])
        return np.flatnonzero(picked if keep is None else picked & keep)


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "client" / "tests" / "fixtures" / "fuel"
FIXTURE = FIXTURES_DIR / f"{FIXTURE_NAME}.json"
# The update pass's second frame (scripts/fuel_fixtures.py's NEXT).
FIXTURE_NEXT = FIXTURES_DIR / f"{FIXTURE_NAME}_next.json"
NUMPY = {"u8": "<u1", "u16": "<u2", "u32": "<u4", "f16": "<f2", "f32": "<f4"}


def segments(fixture: Path = FIXTURE) -> Segments:
    """The committed fixture's segments: the bytes the client drew, read with numpy alone, since the golden image
    doesn't install the engine package."""
    header = cast(dict[str, Any], json.loads(fixture.read_text()))
    if (header.get("format"), header.get("version")) != (FORMAT, VERSION):
        raise ValueError(f"{fixture}: {header.get('format')} v{header.get('version')}, not {FORMAT} v{VERSION}")
    blob = gzip.decompress((fixture.parent / header["data"]).read_bytes())
    if len(blob) != header["data_size"] or hashlib.sha256(blob).hexdigest() != header["data_sha256"]:
        raise ValueError(f"{fixture}: the data's size or digest differs from the header's")
    tables = header["tables"]

    def column(table: str, name: str) -> NDArray[np.generic]:
        entry = tables[table]["columns"][name]
        return np.frombuffer(blob[entry["offset"] : entry["offset"] + entry["size"]], dtype=NUMPY[entry["dtype"]])

    regions = {int(i): name for i, name in header["regions"].items()}
    kinds = {v: k for k, v in header["kinds"].items()}
    counts = column("objects", "segment_count").astype(np.int64)
    region = [regions[int(r)] for r in np.repeat(column("objects", "region_id"), counts)]
    kind = [kinds[int(k)] for k in np.repeat(column("objects", "kind"), counts)]
    segment_m = np.repeat(column("objects", "segment_length_m"), counts).astype(np.float64)
    return Segments(
        region, kind, segment_m, column("segments", "surface_temperature_c").astype(np.float64),
        column("segments", "ignited_fraction").astype(np.int64),
        column("segments", "thickness_fraction").astype(np.int64),
        column("segments", "char_fraction").astype(np.int64),
    )  # fmt: skip


def footprints(png: Path) -> NDArray[np.float64]:
    return np.asarray(json.loads(png.with_suffix(".segments.json").read_text()), dtype=np.float64)


def strip(shape: tuple[int, int], rows: NDArray[np.float64], shrink_px: float = 0.0) -> Mask:
    """The pixels whose centres lie inside any of ``rows``' strips ([ax, ay, bx, by, half_width] each), the strips
    shortened by ``shrink_px`` at both ends."""
    out = np.zeros(shape, dtype=bool)
    for ax, ay, bx, by, half in rows:
        dx, dy = bx - ax, by - ay
        length = float(np.hypot(dx, dy))
        if length <= 2.0 * shrink_px:
            continue
        # Only the strip's own bounding window: a whole-frame grid per segment took minutes over 2,265 segments.
        x0, x1 = max(int(min(ax, bx) - half) - 1, 0), min(int(max(ax, bx) + half) + 2, shape[1])
        y0, y1 = max(int(min(ay, by) - half) - 1, 0), min(int(max(ay, by) + half) + 2, shape[0])
        if x0 >= x1 or y0 >= y1:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float64) + 0.5
        ux, uy = dx / length, dy / length
        along = (xs - ax) * ux + (ys - ay) * uy
        across = np.abs(-(xs - ax) * uy + (ys - ay) * ux)
        out[y0:y1, x0:x1] |= (along >= shrink_px) & (along <= length - shrink_px) & (across <= half)
    return out


def _mean_y(rgb: golden_compare.Rgb, mask: Mask) -> float:
    """Mean linear luminance (CIE Y) of the masked pixels: blending is linear in it, so coverage shares add there."""
    c = rgb[mask].astype(np.float64) / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float((linear @ golden_compare.SRGB_TO_XYZ[1]).mean()) if mask.any() else float("nan")


def _mean_l(rgb: golden_compare.Rgb, mask: Mask) -> float:
    # Only the masked pixels go through Lab: the whole frame took 0.2 s a call, 30 calls a run (review P-N3).
    return float(gm.lightness(rgb[mask][None]).mean()) if mask.any() else float("nan")


@dataclass(frozen=True)
class FuelFrame:
    """One shaded fuel frame, the fuel-ID mask of the same view, and its segments' footprints."""

    rgb: golden_compare.Rgb
    fuel: Mask
    foot: NDArray[np.float64]

    @classmethod
    def load(cls, frames: Path, tier: str, scene: str) -> FuelFrame:
        png = frames / f"fuel-{tier}{scene}.png"
        fuel = gm.mask_of(golden_compare.load_rgb(frames / f"fuel-{tier}-fuel_mask.png"))
        return cls(golden_compare.load_rgb(png), fuel, footprints(png))

    def pixels(self, rows: Ints) -> Mask:
        return strip((self.rgb.shape[0], self.rgb.shape[1]), self.foot[rows]) & self.fuel


def _contrast(name: str, frame: FuelFrame, hi: Ints, lo: Ints, *, bar: float, sign: float) -> list[str]:
    """``hi``'s fuel pixels against ``lo``'s, in L*: brighter by ``bar`` (sign 1) or darker by it (sign -1)."""
    a, b = frame.pixels(hi), frame.pixels(lo)
    if not (a.any() and b.any()):
        return [f"{name}: no pixels to compare ({int(a.sum())} and {int(b.sum())})"]
    change = sign * (_mean_l(frame.rgb, a) - _mean_l(frame.rgb, b))
    return [] if change >= bar else [f"{name}: {change:.1f} L*, below {bar}"]


def state_findings(frames: Path, tier: str, seg: Segments) -> list[str]:
    """Burning, char darkening and glow on fuel, on the frame drawn with flames off (§7.2; S5: a flame's own light
    would otherwise brighten the segments it rises from)."""
    frame = FuelFrame.load(frames, tier, "-noflame")
    lit, unlit = seg.rows("rod_lit", seg.ignited == 255), seg.rows("rod_lit", seg.ignited == 0)
    found = _contrast(f"burning ({tier})", frame, lit, unlit, bar=FUEL_MIN_L, sign=1.0)
    for region in ("rod_burnt", "slab_char"):
        live = seg.thickness == 255
        hi, lo = seg.rows(region, live & (seg.char >= 128)), seg.rows(region, live & (seg.char <= 25))
        found += _contrast(f"char on {region} ({tier})", frame, hi, lo, bar=CHAR_MIN_L, sign=-1.0)
    hot, cold = seg.rows("stick_glow", seg.temperature_c >= HOT_C), seg.rows("stick_glow", seg.temperature_c <= COLD_C)
    return found + _contrast(f"glow on fuel ({tier})", frame, hot, cold, bar=FUEL_MIN_L, sign=1.0)


def burn_through_findings(frames: Path, tier: str, seg: Segments) -> list[str]:
    """No fuel pixel inside the burnt run, its strip shortened at each end by the drawn half-width (the live
    neighbours' round ends reach that far); every live segment of that rod draws, and each run of them at its
    drawn width (owner, 2026-11-22: the width clause restored, ends excluded)."""
    png = frames / f"fuel-{tier}-fuel_mask.png"
    rgb = golden_compare.load_rgb(png)
    fuel, foot = gm.mask_of(rgb), footprints(png)
    burnt = seg.rows("rod_burnt", seg.thickness == 0)
    run = np.array([[*foot[burnt[0], :2], *foot[burnt[-1], 2:4], foot[burnt[0], 4]]])
    inside = int((strip(fuel.shape, run, shrink_px=float(run[0, 4])) & fuel).sum())
    found = [] if inside == 0 else [f"burn-through ({tier}): {inside} fuel pixels inside the burnt run"]
    # A rod's visible surface sits up to its projected radius off the axis these strips follow, so a live segment
    # within that distance of the run's ends shows the burnt run's (discarded) surface: those are ambiguous by
    # geometry, and only the others must draw.
    ends = foot[[burnt[0], burnt[-1]]][:, :4].reshape(-1, 2)
    clear = [int(r) for r in seg.rows("rod_burnt", seg.thickness > 0) if _distance(foot[r], ends) > foot[r, 4]]
    silent = [r for r in clear if not (strip(fuel.shape, foot[[r]]) & fuel).any()]
    found += [f"burn-through ({tier}): live segments {silent} draw nothing"] if silent else []
    return found + _width_findings(tier, rgb[..., 1].astype(np.float64) / 255.0, foot, clear)


def _width_findings(tier: str, coverage: NDArray[np.float64], foot: NDArray[np.float64], rows: list[int]) -> list[str]:
    """Each contiguous run of ``rows`` draws its drawn width, less WIDTH_SLACK_PX: its summed coverage within its
    strips widened by AREA_WINDOW_PX, divided by its length on screen."""
    if not rows:
        return []  # no live segment clear of the burnt run's ends: nothing to measure
    found = []
    for run in np.split(np.array(rows), np.flatnonzero(np.diff(rows) != 1) + 1):
        strips = foot[run].copy()
        strips[:, 4] += AREA_WINDOW_PX
        length = float(np.hypot(foot[run, 2] - foot[run, 0], foot[run, 3] - foot[run, 1]).sum())
        width = float((coverage * strip(coverage.shape, strips)).sum()) / length
        drawn = 2.0 * float(foot[run[0], 4])
        if width < drawn - WIDTH_SLACK_PX:
            found.append(
                f"burn-through ({tier}): live run {int(run[0])}-{int(run[-1])} draws {width:.2f} px, not {drawn:.2f}"
            )
    return found


def _distance(row: NDArray[np.float64], points: NDArray[np.float64]) -> float:
    """The least distance in pixels from either end of a segment's strip to any of ``points``."""
    ends = np.array([[row[0], row[1]], [row[2], row[3]]])
    gaps = ends[:, None, :] - points[None, :, :]
    return float(np.min(np.hypot(gaps[..., 0], gaps[..., 1])))


def flame_findings(frames: Path, tier: str, seg: Segments) -> list[str]:
    """Flames add shape (pixels where fuel isn't, mostly above the segments they rise from) and brightness."""
    flame = gm.mask_of(golden_compare.load_rgb(frames / f"fuel-{tier}-flame_mask.png"))
    if not flame.any():
        return [f"flame shape ({tier}): the flame mask marks no pixels"]
    foot = footprints(frames / f"fuel-{tier}-flame_mask.png")
    lit = seg.rows("rod_lit", seg.ignited == 255)
    lowest = float(np.max(foot[lit][:, [1, 3]]))  # screen y grows downwards: the strip's lowest point
    above = float((np.nonzero(flame)[0] < lowest).mean())
    found = [] if above >= FLAME_ABOVE_SHARE else [f"flame shape ({tier}): {above:.0%} of flame pixels above the fuel"]
    shaded = golden_compare.load_rgb(frames / f"fuel-{tier}.png")
    noflame = golden_compare.load_rgb(frames / f"fuel-{tier}-noflame.png")
    gain = _mean_l(shaded, flame) - _mean_l(noflame, flame)
    return found + (
        [] if gain >= FUEL_MIN_L else [f"flame shape ({tier}): {gain:.1f} L* over the flames, below {FUEL_MIN_L}"]
    )


def burnout_findings(frames: Path, tier: str, seg: Segments) -> list[str]:
    """A burnt-out object draws without glow or burning (§4.3): rod_spent, still at 1,200 °C and reporting ignition, is
    no brighter, flames off, than rod_burnt's cold charred segments, by less than the glow check's own bar."""
    frame = FuelFrame.load(frames, tier, "-noflame")
    spent = seg.rows("rod_spent")
    cold = seg.rows("rod_burnt", (seg.thickness == 255) & (seg.char >= CHARRED) & (seg.temperature_c <= COLD_C))
    a, b = frame.pixels(spent), frame.pixels(cold)
    if not (a.any() and b.any()):
        return [f"burnout ({tier}): no pixels to compare ({int(a.sum())} and {int(b.sum())})"]
    gain = _mean_l(frame.rgb, a) - _mean_l(frame.rgb, b)
    return [] if gain < FUEL_MIN_L else [f"burnout ({tier}): rod_spent glows {gain:.1f} L* over cold char"]


def dead_flame_findings(frames: Path, tier: str, seg: Segments) -> list[str]:
    """No flame rises from a burnt-out object or a burnt-through segment (§4.3), however ignited they report: no
    flame-ID pixel within FLAME_REACH_M of rod_spent or of rod_gap (whose only ignited segments are burnt through)."""
    png = frames / f"fuel-{tier}-flame_mask.png"
    flame, foot = gm.mask_of(golden_compare.load_rgb(png)), footprints(png)
    found = []
    for region in ("rod_spent", "rod_gap"):
        rows = seg.rows(region)
        run_px = np.hypot(foot[rows, 2] - foot[rows, 0], foot[rows, 3] - foot[rows, 1])
        px_per_m = float(np.median(run_px / seg.segment_m[rows]))
        near = foot[rows].copy()
        near[:, 4] += FLAME_REACH_M * px_per_m
        count = int((strip(flame.shape, near) & flame).sum())
        if count:
            found.append(f"dead flames ({tier}): {count} flame pixels at {region}")
    return found


# (front, behind): a hot thin stick and what it lies over. The first pair is two rods, the log later in row order
# (review C-S1, D1); the second a stick resting on the plank, which the slab's floor must not bury (C-S4).
FADE_PAIR = ("stick_cross", "log_cross")  # the pair whose outer fade is measured: two rods, so a fade and a core meet
CROSSINGS = (FADE_PAIR, ("stick_on_slab", "slab_leaning"))
# The outer fade over the log, in linear light, must add at least this share of the stick's own gain there (owner
# ruling 8, 2026-11-22, derived from the coverage model; the old L* bar's proof numbers were known when it was written).
# Coverage falls from 0.5 at the drawn edge to 0 half a rendered pixel past it, so the one-pixel band averages 1/8;
# inside the floored 2 px stick it rises from 0.5 to 1 over half a pixel, so the strip averages 7/8. An intact fade
# adds 1/7 of the stick's gain and an overwritten one none; the bar is half of 1/7. Measured, the intact share is
# 0.396 on llvmpipe, above the model (probably the hot stick's bloom; not separated by measurement), so the bar is a
# floor, not a fit.
FADE_SHARE = 1.0 / 14.0
# Laptop's upscale smears the stick's core into the band, which a measure at output pixels can't separate: unchecked
# there until a laptop measure is derived (docs/plans/checklists.md step 8).
FADE_TIERS = ("rig", "max")


def crossing_findings(frames: Path, tier: str, seg: Segments) -> list[str]:
    """Depth, not draw order, decides who occludes whom: where each pair's hot stick lies over the other object, its
    pixels are brighter than that object's own by the glow bar, flames off; and the rod pair's outer fade, one
    rendered pixel past the stick's drawn edge, blends over the log rather than under it (every rod's core draws before
    any rod's fade), judged on FADE_TIERS."""
    frame = FuelFrame.load(frames, tier, "-noflame")
    found = []
    for front, behind in CROSSINGS:
        stick, under = frame.pixels(seg.rows(front)), frame.pixels(seg.rows(behind))
        over, bare = stick & under, under & ~stick
        if not (over.any() and bare.any()):
            found.append(
                f"crossing ({tier}): no pixels to compare at {front} ({int(over.sum())} and {int(bare.sum())})"
            )
            continue
        gain = _mean_l(frame.rgb, over) - _mean_l(frame.rgb, bare)
        if gain < FUEL_MIN_L:
            found.append(f"crossing ({tier}): {front} over {behind} shows {gain:.1f} L*, below {FUEL_MIN_L}")
        elif (front, behind) == FADE_PAIR and tier in FADE_TIERS:
            found += _fringe_findings(frame, tier, seg, over, bare)
    return found


def _fringe_findings(frame: FuelFrame, tier: str, seg: Segments, over: Mask, under: Mask) -> list[str]:
    """The stick's outer fade band (past its drawn half-width by one rendered pixel) inside the log's strip, against
    the stick's own gain over the log (``over`` against ``under``), both in linear luminance."""
    front, behind = FADE_PAIR
    shape = (frame.rgb.shape[0], frame.rgb.shape[1])
    rows = frame.foot[seg.rows(front)]
    wide = rows.copy()
    wide[:, 4] += gm.SPECKLE_TIERS[tier]  # output pixels per rendered pixel: the fade's width on this tier
    log = strip(shape, frame.foot[seg.rows(behind)]) & frame.fuel
    band = strip(shape, wide) & ~strip(shape, rows) & log
    bare = log & ~strip(shape, wide)
    if not (band.any() and bare.any()):
        return [f"crossing fade ({tier}): no pixels to compare ({int(band.sum())} and {int(bare.sum())})"]
    core_gain = _mean_y(frame.rgb, over) - _mean_y(frame.rgb, under)
    gain = _mean_y(frame.rgb, band) - _mean_y(frame.rgb, bare)
    if gain >= FADE_SHARE * core_gain:
        return []
    share = gain / core_gain  # positive: the caller found the stick brighter than the log by the glow bar
    return [
        f"crossing fade ({tier}): the stick's fade over the log adds {share:.3f} of its gain, below {FADE_SHARE:.3f}"
    ]


def update_findings(frames: Path, tier: str, seg_next: Segments) -> list[str]:
    """The update frame shows the next fixture's segment state, uploaded in place: its glow ramp, reversed from the
    first frame's, reads hot where the next fixture is hot (review E-N2)."""
    frame = FuelFrame.load(frames, tier, "-update")
    hot = seg_next.rows("stick_glow", seg_next.temperature_c >= HOT_C)
    cold = seg_next.rows("stick_glow", seg_next.temperature_c <= COLD_C)
    return _contrast(f"in-place update ({tier})", frame, hot, cold, bar=FUEL_MIN_L, sign=1.0)


def object_areas(frames: Path, tier: str, seg: Segments) -> dict[str, float]:
    """Each object's area, by its region, as summed coverage (0 to 1 per pixel) in its strips widened by
    AREA_WINDOW_PX: area under anti-aliasing, where a threshold would undercount a fringe the half-resolution tier
    spreads. Per object, not per kind: pooled with thick rods and a pile, a thin stick's doubled width on one tier hid
    inside the total, and the floor-in-rendered-pixels deletion passed (deletion proof, 2026-11-22)."""
    png = frames / f"fuel-{tier}-fuel_mask.png"
    # Green: fuel draws white, so every channel carries its coverage, and the bodies' pure-red ID writes none of it.
    coverage = golden_compare.load_rgb(png)[..., 1].astype(np.float64) / 255.0
    foot = footprints(png).copy()
    foot[:, 4] += AREA_WINDOW_PX
    regions = np.array(seg.region)
    return {r: float((coverage * strip(coverage.shape, foot[regions == r])).sum()) for r in sorted(set(seg.region))}


def agreement_findings(frames: Path, seg: Segments) -> list[str]:
    """Each object's fuel-ID area at laptop and max within TIER_AREA_MAX of rig's (§7.2)."""
    rig = object_areas(frames, "rig", seg)
    found = []
    for tier in ("laptop", "max"):
        for region, area in object_areas(frames, tier, seg).items():
            if abs(area - rig[region]) > TIER_AREA_MAX * rig[region]:  # drawn on one tier, absent on rig, fails too
                found.append(
                    f"fuel tier agreement: {region} at {tier} is {area:.0f} px against rig's {rig[region]:.0f}"
                )
    return found


def fuel_findings(frames: Path) -> list[str]:
    seg, seg_next = segments(), segments(FIXTURE_NEXT)
    found: list[str] = []
    for tier in gm.TIERS:
        found += state_findings(frames, tier, seg) + burn_through_findings(frames, tier, seg)
        found += flame_findings(frames, tier, seg) + burnout_findings(frames, tier, seg)
        found += dead_flame_findings(frames, tier, seg) + crossing_findings(frames, tier, seg)
        found += update_findings(frames, tier, seg_next)
    return found + agreement_findings(frames, seg)
