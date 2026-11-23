"""Every data format's rejection tests, generated from its schema (checklist step 3b: one schema and one reader per
format; flexibility review, Architecture 7).

Each ``Format`` in the engine is found by scanning its modules, fail closed: a format with no sample here is a failure,
so a new format gets its tests by being declared and given a valid document. For each, the walk below feeds every
field of every level each value its converter lists as bad, deletes each required field, adds an unknown key at each
level, and checks the code the refusal carries, not its words. The hand-written tests that remain elsewhere hold the
rules a schema can't state (an id used twice, a default outside its bounds, a box with min above max).
"""

from __future__ import annotations

import copy
import importlib
import pkgutil
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

import maxim_overdrive
import simcore
from simcore.core import schema as schema_module
from simcore.core.limits import ACTION_LIMITS, ActionLimits
from simcore.core.materials import MATERIAL, MATERIAL_TABLE, MaterialTable
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.scene import PRIMITIVE, SCENE, Scene
from simcore.core.schema import (
    Field,
    Format,
    Identity,
    ListOf,
    MapOf,
    Nested,
    Real,
    Rgb,
    Schema,
    Tagged,
    Text,
    Vector,
    Whole,
    read_version,
)
from simcore.protocol.tiers import RIG_PROFILE, RigProfile

ROOT = Path(__file__).resolve().parents[1]


def _yaml(rel: str) -> dict[str, Any]:
    doc: dict[str, Any] = yaml.safe_load((ROOT / rel).read_text())
    return doc


def _scene(doc: Mapping[str, object]) -> Scene:
    return Scene.from_dict(doc)  # the scene's reader reads and builds in one call


def _scene_sample() -> dict[str, Any]:
    """The alley fixture plus one primitive of every kind it lacks, so the walk reaches each tagged kind's fields
    (step 3b(b) review, Executor S1: the alley is all boxes, so the cylinder went unwalked)."""
    doc = _yaml("tests/fixtures/scenes/alley_box.yaml")
    post = {"kind": "cylinder", "name": "post", "material": "wood", "center_xy_m": [3.0, 2.0], "radius_m": 0.2}
    doc["primitives"].append({**post, "z_m": [0.4, 1.6]})
    return doc


# Every format, a valid document of it, and what builds the format's type from a read document.
SAMPLES: dict[str, tuple[Format, dict[str, Any], Callable[[Any], object]]] = {
    "material table": (MATERIAL_TABLE, _yaml("data/materials/core.yaml"), MaterialTable.from_document),
    "action limits": (ACTION_LIMITS, _yaml("data/world/actions.yaml"), ActionLimits.from_document),
    "rig profile": (RIG_PROFILE, _yaml("data/rigs/rig.yaml"), RigProfile.from_document),
    "scene": (SCENE, _scene_sample(), lambda doc: doc),
}


def _read_and_build(name: str, doc: object) -> object:
    fmt, _, build = SAMPLES[name]
    if fmt is SCENE:
        return _scene(doc)  # type: ignore[arg-type]
    return build(fmt.read(doc, name))


def _declared_formats() -> dict[str, Format]:
    found: dict[str, Format] = {}
    packages = [(simcore.__path__, "simcore."), (maxim_overdrive.__path__, "maxim_overdrive.")]
    for info in (i for path, prefix in packages for i in pkgutil.walk_packages(path, prefix)):
        if info.name.startswith("simcore.adapters.sem"):
            continue  # imports maxim optionally; it declares no format
        module = importlib.import_module(info.name)
        found |= {v.name: v for v in vars(module).values() if isinstance(v, Format)}
    return found


def test_every_declared_format_has_a_sample_and_every_sample_builds():
    assert set(_declared_formats()) == set(SAMPLES)
    for name, (fmt, doc, _) in SAMPLES.items():
        assert doc["version"] == fmt.version, name
        _read_and_build(name, doc)


# -- the walk: every field path of a format over its sample -----------------------------------------------------------

Case = tuple[str, Callable[[dict[str, Any]], None], RefusalCode]
VISITED: set[tuple[int, str]] = set()  # (a Tagged converter, a kind) the walk descended into


