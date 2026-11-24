"""The protocol's schema as a committed artifact (boundaries §9.1): ``render()`` is ``docs/generated/protocol.md``.

The code is primary. The artifact is what a client author reads, and ``tests/test_wire.py`` compares it byte for byte,
so a change to a message, a header field or the catalogue shows in review as a diff of this file.
"""

from __future__ import annotations

from simcore.core.schema import Schema
from simcore.protocol import catalogue
from simcore.protocol.frame_header import ARRAY, CHANNEL, GRID, HEADER, TABLE
from simcore.protocol.messages import CLIENT_MESSAGES, MAX_MESSAGE_BYTES, PROTOCOL
from simcore.protocol.strict_json import JSON_INT_MAX, MAX_DEPTH

__all__ = ["render"]


def _fields(schema: Schema) -> list[str]:
    rows = ["| Field | Required | Null | Read by |", "|---|---|---|---|"]
    for f in schema.fields:
        rows.append(
            f"| `{f.name}` | {'yes' if f.required else 'no'} | {'yes' if f.nullable else 'no'} | `{f.convert!r}` |"
        )
    return rows


def render() -> str:
    lines = [
        "# Wire protocol v0 (generated)",
        "",
        "Generated from `src/simcore/protocol/` by `simcore.protocol.registry.render()`; `tests/test_wire.py`",
        "compares it byte for byte. Edit the code, never this file. The contracts are",
        "`docs/design/client_rendering.md` §4 and `docs/design/tile_and_client.md` §3.3.",
        "",
        f"- **protocol:** {PROTOCOL}.",
        f"- **JSON:** integers of magnitude at most {JSON_INT_MAX} (2^53 - 1); no NaN or infinity; no repeated key;",
        f"  containers nested at most {MAX_DEPTH} deep; a client message at most {MAX_MESSAGE_BYTES} bytes.",
        "",
        "## Client messages",
        "",
        f"A JSON object whose `{CLIENT_MESSAGES.tag}` names it.",
    ]
    for kind, schema in CLIENT_MESSAGES.schemas.items():
        lines += ["", f"### `{kind}`", "", *_fields(schema)]
    lines += ["", "## Cell frame", "", "`[u32 header length][JSON header][arrays]`, little-endian.", ""]
    for name, schema in (("header", HEADER), ("grid", GRID), ("table", TABLE), ("array", ARRAY), ("channel", CHANNEL)):
        lines += [f"### {name}", "", *_fields(schema), ""]
    return "\n".join(lines) + "\n" + catalogue.render()
