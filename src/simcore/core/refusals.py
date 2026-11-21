"""The refusal codes: one closed vocabulary for every refusal the engine gives (tile §3.4, WT-S1; boundaries §5.4).

Anything agent-facing (a modulator's error, later a receipt) answers with a code, never exception text, since
``checks.shown`` bounds an echo but doesn't scrub it. The message stays on the exception for logs and tests.

The enum is append-only: a code's value is its wire spelling and, from step 5a, part of the intent log, so a code is
never renamed, reused or removed (``tests/test_refusals.py`` pins every value in order). Tile §3.4's codes are listed
before they have a producer, so the protocol (step 7), bodies (5) and fire (6) add producers, not codes.
"""

from __future__ import annotations

from enum import StrEnum


class RefusalCode(StrEnum):
    # decode: the protocol layer (tile §3.4, step 7)
    BAD_JSON = "bad_json"
    UNKNOWN_KIND = "unknown_kind"
    UNKNOWN_FIELD = "unknown_field"
    BUSY = "busy"
    # stage 1 (step 7)
    NOT_INT = "not_int"
    BAD_SHAPE = "bad_shape"
    OUT_OF_RANGE = "out_of_range"
    OUTSIDE_EXTENT = "outside_extent"
    RATE_LIMITED = "rate_limited"
    COALESCED = "coalesced"
    # stage 2: fire (step 6)
    OUT_OF_REACH = "out_of_reach"
    NOT_ON_SURFACE = "not_on_surface"
    AMBIGUOUS_POINT = "ambiguous_point"
    REGION_GONE = "region_gone"
    NO_IGNITER = "no_igniter"
    OVER_ITEM_MAX = "over_item_max"
    PILOT_LIVE = "pilot_live"
    RESTRIKE_WAIT = "restrike_wait"
    # stage 2: bodies (step 5)
    NO_BODY = "no_body"
    NO_PATH = "no_path"
    UNREACHABLE = "unreachable"
    # produced today (step 3b part b): the format gates, stage 1 and 2 of today's actions, imagined objects
    MISSING_FIELD = "missing_field"
    NOT_FINITE = "not_finite"
    BAD_VERSION = "bad_version"
    BAD_IDENTITY_KEY = "bad_identity_key"
    BAD_NAME = "bad_name"
    NO_REGION = "no_region"
    NOT_SOLID = "not_solid"
    NOT_ON_REGION = "not_on_region"
    NOT_BURNING = "not_burning"
    WRONG_TARGET = "wrong_target"
    NAMESAKE = "namesake"
    NAME_TAKEN = "name_taken"
    UNKNOWN_MATERIAL = "unknown_material"
    OVER_BUDGET = "over_budget"
    SPACE_TAKEN = "space_taken"
    TOO_SMALL = "too_small"
    DUPLICATE_KEY = "duplicate_key"


class Refused(ValueError):
    """A refusal with its code. ``field``, when given, is a name from the reader's own schema (never input), so
    ``agent_text`` stays inside the closed vocabulary: a code, or a code and a schema field."""

    def __init__(self, message: str, *, code: RefusalCode, field: str | None = None) -> None:
        super().__init__(message)
        self.code = RefusalCode(code)  # a bare string that is not a code is a programming error: ValueError here
        self.field = field

    @property
    def agent_text(self) -> str:
        return self.code.value if self.field is None else f"{self.code.value} ({self.field})"