def _set(path: tuple[object, ...], value: object) -> Callable[[dict[str, Any]], None]:
    def edit(doc: dict[str, Any]) -> None:
        target: Any = doc
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value

    return edit


def _drop(path: tuple[object, ...]) -> Callable[[dict[str, Any]], None]:
    def edit(doc: dict[str, Any]) -> None:
        target: Any = doc
        for step in path[:-1]:
            target = target[step]
        del target[path[-1]]

    return edit


def _inner(convert: object, value: Any, path: tuple[object, ...]) -> Iterator[tuple[Schema, Any, tuple[object, ...]]]:
    """The schemas nested in one field, with the sample's value at each and its path."""
    if isinstance(convert, Nested):
        yield convert.schema, value, path
    elif isinstance(convert, Tagged) and isinstance(value, Mapping):
        kind = value.get(convert.tag, convert.default)
        VISITED.add((id(convert), kind))
        yield convert.schemas[kind], value, path
    elif isinstance(convert, ListOf) and value:
        for i, item in enumerate(value):  # every item, so each kind of a tagged list is reached
            yield from _inner(convert.item, item, (*path, i))
    elif isinstance(convert, MapOf) and value:
        key = next(iter(value))
        yield convert.value.schema, value[key], (*path, key)


def _cases(schema: Schema, doc: Mapping[str, Any], path: tuple[object, ...] = ()) -> Iterator[Case]:
    where = "/".join(map(str, path)) or "top"
    yield f"{where}: an unknown key", _set((*path, "zz_unknown"), 1), RefusalCode.UNKNOWN_FIELD
    for key in schema.reserved:
        yield f"{where}: reserved {key}", _set((*path, key), []), RefusalCode.UNKNOWN_FIELD
    for f in schema.fields:
        here = (*path, f.name)
        if f.required:
            yield f"{where}: no {f.name}", _drop(here), RefusalCode.MISSING_FIELD
        for value, code in f.convert.bad:
            yield f"{where}: {f.name} = {value!r}", _set(here, value), code
        if isinstance(f.convert, ListOf | MapOf):
            too_many = [doc[f.name][0]] * (f.convert.max_items + 1) if isinstance(f.convert, ListOf) else None
            if too_many is not None and doc.get(f.name):
                yield f"{where}: too many {f.name}", _set(here, too_many), RefusalCode.OVER_BUDGET
        if f.name in doc:
            for inner, value, inner_path in _inner(f.convert, doc[f.name], here):
                yield from _cases(inner, value, inner_path)


def _all_cases() -> list[tuple[str, str, Callable[[dict[str, Any]], None], RefusalCode]]:
    out = []
    for name, (fmt, doc, _) in SAMPLES.items():
        out += [(name, label, edit, code) for label, edit, code in _cases(fmt.schema, doc)]
    return out


CASES = _all_cases()


@pytest.mark.parametrize(("name", "label", "edit", "code"), CASES, ids=[f"{c[0]}: {c[1]}" for c in CASES])
def test_every_field_of_every_format_refuses_what_its_schema_refuses(name, label, edit, code):
    doc = copy.deepcopy(SAMPLES[name][1])
    edit(doc)
    with pytest.raises(Refused) as caught:
        _read_and_build(name, doc)
    assert caught.value.code is code, (label, str(caught.value))


def test_the_walk_reaches_every_level_of_every_format():
    """A walk that stopped at the top would pass the test above; this counts what it reached (measure fuzz reach)."""
    reached = {(c[0], c[1].split(":")[0]) for c in CASES}
    assert ("material table", "materials/air") in reached
    assert {("action limits", "ignite"), ("action limits", "strike")} <= reached
    assert {("scene", "spawns/0"), ("scene", "primitives/0")} <= reached
    assert len(CASES) > 250
    tagged = {id(c): c for fmt, _, _ in SAMPLES.values() for f in _walk_fields(fmt.schema) for c in _tagged(f.convert)}
    missing = {(t.tag, k) for i, t in tagged.items() for k in t.schemas if (i, k) not in VISITED}
    assert tagged
    assert not missing, f"no sample reaches these kinds, so their fields go unwalked: {missing}"


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_every_optional_field_left_out_takes_its_default(name):
    fmt, sample, _ = SAMPLES[name]
    optional = [f for f in fmt.schema.fields if not f.required and f.name in sample]
    for f in optional:
        doc = copy.deepcopy(sample)
        del doc[f.name]
        assert fmt.read(doc, name)[f.name] == f.default
        _read_and_build(name, doc)


