# TurboPi Hardware Abstraction Layer (HAL)

## Purpose

The HAL provides a single interface for hardware interactions and keeps direct
device access out of higher-level services.

This module currently provides:
- Motor HAL primitives with safe startup and calibration support
- Camera HAL primitives for frame capture workflows
- Sensor HAL primitives for calibrated sensor reads

## Safety Expectations

- Motors start in a disarmed state by default.
- Motion commands are rejected when motors are disarmed.
- Stop commands must force zero output.
- Higher-level control and safety components should route all motion through HAL.

The HAL does not replace the Safety Arbiter. It is the hardware-facing layer
that safety and control modules call.

## Modules

- `motor.py`: velocity commands, normalized outputs, arm/disarm/stop behavior
- `camera.py`: open/close semantics and frame metadata
- `sensor.py`: named sensor reads with calibration offsets

## Calibration

Calibration is loaded from runtime environment values in
`/etc/turbopi/config.env`.

Motor calibration keys:
- `MAX_LINEAR_SPEED`
- `MAX_ANGULAR_SPEED`
- `HAL_MOTOR_LEFT_TRIM`
- `HAL_MOTOR_RIGHT_TRIM`
- `HAL_MOTOR_LEFT_SCALE`
- `HAL_MOTOR_RIGHT_SCALE`

Camera calibration keys:
- `HAL_CAMERA_WIDTH`
- `HAL_CAMERA_HEIGHT`
- `HAL_CAMERA_FPS`
- `HAL_CAMERA_PIXEL_FORMAT`

Sensor calibration keys:
- `HAL_SENSOR_DISTANCE_OFFSET_CM`

Invalid or missing values fall back to safe defaults.

## Testing

Run HAL-focused tests:

```bash
/opt/homebrew/bin/python3 -m pytest src/hal/test_motor.py src/hal/test_camera.py src/hal/test_sensor.py -q
```

Run HAL tests plus related safety checks:

```bash
/opt/homebrew/bin/python3 -m pytest src/hal/test_motor.py src/hal/test_camera.py src/hal/test_sensor.py src/voice/test_wake_word.py src/api/test_wake_word_api.py -q
```