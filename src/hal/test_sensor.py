#!/usr/bin/env python3
"""Unit tests for the TurboPi sensor HAL."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hal.sensor import FakeSensorHAL, SensorCalibration, SensorError


class TestSensorHAL(unittest.TestCase):
    """Tests for sensor abstraction and calibration."""

    def test_sensor_calibration_loads_from_env(self):
        with patch.dict(os.environ, {'HAL_SENSOR_DISTANCE_OFFSET_CM': '7.5'}, clear=False):
            calibration = SensorCalibration.from_env()

        self.assertEqual(calibration.distance_offset_cm, 7.5)

    def test_distance_reading_applies_offset(self):
        hal = FakeSensorHAL(
            calibration=SensorCalibration(distance_offset_cm=5.0),
            initial_values={'distance_cm': 20.0},
        )

        reading = hal.read('distance_cm')
        self.assertEqual(reading.value, 25.0)
        self.assertEqual(reading.unit, 'cm')

    def test_unknown_sensor_raises_error(self):
        hal = FakeSensorHAL(initial_values={'distance_cm': 20.0})

        with self.assertRaises(SensorError):
            hal.read('battery_voltage')


if __name__ == '__main__':
    unittest.main()