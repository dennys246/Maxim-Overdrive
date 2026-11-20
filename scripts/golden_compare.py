"""Compare a rendered frame with its committed golden (client_rendering.md §6.2, §6.5; B7).

The metric is CIE76 ΔE, the Euclidean distance in CIELAB, where a difference of about 1 is the smallest a viewer
notices. A frame passes when the mean ΔE is at most 1.0, the 99.5th percentile at most 4.0, and no 4-connected blob of
pixels with ΔE above 10 is larger than 64 px. The blob rule catches a small object that moved or vanished, which the
mean and the percentile average away.

Goldens are keyed by the renderer that drew them, ``compat-llvmpipe-mesa<mesa>-godot<godot>``, read from the run's own
log rather than from configuration, so a Mesa or Godot bump can never be compared with goldens another build drew. A
run on anything but llvmpipe at a 256-bit vector width is refused: that is the pinned CI rasterizer (CR-B3).

Run: ``python scripts/golden_compare.py --log <godot log> --actual <png> --goldens <dir> --name <tier>/<frame>.png``
(exit 1 on any finding; ``--diff <png>`` writes a ΔE image for a failed run).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy import ndimage

MEAN_MAX = 1.0
P995_MAX = 4.0
BLOB_DE = 10.0
BLOB_PX_MAX = 64
VECTOR_BITS = 256

GODOT_LINE = re.compile(r"^Godot Engine v(\d+\.\d+\.\d+)\.")
RENDERER_LINE = re.compile(
    r"Mesa (\d+\.\d+\.\d+)\S* - Compatibility - Using Device: .*llvmpipe \(LLVM [^,]+, (\d+) bits\)"
)

# sRGB D65 to linear-light XYZ, and the D65 white point (IEC 61966-2-1; CIE 15).
SRGB_TO_XYZ = np.array(
    [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]]
)
WHITE_D65 = np.array([0.95047, 1.0, 1.08883])

Rgb = NDArray[np.uint8]
Floats = NDArray[np.float64]


def srgb_to_lab(rgb: Rgb) -> Floats:
    """CIELAB (D65) of an ``(h, w, 3)`` 8-bit sRGB image."""
    c = rgb.astype(np.float64) / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = linear @ SRGB_TO_XYZ.T / WHITE_D65
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    lab: Floats = np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
    return lab


def delta_e76(a: Rgb, b: Rgb) -> Floats:
    de: Floats = np.linalg.norm(srgb_to_lab(a) - srgb_to_lab(b), axis=-1)
    return de


def largest_blob(mask: NDArray[np.bool_]) -> int:
    """Pixels in the largest 4-connected region of ``mask`` (scipy's default 2-D structure is the 4-neighbour cross)."""
    labels, count = ndimage.label(mask)
    return int(np.bincount(labels.ravel())[1:].max()) if count else 0


@dataclass(frozen=True)
class Verdict:
    mean: float
    p995: float
    blob_px: int

    def findings(self) -> list[str]:
        out = []
        if self.mean > MEAN_MAX:
            out.append(f"mean ΔE {self.mean:.3f} > {MEAN_MAX}")
        if self.p995 > P995_MAX:
            out.append(f"99.5th percentile ΔE {self.p995:.3f} > {P995_MAX}")
        if self.blob_px > BLOB_PX_MAX:
            out.append(f"a {self.blob_px} px blob with ΔE > {BLOB_DE} (limit {BLOB_PX_MAX} px)")
        return out


def compare(actual: Rgb, golden: Rgb) -> Verdict:
    if actual.shape != golden.shape:
        raise ValueError(f"the frame is {actual.shape}, the golden {golden.shape}")
    de = delta_e76(actual, golden)
    return Verdict(float(de.mean()), float(np.percentile(de, 99.5)), largest_blob(de > BLOB_DE))


def golden_key(log: str) -> str:
    """``compat-llvmpipe-mesa<v>-godot<v>`` from the run's log; refuses any other rasterizer or vector width."""
    godot = next((m.group(1) for line in log.splitlines() if (m := GODOT_LINE.match(line))), None)
    renderer = next((m for line in log.splitlines() if (m := RENDERER_LINE.search(line))), None)
    if godot is None:
        raise ValueError("the log has no 'Godot Engine v<version>' line")
    if renderer is None:
        raise ValueError("the log names no Compatibility renderer on Mesa llvmpipe; goldens are drawn only there")
    if int(renderer.group(2)) != VECTOR_BITS:
        raise ValueError(f"llvmpipe ran at {renderer.group(2)} bits, not {VECTOR_BITS} (LP_NATIVE_VECTOR_WIDTH)")
    return f"compat-llvmpipe-mesa{renderer.group(1)}-godot{godot}"


def load_rgb(path: Path) -> Rgb:
    with Image.open(path) as im:
        rgb: Rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
    return rgb


def write_diff(path: Path, actual: Rgb, golden: Rgb) -> None:
    """ΔE as grey, saturating at the blob threshold, so the eye finds what moved."""
    grey = np.clip(delta_e76(actual, golden) * (255 / BLOB_DE), 0, 255).astype(np.uint8)
    Image.fromarray(grey).save(path)


def run(args: argparse.Namespace) -> list[str]:
    key = golden_key(Path(args.log).read_text())
    golden = Path(args.goldens) / key / args.name
    if not golden.is_file():
        return [f"no golden at {golden}: record one from this run's frame in a commit of its own (§6.5)"]
    actual, expected = load_rgb(Path(args.actual)), load_rgb(golden)
    found = compare(actual, expected).findings()
    if found and args.diff:
        write_diff(Path(args.diff), actual, expected)
    return [f"{golden}: {f}" for f in found]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", required=True, help="Godot's output from the golden run")
    parser.add_argument("--actual", required=True, help="the PNG the run wrote")
    parser.add_argument("--goldens", required=True, help="client/tests/goldens")
    parser.add_argument("--name", required=True, help="<tier>/<frame>.png under the renderer's key")
    parser.add_argument("--diff", help="where to write a ΔE image when the frame fails")
    args = parser.parse_args(argv)
    try:
        found = run(args)
    except ValueError as e:
        found = [str(e)]
    for f in found:
        print(f"golden_compare: {f}", file=sys.stderr)
    print(f"golden_compare: {'FAIL' if found else 'PASS'} {args.name}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
