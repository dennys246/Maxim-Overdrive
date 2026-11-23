"""One declarative schema per data format, and the one reader that applies it (flexibility review, Architecture 7).

A format's fields are declared once, each with the converter from ``checks`` that turns an untrusted value into the
value the engine uses, or refuses it with a code. The reader (``Schema.read``) holds a mapping to the schema's keys
and converts every field; a validating constructor (``Material``, ``ActionLimits``, the primitives) runs the same
converters on what it is handed (``Schema.check``), so there is one rule per field whoever builds the value.

Each converter also lists the values it must refuse (``bad``). ``tests/test_formats.py`` walks every format's schema
over a valid document and feeds each field each of them, plus a missing and an unknown key, so a new field gets its
rejection tests by being declared. Versions, refusals of old versions and migrations are ``Format``'s.

Content stores time in world units, never ticks (tile §3.2): a field named for ticks, at any depth, is refused when
its ``Format`` is declared, since the tick (step 5a) is derived from seconds at load, never authored. A schema alone
is not content: the wire's carry the simulation's integer ticks (a frame's tick, kindle's ``duration_ticks``).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from simcore.core.checks import (
    IDENTITY_KEY_CHARS,
    entity_key,
    finite_real,
    finite_vector,
    identity_key,
    known_keys,
    shown,
    whole_number,
)
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.text import NAME_JOINERS, visible_name

Bad = tuple[tuple[object, RefusalCode], ...]  # a value the converter must refuse, and the code it refuses it with
_NOT_NUMBERS: Bad = (
    (math.nan, RefusalCode.NOT_FINITE),
    (math.inf, RefusalCode.NOT_FINITE),
    (True, RefusalCode.NOT_FINITE),
    ("1.0", RefusalCode.NOT_FINITE),
    ([1.0], RefusalCode.NOT_FINITE),
)


TEXT_CHARS = 128  # a name's budget (boundaries §5.4): imagined names are held tighter by Budget.max_name_chars


def item_count(value: Sequence[object] | Mapping[object, object]) -> int:
    """A container's length, or one past any budget for a length too large to count (``range(10**20)``; no file
    holds one)."""
    try:
        return len(value)
    except OverflowError:
        return 2**63


def _out_of_range(what: str, value: object, rule: str) -> Refused:
    return Refused(f"{what} must be {rule}, got {shown(value)}", code=RefusalCode.OUT_OF_RANGE)


@dataclass(frozen=True)
class Real:
    """A finite float, optionally bounded: ``lo`` < v (``lo_open``) or ``lo`` <= v, and v <= ``hi``."""

    lo: float | None = None
    hi: float | None = None
    lo_open: bool = False

    def convert(self, value: object, what: str) -> float:
        v = finite_real(value, what)
        below = self.lo is not None and (v <= self.lo if self.lo_open else v < self.lo)
        if below or (self.hi is not None and v > self.hi):
            raise _out_of_range(what, value, self._rule())
        return v

    def _rule(self) -> str:
        low = "" if self.lo is None else f"{'above' if self.lo_open else 'at least'} {self.lo:g}"
        high = "" if self.hi is None else f"at most {self.hi:g}"
        return " and ".join(p for p in (low, high) if p)

    @property
    def bad(self) -> Bad:
        edges = [] if self.lo is None else [(self.lo if self.lo_open else self.lo - 1.0, RefusalCode.OUT_OF_RANGE)]
        edges += [] if self.hi is None else [(self.hi + 1.0, RefusalCode.OUT_OF_RANGE)]
        return (*_NOT_NUMBERS, *edges)


@dataclass(frozen=True)
class Whole:
    """An int within [``lo``, ``hi``]: not a bool, not a float such as 2.0, not a numeric string."""

    lo: int
    hi: int

    def convert(self, value: object, what: str) -> int:
        v = whole_number(value, what)
        if not self.lo <= v <= self.hi:
            raise _out_of_range(what, value, f"from {self.lo} to {self.hi}")
        return v

    @property
    def bad(self) -> Bad:
        not_ints = ((True, RefusalCode.NOT_INT), (2.0, RefusalCode.NOT_INT), ("1", RefusalCode.NOT_INT))
        return (*not_ints, (self.lo - 1, RefusalCode.OUT_OF_RANGE), (self.hi + 1, RefusalCode.OUT_OF_RANGE))


@dataclass(frozen=True)
class Vector:
    """``n`` finite floats, each within ``bound`` of zero (and above zero when ``positive``)."""

    n: int
    bound: float
    positive: bool = False

    def convert(self, value: object, what: str) -> tuple[float, ...]:
        values = finite_vector(value, self.n, what)
        if any(abs(v) > self.bound or (self.positive and v <= 0) for v in values):
            rule = f"{'above 0 and ' if self.positive else ''}within {self.bound:g} of 0 on every axis"
            raise _out_of_range(what, value, rule)
        return values

    @property
    def bad(self) -> Bad:
        short, edge = [0.0] * (self.n - 1), [0.0] * (self.n - 1)
        return (
            (short, RefusalCode.BAD_SHAPE),
            ("0" * self.n, RefusalCode.BAD_SHAPE),
            ([*edge, math.nan], RefusalCode.NOT_FINITE),
            ([*edge, self.bound * 2], RefusalCode.OUT_OF_RANGE),
        )


@dataclass(frozen=True)
class Rgb:
    """A colour: three whole numbers from 0 to 255."""

    def convert(self, value: object, what: str) -> tuple[int, int, int]:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or item_count(value) != 3:
            raise Refused(f"{what} must be three whole numbers, got {shown(value)}", code=RefusalCode.BAD_SHAPE)
        byte = Whole(0, 255)
        return (byte.convert(value[0], what), byte.convert(value[1], what), byte.convert(value[2], what))

    @property
    def bad(self) -> Bad:
        shape = ((5, RefusalCode.BAD_SHAPE), ("red", RefusalCode.BAD_SHAPE), ([1, 2], RefusalCode.BAD_SHAPE))
        return (*shape, ([1, 2, "3"], RefusalCode.NOT_INT), ([0, 0, 256], RefusalCode.OUT_OF_RANGE))


@dataclass(frozen=True)
class Text:
    """A display or lookup name: a printable string of 1 to ``max_chars`` characters with no outer spaces, and none
    of the ``reserved`` names under Maxim's name rule (``checks.entity_key``).

    Maxim strips the names it resolves, so " crate" would answer to "crate". A region's name reaches every agent as
    an entity name, so a control, bidi or format character (a newline, U+202E, U+200B) is refused, not passed on
    (boundaries §5.3, §5.4; step 3b(b) review, Trust T1-S2). The limit and the reserved names are fields, so the
    schema snapshot pins them (delta review, D-S4)."""

    max_chars: int = TEXT_CHARS
    reserved: tuple[str, ...] = ()  # sorted, so its repr (and the schema snapshot) never depends on the hash seed

    def __post_init__(self) -> None:
        # under Maxim's name rule, as convert compares them, so Text(reserved=("Self",)) can't silently match nothing
        object.__setattr__(self, "reserved", tuple(sorted({entity_key(r) for r in self.reserved})))

    def convert(self, value: object, what: str) -> str:
        ok = (
            type(value) is str  # a str subclass could print as something else (delta review, D5)
            and 0 < len(value) <= self.max_chars
            and value.translate(NAME_JOINERS).isprintable()  # ZWJ, ZWNJ: IDNA's CONTEXTJ judges them (Sinhala)
            and value == value.strip()
            and visible_name(value)  # a name an agent can see and tell apart
        )
        if not ok:
            rule = (
                f"a printable string of 1 to {self.max_chars} characters with no outer spaces, in NFKC form, each word "
                "made of the letters, digits and marks an identifier may hold (IDNA2008)"
            )
            raise Refused(f"{what} must be {rule}, got {shown(value)}", code=RefusalCode.BAD_NAME)
        if entity_key(str(value)) in self.reserved:
            message = f"{what} {shown(value)} is a name Maxim resolves to the agent itself"
            raise Refused(message, code=RefusalCode.BAD_NAME)
        return str(value)

    @property
    def bad(self) -> Bad:
        long = "x" * (self.max_chars + 1)
        names = (
            *(7, "", " x", "x ", long, "a\nb", "a\u202eb", "cr\u200bate", "a\x00b", "\ud800", "\u3164", "\u2800"),
            *("crate\ufe0f", "a\u17b4b", "-", "cr\u034fate", "crate\U000e0100", "crate\u2800", "cafe\u0301"),
            *("crate\U00013441", "\uff43rate", "\ufb01x", "cr\u200date", "\u1100\u1161"),  # blank, compat, joiner, NFKC
            *("\u212arate", "\u0b95\u0bcd\u200d", "\u0915\u094d\u200c crate"),  # a Kelvin-sign twin, trailing joiners
            *("room \u0661\u06f2", "1\u0662"),  # two digit systems in one word (R5-2)
            *(type("_NameLike", (str,), {})("crate"), *self.reserved),  # a str subclass, whose __str__ may differ
        )
        return tuple((n, RefusalCode.BAD_NAME) for n in names)


@dataclass(frozen=True)
class Identity:
    """An identity key (``checks.identity_key``): a body's, an archetype's, an item's, later an NPC's or a stream's.
    ``max_chars`` is the rule's own limit, as a field so the schema snapshot pins it."""

    max_chars: int = IDENTITY_KEY_CHARS

    def __post_init__(self) -> None:
        if self.max_chars != IDENTITY_KEY_CHARS:  # one rule for every identity key, never a per-field one
            raise TypeError(f"an identity key is at most {IDENTITY_KEY_CHARS} characters")

    def convert(self, value: object, what: str) -> str:
        return identity_key(value, what)

    @property
    def bad(self) -> Bad:
        return (
            (7, RefusalCode.BAD_IDENTITY_KEY),
            ("a:b", RefusalCode.BAD_IDENTITY_KEY),
            ("", RefusalCode.BAD_IDENTITY_KEY),
        )


