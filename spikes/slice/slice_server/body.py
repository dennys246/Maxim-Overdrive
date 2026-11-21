"""The slice's body: dynamic motion, kinematic collision (plan §3.4).

The body keeps a velocity. A drive force pulls it toward the commanded velocity, and the motion is integrated by
semi-implicit Euler: velocity first, from the force, then position, from the new velocity. Collision does not use
forces. Each substep proposes a move and tests it against solid cells, sliding by the tile spec's rule (full step,
else the x part, else the y part, else stay) and zeroing the blocked axis's velocity. Substeps keep any single move
below half a cell, so the body cannot tunnel through a wall between two tests.

The body reads cells from a published frame and never writes the world: it is the server's state, beside the world.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from slice_server.config import BodyParams

Mask = npt.NDArray[np.bool_]


@dataclass
class Body:
    x: float
    y: float
    feet_z: float
    vx: float = 0.0
    vy: float = 0.0
    yaw: float = 0.0
    work_j: float = 0.0  # positive drive work done so far: Phase 5's action energy, logged (plan §3.4)


@dataclass(frozen=True)
class Command:
    """What a ``move`` intent asks for: a unit direction in the world's x-y plane, an effort in [0, 1], Overdrive."""

    dir_x: float = 0.0
    dir_y: float = 0.0
    effort: float = 0.0
    overdrive: bool = False


@dataclass(frozen=True)
class Cells:
    """The solid mask of one frame, with the spacing and extent the collision test needs."""

    solid: Mask
    dx: float

    @property
    def extent_xy(self) -> tuple[float, float]:
        return self.solid.shape[0] * self.dx, self.solid.shape[1] * self.dx


def blocked(cells: Cells, x: float, y: float, feet_z: float, p: BodyParams) -> bool:
    """Whether a body standing at (x, y) overlaps a solid cell or leaves the extent.

    The body is an upright cylinder from ``feet_z + step_clearance_m`` to ``feet_z + height_m``; a cell blocks when
    the distance from the cylinder's axis to the cell's square is less than the radius (touching is allowed).
    """
    r, dx = p.radius_m, cells.dx
    ex, ey = cells.extent_xy
    if x - r < 0 or y - r < 0 or x + r > ex or y + r > ey:
        return True
    nx, ny, nz = cells.solid.shape
    i0, i1 = max(0, math.floor((x - r) / dx)), min(nx, math.floor((x + r) / dx) + 1)
    j0, j1 = max(0, math.floor((y - r) / dx)), min(ny, math.floor((y + r) / dx) + 1)
    k0 = max(0, math.floor((feet_z + p.step_clearance_m) / dx))
    k1 = min(nz, math.ceil((feet_z + p.height_m) / dx))
    column = cells.solid[i0:i1, j0:j1, k0:k1].any(axis=2)
    if not column.any():
        return False
    ii, jj = np.nonzero(column)
    # The nearest point of each solid cell's square to the axis, and its distance.
    lo_x, lo_y = (ii + i0) * dx, (jj + j0) * dx
    near_x = np.clip(x, lo_x, lo_x + dx)
    near_y = np.clip(y, lo_y, lo_y + dx)
    return bool(np.any((near_x - x) ** 2 + (near_y - y) ** 2 < r * r))


def _drive(body: Body, cmd: Command, p: BodyParams, h: float) -> None:
    """One semi-implicit Euler velocity update from the drive force, with the work it does booked."""
    speed = (p.overdrive_speed_m_s if cmd.overdrive else p.walk_speed_m_s) * cmd.effort
    fx = p.mass_kg * (cmd.dir_x * speed - body.vx) / p.response_s
    fy = p.mass_kg * (cmd.dir_y * speed - body.vy) / p.response_s
    body.vx += fx / p.mass_kg * h
    body.vy += fy / p.mass_kg * h
    _cap(body, p)
    body.work_j += max(0.0, fx * body.vx + fy * body.vy) * h


def _cap(body: Body, p: BodyParams) -> None:
    speed = math.hypot(body.vx, body.vy)
    if speed > p.max_speed_m_s:
        body.vx, body.vy = body.vx * p.max_speed_m_s / speed, body.vy * p.max_speed_m_s / speed


def _slide(body: Body, cells: Cells, p: BodyParams, h: float) -> None:
    """Move by the velocity for one substep, sliding along whatever blocks it."""
    dx, dy = body.vx * h, body.vy * h
    if not blocked(cells, body.x + dx, body.y + dy, body.feet_z, p):
        body.x, body.y = body.x + dx, body.y + dy
    elif not blocked(cells, body.x + dx, body.y, body.feet_z, p):
        body.x, body.vy = body.x + dx, 0.0
    elif not blocked(cells, body.x, body.y + dy, body.feet_z, p):
        body.y, body.vx = body.y + dy, 0.0
    else:
        body.vx = body.vy = 0.0


def step(body: Body, cmd: Command, cells: Cells, p: BodyParams, dt: float) -> None:
    """Advance one body by one tick of ``dt`` seconds in ``p.substeps`` substeps."""
    h = dt / p.substeps
    for _ in range(p.substeps):
        _drive(body, cmd, p, h)
        _slide(body, cells, p, h)
    if math.hypot(body.vx, body.vy) > 0.05:
        body.yaw = math.atan2(body.vy, body.vx)


def impulse(body: Body, jx: float, jy: float, p: BodyParams) -> None:
    """Knockback: an impulse in newton-seconds changes velocity by J / m at once (week 3's strikes and blasts)."""
    body.vx += jx / p.mass_kg
    body.vy += jy / p.mass_kg
    _cap(body, p)


def check_no_tunnelling(p: BodyParams, dt: float, dx: float) -> None:
    """Refuse parameters under which one substep at top speed could cross half a cell."""
    per_substep = p.max_speed_m_s * dt / p.substeps
    if per_substep > dx / 2:
        raise ValueError(f"a substep moves up to {per_substep:.3f} m, over half a {dx} m cell: raise substeps")
