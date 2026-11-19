"""Stand-ins for Maxim's SEM dataclasses, field for field, used only when pymaxim is not installed.

tests/test_sem_compat.py holds every class here to Maxim's: same fields, order, types, defaults and flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SensorReading:
    sensor_name: str
    entity_name: str
    value: Any
    unit: str
    timestamp: float
    extra: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


@dataclass(frozen=True, slots=True)
class ModulatorResult:
    success: bool
    modulator_name: str
    entity_name: str
    affordance: str
    params: dict[str, Any]
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AffordanceSchema:
    params: dict[str, type | tuple[type, Any]] = field(default_factory=dict)
    description: str = ""
    timeout: float = 30.0
    requires: dict[str, float] = field(default_factory=dict)
    self_effect: dict[str, float] = field(default_factory=dict)
    target_effect: dict[str, float] = field(default_factory=dict)
    always_active: bool = False
    speech_param: str | None = None
