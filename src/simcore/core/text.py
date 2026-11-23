"""Which characters text may hold: a name's (IDNA2008, for ``schema.Text``) and a guest's (``player_text``).

Two rules, for two kinds of text. A **name** (a region's, an imagined object's) reaches every agent as an entity name,
so it must be an identifier people can read and tell apart. **Guest text** (a guest's speech, any guest string that can
reach a prompt; boundaries §5.3) is free text in any script, so it keeps punctuation, symbols and emoji, but none of the
characters that render as nothing or reorder what is shown.
"""

from __future__ import annotations

import re
import unicodedata

import idna

from simcore.core.refusals import RefusalCode, Refused
from simcore.core.text_tables import DEFAULT_IGNORABLE, EMOJI

__all__ = ["NAME_JOINERS", "player_text", "visible_name"]

# A name's characters follow IDNA2008 (RFC 5890-5893; the idna package's code-point tables and contextual rules), the
# standard for which characters are safe in an identifier people read, rather than a rule written here: three review
# rounds found holes in hand-written ones (delta rounds 1-3). Each word between the separators below must be a valid
# IDNA2008 label as written, lower-cased or upper-cased (or digits of one system; see _visible_word), so combining marks
# are allowed after a base letter (Hindi, Tamil, vocalised Arabic), and Default_Ignorables, joiners outside their
# contexts, symbols and compatibility forms are not. The whole name must be its own NFKC form, so a fullwidth "crate"
# (U+FF43...) or a ligature is not a second "crate". IDNA admits two letters that render blank (EGYPTIAN HIEROGLYPH FULL
# and HALF BLANK), so a letter named BLANK or FILLER is refused by its Unicode name. Look-alikes from other scripts
# ("\u0441rate") need TR39's confusable skeleton: B38.
_NAME_SEPARATORS = re.compile("[ _.'\u2019-]+")
_BLANK_WORDS = ("BLANK", "FILLER")
NAME_JOINERS = {0x200C: "x", 0x200D: "x"}  # allowed past isprintable only so IDNA can rule on their context


def visible_name(value: str) -> bool:
    """A name an agent can see and tell apart (``schema.Text`` holds the rest of a name's rule)."""
    words = [w for w in _NAME_SEPARATORS.split(value) if w]
    if not words or unicodedata.normalize("NFKC", value) != value:
        return False
    if any(_blank(ch) for ch in value):
        return False
    return all(_visible_word(w) for w in words)


def _visible_word(word: str) -> bool:
    """One word of a name: digits only (any script's, judged as digits: IDNA's per-label bidi rule refuses a lone
    Arabic-Indic number, so "room \u0662" would be refused while "room 2" is kept; delta round 4, R4-1), all from one
    digit system, or a valid IDNA2008 label as written, lower-cased or upper-cased (IDNA allows Cherokee's capitals and
    not its small letters, so Cherokee in any case is judged by its capitals; casefold would admit twins IDNA refuses,
    such as U+1C80 beside "\u0432"; R5-1). A joiner may not end a word: after a virama with nothing following it renders
    nothing, so "\u0b95\u0bcd\u200d" would be a twin of "\u0b95\u0bcd" (R4-3)."""
    if all(unicodedata.category(ch) == "Nd" for ch in word):
        # one digit system per word, stricter than IDNA's CONTEXTO rule (which bans only Arabic-Indic beside Extended
        # Arabic-Indic, whose 1, 2 and 3 look alike, so "\u0661\u06f2" would twin "\u0661\u0662"; delta round 5, R5-2,
        # and round 6, N6-1): keep it stricter, the safe direction
        return len({ord(ch) - unicodedata.digit(ch) for ch in word}) == 1
    if word[-1] in "\u200c\u200d":
        return False
    for candidate in (word, word.lower(), word.upper()):  # Cherokee in lower or title case is valid upper-cased (R5-1)
        try:
            idna.check_label(candidate)
        except idna.IDNAError:  # this spelling is not a valid label; the other may be
            continue
        return True
    return False


