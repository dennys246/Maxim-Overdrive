"""Render the renderer goldens and judge them (client_rendering.md §6.5; B7, T12). The golden job's whole procedure.

It runs inside the golden image (ci/godot-golden/run.sh), and reuses the gate's own Godot handling so the two can't
drift (S2A-S1): ``godot_check.run_godot`` (per-user directories in the work directory, an outer timeout) and its
scans. Godot's exit status is never trusted alone.

1. A copy of client/, as a fresh checkout has it, is imported headless (``godot_check.import_step``), so a golden
   scene may use any ``class_name`` and imported asset (S2E-S1).
2. Each golden scene is drawn under Xvfb with the §6.5 command; any error line, a timeout, a non-zero exit or a
   missing PNG fails it.
3. ``golden_compare.judge`` compares the frame with the golden keyed by the build the log names.

The frames, logs and ΔE images land in ``--out``, which CI keeps as an artifact, so a new golden comes from CI's own
output. ``--no-xvfb`` draws in the current display instead (the owner's Mac, advisory: its log names no llvmpipe, so
the judge refuses it, but the frame is written).

Run: ``python scripts/golden_run.py --out <dir> [--godot <binary>] [--no-xvfb]`` (exit 1 on any finding).
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import godot_check as gc
import golden_compare

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
GOLDENS = CLIENT / "tests" / "goldens"
# Xvfb is an X server that draws into memory: Godot's Linux build has no surfaceless GL mode, so it needs a display.
XVFB = ("xvfb-run", "-a", "-s", "-screen 0 1280x720x24")
DRAW = (
    "--audio-driver", "Dummy", "--rendering-driver", "opengl3", "--rendering-method", "gl_compatibility",
    "--fixed-fps", "60", "--resolution", "1280x720",
)  # fmt: skip
# (scene, golden name under the build's key). Step 2's frame has no tier, so it sits under renderer/.
SCENES = (("res://tests/golden.tscn", "renderer/boxes.png"),)


def draw(
    godot: str, project: Path, scene: str, png: Path, *, home: Path, timeout_s: float, wrapper: tuple[str, ...]
) -> tuple[list[str], str]:
    """Draw one golden scene into ``png``; returns (findings, log)."""
    args = [*DRAW, "--path", str(project), scene, "--", f"--out={png}"]
    run = gc.run_godot(godot, f"draw {scene}", args, home=home, timeout_s=timeout_s, wrapper=wrapper)
    found = gc.error_findings(run) + gc.exit_findings(run)
    if not found and not png.is_file():
        found.append(f"draw {scene}: no frame at {png}")
    return found, "\n".join(run.lines)


def golden_job(godot: str, *, work: Path, out: Path, timeout_s: float, wrapper: tuple[str, ...]) -> list[str]:
    home, project = work / "home", gc.copy_project(CLIENT, work / "client")
    found = gc.import_step(godot, CLIENT, project, home=home, timeout_s=timeout_s)
    for scene, name in SCENES if not found else ():
        png = out / name.replace("/", "-")
        drawn, log = draw(godot, project, scene, png, home=home, timeout_s=timeout_s, wrapper=wrapper)
        png.with_suffix(".log").write_text(log + "\n")
        print(log)
        found += drawn or golden_compare.judge(log, png, GOLDENS, name, png.with_suffix(".diff.png"))
    return found


def main(argv: list[str] | None = None, *, work_parent: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="where frames, logs and ΔE images go")
    parser.add_argument("--godot", default=None, help="the Godot binary (default: as scripts/godot_check.py finds it)")
    parser.add_argument("--no-xvfb", action="store_true", help="draw in the current display, not under xvfb-run")
    parser.add_argument("--timeout", type=float, default=gc.TIMEOUT_S, help="seconds per Godot call")
    args = parser.parse_args(argv)
    godot = args.godot or gc.find_godot(os.environ, sys.platform)
    if godot is None:
        print("golden_run: FAIL: no Godot; pass --godot or set GODOT", file=sys.stderr)
        return 1
    args.out = args.out.resolve()  # Godot reads a relative path against the project, not this directory
    args.out.mkdir(parents=True, exist_ok=True)
    wrapper = () if args.no_xvfb else XVFB
    with tempfile.TemporaryDirectory(prefix="golden-", dir=work_parent or args.out) as work:
        found = golden_job(godot, work=Path(work), out=args.out, timeout_s=args.timeout, wrapper=wrapper)
    for f in found:
        print(f"golden_run: {f}", file=sys.stderr)
    print(f"golden_run: {'FAIL' if found else 'PASS'} ({len(SCENES)} scene(s))")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
