"""The refusal codes: one closed vocabulary for every refusal the engine gives (tile §3.4, WT-S1; boundaries §5.4).

Anything agent-facing (a modulator's error, later a receipt) answers with a code, never exception text, since
``checks.shown`` bounds an echo but doesn't scrub it. The message stays on the exception for logs and tests.

Codes that reach the wire or the log are classed by stage, reply and logging in tile §3.4; the codes produced today
get their class with the intent log (step 5a), whose writer needs it.

The enum is append-only: a code's value is its wire spelling and, from step 5a, part of the intent log, so a code is
never renamed, reused or removed (``tests/test_refusals.py`` pins every value in order). Tile §3.4's codes are listed
before they have a producer, so bodies (5) and fire (6) add producers, not codes; step 7 added the handshake's,
the time authority's and guest text's codes, which tile §3.4 lists with them.
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
    # step 7: guest text (engine.text.player_text, O61), and the handshake and time authority (boundaries §5.3)
    BAD_TEXT = "bad_text"
    BAD_TOKEN = "bad_token"
    TOKEN_IN_USE = "token_in_use"
    HOST_ONLY = "host_only"
    # the handshake's order (boundaries §5.3): no hello within the deadline, another message first, or a second hello
    HELLO_FIRST = "hello_first"


class Refused(ValueError):
    """A refusal with its code. ``field``, when given, is a name we wrote (a schema field, or a call key such as
    ``target``), never input, so ``agent_text`` stays inside the closed vocabulary: a code, or a code and that name."""

    def __init__(self, message: str, *, code: RefusalCode, field: str | None = None) -> None:
        super().__init__(message)
        self.code = RefusalCode(code)  # a bare string that is not a code is a programming error: ValueError here
        self.field = field

    @property
    def agent_text(self) -> str:
        return agent_text(self.code, self.field)


def agent_text(code: RefusalCode, field: str | None = None) -> str:
    """What an agent is told of a refusal: its code, and the name we wrote (a schema field, a call key) at fault."""
    return code.value if field is None else f"{code.value} ({field})"
