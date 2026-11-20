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