@pytest.mark.parametrize("name", sorted(SAMPLES))
@pytest.mark.parametrize("version", [None, True, 0.0, "1", -1, "missing", "next"])
def test_every_format_refuses_a_version_it_does_not_know(name, version):
    fmt, sample, _ = SAMPLES[name]
    doc = copy.deepcopy(sample)
    if version == "missing":
        del doc["version"]
    else:
        doc["version"] = fmt.version + 1 if version == "next" else version
    with pytest.raises(Refused) as caught:
        _read_and_build(name, doc)
    assert caught.value.code is RefusalCode.BAD_VERSION


@pytest.mark.parametrize("raw", [None, [], "version: 1", 3])
def test_a_document_that_is_not_a_mapping_has_no_version(raw):
    with pytest.raises(Refused) as caught:
        read_version(raw, "doc")
    assert caught.value.code is RefusalCode.BAD_SHAPE


# -- the schema's own rules -------------------------------------------------------------------------------------------


def test_content_stores_time_in_seconds_never_ticks():
    with pytest.raises(TypeError, match="never ticks"):
        Format("doc", 1, Schema((Field("hold_ticks", Whole(0, 10)),)))
    deep = Schema((Field("items", ListOf(Nested(Schema((Field("hold_ticks", Whole(0, 10)),))), 4)),))
    with pytest.raises(TypeError, match="never ticks"):  # however deep it is nested
        Format("doc", 1, deep)
    tagged = Tagged("kind", "", {"a": Schema((Field("delay_ticks", Whole(0, 9)),))})
    with pytest.raises(TypeError, match="never ticks"):
        Format("doc", 1, Schema((Field("event", tagged),)))


def test_a_schema_cannot_name_a_field_twice():
    with pytest.raises(TypeError, match="twice"):
        Schema((Field("a", Real()), Field("a", Real())))


def _walk_fields(s: Schema) -> Iterator[Field]:
    for f in s.fields:
        yield f
        c = f.convert
        inner = (
            (c,)
            if isinstance(c, Nested)
            else (c.item,)
            if isinstance(c, ListOf)
            else (c.value,)
            if isinstance(c, MapOf)
            else ()
        )
        for i in inner:
            yield from (
                _walk_fields(i.schema)
                if isinstance(i, Nested)
                else (g for t in i.schemas.values() for g in _walk_fields(t))
            )
        if isinstance(c, Tagged):
            yield from (g for t in c.schemas.values() for g in _walk_fields(t))


def _tagged(convert: object) -> list[Tagged]:
    if isinstance(convert, Tagged):
        return [convert]
    if isinstance(convert, ListOf):
        return _tagged(convert.item)
    return []


def test_the_tick_rule_reads_words_not_letters():
    Format("doc", 1, Schema((Field("stick_length_m", Real()),)))  # "tick" inside a word is not a tick count
    with pytest.raises(TypeError, match="never ticks"):
        Format("doc", 1, Schema((Field("delay_ticks", Whole(0, 9)),)))


def test_no_shipped_format_has_a_field_counted_in_ticks():
    for fmt, _, _ in SAMPLES.values():
        assert not [f.name for f in _walk_fields(fmt.schema) if "tick" in f.name], fmt.name