@dataclass(frozen=True)
class Nested:
    """A mapping read by another schema."""

    schema: Schema

    def convert(self, value: object, what: str) -> Mapping[str, object]:
        return self.schema.read(value, what)

    @property
    def bad(self) -> Bad:
        return (([], RefusalCode.BAD_SHAPE), ("x", RefusalCode.BAD_SHAPE))


@dataclass(frozen=True)
class Tagged:
    """A mapping whose ``tag`` key (``default`` when absent) picks the schema that reads the rest of it."""

    tag: str
    default: str
    schemas: Mapping[str, Schema]

    def convert(self, value: object, what: str) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise Refused(f"{what} must be a mapping, got {shown(value)}", code=RefusalCode.BAD_SHAPE)
        kind = value.get(self.tag, self.default)
        if not isinstance(kind, str) or kind not in self.schemas:  # a list or a mapping isn't hashed
            raise Refused(f"{what}: unknown {self.tag} {shown(kind)}", code=RefusalCode.UNKNOWN_KIND)
        read = self.schemas[kind].read(value, f"{what} ({kind})", envelope=(self.tag,))
        return MappingProxyType({**read, self.tag: kind})

    @property
    def bad(self) -> Bad:
        return (([], RefusalCode.BAD_SHAPE), ({self.tag: "nothing"}, RefusalCode.UNKNOWN_KIND))


