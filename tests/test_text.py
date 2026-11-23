"""simcore.core.text.player_text, the guest-text gate (boundaries \u00a75.3; O61, TB-N5): real text in many scripts
passes; every format character but a joiner between two visible characters is refused, and NFC runs before the cap.
"""

from __future__ import annotations

import unicodedata
from itertools import pairwise

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from simcore.core import text as text_module
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.text import MAX_BLANK_RUN, MAX_MARKS, player_text, visible_name
from simcore.core.text_tables import DEFAULT_IGNORABLE, EMOJI, NO_INK

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
    "\u2422",  # alone too: its glyph is ink (O72; review E-N1)
    "a\u2422\u2422\u2422b",  # and three in a row are no run
    "\U00011c44\U00011c44\U00011c44",  # Bhaiksuki gap fillers, as a manuscript writes them
    "\u101c\u103b\u103e\u102d\u102f\u1037",  # Burmese: four marks on one letter, UDHR's tallest stack (O71)
    "\u05e9\u05b8\u05bc\u05c1\u0596",  # pointed Hebrew with a cantillation mark: four marks
    "x\u0301\u0302\u0303\u0304",  # four marks on a letter NFC leaves alone: the cap itself
    "Done.  Next",  # two spaces after a full stop: a run of two passes (O70)
    "\u4f60\u597d\u3000\u3000\u4e16\u754c",  # two ideographic spaces
    "  hi",  # a run of two at the start
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


def _is_mark(ch: str) -> bool:
    return unicodedata.category(ch) in ("Mn", "Me")


def _assert_no_long_runs(out: str) -> None:
    """The test's own reading of O70 and O71: with the marks taken out, no three characters in a row draw nothing (a
    space, a format character, a listed blank); and no five marks stand in a row."""
    within = lambda cp: any(lo <= cp <= hi for lo, hi in NO_INK)  # noqa: E731
    bare = [ch for ch in out if not _is_mark(ch)]
    inkless = [ch.isspace() or unicodedata.category(ch) == "Cf" or within(ord(ch)) for ch in bare]
    assert not any(all(inkless[i : i + MAX_BLANK_RUN + 1]) for i in range(len(bare) - MAX_BLANK_RUN))
    marks = [_is_mark(ch) for ch in out]
    assert not any(all(marks[i : i + MAX_MARKS + 1]) for i in range(len(out) - MAX_MARKS))


# Pieces that reach the run and stack rules, which random text almost never does (review E-N2): letters, spaces and
# blanks, joiners and marks, so most examples pass the character rules and are judged by the run rules.
_MARKS = ["\u0301", "\u0302", "\u05bc", "\u102d"]
_PIECES = ["a", "\u05e9", "\u4f60", " ", "\u2009", "\u3000", "\u2800", "\U0001d159", ZWJ, *_MARKS * 3]


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(_PIECES), min_size=1, max_size=24))
def test_whatever_passes_holds_no_long_run_and_no_tall_stack(pieces):
    codes: set[RefusalCode] = set()
    try:
        out = player_text("".join(pieces), "speech", max_chars=40)
    except Refused as refused:  # its one code for characters; anything else escaping fails the test
        codes.add(refused.code)
        out = ""
    assert codes <= {RefusalCode.BAD_TEXT}
    _assert_no_long_runs(out)


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
    _assert_no_long_runs(out)
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
    ("a\U00016fe4b", "a zero-width filler mark inside a word: refused by that rule alone (delta 3, T3-S1)"),
    ("\U0001d159", "the null notehead alone, which no property marks (O70; delta 2, N-N2)"),
    ("\U0001d159 ", "the null notehead and a space"),
]


# A run of characters that draw nothing carries hidden bits at any length, so a run is capped (O70; delta 4, T4-S1)
LONG_RUNS = [
    ("a   b", "three spaces"),
    ("a\u2009\u200a\u2009b", "thin and hair spaces"),
    ("a \u2800 b", "spaces around a braille blank"),
    ("a\U0001d159\U0001d159\U0001d159b", "three null noteheads"),
    ("hi   ", "a run at the end"),
    ("   hi", "a run at the start"),
    ("hi" + "\u2009\u200a\u3000\u2800" * 124 + "!", "the 496-character run that hid about 2,390 bits"),
    ("a" + "  \u0301" * 150 + "b", "marks floated on spaces, which neither end a run nor start one (review TW-S1)"),
]


