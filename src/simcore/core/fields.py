"""The field registry (`docs/design/sim_core.md` §6), code-primary: a `FieldSpec` per field, an `InputSpec` per input.

Each field lists its writers, the one owner of who may write it (§5.1): the write window hands a writable array only to
a declared writer holding its token (`simcore.core.writers`). Each input names its appender and its one resolving law.
`render()` is the committed artifact `docs/generated/fields.md`, compared byte for byte by `tests/test_fields.py`.

Step 5a's PR 2 registers the cell fields and the inputs; PR 3 adds `source_exposure` (sim_core.md §3), which
`Simulation.step` records at the end of each tick. The body and keyed fuel tables (5b, 6.0a) and the snapshot, digest
and save columns' readers (PR 4) join as their PRs land.
"""

from __future__ import annotations

from dataclasses import dataclass

# Writers that are not laws: Topology applies world-edit requests (§5.1), and construction sets the authored state.
TOPOLOGY = "topology"
CONSTRUCTION = "construction"
# The laws' names, in the law tuple's order: a mirror of `simcore.core.physics.DEFAULT_LAWS`, its owner, kept here
# because the registry sits below the laws (tests hold the two to each other).
LAW_NAMES = ("damage.loads", "heat", "damage.thermal")
WRITERS = (*LAW_NAMES, TOPOLOGY, CONSTRUCTION)
# Who appends an input (§5.1): the applier, from a record's stage 2, and Simulation, which records which source value
# stood at the end of each tick (§3). Each names the `simcore.core` module that appends; tests hold them to that.
APPLIER = "applier"
SIMULATION = "simulation"
APPENDERS = (APPLIER, SIMULATION)


@dataclass(frozen=True)
class FieldSpec:
    """One field: its storage, what it means, and who writes it, in order (laws, then Topology, then construction)."""

    name: str
    dtype: str
    units: str
    container: str
    saved: bool
    digested: bool
    writers: tuple[str, ...]


@dataclass(frozen=True)
class InputSpec:
    """One input kind: who appends it, and the one law that resolves it (§5.1: one resolver per input kind)."""

    name: str
    appender: str
    resolver: str


FIELDS = (
    FieldSpec("material", "uint8", "material id", "cells", True, True, (TOPOLOGY, CONSTRUCTION)),
    FieldSpec("original_material", "uint8", "material id", "cells", True, True, (TOPOLOGY, CONSTRUCTION)),
    FieldSpec(
        "integrity", "float32", "1", "cells", True, True, ("damage.loads", "damage.thermal", TOPOLOGY, CONSTRUCTION)
    ),
    FieldSpec("temperature", "float64", "degC", "cells", True, True, ("heat", CONSTRUCTION)),
    FieldSpec("regions", "region table", "-", "table", True, True, (TOPOLOGY, CONSTRUCTION)),
)

INPUTS = (
    InputSpec("sources", APPLIER, "heat"),
    InputSpec("source_exposure", SIMULATION, "heat"),
    InputSpec("loads", APPLIER, "damage.loads"),
)

_WRITERS_OF = {f.name: f.writers for f in FIELDS}


def writers_of(field: str) -> tuple[str, ...]:
    """The declared writers of ``field``, or a KeyError for a field the registry doesn't hold."""
    return _WRITERS_OF[field]


def render() -> str:
    """The registry as the committed artifact `docs/generated/fields.md`."""
    lines = [
        "# Field registry (generated)",
        "",
        "Generated from `src/simcore/core/fields.py` by `simcore.core.fields.render()`; `tests/test_fields.py`",
        "compares it byte for byte. Edit the code, never this file. The contract is `docs/design/sim_core.md` §6.",
        "",
        "| Field | dtype | units | container | saved | digested | writers, in order |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in FIELDS:
        lines.append(
            f"| `{f.name}` | {f.dtype} | {f.units} | {f.container} | {'yes' if f.saved else 'no'} | "
            f"{'yes' if f.digested else 'no'} | {', '.join(f.writers)} |"
        )
    lines += ["", "| Input | appended by | resolved by |", "|---|---|---|"]
    lines += [f"| `{i.name}` | {i.appender} | {i.resolver} |" for i in INPUTS]
    return "\n".join(lines) + "\n"
