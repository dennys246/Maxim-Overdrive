import dataclasses
import math

import numpy as np
import pytest
from slice_server import config
from slice_server.body import Body, Cells, Command, blocked, check_no_tunnelling, impulse, step

P = config.load().body
DX = 0.2


def _open(nx: int = 60, ny: int = 20, nz: int = 24) -> Cells:
    solid = np.zeros((nx, ny, nz), dtype=bool)
    solid[:, :, :2] = True  # a 0.4 m floor
    return Cells(solid, DX)


def test_from_rest_the_velocity_follows_the_servo_closed_form() -> None:
    # Semi-implicit Euler on dv/dt = (v* - v)/tau gives v_n = v* (1 - (1 - h/tau)^n) exactly.
    body, cells = Body(2.0, 2.0, 0.4), _open()
    for _ in range(5):
        step(body, Command(1.0, 0.0, 1.0), cells, P, 0.1)
    h, n = 0.1 / P.substeps, 5 * P.substeps
    want = P.walk_speed_m_s * (1 - (1 - h / P.response_s) ** n)
    assert body.vx == pytest.approx(want, rel=1e-12)
    # and it tracks the continuous law within the integrator's first-order error
    assert body.vx == pytest.approx(P.walk_speed_m_s * (1 - math.exp(-0.5 / P.response_s)), rel=0.03)


def test_overdrive_doubles_the_top_speed() -> None:
    walk, run = Body(2.0, 2.0, 0.4), Body(2.0, 2.0, 0.4)
    for _ in range(30):
        step(walk, Command(1.0, 0.0, 1.0), _open(), P, 0.1)
        step(run, Command(1.0, 0.0, 1.0, overdrive=True), _open(), P, 0.1)
    assert run.vx == pytest.approx(2 * walk.vx, rel=1e-6)


def _walled() -> Cells:
    cells = _open()
    cells.solid[30, :, :] = True  # a one-cell wall, 0.2 m thick, at x = 6.0-6.2 m
    return cells


def test_a_wall_stops_the_body_at_its_face_and_kills_that_velocity() -> None:
    body = Body(5.0, 2.0, 0.4)
    for _ in range(40):
        step(body, Command(1.0, 0.0, 1.0), _walled(), P, 0.1)
    assert body.x + P.radius_m <= 6.0 + 1e-12
    assert body.x + P.radius_m > 6.0 - 0.1  # it got there
    assert body.vx == 0.0


def test_a_diagonal_into_a_wall_slides_along_it() -> None:
    body = Body(5.5, 1.0, 0.4)
    for _ in range(20):
        step(body, Command(math.sqrt(0.5), math.sqrt(0.5), 1.0), _walled(), P, 0.1)
    assert body.x + P.radius_m <= 6.0 + 1e-12
    assert body.y > 2.0


def test_nothing_tunnels_a_one_cell_wall_at_top_speed() -> None:
    # The guard: with too few substeps this body crosses the wall (proved by the second half).
    body = Body(5.0, 2.0, 0.4)
    for _ in range(10):
        impulse(body, 1e6, 0.0, P)  # pinned at max speed
        step(body, Command(1.0, 0.0, 1.0, overdrive=True), _walled(), P, 0.1)
    assert body.x < 6.0
    # One substep over a 0.2 s tick at 6 m/s is a single 1.2 m move: past the 0.6 m body plus the 0.2 m wall.
    few = dataclasses.replace(P, substeps=1, response_s=1e9)  # no drive, so the velocity stays at 6 m/s
    fast = Body(5.65, 2.0, 0.4, vx=P.max_speed_m_s)
    step(fast, Command(), _walled(), few, 0.2)
    assert fast.x - P.radius_m > 6.2, "with one substep the same body jumps the wall, so the test above can fail"


def test_parameters_that_could_tunnel_are_refused() -> None:
    check_no_tunnelling(P, 0.1, DX)
    with pytest.raises(ValueError, match="substeps"):
        check_no_tunnelling(dataclasses.replace(P, substeps=4), 0.1, DX)


def test_the_floor_never_blocks_and_the_extent_does() -> None:
    cells = _open()
    assert not blocked(cells, 2.0, 2.0, 0.4, P)
    assert blocked(cells, 0.1, 2.0, 0.4, P)
    assert blocked(cells, 2.0, 3.95, 0.4, P)


def test_drive_work_is_booked_and_an_impulse_changes_velocity_by_j_over_m() -> None:
    body = Body(2.0, 2.0, 0.4)
    step(body, Command(1.0, 0.0, 1.0), _open(), P, 0.1)
    assert body.work_j > 0
    still = Body(2.0, 2.0, 0.4)
    impulse(still, 0.0, 80.0, P)
    assert still.vy == pytest.approx(80.0 / P.mass_kg)