@pytest.mark.parametrize(("text", "why"), LONG_RUNS, ids=[why for _, why in LONG_RUNS])
def test_a_run_of_more_than_two_characters_that_draw_nothing_is_refused(text, why):
    with pytest.raises(Refused, match="run of more than 2") as refused:
        player_text(text, "speech", max_chars=500)
    assert refused.value.code is RefusalCode.BAD_TEXT


@pytest.mark.parametrize(("text", "at"), [("a   b", 3), ("   hi", 2), ("hi a \u0301 \u0301 b", 8)])
def test_a_long_run_is_named_at_the_character_that_overflows(text, at):
    with pytest.raises(Refused, match=f"draw nothing, at {at}$"):
        player_text(text, "speech", max_chars=64)


# A stack of marks of any height carries hidden bits (about 9.7 a mark, so "h", 497 marks and "i!" hid about 4,805),
# so a character carries at most four (O71; review E-S1, TW-S1)
TALL_STACKS = [
    ("x\u0301\u0302\u0303\u0304\u0305", "five marks on a letter", 5),
    ("\u05e9\u05b8\u05bc\u05bd\u05c1\u0596", "pointed Hebrew with a fifth mark", 5),
    ("h" + "\u17d2" * 200 + "i", "invisible Khmer stackers", 5),
    ("1\ufe0f\u20e3\u20e3\u20e3\u20e3", "a keycap with more enclosing marks", 5),
    (" \u0301\u0302\u0303\u0304\u0305x", "five marks on a space", 5),
]


@pytest.mark.parametrize(("text", "why", "at"), TALL_STACKS, ids=[why for _, why, _ in TALL_STACKS])
def test_a_character_carrying_more_than_four_marks_is_refused(text, why, at):
    with pytest.raises(Refused, match=f"more than 4 marks on one character, at {at}$") as refused:
        player_text(text, "speech", max_chars=500)
    assert refused.value.code is RefusalCode.BAD_TEXT


@pytest.mark.parametrize("joiner", ["\u2d7f", "\U0001107f", "\U00011a47", "\U00011a99", "\U00011f42"], ids=ascii)
def test_the_invisible_joiner_marks_are_refused(joiner):
    """Five marks that draw nothing and no property or name marks, listed in NO_INK (O71; review TW-S1)."""
    with pytest.raises(Refused, match="Mn character at 2") as refused:
        player_text("hi" + joiner + "x", "speech", max_chars=64)
    assert refused.value.code is RefusalCode.BAD_TEXT


def test_a_listed_character_is_no_name_either(monkeypatch):
    """The name rule reads NO_INK too: list a letter IDNA allows and a name holding it is refused (review E-S2)."""
    assert visible_name("crate")
    monkeypatch.setattr(text_module, "NO_INK", ((ord("t"), ord("t")),))
    assert not visible_name("crate")


# Hand-reviewed: characters named BLANK or FILLER whose chart glyph is ink (O72)
_NAMED_BLANK_BUT_DRAWN = {0x2422, 0xA8F9, 0x10AF6, 0x1144E, 0x11945, 0x11C44, 0x11C45, 0x11F48}


def test_every_character_named_blank_or_filler_is_listed_or_reviewed():
    """A Unicode upgrade that adds a blank fails here until it is listed in NO_INK or reviewed as drawn (O72)."""
    within = lambda table, cp: any(lo <= cp <= hi for lo, hi in table)  # noqa: E731
    named = [cp for cp in range(0x110000) if any(w in unicodedata.name(chr(cp), "") for w in ("BLANK", "FILLER"))]
    unsorted = [hex(cp) for cp in named if not (within(NO_INK, cp) or within(DEFAULT_IGNORABLE, cp))]
    assert set(unsorted) == {hex(cp) for cp in _NAMED_BLANK_BUT_DRAWN}


@pytest.mark.parametrize(("text", "why"), HIDDEN, ids=[why for _, why in HIDDEN])
def test_characters_that_draw_nothing_are_refused(text, why):
    with pytest.raises(Refused) as refused:
        player_text(text, "speech", max_chars=20)
    assert refused.value.code is RefusalCode.BAD_TEXT


def test_the_property_tables_are_sorted_disjoint_ranges_holding_unicode_16_s_points():
    for table in (DEFAULT_IGNORABLE, EMOJI, NO_INK):
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
    assert all(within(NO_INK, cp) for cp in (0x2800, 0x13441, 0x16FE4, 0x1D159, 0x2D7F, 0x11F42))
    assert not any(within(EMOJI, cp) for cp in (ord("a"), 0x1F600, 0x1F525))  # emoji by default: no second form
