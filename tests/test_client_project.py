"""The Godot client's settings and pins, read from the files without running Godot (B6, B7; client_rendering.md §7).

- **The renderer** is Compatibility (OpenGL 3.3; T8): the one shader is unshaded, so Forward+ buys little, and
  Compatibility runs on integrated GPUs and on CI's llvmpipe.
- **GDScript, not C#:** no .NET toolchain, and the parse check needs no build (§7.2).
- **Every GDScript warning is an Error** (§7.2, CR-S7), all 49 that Godot 4.7.2 has, so "typed GDScript" fails the
  gate instead of scrolling past. ``directory_rules`` is emptied because 4.7.2's default exempts ``res://addons``,
  where the engine half of the client lives. The client runner's own test reads the live settings, which catches a
  warning a Godot upgrade adds; this one holds the file to the list measured on 4.7.2.
- **stdout is flushed on every print,** so the sentinel line can't be lost behind a buffered one when Godot exits.
- **One Godot pin** (``ci/godot.env``) serves the gate, the CI install and the golden image; the client's own
  ``EnginePin`` must agree with it.
- **The golden image** pins its base by digest, Mesa by package version, and the vector width; CI installs the pinned
  Godot everywhere the gate runs.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
PINS = (ROOT / "ci" / "godot.env").read_text()
DOCKERFILE = (ROOT / "ci" / "godot-golden" / "Dockerfile").read_text()
INSTALLER = ROOT / "ci" / "install_godot.sh"

# Every warning level Godot 4.7.2 has (ProjectSettings, debug/gdscript/warnings/*, integer-valued), measured with
# 4.7.2.stable.official.ed1daf0bf. §7.2 names seven of them; the defaults leave most at Warn or Ignore.
WARNINGS_4_7_2 = frozenset(
    [
        "assert_always_false",
        "assert_always_true",
        "confusable_capture_reassignment",
        "confusable_identifier",
        "confusable_local_declaration",
        "confusable_local_usage",
        "confusable_temporary_modification",
        "constant_used_as_function",
        "deprecated_keyword",
        "empty_file",
        "enum_variable_without_default",
        "function_used_as_property",
        "get_node_default_without_onready",
        "incompatible_ternary",
        "inference_on_variant",
        "inferred_declaration",
        "int_as_enum_without_cast",
        "int_as_enum_without_match",
        "integer_division",
        "missing_await",
        "missing_tool",
        "narrowing_conversion",
        "native_method_override",
        "onready_with_export",
        "property_used_as_function",
        "redundant_await",
        "redundant_static_unload",
        "return_value_discarded",
        "shadowed_global_identifier",
        "shadowed_variable",
        "shadowed_variable_base_class",
        "standalone_expression",
        "standalone_ternary",
        "static_called_on_instance",
        "unassigned_variable",
        "unassigned_variable_op_assign",
        "unreachable_code",
        "unreachable_pattern",
        "unsafe_call_argument",
        "unsafe_cast",
        "unsafe_method_access",
        "unsafe_property_access",
        "unsafe_void_return",
        "untyped_declaration",
        "unused_local_constant",
        "unused_parameter",
        "unused_private_class_variable",
        "unused_signal",
        "unused_variable",
    ]
)
DESIGN_NAMED = {  # client_rendering.md §7.2 and the review that measured them (reviews/tile_v1/client_rendering.md)
    "untyped_declaration", "inferred_declaration", "unsafe_property_access", "unsafe_method_access", "unsafe_cast",
    "unsafe_call_argument", "return_value_discarded", "unsafe_void_return", "narrowing_conversion",
    "integer_division", "unused_variable", "shadowed_variable",
}  # fmt: skip


def project_settings(text: str) -> dict[str, str]:
    """``section/key`` -> raw value from Godot's project.godot (an INI dialect whose values are Godot literals)."""
    out, section = {}, ""
    for line in text.splitlines():
        if not line.strip() or line.startswith(";"):
            continue
        if line.startswith("["):
            section = line.strip("[]")
            continue
        key, _, value = line.partition("=")
        out[f"{section}/{key}" if section else key] = value
    return out


SETTINGS = project_settings((CLIENT / "project.godot").read_text())


def test_the_renderer_is_compatibility_on_every_platform():
    assert SETTINGS["rendering/renderer/rendering_method"] == '"gl_compatibility"'
    assert SETTINGS["rendering/renderer/rendering_method.mobile"] == '"gl_compatibility"'
    assert SETTINGS["rendering/renderer/rendering_method.web"] == '"gl_compatibility"'
    assert SETTINGS["application/config/features"] == 'PackedStringArray("4.7", "GL Compatibility")'


