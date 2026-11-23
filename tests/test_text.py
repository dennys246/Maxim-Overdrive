"""simcore.core.text.player_text, the guest-text gate (boundaries \u00a75.3; O61, TB-N5): real text in many scripts
passes; every format character but a joiner between two visible characters is refused, and NFC runs before the cap.
"""

from __future__ import annotations

import unicodedata
from itertools import pairwise

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from simcore.core.refusals import RefusalCode, Refused
from simcore.core.text import player_text, visible_name
from simcore.core.text_tables import DEFAULT_IGNORABLE, EMOJI

ZWNJ, ZWJ = "\u200c", "\u200d"

# Real guest text from many scripts, each kept as typed (NFC already).
PASSES = [
    "hot noodles?",
    "\u0633\u0644\u0627\u0645\u200c\u062f\u0646\u06cc\u0627",  # Persian "hello world", ZWNJ inside the compound
    "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645",  # Persian "I want": the mi- prefix needs ZWNJ
    "\u0915\u094d\u200d\u0937",  # Devanagari: a half form with ZWJ
    "\u0d15\u0d4d\u200d",  # Malayalam chillu, ZWJ last: refused below (a joiner at the end)
    "\U0001f468\u200d\U0001f469\u200d\U0001f467",  # a family: ZWJ between pictographs
    "\u2764\ufe0f\u200d\U0001f525",  # a heart on fire: VS16 (a mark) before the ZWJ
    "\u4f60\u597d\uff0c\u4e16\u754c",  # Chinese with a fullwidth comma
    "\u0928\u092e\u0938\u094d\u0924\u0947",  # Hindi
    "\u05e9\u05dc\u05d5\u05dd",  # Hebrew, right to left without any control
    "caf\u00e9 \u2014 50% off!",
    "\u2764\ufe0f",  # a heart drawn red: one VS16 after a character with emoji forms (O65)
    "1\ufe0f\u20e3",  # a keycap: digit, VS16, the enclosing keycap
    "\u263a\ufe0e",  # a smiley drawn as text: VS15
    "\u2813\u280a\u2800\u281e\u2813\u2811\u2817\u2811",  # braille "hi there": its blank is its space (delta 2, N-S1)
    "\u2422 x",  # the BLANK SYMBOL, which draws
]


@pytest.mark.parametrize("text", [t for t in PASSES if not t.endswith(ZWJ)], ids=ascii)
def test_real_text_from_many_scripts_passes_as_typed(text):
    assert player_text(text, "speech", max_chars=64) == text


REFUSED = [
    ("a" + ZWNJ + ZWNJ + "b", "doubled"),
    (ZWNJ + "a", "first"),
    ("a" + ZWJ, "last"),
    ("\u0d15\u0d4d\u200d", "last, after a virama"),
    ("a " + ZWNJ + "b", "beside a space"),
    ("a" + ZWJ + "\u200b" + "b", "beside another format character"),
    ("a\u202eb", "a bidi override"),
    ("a\u2066b\u2069", "bidi isolates"),
    ("a\u200bb", "a zero-width space"),
    ("\ufeffa", "a byte-order mark"),
    ("a\u2060b", "a word joiner"),
    ("\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f", "a tag-sequence flag"),
    ("hi\U000e0041\U000e0042", "tag characters smuggling ASCII"),
    ("line\nbreak", "a newline"),
    ("a\tb", "a tab"),
    ("a\x00b", "a NUL"),
    ("a\u2028b", "a line separator"),
    ("a\ue000b", "private use"),
    ("a\U000e01f0b", "unassigned"),
]


@pytest.mark.parametrize(("text", "why"), REFUSED, ids=[why for _, why in REFUSED])
def test_every_other_format_or_control_character_is_refused(text, why):
    with pytest.raises(Refused) as refused:
        player_text(text, "speech", max_chars=64)
    assert refused.value.code is RefusalCode.BAD_TEXT, why


def test_nfc_runs_before_the_cap():
    decomposed = "e\u0301" * 6  # twelve code points, six after NFC
    assert player_text(decomposed, "speech", max_chars=6) == "\u00e9" * 6
    with pytest.raises(Refused):
        player_text("\u00e9" * 7, "speech", max_chars=6)


@pytest.mark.parametrize("bad", ["", "   ", "\u3000"])
def test_empty_or_all_space_text_is_refused(bad):
    with pytest.raises(Refused) as refused:
        player_text(bad, "speech", max_chars=10)
    assert refused.value.code is RefusalCode.BAD_TEXT


