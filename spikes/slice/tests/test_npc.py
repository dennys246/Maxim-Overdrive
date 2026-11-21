import math

from slice_server import config
from slice_server.body import Body
from slice_server.npc import Perception, SeenFire, decide

P = config.load().npc.vendor
CRATE = SeenFire("crate", (6.3, 2.9, 0.7), ((6.0, 2.6, 0.4), (6.6, 3.2, 1.0)), 20e3)  # just lit, growing
FAR = SeenFire("crate_far", (9.3, 1.1, 0.7), ((9.0, 0.8, 0.4), (9.6, 1.4, 1.0)), 20e3)


def _seen(**kw) -> Perception:
    base = {"flux_w_m2": 0.0, "fires": (), "player_x": 1.0, "player_y": 2.0, "player_core_c": 37.0,
            "player_warn_c": 70.0, "charges": 1}  # fmt: skip
    return Perception(**(base | kw))


def _stall() -> Body:
    return Body(P.stall_x, P.stall_y, 0.4)


def test_flee_beats_everything_and_heads_for_the_mouth() -> None:
    d = decide(_stall(), _seen(flux_w_m2=P.flee_flux_w_m2 + 1, fires=(CRATE,)), P)
    assert d.state == "flee"
    assert d.command.dir_x < 0, "west, toward the alley's mouth"


def test_a_small_fire_near_the_stall_is_walked_to_then_doused() -> None:
    walking = decide(_stall(), _seen(fires=(CRATE,)), P)
    assert walking.state == "douse"
    assert walking.douse is None
    assert walking.command.dir_x > 0
    close = Body(5.2, 2.9, 0.4)  # 0.8 m from the crate's face
    assert decide(close, _seen(fires=(CRATE,)), P).douse == "crate"


def test_with_no_charge_or_a_big_fire_it_warns_instead() -> None:
    assert decide(_stall(), _seen(fires=(CRATE,), charges=0), P).state == "warn"
    big = SeenFire("crate", CRATE.centroid, CRATE.bounds, P.small_fire_w + 1.0)
    assert decide(_stall(), _seen(fires=(big,)), P).state == "warn"


def test_a_fire_far_from_the_stall_is_warned_about_not_doused() -> None:
    d = decide(_stall(), _seen(fires=(FAR,)), P)
    assert d.state == "warn"
    assert d.target == "crate_far"


def test_it_comments_on_an_overheating_player_close_by() -> None:
    hot = {"player_core_c": 75.0, "player_x": P.stall_x - 1.0, "player_y": P.stall_y}
    assert decide(_stall(), _seen(**hot), P).state == "comment"
    far = hot | {"player_x": P.stall_x - P.comment_range_m - 1.0}
    assert decide(_stall(), _seen(**far), P).state == "idle"


def test_idle_walks_back_to_the_stall_and_stops_there() -> None:
    away = decide(Body(P.stall_x - 2.0, P.stall_y, 0.4), _seen(), P)
    assert away.state == "idle"
    assert math.isclose(away.command.dir_x, 1.0)
    assert decide(_stall(), _seen(), P).command.effort == 0.0