def test_every_gdscript_warning_is_an_error_and_none_is_exempt_by_directory():
    levels = {k.removeprefix("debug/gdscript/warnings/"): v for k, v in SETTINGS.items() if "gdscript/warnings/" in k}
    assert levels.pop("directory_rules") == "{}"
    assert set(levels) == WARNINGS_4_7_2
    assert {name for name, level in levels.items() if level != "2"} == set()
    assert DESIGN_NAMED <= WARNINGS_4_7_2


def test_stdout_is_flushed_on_every_print():
    assert SETTINGS["application/run/flush_stdout_on_print"] == "true"


def test_the_main_scene_and_the_layout_exist():
    assert SETTINGS["application/run/main_scene"] == '"res://game/main.tscn"'
    for rel in ("game/main.tscn", "addons/engine", "tests/run.gd", "tests/load_all.gd", "tests/golden.tscn"):
        assert (CLIENT / rel).exists(), rel
    assert not (CLIENT / "tests" / "probes").exists()  # windowed probes live in tools/godot_probes, outside the game


def test_every_script_and_shader_is_committed_with_its_uid():
    """Godot 4.7 gives each script and shader a .uid file; scripts/godot_check.py fails an import that creates one."""
    scripts = sorted([*CLIENT.rglob("*.gd"), *CLIENT.rglob("*.gdshader"), *CLIENT.rglob("*.gdshaderinc")])
    assert scripts
    assert [s for s in scripts if not Path(f"{s}.uid").is_file()] == []


def test_goldens_are_kept_out_of_the_import():
    """Without .gdignore Godot imports each golden PNG as a game texture and writes a .import file beside it."""
    assert (CLIENT / "tests" / "goldens" / ".gdignore").is_file()


def test_the_engine_pin_agrees_everywhere():
    version = re.search(r"^GODOT_VERSION=(\d+)\.(\d+)\.(\d+)\.(\w+)\.", PINS, re.MULTILINE)
    assert version is not None
    assert version.groups() == ("4", "7", "2", "stable")
    pin = (CLIENT / "addons" / "engine" / "engine_pin.gd").read_text()
    for name, value in zip(("MAJOR", "MINOR", "PATCH"), version.groups()[:3], strict=True):
        assert f"const {name}: int = {value}\n" in pin
    assert 'const STATUS: String = "stable"\n' in pin
    assert all(
        re.search(rf"^GODOT_{p}_SHA256=[0-9a-f]{{64}}$", PINS, re.MULTILINE)
        for p in ("LINUX_X86_64", "MACOS_UNIVERSAL")
    )


def test_the_installer_refuses_a_download_with_another_digest():
    script = INSTALLER.read_text()
    assert "check=(sha256sum -c -)" in script
    assert "check=(shasum -a 256 -c -)" in script
    assert 'rm -f "$dest/$zip"' in script  # a download that fails its digest is deleted
    assert "--proto '=https'" in script
    assert '"$dest/$bin" --headless --version)"' in script
    assert 'version="$(HOME="$home" XDG_DATA_HOME=' in script  # Godot runs with HOME inside <dest> (S2D-N3)


def _detected(tmp_path: Path, system: str, machine: str) -> subprocess.CompletedProcess[str]:
    """What ci/install_godot.sh picks on a machine whose uname says ``system``/``machine`` (a stand-in uname)."""
    fake = tmp_path / "bin"
    fake.mkdir(exist_ok=True)
    uname = fake / "uname"
    uname.write_text(f'#!/bin/sh\ncase "$1" in -s) echo {system} ;; -m) echo {machine} ;; esac\n')
    uname.chmod(0o755)
    env = {"PATH": f"{fake}{os.pathsep}/usr/bin{os.pathsep}/bin"}
    return subprocess.run(["bash", str(INSTALLER), "--platform"], env=env, capture_output=True, text=True, check=False)


@pytest.mark.parametrize(
    ("system", "machine", "platform"),
    [
        ("Linux", "x86_64", "linux-x86_64"),
        ("Darwin", "arm64", "macos-universal"),
        ("Darwin", "x86_64", "macos-universal"),
    ],
)
def test_the_installer_picks_the_build_for_this_machine(tmp_path, system, machine, platform):
    """S2A-S2: the platform mapping lives in the installer only, not in each workflow."""
    done = _detected(tmp_path, system, machine)
    assert (done.returncode, done.stdout) == (0, f"{platform}\n")