Item = Nested | Tagged


@dataclass(frozen=True)
class ListOf:
    """A list of at most ``max_items`` items, each read by ``item``; counted before any item is read (§5.4)."""

    item: Item
    max_items: int

    def convert(self, value: object, what: str) -> tuple[Mapping[str, object], ...]:
        if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
            raise Refused(f"{what} must be a list, got {type(value).__name__}", code=RefusalCode.BAD_SHAPE)
        if item_count(value) > self.max_items:
            raise Refused(f"{what} holds at most {self.max_items} items", code=RefusalCode.OVER_BUDGET)
        return tuple(self.item.convert(v, f"{what}[{i}]") for i, v in enumerate(value))

    @property
    def bad(self) -> Bad:
        return (({}, RefusalCode.BAD_SHAPE), ("x", RefusalCode.BAD_SHAPE), ([7], RefusalCode.BAD_SHAPE))


@dataclass(frozen=True)
class MapOf:
    """A mapping of names (read by ``key``) to values read by ``value``, at most ``max_items`` of them."""

    key: Text | Identity
    value: Nested
    max_items: int

    def convert(self, value: object, what: str) -> Mapping[str, Mapping[str, object]]:
        if not isinstance(value, Mapping):
            raise Refused(f"{what} must be a mapping, got {type(value).__name__}", code=RefusalCode.BAD_SHAPE)
        if item_count(value) > self.max_items:
            raise Refused(f"{what} holds at most {self.max_items} entries", code=RefusalCode.OVER_BUDGET)
        out = {self.key.convert(k, f"a name in {what}"): v for k, v in value.items()}
        return MappingProxyType({k: self.value.convert(v, f"{what} {k}") for k, v in out.items()})

    @property
    def bad(self) -> Bad:
        return (([], RefusalCode.BAD_SHAPE), ({7: {}}, self.key.bad[0][1]))


