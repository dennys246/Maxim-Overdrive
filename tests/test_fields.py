"""The field registry (sim_core.md §6): its committed artifact, its writers and its inputs agree with the code."""

import importlib.util
from pathlib import Path

import pytest

from simcore.core import fields, physics

ARTIFACT = Path(__file__).resolve().parents[1] / "docs" / "generated" / "fields.md"


def test_the_committed_artifact_is_the_registry_byte_for_byte():
    # Regenerate with: PYTHONPATH=src python -c 'from simcore.core.fields import render; print(render(), end="")'
    assert ARTIFACT.read_bytes() == fields.render().encode()


def test_the_law_names_are_the_law_tuple_in_order():
    assert tuple(law.name for law in physics.DEFAULT_LAWS) == fields.LAW_NAMES


def test_every_declared_writer_is_a_known_writer_and_named_once_per_field():
    for spec in fields.FIELDS:
        assert set(spec.writers) <= set(fields.WRITERS), spec.name
        assert len(set(spec.writers)) == len(spec.writers), spec.name
    assert len({spec.name for spec in fields.FIELDS}) == len(fields.FIELDS)


def test_every_field_lists_its_writers_laws_first_in_tuple_order():
    order = {name: i for i, name in enumerate(fields.WRITERS)}
    for spec in fields.FIELDS:
        assert [order[w] for w in spec.writers] == sorted(order[w] for w in spec.writers), spec.name


def test_every_input_kind_has_one_resolver_and_it_is_a_law():
    # §5.1: one resolver per input kind. Each kind is listed once, so it can't name two resolvers.
    names = [i.name for i in fields.INPUTS]
    assert len(set(names)) == len(names)
    assert all(i.resolver in fields.LAW_NAMES for i in fields.INPUTS)


def test_every_input_names_a_known_appender_and_it_is_a_core_module():
    """PR 3 review S2 (Architecture): the appender was a bare string, so a typo passed every test."""
    assert all(i.appender in fields.APPENDERS for i in fields.INPUTS)
    for appender in fields.APPENDERS:
        assert importlib.util.find_spec(f"simcore.core.{appender}") is not None, appender


def test_every_law_writes_only_fields_that_declare_it():
    for law in physics.DEFAULT_LAWS:
        assert law.writes, law.name  # each law in the tuple writes something
        assert all(law.name in fields.writers_of(f) for f in law.writes), law.name


def test_an_unknown_field_has_no_writers():
    with pytest.raises(KeyError):
        fields.writers_of("pressure")
