"""Standards check 6: the gate registry (boundaries §5.2, §5.4; B-4).

Every entry point untrusted input can reach has a row: gate name, kind (authentication, authorization or validation),
the test module holding its rejection paths, and its status (it meets the gate contract of §5.4, it takes no input,
or it is a gate-to-be with the step that hardens it). The check is mechanical, not a reachability analysis:

- every public callable defined in a gate module (``GATE_MODULES``) has a row, so a new ``handle(raw)`` there fails;
- every public method of a class implementing one of Maxim's SEM protocols (``Sensor``, ``Modulator``) anywhere in
  ``src/`` has a row, since Maxim's objects reach the engine only through those methods; a class implements one when
  its body defines the protocol's members or a base class it names does, so a new ``Modulator`` fails, and so does a
  subclass of one that overrides ``execute``. (Members set in ``__init__`` or bases reached through an alias are not
  seen.)
- every row names a callable that exists, and its test module exists and uses that name as code (a name, an
  attribute or an import, not a comment or a string);
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
EXCEPTION_BASES = {"Exception", "ValueError", "TypeError", "RuntimeError", "KeyError", "Refused"}


@dataclass(frozen=True)
class Gate:
    kind: str
    tests: str  # the module that holds its rejection paths
    status: str  # "meets", "no input", "partial: <what is missing>", or "to-be: <the step that hardens it>"


_V = "validation"
_ACT = "tests/test_act_validation.py"
_VAL = "tests/test_validation.py"
_SEM = "tests/test_sem_bridge.py"
_CON = "tests/test_constructors.py"
_EXT = "tests/test_extremes.py"
_FMT = "tests/test_formats.py"
# §5.4 asks anything agent-facing (errors, receipts) to answer in a closed code vocabulary. Since step 3b part (b) every
# refusal these gates give carries a code (simcore.core.refusals, WT-S1), and the membrane answers an agent with the
# code alone (step 3b review, Trust S3).

GATE_MODULES = (
    "src/simcore/adapters/loaders.py",
    "src/simcore/core/schema.py",
    "src/simcore/adapters/sem/bridge.py",
    "src/simcore/core/imagination.py",
    "src/simcore/core/intents.py",
    "src/simcore/protocol/tiers.py",
)

_SCHEMA_READERS = (
    "Real", "Real.convert", "Whole", "Whole.convert", "Vector", "Vector.convert", "Rgb", "Rgb.convert", "Text",
    "Text.convert", "Identity", "Identity.convert", "Nested", "Nested.convert", "Tagged", "Tagged.convert", "ListOf",
    "ListOf.convert", "MapOf", "MapOf.convert", "Field", "Field.read", "Schema", "Schema.read", "Schema.check",
    "read_version", "Format", "Format.read",
)  # fmt: skip
# what each converter refuses (the generated tests' input) and a schema's fields by name: descriptions, not readers
_SCHEMA_DESCRIPTIONS = (
    "Real.bad", "Whole.bad", "Vector.bad", "Rgb.bad", "Text.bad", "Identity.bad", "Nested.bad", "Tagged.bad",
    "ListOf.bad", "MapOf.bad", "Schema.by_name",
)  # fmt: skip

GATES: dict[str, Gate] = {
    # file gates: strict YAML, a version, closed keys, ValueError only, bounded echo; not agent-facing
    "src/simcore/adapters/loaders.py::read_yaml": Gate(_V, _ACT, "meets"),
    "src/simcore/adapters/loaders.py::existing_directory": Gate(_V, _VAL, "meets"),
    "src/simcore/adapters/loaders.py::real_path": Gate(_V, _VAL, "no input"),
    # B29: the data locator's handle, which joins bare names only and which only these gates open
    "src/simcore/adapters/loaders.py::DataPath": Gate(_V, _VAL, "meets"),
    # an operator's rig name: a malformed name is a ValueError; a well-formed name with no file is the gate's
    # FileNotFoundError (an OSError), which tells an operator the rig is missing rather than malformed
    "src/maxim_overdrive/data.py::rig_profile": Gate(
        _V, _VAL, "partial: a missing rig file raises FileNotFoundError, not ValueError (delta round 5, D5-N1)"
    ),
    "src/simcore/adapters/loaders.py::load_materials": Gate(_V, _VAL, "meets"),
    "src/simcore/adapters/loaders.py::load_action_limits": Gate(_V, _ACT, "meets"),
    "src/simcore/protocol/tiers.py::RigProfile": Gate(_V, _VAL, "meets"),
    "src/simcore/protocol/tiers.py::RigProfile.load": Gate(_V, _VAL, "meets"),
    # builders from a document their Format has already read: the Format is the gate (step 3b(b) review, A1)
    "src/simcore/protocol/tiers.py::RigProfile.from_document": Gate(_V, _FMT, "no input"),
    # the one reader every format applies (simcore.core.schema): its converters, fields, schemas and versions
    **{f"src/simcore/core/schema.py::{name}": Gate(_V, _FMT, "meets") for name in _SCHEMA_READERS},
    **{f"src/simcore/core/schema.py::{name}": Gate(_V, _FMT, "no input") for name in _SCHEMA_DESCRIPTIONS},
    "src/simcore/core/materials.py::MaterialTable.from_document": Gate(_V, _FMT, "no input"),
    "src/simcore/core/limits.py::ActionLimits.from_document": Gate(_V, _FMT, "no input"),
    # validating constructors the loaders and the actions build (§5.1)
    "src/simcore/core/materials.py::Material": Gate(_V, _CON, "meets"),
    "src/simcore/core/materials.py::MaterialTable": Gate(_V, _CON, "meets"),
    "src/simcore/core/limits.py::ActionLimits": Gate(_V, _ACT, "meets"),
    "src/simcore/core/world.py::HeatSource": Gate(_V, _ACT, "meets"),
    # stage 1 of every action: typed parsing, finiteness and ceilings
    "src/simcore/core/intents.py::parse_action": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Strike": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Strike.check": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Ignite": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Ignite.check": Gate(_V, _ACT, "meets"),
    "src/simcore/core/intents.py::Extinguish": Gate(_V, _ACT, "no input"),
    "src/simcore/core/intents.py::Extinguish.check": Gate(_V, _ACT, "no input"),
    # stage 2: the world checks, which the host's step will call directly from phase1/agents
    "src/simcore/core/applier.py::Applier.apply": Gate("authorization", _CON, "meets"),
    # imagined objects: spec constructors, budgets before allocation, then the world's rules
    "src/simcore/core/imagination.py::Budget": Gate(_V, _CON, "meets"),
    "src/simcore/core/imagination.py::place": Gate(_V, "tests/test_imagination.py", "meets"),
    "src/simcore/core/scene.py::primitives_from_data": Gate(_V, _VAL, "meets"),
    "src/simcore/core/scene.py::Box": Gate(_V, _EXT, "meets"),
    "src/simcore/core/scene.py::Cylinder": Gate(_V, _EXT, "meets"),
    "src/simcore/core/scene.py::Scene.from_dict": Gate(
        _V, _FMT, "partial: no cell budget before Scene.build allocates the grid, until step 5a's memory budget (T1-S6)"
    ),
    "src/simcore/core/scene.py::Scene": Gate(_V, _VAL, "meets"),
    "src/simcore/core/scene.py::Spawn": Gate(_V, "tests/test_scene_v1.py", "meets"),
    "src/simcore/core/scene.py::Spawn.from_document": Gate(_V, "tests/test_scene_v1.py", "no input"),
    "src/simcore/core/checks.py::identity_key": Gate(_V, "tests/test_scene_v1.py", "meets"),
    # the SEM membrane: Maxim's calls arrive through these methods
    "src/simcore/adapters/sem/bridge.py::StructureModulator": Gate(_V, _VAL, "meets"),
    "src/simcore/adapters/sem/bridge.py::StructureModulator.affordances": Gate(_V, _ACT, "no input"),
    "src/simcore/adapters/sem/bridge.py::StructureModulator.execute": Gate("authorization", _ACT, "meets"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument": Gate(_V, "tests/test_frames.py", "meets"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.name": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.unit": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.reading_schema": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.value": Gate(_V, _VAL, "no input"),
    "src/simcore/adapters/sem/bridge.py::RegionInstrument.read": Gate(_V, _SEM, "no input"),
    "src/simcore/adapters/sem/bridge.py::region_parts": Gate(_V, _ACT, "meets"),
    "src/simcore/adapters/sem/bridge.py::to_maxim_entity": Gate(_V, _ACT, "meets"),
}


def _base_names(node: ast.ClassDef) -> set[str]:
    return {b.id if isinstance(b, ast.Name) else getattr(b, "attr", "") for b in node.bases}


def _is_exception(node: ast.ClassDef) -> bool:
    names = _base_names(node)
    return bool(names & EXCEPTION_BASES) or any(n.endswith("Error") for n in names)


@dataclass(frozen=True)
class _Class:
    qualified: str  # path::Name
    bases: frozenset[str]  # each base's last name
    methods: tuple[str, ...]  # public methods defined in its own body
    names: frozenset[str]  # every name its body defines


def _module_entries(rel: str, source: str) -> tuple[set[str], list[_Class]]:
    """A module's public top-level callables, and its public classes (exceptions aside)."""
    public: set[str] = set()
    classes: list[_Class] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            public.add(f"{rel}::{node.name}")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_") and not _is_exception(node):
            methods, names = _members(node)
            classes.append(
                _Class(f"{rel}::{node.name}", frozenset(_base_names(node)), tuple(methods), frozenset(names))
            )
            public |= {f"{rel}::{node.name}"} | {f"{rel}::{node.name}.{m}" for m in methods}
    return public, classes


