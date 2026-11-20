"""scripts/lint_inputs.py and scripts/lint_gates.py: untrusted input by source, and the gate registry (B-4).

Each rule is proven by planting what it forbids (boundaries §5.2): a ``json.loads`` in a module that is not a gate, a
public entry point with no row, a new ``handle(raw: bytes)`` inside a gate module, and a new ``Modulator`` whose
``execute`` has no row. All four must go red.
"""

from __future__ import annotations

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


# -- input primitives by module ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "x = json.loads(raw)",
        "x = json.load(f)",
        "x = yaml.safe_load(text)",
        "t = Path(p).read_text()",
        "b = path.read_bytes()",
        "f = open('x')",
        "a = np.load('z.npy')",
        "a = numpy.load('z.npy')",
        "v = os.environ['X']",
        "v = os.getenv('X')",
        "v = getenv('X')",
        "a = sys.argv[1]",
        "line = input()",
        "m = sock.recv(1024)",
        "h = path.open()",
    ],
)
def test_an_input_primitive_outside_a_gate_module_is_a_finding(line):
    assert inputs.input_findings("src/simcore/protocol/encoding.py", line + "\n"), line


def test_an_input_gate_may_read_and_nothing_outside_src_is_held_to_it():
    assert inputs.input_findings("src/simcore/adapters/loaders.py", "t = path.read_text()\n") == []
    assert inputs.input_findings("scripts/x.py", "t = path.read_text()\n") == []
    assert inputs.input_findings("src/simcore/core/x.py", "t = grid.temperature.copy()\nn = self.load\n") == []


def test_a_planted_json_loads_in_a_module_that_is_not_a_gate_goes_red():
    files = _repo_files()
    assert inputs.check_inputs(files) == []
    rel = "src/simcore/protocol/tiers.py"
    files[rel] += "\n\ndef decode(raw):\n    return json.loads(raw)\n"
    assert any("json.loads" in p and rel in p for p in inputs.check_inputs(files))


# -- unsafe decoders, everywhere --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "import pickle",
        "import marshal",
        "from shelve import open",
        "import cloudpickle as cp",
        "x = yaml.load(text)",
        "x = yaml.load(text, Loader=yaml.Loader)",
        "x = yaml.load(text, Loader=yaml.FullLoader)",
        "x = yaml.load_all(text, Loader=MyLoader)",
        "x = yaml.unsafe_load(text)",
        "x = yaml.full_load(text)",
        "a = np.load('z.npy', allow_pickle=True)",
        "y = eval('1')",
        "exec('x = 1')",
    ],
)
def test_an_unsafe_decoder_is_a_finding_anywhere(source):
    for rel in ("src/simcore/adapters/loaders.py", "scripts/x.py", "tests/test_x.py"):
        assert inputs.unsafe_findings(rel, source + "\n"), (rel, source)


@pytest.mark.parametrize(
    "source",
    [
        "x = yaml.load(text, Loader=yaml.SafeLoader)",
        "x = yaml.load(text, yaml.CSafeLoader)",
        "class L(yaml.SafeLoader):\n    pass\nx = yaml.load(text, Loader=L)",
        "x = yaml.safe_load(text)",
        "a = np.load('z.npy')",
        "a = np.load('z.npy', allow_pickle=False)",
        "s = 'eval(x) and pickle are banned'",
        "x = model.eval()",
    ],
)
def test_a_safe_decoder_is_not_a_finding(source):
    assert inputs.unsafe_findings("tests/test_x.py", source + "\n") == [], source


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


# -- evasions the step 3b review found (Trust S1, Architecture N5): each one is a finding ------------------------------

EVASIONS_EVERYWHERE = [
    "import yaml as y\nx = y.load(s, Loader=y.Loader)",
    "from yaml import unsafe_load\nx = unsafe_load(s)",
    "from yaml import load, Loader\nx = load(s, Loader=Loader)",
    "import yaml\nf = getattr(yaml, 'unsafe_load')",
    "import importlib\nm = importlib.import_module('pickle')",
    "m = __import__('pickle')",
    "import _pickle",
    "a = np.load(p, allow_pickle=flag)",
    "a = np.load(p, **{'allow_pickle': True})",
    "import numpy as n\na = n.load(p, allow_pickle=True)",
    "a = numpy.lib.format.read_array(f, allow_pickle=True)",
    "x = builtins.eval(s)",
    "x = builtins.exec(s)",
    "e = eval\nx = e(s)",
]


