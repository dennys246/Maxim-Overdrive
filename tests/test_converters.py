"""simcore.core.converters: each converter refuses every value it lists as bad with that value's code, and reads what
it should (the wire's millimetre vectors, words, flags, digests and tokens)."""

from __future__ import annotations

import pytest

from simcore.core.converters import OPAQUE_ALPHABET, Choice, Digest, Flag, Opaque, Wholes
from simcore.core.digest import digest
from simcore.core.refusals import Refused
from simcore.core.schema import Converter, Real, Whole, item_count

CONVERTERS = [Wholes(3, -5, 5), Wholes(2, 0, 2**31 - 1), Choice(("pause", "resume")), Flag(), Digest(), Opaque(8)]


@pytest.mark.parametrize(
    ("converter", "bad", "code"), [(c, bad, code) for c in CONVERTERS for bad, code in c.bad], ids=repr
)
def test_each_converter_refuses_each_value_it_lists(converter, bad, code):
    with pytest.raises(Refused) as refused:
        converter.convert(bad, "field")
    assert refused.value.code is code


def test_wholes_reads_ints_and_nothing_posing_as_one():
    assert Wholes(3, -5, 5).convert([1, -5, 5], "p") == (1, -5, 5)
    assert Wholes(2, 0, 9).convert((0, 9), "p") == (0, 9)


def test_choice_takes_only_its_words_and_only_exact_strings():
    assert Choice(("pause",)).convert("pause", "op") == "pause"
    with pytest.raises(Refused):
        Choice(("pause",)).convert(type("_Word", (str,), {})("pause"), "op")


@pytest.mark.parametrize("value", [True, False])
def test_flag_reads_a_bool(value):
    assert Flag().convert(value, "required") is value


def test_digest_reads_the_one_scheme_this_build_knows():
    good = digest([1])
    assert Digest().convert(good, "catalogue") == good


def test_an_opaque_value_is_read_whole_and_never_echoed():
    token = "Ab3_-" + "x" * 3
    assert Opaque(8).convert(token, "token") == token
    with pytest.raises(Refused) as refused:
        Opaque(8).convert("not a secret!", "token")
    assert "secret" not in str(refused.value)
    assert set("-_") <= OPAQUE_ALPHABET
    assert len(OPAQUE_ALPHABET) == 64  # the URL-safe base64 alphabet secrets.token_urlsafe writes


def test_every_converter_meets_the_converter_protocol():
    def held(converter: Converter) -> int:  # mypy holds each to the protocol at this call
        return len(converter.bad)

    assert all(held(c) > 0 for c in [*CONVERTERS, Real(), Whole(0, 1)])


def test_item_count_counts_a_container_too_long_to_count_as_past_any_budget():
    assert item_count([1, 2]) == 2
    assert item_count(range(10**20)) == 2**63