@pytest.mark.parametrize(
    ("convert", "value", "rule"),
    [
        (Real(lo=0.0), -1.0, "at least 0"),
        (Real(lo=0.0, lo_open=True), 0.0, "above 0"),
        (Real(hi=1.0), 2.0, "at most 1"),
        (Real(lo=0.0, hi=1.0), 2.0, "at least 0 and at most 1"),
        (Vector(2, 1.0, positive=True), [0.0, 0.5], "above 0 and within 1"),
        (Whole(0, 3), 4, "from 0 to 3"),
    ],
)
def test_a_bound_names_its_rule(convert, value, rule):
    with pytest.raises(Refused, match=rule) as caught:
        convert.convert(value, "x")
    assert caught.value.code is RefusalCode.OUT_OF_RANGE


def test_a_map_counts_its_entries_before_reading_them():
    m = MapOf(Text(), Nested(Schema(())), max_items=1)
    with pytest.raises(Refused) as caught:
        m.convert({"a": {}, "b": {}}, "x")
    assert caught.value.code is RefusalCode.OVER_BUDGET
    assert m.convert({"a": {}}, "x") == {"a": {}}


def test_a_tagged_mapping_reads_its_default_kind_and_keeps_its_tag():
    t = Tagged("kind", "a", {"a": Schema((Field("n", Whole(0, 9)),)), "b": Schema(())})
    assert dict(t.convert({"n": 3}, "x")) == {"n": 3, "kind": "a"}
    assert dict(t.convert({"kind": "b"}, "x")) == {"kind": "b"}
    with pytest.raises(Refused) as caught:
        t.convert({"kind": ["a"]}, "x")  # a list is not hashed
    assert caught.value.code is RefusalCode.UNKNOWN_KIND


def test_an_identity_converter_is_the_identity_key_rule():
    assert Identity().convert("crate_7", "x") == "crate_7"


# -- versions and migrations (checklist step 3b: only for formats other people hold) ----------------------------------


def _held(**kwargs: Any) -> Format:
    return Format("save", 2, Schema((Field("n", Whole(0, 99)),)), held_by_others=True, **kwargs)


def test_a_format_other_people_hold_migrates_an_old_document_step_by_step():
    seen: list[int] = []

    def v0(doc: Mapping[str, object]) -> Mapping[str, object]:
        seen.append(0)
        return {"version": 0, "count": doc["count"]}

    def v1(doc: Mapping[str, object]) -> Mapping[str, object]:
        seen.append(int(doc["version"]))  # type: ignore[call-overload]  # the migration before set it
        return {"n": doc["count"]}

    fmt = _held(migrations={0: v0, 1: v1})
    assert dict(fmt.read({"version": 0, "count": 5}, "save")) == {"n": 5}
    assert seen == [0, 1]
    assert dict(fmt.read({"version": 2, "n": 7}, "save")) == {"n": 7}


def test_a_version_with_no_migration_is_refused_not_guessed():
    fmt = _held(migrations={1: lambda doc: {"n": doc["count"]}})
    with pytest.raises(Refused, match="version must be 2, got 0") as caught:
        fmt.read({"version": 0, "count": 5}, "save")
    assert caught.value.code is RefusalCode.BAD_VERSION


def test_a_repo_only_format_cannot_register_a_migration():
    with pytest.raises(TypeError, match="never migrate"):
        Format("scene", 2, Schema(()), migrations={1: dict})


@pytest.mark.parametrize("version", [2, 3, -1])
def test_a_migration_or_refusal_must_name_an_older_version(version):
    with pytest.raises(TypeError, match="at or past"):
        _held(refused={version: "gone"})


def test_no_shipped_format_migrates_because_none_is_held_by_others_yet():
    """Saves (step 9), logs (5a) and bug reports are the first formats other people hold; each repo-only format
    refuses an old version instead (scene v0, rig v0), with a test."""
    for fmt, _, _ in SAMPLES.values():
        assert not fmt.held_by_others, fmt.name
        assert not fmt.migrations, fmt.name
    assert set(SCENE.refused) == {0}
    assert set(RIG_PROFILE.refused) == {0}


def test_the_schema_module_reads_no_files():
    assert "yaml" not in vars(schema_module)
    assert "Path" not in vars(schema_module)


