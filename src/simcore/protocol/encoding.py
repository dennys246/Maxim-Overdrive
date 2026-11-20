"""Display quantization: the arrays a client uploads as 3-D textures, made from the world's cells.

Presentation only (boundaries §8.3): the core never imports this module, and neither does the SEM membrane, so what
a renderer is shown can't feed back into physics or perception.
"""

from __future__ import annotations

import numpy as np

from simcore.core.grid import MaterialGrid

# Glow starts near the Draper point (~525 °C), where hot solids first emit visible red light.
GLOW_START_C = 525.0
GLOW_FULL_C = 1500.0


def snapshot(grid: MaterialGrid) -> dict[str, object]:
    """Quantized per-cell state for a renderer: the arrays a client uploads as 3-D textures.

    ``crack`` (1 - integrity) and ``glow`` are ready shader inputs, so the finest physical state shows up directly as
    cracks, scorching and glowing metal without the renderer knowing any physics.
    """
    integrity = np.clip(grid.integrity, 0.0, 1.0)
    glow = np.clip((grid.temperature - GLOW_START_C) / (GLOW_FULL_C - GLOW_START_C), 0.0, 1.0) * grid.solid
    return {
        "shape": grid.shape,
        "cell_size_m": grid.dx,
        "time_s": grid.time_s,
        "material": grid.material.copy(),
        "crack": np.round((1.0 - integrity) * grid.solid * 255).astype(np.uint8),
        "glow": np.round(glow * 255).astype(np.uint8),
        "temperature_c": np.clip(grid.temperature, -273.0, 6000.0).astype(np.float16),
    }
