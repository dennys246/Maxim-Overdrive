"""Standards check 6: the gate registry (boundaries §5.2, §5.4; B-4).

Every entry point untrusted input can reach has a row: gate name, kind (authentication, authorization or validation),
the test module holding its rejection paths, and its status (it meets the gate contract of §5.4, it takes no input,
or it is a gate-to-be with the step that hardens it). The check is mechanical, not a reachability analysis:

- every public callable defined in a gate module (``GATE_MODULES``) has a row, so a new ``handle(raw)`` there fails;
- every public method of a class implementing one of Maxim's SEM protocols (``Sensor``, ``Modulator``) anywhere in
  ``src/`` has a row, since Maxim's objects reach the engine only through those methods; a new ``Modulator`` fails;
- every row names a callable that exists, and its test module exists and names it;
- every input gate (``lint_inputs.INPUT_GATES``) is a gate module.

Each gate module is held at 100% branch coverage by the repository's floor (``pyproject.toml``, ``fail_under``).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from lint_inputs import INPUT_GATES

KINDS = {"authentication", "authorization", "validation"}
# The members of Maxim's SEM protocols (maxim.embodiment.sem); tests/test_lint_gates.py holds them to Maxim's own.
MAXIM_PROTOCOLS = {
    "Sensor": frozenset({"name", "unit", "reading_schema", "read"}),
    "Modulator": frozenset({"name", "affordances", "execute"}),
}
EXCEPTION_BASES = {"Exception", "ValueError", "TypeError", "RuntimeError", "KeyError"}


@dataclass(frozen=True)
class Gate:
    kind: str
    tests: str  # the module that holds its rejection paths
    status: str  # "meets", "no input", or "to-be: <the step or backlog row that hardens it>"


_V = "validation"
_ACT = "tests/test_act_validation.py"
_VAL = "tests/test_validation.py"
_SEM = "tests/test_sem_bridge.py"

GATE_MODULES = (
    "src/simcore/adapters/loaders.py",
    "src/simcore/adapters/sem/bridge.py",
    "src/simcore/core/imagination.py",
    "src/simcore/core/intents.py",
    "src/simcore/protocol/tiers.py",
)

GATES: dict[str, Gate] = {
    # file gates: strict YAML, a version, closed keys, ValueError only, bounded echo
    "src/simcore/adapters/loaders.py::read_yaml": Gate(_V, _ACT, "meets"),
    "src/simcore/adapters/loaders.py::load_materials": Gate(_V, _VAL, "meets"),
    "src/simcore/adapters/loaders.py::load_action_limits": Gate(_V, _ACT, "meets"),
    "src/simcore/protocol/tiers.py::RigProfile": Gate(_V, _VAL, "meets"),
    "src/simcore/protocol/tiers.py::RigProfile.load": Gate(_V, _VAL, "meets"),
    # stage 1 of every action: typed parsing, finiteness and ceilings
    "src/simcore/core/intents.py::parse_action": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Strike": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Strike.check": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Ignite": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Ignite.check": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Extinguish": Gate(_V, _ACT, "no input"),
    "src/simcore/core/intents.py::Extinguish.check": Gate(_V, _ACT, "no input"),
    # imagined objects: spec constructors, budgets before allocation, then the world's rules
    "src/simcore/core/imagination.py::Budget": Gate(_V, _VAL, "meets"),
    "src/simcore/core/imagination.py::place": Gate(_V, "tests/test_imagination.py", "meets"),
    "src/simcore/core/scene.py::Scene.from_dict": Gate(_V, _VAL, "to-be: scene v1 (plan step 3b part b)"),
    # the SEM membrane: Maxim's calls arrive through these methods
    "src/simcore/adapters/sem/bridge.py::StructureModulator": Gate(_V, _VAL, "meets"),
    "src/simcore/adapters/sem/bridge.py::StructureModulator.affordances": Gate(_V, _ACT, "no input"),
    "src/simcore/adapters/sem/bridge.py::StructureModulator.execute": Gate("authorization", _ACT, "meets"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument": Gate(_V, _VAL, "meets"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.name": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.unit": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.reading_schema": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.value": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.read": Gate(_V, _SEM, "no input"),
    "src/simcore/adapters/sem/bridge.py::region_parts": Gate(_V, _ACT, "meets"),
    "src/simcore/adapters/sem/bridge.py::to_maxim_entity": Gate(_V, _ACT, "meets"),
}


def _is_exception(node: ast.ClassDef) -> bool:
    names = {b.id if isinstance(b, ast.Name) else getattr(b, "attr", "") for b in node.bases}
    return bool(names & EXCEPTION_BASES) or any(n.endswith("Error") for n in names)


def _members(node: ast.ClassDef) -> tuple[list[str], set[str]]:
    """A class's public methods, and every name its body defines (methods and class attributes)."""
    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef)]
    assigned = {t.id for m in node.body if isinstance(m, ast.Assign) for t in m.targets if isinstance(t, ast.Name)}
    assigned |= {m.target.id for m in node.body if isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name)}
    return [m for m in methods if not m.startswith("_")], set(methods) | assigned


def entry_points(rel: str, source: str) -> tuple[set[str], set[str]]:
    """(every public callable, the public methods of every Maxim-protocol class) defined at a module's top level."""
    public: set[str] = set()
    protocol: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            public.add(f"{rel}::{node.name}")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_") and not _is_exception(node):
            methods, names = _members(node)
            qualified = {f"{rel}::{node.name}.{m}" for m in methods}
            public |= {f"{rel}::{node.name}"} | qualified
            if any(members <= names for members in MAXIM_PROTOCOLS.values()):
                protocol |= qualified
    return public, protocol


def _row_problems(name: str, gate: Gate, defined: set[str], files: dict[str, str]) -> list[str]:
    out = []
    if name not in defined:
        out.append(f"gate registry: {name} names no public callable")
    if gate.kind not in KINDS:
        out.append(f"gate registry: {name} has kind {gate.kind!r}; it must be one of {sorted(KINDS)}")
    if gate.status not in ("meets", "no input") and not gate.status.startswith("to-be: "):
        out.append(f"gate registry: {name} has status {gate.status!r}; it meets, takes no input, or is 'to-be: <step>'")
    short = name.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
    if gate.tests not in files:
        out.append(f"gate registry: {name}'s rejection tests {gate.tests} do not exist")
    elif short not in files[gate.tests]:
        out.append(f"gate registry: {gate.tests} never names {short}, the gate it is the rejection tests of")
    return out


def check_gates(files: dict[str, str], gates: dict[str, Gate] | None = None) -> list[str]:
    gates = GATES if gates is None else gates
    problems = [f"gate registry: {rel} is an input gate but not a gate module" for rel in INPUT_GATES]
    problems = [p for p in problems if p.split(" ")[2] not in GATE_MODULES]
    defined: set[str] = set()
    needed: set[str] = set()
    for rel, text in sorted(files.items()):
        if rel.startswith("src/") and rel.endswith(".py"):
            public, protocol = entry_points(rel, text)
            defined |= public
            needed |= protocol | (public if rel in GATE_MODULES else set())
    problems += [
        f"gate registry: {rel} is a gate module that does not exist" for rel in GATE_MODULES if rel not in files
    ]
    problems += [f"gate registry: {name} is an entry point with no row" for name in sorted(needed - set(gates))]
    for name, gate in sorted(gates.items()):
        problems += _row_problems(name, gate, defined, files)
    return problems
