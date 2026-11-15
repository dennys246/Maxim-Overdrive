"""Stand-ins for Maxim's SEM dataclasses, field for field, used only when pymaxim is not installed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SensorReading:
    sensor_name: str
    entity_name: str
    value: Any
    unit: str
    timestamp: float
    extra: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True)
class ModulatorResult:
    success: bool
    modulator_name: str
    entity_name: str
    affordance: str
    params: dict[str, Any]
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AffordanceSchema:
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
