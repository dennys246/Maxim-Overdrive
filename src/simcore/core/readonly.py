"""Read-only arrays that stay read-only: the core's arrays at rest (boundaries §4.1, §5.1)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def frozen[T: np.generic](arr: npt.NDArray[T]) -> npt.NDArray[T]:
    """A read-only copy of ``arr`` that nothing can make writable.

    ``flags.writeable = False`` alone is undone in one line, on the array or on its ``.base``. This copy's memory is an
    immutable ``bytes`` object, so the WRITEABLE flag can't be set again on it or its base, and ``out=``, ``.base``
    and item writes all raise.
    """
    return np.frombuffer(arr.tobytes(), dtype=arr.dtype).reshape(arr.shape)
