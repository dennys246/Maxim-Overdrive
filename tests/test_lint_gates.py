"""scripts/lint_inputs.py and scripts/lint_gates.py: untrusted input by source, and the gate registry (B-4).

Each rule is proven by planting what it forbids (boundaries §5.2): an ``open`` in a module that is not a gate, a
public entry point with no row, a new ``handle(raw: bytes)`` inside a gate module, and a new ``Modulator`` whose
``execute`` has no row. All four must go red.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.test_lint_standards import _load

ROOT = Path(__file__).resolve().parents[1]
inputs = _load("lint_inputs")
gates = _load("lint_gates")  # after lint_inputs, which it imports by name


def _repo_files() -> dict[str, str]:
    return {
        p.relative_to(ROOT).as_posix(): p.read_text()
        for top in ("src", "tests")
        for p in sorted((ROOT / top).rglob("*.py"))
    }


# -- input primitives on the real tree (every spelling lives in tests/test_lint_inputs_corpus.py) --------------------


def test_a_planted_open_in_a_module_that_is_not_a_gate_goes_red():
    # A json.loads there is the import allowlist's (tests/test_input_allowlist.py plants one per route); the
    # lint holds what needs no import, such as the open builtin.
    files = _repo_files()
    assert inputs.check_inputs(files) == []
    rel = "src/simcore/protocol/tiers.py"
    files[rel] += "\n\ndef decode(path):\n    return open(path).read()\n"
    assert any("builtins.open" in p and rel in p for p in inputs.check_inputs(files))


# -- the gate registry ------------------------------------------------------------------------------------------------


def test_the_repository_registers_every_entry_point():
    assert gates.check_gates(_repo_files()) == []


def test_a_public_entry_with_no_row_goes_red():
    files = _repo_files()
    rel = "src/simcore/adapters/loaders.py"
    files[rel] += "\n\ndef load_presets(path):\n    return read_yaml(path)\n"
    assert gates.check_gates(files) == [f"gate registry: {rel}::load_presets is an entry point with no row"]


def test_a_new_handle_inside_a_gate_module_goes_red():
    # v1 B2's exact scenario: an annotation rule would have missed it.
    files = _repo_files()
    rel = "src/simcore/adapters/sem/bridge.py"
    files[rel] += "\n\nclass Door:\n    def handle(self, raw: bytes) -> None:\n        pass\n"
    assert gates.check_gates(files) == [
        f"gate registry: {rel}::Door is an entry point with no row",
        f"gate registry: {rel}::Door.handle is an entry point with no row",
    ]


def test_a_new_modulator_outside_a_gate_module_goes_red():
    files = _repo_files()
    rel = "src/simcore/adapters/doors.py"
    files[rel] = (
        "class DoorModulator:\n    name = 'door'\n\n    @property\n    def affordances(self):\n        return {}\n\n"
        "    def execute(self, affordance, params):\n        return None\n"
    )
    assert gates.check_gates(files) == [
        f"gate registry: {rel}::DoorModulator.affordances is an entry point with no row",
        f"gate registry: {rel}::DoorModulator.execute is an entry point with no row",
    ]


def test_an_exception_or_a_private_name_in_a_gate_module_needs_no_row():
    files = _repo_files()
    rel = "src/simcore/core/intents.py"
    files[rel] += (
        "\n\nclass Refused(ValueError):\n    pass\n\n\nclass Bad(SomeError):\n    pass\n\n\ndef _helper():\n    pass\n"
    )
    assert gates.check_gates(files) == []


def test_every_row_is_held_to_a_callable_a_kind_a_status_and_tests_that_name_it():
    files = _repo_files()
    rel = "src/simcore/core/intents.py"
    bad = {
        f"{rel}::parse_action": gates.Gate("validation", "tests/test_act_validation.py", "meets"),
        f"{rel}::vanished": gates.Gate("validation", "tests/test_act_validation.py", "meets"),
        f"{rel}::Strike": gates.Gate("trust", "tests/test_act_validation.py", "fine"),
        f"{rel}::Ignite": gates.Gate("validation", "tests/test_nowhere.py", "to-be: step 9"),
        f"{rel}::Extinguish": gates.Gate("validation", "tests/test_heat.py", "no input"),
    }
    problems = gates.check_gates(files, bad)
    assert f"gate registry: {rel}::vanished names no public callable" in problems
    assert any("Strike has kind 'trust'" in p for p in problems)
    assert any("Strike has status 'fine'" in p for p in problems)
    assert f"gate registry: {rel}::Ignite's rejection tests tests/test_nowhere.py do not exist" in problems
    assert any("tests/test_heat.py never names Extinguish" in p for p in problems)
    assert f"gate registry: {rel}::Strike.check is an entry point with no row" in problems  # the rest are unregistered


def test_every_input_gate_is_a_gate_module_and_every_gate_module_exists():
    assert set(inputs.INPUT_GATES) <= set(gates.GATE_MODULES)
    files = _repo_files()
    del files["src/simcore/protocol/tiers.py"]
    problems = gates.check_gates(files)
    assert "gate registry: src/simcore/protocol/tiers.py is a gate module that does not exist" in problems


def test_an_input_gate_outside_the_gate_modules_is_a_finding(monkeypatch):
    monkeypatch.setattr(gates, "INPUT_GATES", {"src/simcore/protocol/encoding.py": "planted"})
    assert "gate registry: src/simcore/protocol/encoding.py is an input gate but not a gate module" in (
        gates.check_gates(_repo_files())
    )


def test_the_protocol_members_are_maxims_own():
    sem = pytest.importorskip("maxim.embodiment.sem")
    for name, members in gates.MAXIM_PROTOCOLS.items():
        protocol = getattr(sem, name)
        declared = {m for m in vars(protocol) if not m.startswith("_")}
        assert declared == members, name


# -- registry gaps (Trust S2, S3, N7) ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "src/simcore/core/applier.py::Applier.apply",
        "src/simcore/core/scene.py::primitives_from_data",
        "src/simcore/core/scene.py::Box",
        "src/simcore/core/scene.py::Cylinder",
        "src/simcore/core/materials.py::Material",
        "src/simcore/core/materials.py::MaterialTable",
        "src/simcore/core/limits.py::ActionLimits",
        "src/simcore/core/world.py::HeatSource",
    ],
)
def test_every_constructor_and_stage_two_entry_that_untrusted_data_reaches_has_a_row(name):
    assert name in gates.GATES


def test_a_subclass_that_overrides_a_modulators_execute_needs_a_row():
    files = _repo_files()
    rel = "src/simcore/adapters/doors.py"
    files[rel] = (
        "from simcore.adapters.sem.bridge import StructureModulator\n\n\n"
        "class Door(StructureModulator):\n    def execute(self, affordance, params):\n        return None\n"
    )
    assert f"gate registry: {rel}::Door.execute is an entry point with no row" in gates.check_gates(files)


def test_an_agent_facing_gate_claims_the_closed_code_vocabulary_only_because_it_answers_in_it():
    """§5.4's last clause: these gates were partial until the refusal codes (step 3b part b). Each now meets it, and
    each is called with a bad input here to show its refusal is a code, never words (WT-S1)."""
    from maxim_overdrive import data  # noqa: PLC0415
    from simcore.adapters.sem.bridge import region_parts  # noqa: PLC0415
    from simcore.core.applier import Applier  # noqa: PLC0415
    from simcore.core.imagination import SpecRejected, place  # noqa: PLC0415
    from simcore.core.intents import ActionRefused, Ignite, parse_action  # noqa: PLC0415
    from simcore.core.refusals import RefusalCode  # noqa: PLC0415
    from simcore.core.scene import Box, Scene  # noqa: PLC0415
    from simcore.core.world import World  # noqa: PLC0415

    for name in (
        "src/simcore/adapters/sem/bridge.py::StructureModulator.execute",
        "src/simcore/core/imagination.py::place",
        "src/simcore/core/intents.py::parse_action",
        "src/simcore/core/applier.py::Applier.apply",
    ):
        assert gates.GATES[name].status == "meets", name
    scene = Scene((2.0, 2.0, 2.0), (Box((0.6, 0.6, 0.0), (1.2, 1.2, 0.6), "wood", "crate"),))
    world = World.from_scene(scene, data.materials(), dx_m=0.2, limits=data.action_limits())
    applier = Applier(world)
    _, modulators = region_parts(applier, world.frames, "crate")
    error = modulators["structure"].execute("ignite", {"power_w": "hot"}).error
    assert error is not None
    assert RefusalCode(error.split(" ")[0]) is RefusalCode.NOT_FINITE
    with pytest.raises(ActionRefused) as refused:
        parse_action("ignite", {"power_w": 1e30}, world.limits)
    assert refused.value.agent_text == "out_of_range (power_w)"
    assert applier.apply("nowhere", Ignite(1.0, 0.3)).agent_text == "no_region"
    with pytest.raises(SpecRejected) as rejected:
        place(world.grid, {"name": "crate", "primitives": []}, (0.0, 0.0, 0.0))
    assert rejected.value.agent_text == "name_taken"


def test_a_test_module_names_its_gate_as_code_not_in_a_comment_or_a_string():
    files = _repo_files()
    files["tests/test_x.py"] = "# unit, read and value\nx = 'name'\n"
    rows = {
        "src/simcore/adapters/sem/bridge.py::RegionInstrument.unit": gates.Gate(
            "validation", "tests/test_x.py", "no input"
        )
    }
    problems = gates.check_gates(files, rows)
    assert any("tests/test_x.py never names unit" in p for p in problems)


def test_a_tuple_assignment_does_not_hide_a_modulator():
    files = _repo_files()
    rel = "src/simcore/adapters/doors.py"
    files[rel] = (
        "class Door:\n    name, kind = 'door', 'x'\n\n    def affordances(self):\n        return {}\n\n"
        "    def execute(self, affordance, params):\n        return None\n"
    )
    problems = gates.check_gates(files)
    assert f"gate registry: {rel}::Door.execute is an entry point with no row" in problems


def test_no_registered_gate_raises_an_uncoded_value_error():
    """Every refusal from a registered gate carries a code (WT-S1; step 3b(b) review, Architecture A4): a `raise
    ValueError(...)` written in a gate's own body is a refusal nobody can tell an agent. TypeError stays for programming
    errors. Planting one goes red."""

    def uncoded(source: str, name: str) -> list[int]:
        tree = ast.parse(source)
        parts = name.split(".")
        scopes: list[ast.AST] = [tree]
        for part in parts:
            scopes = [
                n
                for scope in scopes
                for n in ast.iter_child_nodes(scope)
                if isinstance(n, ast.FunctionDef | ast.ClassDef) and n.name == part
            ]
        return [
            n.lineno
            for scope in scopes
            for n in ast.walk(scope)
            if isinstance(n, ast.Raise)
            and isinstance(n.exc, ast.Call)
            and isinstance(n.exc.func, ast.Name)
            and n.exc.func.id == "ValueError"
        ]

    files = _repo_files()
    found = {row: lines for row in gates.GATES if (lines := uncoded(files[row.split("::")[0]], row.split("::")[1]))}
    assert found == {}
    planted = "class HeatSource:\n    def __post_init__(self):\n        raise ValueError('x')\n"
    assert uncoded(planted, "HeatSource") == [3]