@pytest.mark.parametrize(("system", "machine"), [("Linux", "aarch64"), ("MINGW64_NT", "x86_64")])
def test_the_installer_refuses_a_machine_with_no_pinned_build(tmp_path, system, machine):
    done = _detected(tmp_path, system, machine)
    assert done.returncode != 0
    assert f"no pinned Godot build for {system}/{machine}" in done.stderr


def test_the_golden_image_pins_every_input():
    assert re.search(r"^FROM ubuntu@sha256:[0-9a-f]{64}$", DOCKERFILE, re.MULTILINE)
    assert re.search(r"^ARG SNAPSHOT=\d{8}T\d{6}Z$", DOCKERFILE, re.MULTILINE)
    assert re.search(r"^ARG MESA=\d+\.\d+\.\d+-\S+$", DOCKERFILE, re.MULTILINE)
    for pkg in ("libgl1-mesa-dri", "libglx-mesa0", "libegl-mesa0", "mesa-libgallium"):
        assert f"{pkg}=${{MESA}}" in DOCKERFILE
    packages = re.findall(r"\b([a-z0-9][a-z0-9.+-]+)=([0-9][^\s\\]*|\$\{MESA\})", DOCKERFILE)
    installed = DOCKERFILE.split("install -y --no-install-recommends", 2)[2].split("&& rm -rf")[0]
    unpinned = [w for w in installed.split() if re.fullmatch(r"[a-z][a-z0-9.+-]+", w) and w not in dict(packages)]
    assert unpinned == []
    assert "LP_NATIVE_VECTOR_WIDTH=256" in DOCKERFILE
    assert "GALLIUM_DRIVER=llvmpipe" in DOCKERFILE
    assert 'godot="$(/opt/ci/install_godot.sh /opt/godot)" && ln -s "$godot"' in DOCKERFILE  # a failure stops it
    assert "--only-binary :all: -c /opt/ci/py3.12.txt" in DOCKERFILE
    assert 'grep -q "snapshot.ubuntu.com/ubuntu/${SNAPSHOT}"' in DOCKERFILE  # the sed really pointed apt there


def test_the_golden_job_renders_under_xvfb_and_keeps_its_frames():
    job = yaml.safe_load((ROOT / ".github" / "workflows" / "golden.yml").read_text())["jobs"]["golden"]
    assert job["runs-on"] == "ubuntu-latest"
    runs = " ".join(s.get("run", "") for s in job["steps"])
    assert "-f ci/godot-golden/Dockerfile" in runs
    assert "ci/godot-golden/run.sh" in runs
    assert any(
        s.get("uses", "").startswith("actions/upload-artifact") and s.get("if") == "always()" for s in job["steps"]
    )
    script = (ROOT / "ci" / "godot-golden" / "run.sh").read_text()
    assert 'exec python3 scripts/golden_run.py --godot godot --out "$out"' in script
    assert "grep" not in script.replace('grep -m1 "model name"', "")  # no second copy of the gate's error scan


def test_every_job_that_runs_the_gate_installs_the_pinned_godot_first():
    for workflow, job in (("test.yml", "prepush"), ("drift.yml", "drift")):
        steps = yaml.safe_load((ROOT / ".github" / "workflows" / workflow).read_text())["jobs"][job]["steps"]
        names = [s.get("name") for s in steps]
        assert names.index("Install Godot") < names.index("Gate"), workflow
        install = steps[names.index("Install Godot")]["run"]
        assert "ci/install_godot.sh" in install
        assert install == 'godot="$(ci/install_godot.sh "$RUNNER_TEMP/godot")" && echo "GODOT=$godot" >> "$GITHUB_ENV"'
        assert "case" not in install  # the installer picks the platform (S2A-S2)


def test_every_workflow_reads_the_repository_and_nothing_more():
    for name in ("golden.yml", "test.yml"):
        assert yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())["permissions"] == {
            "contents": "read"
        }


def test_the_gate_runs_the_godot_checks_before_the_tests_and_no_longer_refuses_client():
    gate = (ROOT / "scripts" / "prepush.sh").read_text()
    assert "MAXIM_OVERDRIVE_GODOT=1 MAXIM_OVERDRIVE_ALL_TIERS=1" in gate  # the Godot fixtures and every tier
    assert '"$PY" scripts/godot_check.py' in gate
    assert gate.index('"$PY" scripts/godot_check.py') < gate.index('step "tests, every tier')
    assert "client/ exists" not in gate