def _protocol_classes(classes: list[_Class]) -> set[str]:
    """Classes implementing a Maxim protocol: by their members, or by inheriting from one that does, so a subclass
    that overrides ``execute`` and inherits the rest is one too (step 3b review, Trust S2)."""
    found = {c.qualified for c in classes if any(m <= c.names for m in MAXIM_PROTOCOLS.values())}
    while True:
        short = {q.rsplit("::", 1)[-1] for q in found}
        more = {c.qualified for c in classes if c.bases & short} - found
        if not more:
            return found
        found |= more


def _members(node: ast.ClassDef) -> tuple[list[str], set[str]]:
    """A class's public methods, and every name its body defines (methods and class attributes)."""
    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef)]
    targets = [t for m in node.body if isinstance(m, ast.Assign) for t in m.targets]
    targets += [e for t in targets if isinstance(t, ast.Tuple | ast.List) for e in t.elts]  # name, kind = ...
    assigned = {t.id for t in targets if isinstance(t, ast.Name)}
    assigned |= {m.target.id for m in node.body if isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name)}
    return [m for m in methods if not m.startswith("_")], set(methods) | assigned


def _identifiers(source: str) -> set[str]:
    """The names a test module uses as code: names, attributes, imported names. Not comments, not strings."""
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.alias):
            out.add((node.asname or node.name).split(".")[-1])
    return out


