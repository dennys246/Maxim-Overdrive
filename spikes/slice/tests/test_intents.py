import math

import pytest
from slice_server.intents import Kindle, Move, Say, Strike, parse
from slice_server.wire import WireRefused


def test_a_move_is_normalised() -> None:
    intent = parse({"type": "move", "dir": [3, 4], "effort": 0.5, "overdrive": True})
    assert isinstance(intent, Move)
    c = intent.command
    assert (c.dir_x, c.dir_y, c.effort, c.overdrive) == (0.6, 0.8, 0.5, True)
    assert math.hypot(c.dir_x, c.dir_y) == pytest.approx(1.0)


def test_a_zero_direction_stands_still() -> None:
    intent = parse({"type": "move", "dir": [0, 0], "effort": 1, "overdrive": False})
    assert isinstance(intent, Move)
    assert intent.command.effort == 0.0


def test_kindle_strike_and_say_parse() -> None:
    assert parse({"type": "kindle"}) == Kindle()
    assert parse({"type": "strike"}) == Strike()
    assert parse({"type": "say", "text": "  hot noodles?  "}) == Say("hot noodles?")


GOOD = {"type": "move", "dir": [1, 0], "effort": 1, "overdrive": False}


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ({**GOOD, "extra": 1}, "bad_intent"),
        ({k: v for k, v in GOOD.items() if k != "effort"}, "bad_intent"),
        ({**GOOD, "dir": [1]}, "bad_intent"),
        ({**GOOD, "dir": "east"}, "bad_intent"),
        ({**GOOD, "dir": [1, True]}, "bad_intent"),
        ({**GOOD, "dir": [1, float("inf")]}, "bad_intent"),
        ({**GOOD, "effort": 1.5}, "bad_intent"),
        ({**GOOD, "effort": -0.1}, "bad_intent"),
        ({**GOOD, "effort": "1"}, "bad_intent"),
        ({**GOOD, "overdrive": 1}, "bad_intent"),
        ({"type": "kindle", "at": [1, 2, 3]}, "bad_intent"),
        ({"type": "look", "yaw": 1.0}, "unknown_type"),
        ({"type": "strike", "at": [1, 2, 3]}, "bad_intent"),
        ({"type": "say"}, "bad_intent"),
        ({"type": "say", "text": "   "}, "bad_intent"),
        ({"type": "say", "text": "x" * 201}, "bad_intent"),
        ({"type": "say", "text": 42}, "bad_intent"),
        ({"no": "type"}, "unknown_type"),
    ],
)
def test_every_malformed_intent_is_refused_with_a_code(raw: dict, code: str) -> None:
    with pytest.raises(WireRefused) as caught:
        parse(raw)
    assert caught.value.code == code