class Converter(Protocol):
    """What reads one field: ``convert`` turns an untrusted value into the engine's or refuses it with a code, and
    ``bad`` lists the values it must refuse, with their codes (the generated rejection tests' input). The converters
    are this module's and ``simcore.core.converters``'s."""

    def convert(self, value: object, what: str) -> object: ...

    @property
    def bad(self) -> Bad: ...


@dataclass(frozen=True)
class Field:
    """One field of a format. An optional field takes ``default`` when absent; a ``nullable`` one may be null.
    ``lookup`` is for per-id tables: the value an id with no entry gets in the generated lookup array."""

    name: str
    convert: Converter
    required: bool = True
    default: object = None
    nullable: bool = False
    lookup: float | None = None

    def read(self, value: object, what: str) -> object:
        if value is None and self.nullable:
            return None
        return self.convert.convert(value, f"{what}.{self.name}")


@dataclass(frozen=True)
class Schema:
    """A closed set of fields. ``reserved`` names keys a later version of the format will take, each refused with
    its reason (scene v1 refuses ``zones``: zones arrive with a later scene version, Phase 2)."""

    fields: tuple[Field, ...]
    reserved: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):  # a schema contradicting itself is a programming error, not bad input
            raise TypeError(f"a schema names a field twice: {sorted(names)}")
        object.__setattr__(self, "reserved", MappingProxyType(dict(self.reserved)))

    @property
    def by_name(self) -> Mapping[str, Field]:
        return MappingProxyType({f.name: f for f in self.fields})

    def read(self, raw: object, what: str, *, envelope: Sequence[str] = ()) -> Mapping[str, object]:
        """``raw`` held to this schema's keys (and the ``envelope`` keys its caller reads, such as ``version``)
        with every field converted, or a Refused that names the field at fault."""
        if isinstance(raw, Mapping):
            for key, reason in self.reserved.items():
                if key in raw:
                    raise Refused(f"{what}.{key}: {reason}", code=RefusalCode.UNKNOWN_FIELD, field=key)
        required = {f.name for f in self.fields if f.required}
        optional = {f.name for f in self.fields if not f.required} | set(envelope)
        v = known_keys(raw, what, required=required, optional=optional)
        return MappingProxyType({f.name: f.read(v[f.name], what) if f.name in v else f.default for f in self.fields})

    def check(self, values: Mapping[str, object], what: str) -> Mapping[str, object]:
        """The fields of a hand-built value converted by the same rules as ``read``, for a validating constructor."""
        return MappingProxyType({f.name: f.read(values[f.name], what) for f in self.fields})