def test_a_constructor_runs_the_readers_rules_on_what_it_is_handed():
    """``Schema.check`` is how a validating constructor applies a format's field rules: the same converters, no keys."""
    colour = Schema((Field("rgb", Rgb()), Field("note", Text(), required=False, nullable=True)))
    assert dict(colour.check({"rgb": [1, 2, 3], "note": None}, "c")) == {"rgb": (1, 2, 3), "note": None}
    with pytest.raises(Refused) as caught:
        colour.check({"rgb": [1, 2, 300], "note": None}, "c")
    assert caught.value.code is RefusalCode.OUT_OF_RANGE
    assert set(colour.by_name) == {"rgb", "note"}


def test_a_tagged_mapping_refuses_its_own_bad_values():
    for value, code in PRIMITIVE.bad:
        with pytest.raises(Refused) as caught:
            PRIMITIVE.convert(value, "p")
        assert caught.value.code is code


def test_the_material_tables_lookup_arrays_are_generated_from_the_schema():
    table = MaterialTable.from_document(MATERIAL_TABLE.read(SAMPLES["material table"][1], "t"))
    marked = {f.name: f.lookup for f in MATERIAL.fields if f.lookup is not None}
    assert set(table.lookups) == set(marked)
    for name, fill in marked.items():
        array = table.lookups[name]
        assert not array.flags.writeable
        for m in table.by_name.values():
            want = getattr(m, name)
            assert array[m.id] == (fill if want is None else want), (name, m.name)
    assert table.conductivity is table.lookups["conductivity_w_mk"]


# -- each format's schema, pinned -------------------------------------------------------------------------------------
# The walk derives its cases from the schema, so it proves the reader keeps the schema, never that the schema is right:
# a field made optional loses its "missing" case and the walk stays green (step 3b(b) review, Executor S1, measured).
# Every format's fields, with their rules, are therefore pinned in a committed file; a change to one is a reviewed diff
# of tests/fixtures/formats/schemas.txt, made with the version bump and the refusal test it needs.

SNAPSHOT = ROOT / "tests" / "fixtures" / "formats" / "schemas.txt"


def _describe(schema: Schema, prefix: str) -> list[str]:
    lines = [f"{prefix} reserved {sorted(schema.reserved)}"] if schema.reserved else []
    for f in schema.fields:
        flags = "required" if f.required else f"optional, default {f.default!r}"
        flags += ", nullable" if f.nullable else ""
        flags += f", lookup {f.lookup!r}" if f.lookup is not None else ""
        c = f.convert
        inner = c.item if isinstance(c, ListOf) else c.value if isinstance(c, MapOf) else c
        lines.append(f"{prefix}.{f.name}: {type(c).__name__} {_rule(c)} ({flags})")
        if isinstance(inner, Nested):
            lines += _describe(inner.schema, f"{prefix}.{f.name}")
        elif isinstance(inner, Tagged):
            for kind, s in sorted(inner.schemas.items()):
                lines += _describe(s, f"{prefix}.{f.name}[{inner.tag}={kind}]")
    return lines


def _rule(c: object) -> str:
    if isinstance(c, ListOf | MapOf):
        return f"max {c.max_items}"
    if isinstance(c, Nested | Tagged):
        return ""
    return repr(c)


def _snapshot() -> str:
    out = []
    for name, (fmt, _, _) in sorted(SAMPLES.items()):
        refused = {v: "refused" for v in fmt.refused}
        out.append(f"{name} v{fmt.version} held_by_others={fmt.held_by_others} old={refused}")
        out += _describe(fmt.schema, f"  {name}")
    return "\n".join(out) + "\n"


def test_every_formats_schema_is_the_one_committed():
    assert _snapshot() == SNAPSHOT.read_text(), "a format's schema changed: review it, then regenerate schemas.txt"


def test_a_list_too_long_to_count_is_over_budget_not_a_crash():
    """Trust T1-N1: len(range(10**20)) raises OverflowError."""
    with pytest.raises(Refused) as caught:
        ListOf(Nested(Schema(())), max_items=4).convert(range(10**20), "x")
    assert caught.value.code is RefusalCode.OVER_BUDGET
