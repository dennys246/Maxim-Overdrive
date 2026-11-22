"""The refusal codes (WT-S1) and the versioned digest (checklist step 3b part b).

The codes are a wire and log vocabulary from the moment they ship, so they are pinned here in order: a new code is
appended, never inserted, renamed or removed. A refusal from every gate carries one, and the membrane tells an agent
the code, never the words.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

from simcore.core import digest as digest_module
from simcore.core.digest import SCHEME, canonical, check_digest, digest
from simcore.core.refusals import RefusalCode, Refused

# Every code, in order, as shipped. Appending is the only change allowed (tile §3.4; checklist step 5a).
SHIPPED = (
    "bad_json", "unknown_kind", "unknown_field", "busy",
    "not_int", "bad_shape", "out_of_range", "outside_extent", "rate_limited", "coalesced",
    "out_of_reach", "not_on_surface", "ambiguous_point", "region_gone", "no_igniter", "over_item_max", "pilot_live",
    "restrike_wait",
    "no_body", "no_path", "unreachable",
    "missing_field", "not_finite", "bad_version", "bad_identity_key", "bad_name", "no_region", "not_solid",
    "not_on_region", "not_burning", "wrong_target", "namesake", "name_taken", "unknown_material", "over_budget",
    "space_taken", "too_small", "duplicate_key",
)  # fmt: skip


def test_the_codes_are_append_only():
    values = tuple(c.value for c in RefusalCode)
    assert values[: len(SHIPPED)] == SHIPPED, "a shipped code was renamed, removed or moved"
    assert len(values) == len(SHIPPED), "a new code: append it to SHIPPED here, after the last one"


def test_every_code_is_a_lower_snake_case_word_and_its_own_name():
    for code in RefusalCode:
        assert code.value == code.name.lower()
        assert code.value.replace("_", "").isalpha()


def test_tile_3_4s_codes_are_all_present():
    tile = {
        "bad_json", "unknown_kind", "unknown_field", "busy", "not_int", "bad_shape", "out_of_range", "outside_extent",
        "rate_limited", "coalesced", "out_of_reach", "not_on_surface", "ambiguous_point", "region_gone", "no_igniter",
        "over_item_max", "pilot_live", "restrike_wait", "no_body", "no_path", "unreachable",
    }  # fmt: skip
    assert tile <= {c.value for c in RefusalCode}


def test_a_refusal_needs_a_code_from_the_vocabulary():
    assert Refused("x", code=RefusalCode.BAD_SHAPE).code is RefusalCode.BAD_SHAPE
    assert Refused("x", code="bad_shape").code is RefusalCode.BAD_SHAPE  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="not a valid RefusalCode"):
        Refused("x", code="no such code")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Refused("x")  # type: ignore[call-arg]  # keyword-only and required: a refusal can't forget its code


def test_what_an_agent_is_told_is_a_code_and_at_most_a_schema_field():
    assert Refused("power_w must be between 0 and 5e5, got 1e9", code=RefusalCode.OUT_OF_RANGE).agent_text == (
        "out_of_range"
    )
    assert Refused("words", code=RefusalCode.OUT_OF_RANGE, field="power_w").agent_text == "out_of_range (power_w)"
    assert isinstance(Refused("x", code=RefusalCode.BAD_SHAPE), ValueError)  # every old `except ValueError` holds


# -- the digest ------------------------------------------------------------------------------------------------------


def test_a_digest_names_its_hash_and_its_canonical_form():
    value = {"b": [1, 2.5, None, True], "a": "x"}
    text = '{"a":"x","b":[1,2.5,null,true]}'
    assert canonical(value) == text
    assert digest(value) == f"sha256/c14n-1:{hashlib.sha256(text.encode()).hexdigest()}"
    assert digest(value).startswith(SCHEME + ":")


def test_the_canonical_form_ignores_key_order_and_container_type():
    assert digest({"a": 1, "b": (1, 2)}) == digest({"b": [1, 2], "a": 1})
    assert digest({"a": 1}) != digest({"a": 1.0})  # an int and a float are different content


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ('q"\\', '"q\\"\\\\"'),
        ("\n\x00", '"\\u000a\\u0000"'),
        ("über", '"über"'),
        (False, "false"),
        (0.1, "0.1"),
        (1e300, "1e+300"),
        (-0.0, "0.0"),  # equal floats, one text (Determinism N4)
        ([], "[]"),
        ({}, "{}"),
    ],
)
def test_the_canonical_form_of_each_kind_of_value(value, text):
    assert canonical(value) == text


class _Str(str):
    pass


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        {1: "a"},
        b"raw",
        object(),
        {1.5},
        np.float64(1.5),  # a float subclass whose repr is np.float64(1.5) (Executor N1, Wire S3, Architecture A8)
        np.int64(3),
        _Str("x"),
        "\ud800",  # a lone surrogate, which a YAML file can carry (Determinism SF2)
        {"k": np.float32(0.5)},
    ],
)
def test_the_canonical_form_refuses_what_it_has_no_form_for(value):
    with pytest.raises(TypeError, match="c14n-1"):
        canonical(value)


def test_an_int_too_long_for_text_has_no_canonical_form():
    with pytest.raises(TypeError, match="c14n-1"):
        canonical(10**600)  # past what int-to-text allows at CPython's lowest per-process limit (640)
    assert canonical(10**599 - 1) == "9" * 599


def test_a_stored_digest_is_held_to_the_scheme_this_reader_knows():
    good = digest([1])
    assert check_digest(good, "d") == good
    for stored, code in [
        (good.replace("c14n-1", "c14n-2"), RefusalCode.BAD_VERSION),
        (good.replace("sha256", "sha512"), RefusalCode.BAD_VERSION),
        (good.split(":")[1], RefusalCode.BAD_SHAPE),  # no scheme: an unversioned hash is refused
        (good[:-1], RefusalCode.BAD_SHAPE),
        (good.upper(), RefusalCode.BAD_SHAPE),
        (7, RefusalCode.BAD_SHAPE),
    ]:
        with pytest.raises(Refused) as caught:
            check_digest(stored, "d")
        assert caught.value.code is code, stored


def test_the_digest_module_reads_nothing_and_keeps_no_state():
    assert {"open", "Path", "os", "json"}.isdisjoint(vars(digest_module))
