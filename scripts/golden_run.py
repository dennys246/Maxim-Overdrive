"""Render the goldens and the rendered checks, and judge them (client_rendering.md §2, §6; B7, T12). The golden job.

It runs inside the golden image (ci/godot-golden/run.sh), and reuses the gate's own Godot handling so the two can't
drift (S2A-S1): ``godot_check.run_godot`` (per-user directories in the work directory, an outer timeout) and its
scans. Godot's exit status is never trusted alone.

1. A copy of client/, as a fresh checkout has it, is imported headless (``godot_check.import_step``), so a scene may
   use any ``class_name`` and imported asset (S2E-S1).
2. Each scene is drawn under Xvfb with the §6.5 command; any error line, a timeout, a non-zero exit or a missing PNG
   fails it. ``client/tests/golden.tscn`` draws ``SHOTS`` from the snapshot fixtures; ``cutaway_check.tscn`` draws
   the cut-away pairs.
3. The judges: each tier's shaded frame against its golden (``golden_compare.judge``, keyed by the build the log
   names), and the measured checks (``golden_measures``): the cut-away, never colour alone, and tier agreement.
   The measured checks hold on any renderer, so the owner's Mac runs them too; only the goldens are CI's alone.

The frames, logs and ΔE images land in ``--out``, which CI keeps as an artifact, so a new golden comes from CI's own
output. ``--no-xvfb`` draws in the current display instead (the owner's Mac, advisory: its log names no llvmpipe, so
the golden judge refuses it, but every frame is written and the measured checks run).

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
import golden_measures as gm

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
GOLDENS = CLIENT / "tests" / "goldens"
# Xvfb is an X server that draws into memory: Godot's Linux build has no surfaceless GL mode, so it needs a display.
XVFB = ("xvfb-run", "-a", "-s", "-screen 0 1280x720x24")
DRAW = (
    "--audio-driver", "Dummy", "--rendering-driver", "opengl3", "--rendering-method", "gl_compatibility",
    "--fixed-fps", "60", "--resolution", "1280x720",
)  # fmt: skip
GOLDEN_SCENE = "res://tests/golden.tscn"
CUTAWAY_SCENE = "res://tests/cutaway_check.tscn"
TIERS = ("laptop", "rig", "max")
# (frame name, fixture, tier, pass): every tier's shaded fire frame is a golden; the cold frame and the masks feed
# the never-colour-alone check.
SHOTS = (
    *((f"fire-{tier}.png", "alley_fire", tier, "shaded") for tier in TIERS),
    ("cold-rig.png", "alley_cold", "rig", "shaded"),
    ("fire-rig-crack_mask.png", "alley_fire", "rig", "crack_mask"),
    ("fire-rig-glow_mask.png", "alley_fire", "rig", "glow_mask"),
)


def draw(
    godot: str, project: Path, scene: str, user_args: list[str], *, home: Path, timeout_s: float,
    wrapper: tuple[str, ...],
) -> tuple[list[str], str]:  # fmt: skip
    """Draw one scene with ``user_args`` after ``--``; returns (findings, log)."""
    args = [*DRAW, "--path", str(project), scene, "--", *user_args]
    run = gc.run_godot(godot, f"draw {scene}", args, home=home, timeout_s=timeout_s, wrapper=wrapper)
    return gc.error_findings(run) + gc.exit_findings(run), "\n".join(run.lines)


def golden_findings(log: str, out: Path) -> list[str]:
    """Each tier's shaded frame against ``goldens/<build key>/<tier>/fire.png``."""
    found = []
    for tier in TIERS:
        png = out / f"fire-{tier}.png"
        found += golden_compare.judge(log, png, GOLDENS, f"{tier}/fire.png", png.with_suffix(".diff.png"))
    return found


def measured_findings(out: Path, cut: Path) -> list[str]:
    """The checks that hold on any renderer: cut-away, never colour alone, tier agreement. Notes are printed."""
    found, notes = gm.cutaway_report(cut)
    for note in notes:
        print(f"golden_run: advisory: {note}")
    found += gm.colour_alone_findings(out)
    rig = golden_compare.load_rgb(out / "fire-rig.png")
    for tier in TIERS:
        if tier != "rig":
            found += gm.agreement_findings(tier, golden_compare.load_rgb(out / f"fire-{tier}.png"), rig)
    return found


def draw_all(
    godot: str, project: Path, out: Path, *, home: Path, timeout_s: float, wrapper: tuple[str, ...]
) -> tuple[list[str], str]:
    """Both scenes; returns (findings, the golden scene's log)."""
    shots = [f"--shot={fixture}:{tier}:{kind}:{out / name}" for name, fixture, tier, kind in SHOTS]
    found, log = draw(godot, project, GOLDEN_SCENE, shots, home=home, timeout_s=timeout_s, wrapper=wrapper)
    (out / "golden.log").write_text(log + "\n")
    cut = out / "cutaway"
    cut.mkdir(exist_ok=True)
    cut_found, cut_log = draw(
        godot, project, CUTAWAY_SCENE, [f"--out={cut}"], home=home, timeout_s=timeout_s, wrapper=wrapper
    )
    (out / "cutaway.log").write_text(cut_log + "\n")
    print(log)
    found += cut_found
    found += [f"draw: no frame at {out / name}" for name, *_ in SHOTS if not found and not (out / name).is_file()]
    return found, log


def golden_job(godot: str, *, work: Path, out: Path, timeout_s: float, wrapper: tuple[str, ...]) -> list[str]:
    home, project = work / "home", gc.copy_project(CLIENT, work / "client")
    found = gc.import_step(godot, CLIENT, project, home=home, timeout_s=timeout_s)
    if found:
        return found
    found, log = draw_all(godot, project, out, home=home, timeout_s=timeout_s, wrapper=wrapper)
    if found:
        return found
    return golden_findings(log, out) + measured_findings(out, out / "cutaway")


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
    print(f"golden_run: {'FAIL' if found else 'PASS'} ({len(SHOTS)} shots, {len(TIERS)} goldens, cut-away)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