@pytest.mark.parametrize("bad", [7, None, b"hi", type("_Text", (str,), {})("hi")])
def test_only_a_plain_string_is_text(bad):
    with pytest.raises(Refused) as refused:
        player_text(bad, "speech", max_chars=10)
    assert refused.value.code is RefusalCode.BAD_SHAPE


def test_a_lone_surrogate_is_refused_before_normalising():
    with pytest.raises(Refused) as refused:
        player_text("a\ud800b", "speech", max_chars=10)
    assert refused.value.code is RefusalCode.BAD_TEXT


def test_a_refusal_never_echoes_the_text():
    with pytest.raises(Refused) as refused:
        player_text("my secret\u202e", "speech", max_chars=64)
    assert "secret" not in str(refused.value)


@settings(max_examples=300, deadline=None)
@given(st.text(max_size=40))
def test_whatever_passes_is_nfc_within_its_cap_and_holds_no_lone_format_character(text):
    codes: set[RefusalCode] = set()
    try:
        out = player_text(text, "speech", max_chars=20)
    except Refused as refused:  # its one code for characters; anything else escaping fails the test
        codes.add(refused.code)
        out = ""
    assert codes <= {RefusalCode.BAD_TEXT}
    if codes:
        return
    assert unicodedata.normalize("NFC", out) == out
    assert 0 < len(out) <= 20
    for i, ch in enumerate(out):
        if unicodedata.category(ch) == "Cf":
            assert ch in (ZWNJ, ZWJ)
            assert 0 < i < len(out) - 1


def test_the_name_rule_is_text_s_too():
    assert visible_name("crate")
    assert not visible_name("cr\u200bate")


# Default-ignorable code points render as nothing, so a run of them can hide content (O65; review T-B2, E-S4)
HIDDEN = [
    ("a\ufe00\ufe01\ufe02", "a run of variation selectors after a letter"),
    ("a\ufe0f", "a variation selector after a character with no emoji forms"),
    ("\u2764\ufe0f\ufe0f", "two variation selectors"),
    ("x\U000e0100", "a supplementary variation selector"),
    ("a\u034fb", "the combining grapheme joiner"),
    ("a\u180bb", "a Mongolian free variation selector"),
    ("\u2764\ufe0f\u200d\ufe0f", "a ZWJ before a variation selector"),
    ("\u3164", "a Hangul filler alone"),
    ("a\u115fb", "a Hangul choseong filler inside a word"),
    ("\u2800", "the braille blank alone"),
    ("\u2800 \u2800", "blanks and spaces only"),
    ("\U00016fe4", "the Khitan small script filler alone (delta review D-B1)"),
    ("a\U00016fe4\u200d\U00016fe4b", "fillers and a joiner, which could carry hidden bits"),
    ("\U00013441", "a hieroglyph full blank"),
]


@pytest.mark.parametrize(("text", "why"), HIDDEN, ids=[why for _, why in HIDDEN])
def test_characters_that_draw_nothing_are_refused(text, why):
    with pytest.raises(Refused) as refused:
        player_text(text, "speech", max_chars=20)
    assert refused.value.code is RefusalCode.BAD_TEXT


def test_the_property_tables_are_sorted_disjoint_ranges_holding_unicode_16_s_points():
    for table in (DEFAULT_IGNORABLE, EMOJI):
        assert all(lo <= hi for lo, hi in table)
        assert all(a[1] + 1 < b[0] for a, b in pairwise(table))  # merged: no touching ranges
    # A sample of each property's published points, so a table cut short or shifted fails here
    ignorable = [0x00AD, 0x034F, 0x061C, 0x115F, 0x17B4, 0x180B, 0x200B, 0x202A, 0x2060, 0x3164, 0xFE00, 0xFEFF]
    ignorable += [0xFFA0, 0xFFF0, 0x1BCA0, 0x1D173, 0xE0000, 0xE0100, 0xE0FFF]
    emoji = [0x0023, 0x0030, 0x00A9, 0x203C, 0x2764, 0x263A, 0x1F5E8, 0x1F321]  # each has a text and an emoji form
    within = lambda table, cp: any(lo <= cp <= hi for lo, hi in table)  # noqa: E731
    assert all(within(DEFAULT_IGNORABLE, cp) for cp in ignorable)
    assert not any(within(DEFAULT_IGNORABLE, cp) for cp in (0x0041, 0x2010, 0x2800, 0xE1000))
    assert all(within(EMOJI, cp) for cp in emoji)
    assert not any(within(EMOJI, cp) for cp in (ord("a"), 0x1F600, 0x1F525))  # emoji by default: no second form