Migration = Callable[[Mapping[str, object]], Mapping[str, object]]


def read_version(raw: object, what: str) -> int:
    """A document's ``version``: a whole number from 0, checked before anything else so a newer document is refused
    for its version, never for the fields it added. ``true`` and ``0.0`` are not version 0; no version is refused."""
    if not isinstance(raw, Mapping):
        raise Refused(f"{what} must be a mapping, got {type(raw).__name__}", code=RefusalCode.BAD_SHAPE)
    version = raw.get("version")
    if type(version) is not int or version < 0:
        raise Refused(f"{what} needs a version (a whole number), got {shown(version)}", code=RefusalCode.BAD_VERSION)
    return version


def _tick_fields(schema: Schema) -> list[str]:
    """Every field named for ticks in ``schema`` and the schemas it nests: a word, not a substring (stick_m is fine)."""
    found, stack = [], [schema]
    while stack:
        current = stack.pop()
        for f in current.fields:
            if {"tick", "ticks"} & set(f.name.split("_")):
                found.append(f.name)
            convert: object = f.convert.item if isinstance(f.convert, ListOf) else f.convert
            if isinstance(convert, Nested):
                stack.append(convert.schema)
            elif isinstance(convert, Tagged):
                stack.extend(convert.schemas.values())
    return sorted(found)


@dataclass(frozen=True)
class Format:
    """A versioned data format: its name, current version and schema, the old versions it refuses with a reason,
    and, only for a format other people hold (saves, logs, bug reports, later mods), its migrations.

    ``migrations`` is the registry the checklist names, keyed by format (this object) and version: entry ``v`` turns
    a version-``v`` document into a version ``v + 1`` one. A repo-only format never migrates: its files are all in
    this repository, so a change bumps the version, updates them, and refuses the old version with a test.
    """

    name: str
    version: int
    schema: Schema
    held_by_others: bool = False
    refused: Mapping[int, str] = field(default_factory=lambda: MappingProxyType({}))
    migrations: Mapping[int, Migration] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if ticks := _tick_fields(self.schema):
            raise TypeError(f"content stores time in seconds, never ticks: {ticks} (tile §3.2)")
        if self.migrations and not self.held_by_others:
            raise TypeError(f"{self.name} is repo-only: bump its version and refuse the old one, never migrate")
        if any(not 0 <= v < self.version for v in (*self.migrations, *self.refused)):
            raise TypeError(f"{self.name}: a migration or a refusal names a version at or past {self.version}")
        object.__setattr__(self, "refused", MappingProxyType(dict(self.refused)))
        object.__setattr__(self, "migrations", MappingProxyType(dict(self.migrations)))

    def read(self, raw: object, what: str) -> Mapping[str, object]:
        """``raw`` at this format's version, migrated to it if it is older and has a migration, or a Refused."""
        version = read_version(raw, what)
        if version in self.refused:
            raise Refused(
                f"{what} version must be {self.version}, got {version}: {self.refused[version]}",
                code=RefusalCode.BAD_VERSION,
            )
        doc: Mapping[str, object] = raw  # type: ignore[assignment]  # read_version proved it is a mapping
        while version < self.version and version in self.migrations:
            doc = {**self.migrations[version](doc), "version": version + 1}
            version += 1
        if version != self.version:
            message = f"{what} version must be {self.version}, got {shown(version)}"  # bounded: a version may be huge
            raise Refused(message, code=RefusalCode.BAD_VERSION)
        return self.schema.read(doc, what, envelope=("version",))