# Guest text (boundaries §5.3; O61, amended by O65). Format characters (Cf) render as nothing or reorder text: bidi
# controls (U+202A-202E, U+2066-2069) can make a line read other than it is, a zero-width space or BOM hides inside a
# word, and tag characters (U+E0000 block) smuggle ASCII invisibly. Every default-ignorable code point (a variation
# selector, U+034F, a Hangul filler) is refused too, since each renders as nothing and a run of them can carry hidden
# bits, an LLM prompt's known smuggling route. Two exceptions keep real writing working: ZWNJ and ZWJ, which Persian
# and Indic spelling and emoji sequences need, between two visible characters (never first or last, never doubled,
# never beside another format character); and one U+FE0E or U+FE0F right after a character with text and emoji forms,
# so a heart can be drawn red. Flags spelled with tag characters (England, Scotland) are refused with them.
_JOINERS = frozenset("\u200c\u200d")
_PRESENTATION = frozenset("\ufe0e\ufe0f")
# Categories refused outright: controls (a newline too: guest text is one line), format, surrogates, private use,
# unassigned code points, and the line and paragraph separators.
_REFUSED_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})


def _within(ranges: tuple[tuple[int, int], ...], ch: str) -> bool:
    return any(lo <= ord(ch) <= hi for lo, hi in ranges)


def _blank(ch: str) -> bool:
    """A character Unicode names a BLANK or a FILLER: one that draws nothing though no property says so (the braille
    blank, Khitan's and the hieroglyphs' fillers; step 7 delta review D-B1). The name rule's own test, shared. In
    guest text a blank is no drawn character, like a space, and only a zero-width one (a mark) is refused outright,
    so braille and the scripts' gap fillers keep working (delta 2, N-S1)."""
    return any(w in unicodedata.name(ch, "") for w in _BLANK_WORDS)


def _visible(ch: str) -> bool:
    """A character that draws something: not refused by category, not a space, not blank. (A default-ignorable one
    is refused outright in ``_refused_at``, and the emoji bases hold none, so it never reaches this question.)"""
    return unicodedata.category(ch) not in _REFUSED_CATEGORIES and not ch.isspace() and not _blank(ch)


def _presentation_at(text: str, i: int) -> bool:
    """A variation selector the rule lets through: one, right after a visible character with emoji forms."""
    return text[i] in _PRESENTATION and i > 0 and _visible(text[i - 1]) and _within(EMOJI, text[i - 1])


def _drawn_at(text: str, i: int) -> bool:
    """What a joiner may stand beside: a visible character, or a variation selector the rule lets through."""
    return _visible(text[i]) or _presentation_at(text, i)


def _refused_at(text: str, i: int) -> bool:
    ch = text[i]
    if ch in _JOINERS:
        return not (0 < i < len(text) - 1 and _drawn_at(text, i - 1) and _visible(text[i + 1]))
    if ch in _PRESENTATION:
        return not _presentation_at(text, i)
    zero_width_blank = _blank(ch) and unicodedata.category(ch) == "Mn"  # a filler mark: nothing, joined to its base
    return unicodedata.category(ch) in _REFUSED_CATEGORIES or _within(DEFAULT_IGNORABLE, ch) or zero_width_blank


def player_text(value: object, what: str, *, max_chars: int) -> str:
    """Guest text as the engine keeps it: in NFC, then 1 to ``max_chars`` characters, at least one of which draws
    something, with no character O61 and O65 refuse. Unassigned code points (Cn) follow the interpreter's Unicode
    version (15.0 on Python 3.12, 16.0 on 3.14), so the text kept is what a replay reads back, never re-checked. A
    refusal names where and what kind of character, never the text: what a guest typed is theirs, and a log is no
    place to echo it."""
    if type(value) is not str:  # a str subclass could print as something else
        raise Refused(f"{what} must be text", code=RefusalCode.BAD_SHAPE)
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):  # NFC has no form for a lone surrogate
        raise Refused(f"{what} holds a lone surrogate", code=RefusalCode.BAD_TEXT)
    text = unicodedata.normalize("NFC", value)  # before the cap, so decomposed and composed text count alike
    if not 0 < len(text) <= max_chars:
        raise Refused(f"{what} must be 1 to {max_chars} characters", code=RefusalCode.BAD_TEXT)
    for i in range(len(text)):
        if _refused_at(text, i):
            kind = unicodedata.category(text[i])
            raise Refused(f"{what} holds a {kind} character at {i} that guest text may not", code=RefusalCode.BAD_TEXT)
    if not any(_visible(ch) for ch in text):
        raise Refused(f"{what} draws nothing: every character is a space or blank", code=RefusalCode.BAD_TEXT)
    return text
