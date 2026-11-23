"""Where a grid's cells are (`docs/design/world_model.md` F13): the spacing, the shape and the coordinates that follow
from them, and the rule that every length a grid or scene takes is a whole number of micrometres. No state and no
window: the cells themselves are `simcore.core.grid`'s.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from simcore.core.refusals import RefusalCode, Refused

UM_PER_M = 1_000_000

MAX_LENGTH_M = 1000.0  # scene.MAX_EXTENT_M too: no tile is a kilometre across, and the conversion below stays finite


def whole_micrometres(length_m: float, what: str) -> int:
    """A positive length of at most ``MAX_LENGTH_M`` as whole micrometres, or a Refused: cell edges are integer
    micrometres (F13, fire_solid §1.3). The 1 nm allowance is float noise on a whole micrometre, never a real length."""
    if not (0 < length_m <= MAX_LENGTH_M):  # NaN fails too; bounded before arithmetic, so round() never overflows
        raise Refused(
            f"{what} must be above 0 and at most {MAX_LENGTH_M:g} m, got {length_m!r}", code=RefusalCode.OUT_OF_RANGE
        )
    um = round(length_m * UM_PER_M)
    if um < 1 or abs(length_m * UM_PER_M - um) > 1e-3:
        raise Refused(f"{what} {length_m} m is not a whole number of micrometres", code=RefusalCode.OUT_OF_RANGE)
    return um


# Array types for the grid's fields. Typing the element type (not bare np.ndarray) is what strict mypy needs on every
# supported numpy: older stubs give ndarray no default type parameters.
Mask = npt.NDArray[np.bool_]
Field = npt.NDArray[np.float64]


class GridGeometry:
    """Where the cells are: the spacing and the shape, and the coordinates that follow from them."""

    def __init__(self, dx: float, shape: tuple[int, int, int]) -> None:
        self._dx, self._shape = dx, shape

    @property
    def dx(self) -> float:
        return self._dx

    @property
    def shape(self) -> tuple[int, int, int]:
        return self._shape

    @property
    def cell_volume_m3(self) -> float:
        return self._dx**3

    @property
    def extent_m(self) -> tuple[float, float, float]:
        return tuple(n * self._dx for n in self._shape)  # type: ignore[return-value]

    def centers(self, axis: int) -> Field:
        """Cell-centre coordinates along one axis, in metres."""
        return (np.arange(self._shape[axis], dtype=np.float64) + 0.5) * self._dx

    def mesh(self) -> tuple[Field, Field, Field]:
        """Broadcastable cell-centre coordinates (x[:, None, None], y[None, :, None], z[None, None, :])."""
        x = self.centers(0)[:, None, None]
        y = self.centers(1)[None, :, None]
        z = self.centers(2)[None, None, :]
        return x, y, z

    def cell_of(self, point_m: tuple[float, float, float]) -> tuple[int, int, int]:
        idx = tuple(int(np.floor(p / self._dx)) for p in point_m)
        for i, n in zip(idx, self._shape, strict=True):
            if not 0 <= i < n:
                raise ValueError(f"point {point_m} is outside the grid {self.extent_m}")
        return idx  # type: ignore[return-value]
