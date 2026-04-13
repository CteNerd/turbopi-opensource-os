#!/usr/bin/env python3
"""Sensor HAL primitives with config-driven calibration offsets."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional


class SensorError(Exception):
    """Raised when sensor reads fail or unknown sensors are requested."""


def _get_float(name: str, default: float) -> float:
    """Read a float from the environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class SensorCalibration:
    """Calibration values applied to generic sensor readings."""

    distance_offset_cm: float = 0.0

    @classmethod
    def from_env(cls) -> 'SensorCalibration':
        """Load sensor calibration values from config.env."""
        return cls(
            distance_offset_cm=_get_float('HAL_SENSOR_DISTANCE_OFFSET_CM', 0.0),
        )


@dataclass(frozen=True)
class SensorReading:
    """Value returned from an abstracted sensor device."""

    name: str
    value: float
    unit: str
    timestamp: str


class BaseSensorHAL(ABC):
    """Abstract sensor collection interface."""

    def __init__(self, calibration: Optional[SensorCalibration] = None):
        self.calibration = calibration or SensorCalibration.from_env()

    @abstractmethod
    def list_sensors(self) -> Iterable[str]:
        """Return the names of available sensors."""

    @abstractmethod
    def read(self, name: str) -> SensorReading:
        """Return a calibrated reading for a named sensor."""


class FakeSensorHAL(BaseSensorHAL):
    """Simple in-memory sensor collection used for tests and integration scaffolding."""

    def __init__(
        self,
        calibration: Optional[SensorCalibration] = None,
        initial_values: Optional[Dict[str, float]] = None,
    ):
        super().__init__(calibration=calibration)
        self._values = initial_values or {'distance_cm': 100.0}

    def set_value(self, name: str, value: float) -> None:
        """Set a raw sensor value for deterministic tests."""
        self._values[name] = value

    def list_sensors(self) -> Iterable[str]:
        """Return sensor names known to this HAL instance."""
        return sorted(self._values.keys())

    def read(self, name: str) -> SensorReading:
        """Return a calibrated sensor reading."""
        if name not in self._values:
            raise SensorError(f'Unknown sensor: {name}')

        value = self._values[name]
        if name == 'distance_cm':
            value += self.calibration.distance_offset_cm

        return SensorReading(
            name=name,
            value=value,
            unit='cm' if name.endswith('_cm') else 'raw',
            timestamp=datetime.now(timezone.utc).isoformat(),
        )