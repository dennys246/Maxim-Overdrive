"""The client's intents, parsed: every key checked, every number finite and in range, or a coded refusal.

The client is untrusted input (CLAUDE.md, Game engineering). A refusal is an ``error`` reply and changes nothing;
it never crashes the server or half-applies an intent. The slice knows ``move``, ``kindle``, ``strike`` and ``say``;
the plan's ``look`` never earned its place (the client turns the camera itself) and is ``unknown_type``.
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


@dataclass(frozen=True)
class Strike:
    """Hit whatever named solid is in front, within reach: harder, hotter and with recoil when in Overdrive."""


@dataclass(frozen=True)
class Say:
    """Words to the vendor. They reach its voice as words and never its behaviour: the simulation ignores them."""

    text: str


MAX_SAY = 200  # characters
Intent = Move | Kindle | Strike | Say


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
    if kind == "strike":
        _keys(raw, {"type"})
        return Strike()
    if kind == "say":
        _keys(raw, {"type", "text"})
        text = raw["text"]
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_SAY:
            raise WireRefused("bad_intent", f"text must be 1 to {MAX_SAY} characters")
        return Say(text.strip())
    raise WireRefused("unknown_type", f"no intent called {str(kind)[:40]!r}")