@pytest.mark.parametrize("source", EVASIONS_EVERYWHERE)
def test_an_evasive_spelling_of_an_unsafe_decoder_is_a_finding_anywhere(source):
    for rel in ("src/simcore/adapters/loaders.py", "scripts/x.py", "tests/test_x.py"):
        assert inputs.unsafe_findings(rel, source + "\n"), (rel, source)


EVASIONS_IN_SRC = [
    "import numpy as n\na = n.load(p)",
    "from numpy import load as ld\na = ld(p)",
    "from os import environ as env\nv = env['X']",
    "import sys as s\na = s.argv",
    "import json as j\nx = j.loads(raw)",
    "import tomllib\nx = tomllib.loads(raw)",
    "import importlib\nm = importlib.import_module(name)",
    "m = __import__(name)",
    "v = getattr(obj, name)",
    "import fileinput\nfor line in fileinput.input():\n    pass",
]


@pytest.mark.parametrize("source", EVASIONS_IN_SRC)
def test_an_evasive_input_primitive_in_the_engine_is_a_finding(source):
    assert inputs.input_findings("src/simcore/protocol/encoding.py", source + "\n"), source


def test_a_literal_getattr_and_an_aliased_safe_loader_are_not_findings():
    assert inputs.input_findings("src/simcore/core/x.py", "v = getattr(obj, 'name', None)\n") == []
    safe = "import yaml as y\nx = y.load(s, Loader=y.SafeLoader)\n"
    assert inputs.unsafe_findings("tests/test_x.py", safe) == []


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


def test_an_agent_facing_gate_does_not_claim_the_closed_code_vocabulary_it_lacks():
    for name in (
        "src/simcore/adapters/sem/bridge.py::StructureModulator.execute",
        "src/simcore/core/imagination.py::place",
        "src/simcore/core/intents.py::parse_action",
        "src/simcore/core/applier.py::Applier.apply",
    ):
        assert gates.GATES[name].status.startswith("partial: "), name


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


# -- chained calls (step 3b delta review, Trust D-B1): a call whose result is used through an attribute is judged too

CHAINED_UNSAFE = [
    "a = np.load(p, allow_pickle=True).item()",
    "import importlib\nb = importlib.import_module('pickle').loads(raw)",
    "b = __import__('pickle').loads(raw)",
    "a = np.load(p, None, True)",  # allow_pickle by position
    "f = __builtins__['eval']",
    "import builtins\nf = vars(builtins)['exec']",
    "import builtins\nf = builtins.__dict__['exec']",
    "import yaml\nL = yaml.CUnsafeLoader",
    "import yaml\nL.add_multi_constructor('tag:yaml.org,2002:python/', yaml.constructor.UnsafeConstructor.x)",
]


@pytest.mark.parametrize("source", CHAINED_UNSAFE)
def test_a_chained_or_indirect_unsafe_decoder_is_a_finding(source):
    assert inputs.unsafe_findings("tests/test_x.py", source + "\n"), source


CHAINED_INPUT = [
    "t = open(p).read()",
    "from pathlib import Path\nt = Path(p).open().read()",
    "a = np.load(p).copy()",
    "import json\nv = json.loads(s).get('a')",
]


@pytest.mark.parametrize("source", CHAINED_INPUT)
def test_a_chained_input_primitive_in_the_engine_is_a_finding(source):
    assert inputs.input_findings("src/simcore/core/x.py", source + "\n"), source


def test_a_tuple_assignment_does_not_hide_a_modulator():
    files = _repo_files()
    rel = "src/simcore/adapters/doors.py"
    files[rel] = (
        "class Door:\n    name, kind = 'door', 'x'\n\n    def affordances(self):\n        return {}\n\n"
        "    def execute(self, affordance, params):\n        return None\n"
    )
    problems = gates.check_gates(files)
    assert f"gate registry: {rel}::Door.execute is an entry point with no row" in problems