def _row_problems(name: str, gate: Gate, defined: set[str], files: dict[str, str]) -> list[str]:
    out = []
    if name not in defined:
        out.append(f"gate registry: {name} names no public callable")
    if gate.kind not in KINDS:
        out.append(f"gate registry: {name} has kind {gate.kind!r}; it must be one of {sorted(KINDS)}")
    if gate.status not in ("meets", "no input") and not gate.status.startswith(("to-be: ", "partial: ")):
        out.append(
            f"gate registry: {name} has status {gate.status!r}; "
            "it meets, takes no input, or is 'partial: <what>' or 'to-be: <step>'"
        )
    short = name.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
    if gate.tests not in files:
        out.append(f"gate registry: {name}'s rejection tests {gate.tests} do not exist")
    elif short not in _identifiers(files[gate.tests]):
        out.append(f"gate registry: {gate.tests} never names {short}, the gate it is the rejection tests of")
    return out


def check_gates(files: dict[str, str], gates: dict[str, Gate] | None = None) -> list[str]:
    gates = GATES if gates is None else gates
    problems = [f"gate registry: {rel} is an input gate but not a gate module" for rel in INPUT_GATES]
    problems = [p for p in problems if p.split(" ")[2] not in GATE_MODULES]
    defined: set[str] = set()
    needed: set[str] = set()
    classes: list[_Class] = []
    for rel, text in sorted(files.items()):
        if rel.startswith("src/") and rel.endswith(".py"):
            public, found = _module_entries(rel, text)
            defined |= public
            classes += found
            needed |= public if rel in GATE_MODULES else set()
    protocol = _protocol_classes(classes)
    needed |= {f"{c.qualified}.{m}" for c in classes if c.qualified in protocol for m in c.methods}
    problems += [
        f"gate registry: {rel} is a gate module that does not exist" for rel in GATE_MODULES if rel not in files
    ]
    problems += [f"gate registry: {name} is an entry point with no row" for name in sorted(needed - set(gates))]
    for name, gate in sorted(gates.items()):
        problems += _row_problems(name, gate, defined, files)
    return problems
