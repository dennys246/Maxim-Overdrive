"""The client's intents, parsed: every key checked, every number finite and in range, or a coded refusal.

The client is untrusted input (CLAUDE.md, Game engineering). A refusal is an ``error`` reply and changes nothing;
it never crashes the server or half-applies an intent. Week 1 knows ``move`` and ``kindle``; the plan's other
intents (``look``, ``strike``, ``say``) arrive with the weeks that use them, and until then are ``unknown_type``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from slice_server.body import Command
from slice_server.wire import WireRefused


@dataclass(frozen=True)
class Move:
    command: Command


@dataclass(frozen=True)
class Kindle:
    """Light whatever named solid is in front of the body, within reach. The server picks the target."""


Intent = Move | Kindle


def _keys(raw: Mapping[str, object], allowed: set[str]) -> None:
    if set(raw) != allowed:
        raise WireRefused("bad_intent", f"{raw.get('type')} takes keys {sorted(allowed)}, got {sorted(raw)}")


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise WireRefused("bad_intent", f"{name} must be a finite number")
    return float(value)


def _move(raw: Mapping[str, object]) -> Move:
    _keys(raw, {"type", "dir", "effort", "overdrive"})
    direction, overdrive = raw["dir"], raw["overdrive"]
    if not isinstance(direction, list) or len(direction) != 2:
        raise WireRefused("bad_intent", "dir must be two numbers")
    x, y = _number(direction[0], "dir[0]"), _number(direction[1], "dir[1]")
    effort = _number(raw["effort"], "effort")
    if not 0.0 <= effort <= 1.0:
        raise WireRefused("bad_intent", "effort must be in [0, 1]")
    if not isinstance(overdrive, bool):
        raise WireRefused("bad_intent", "overdrive must be true or false")
    length = math.hypot(x, y)
    if length < 1e-9:  # standing still: no direction to normalise
        return Move(Command(0.0, 0.0, 0.0, overdrive))
    return Move(Command(x / length, y / length, effort, overdrive))


def parse(raw: Mapping[str, object]) -> Intent:
    kind = raw.get("type")
    if kind == "move":
        return _move(raw)
    if kind == "kindle":
        _keys(raw, {"type"})
        return Kindle()
    raise WireRefused("unknown_type", f"no intent called {str(kind)[:40]!r}")
