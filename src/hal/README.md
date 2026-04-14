# TurboPi Hardware Abstraction Layer (HAL)

## Purpose

The HAL provides a single interface for hardware interactions and keeps direct
device access out of higher-level services.

This module currently provides:
- Motor HAL primitives with safe startup and calibration support
- Config-selectable motor backend (`sim` or vendor hardware)
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
- `HAL_MOTOR_BACKEND` (`sim` or `vendor`)
- `HAL_MOTOR_VENDOR_REQUIRED`
- `HAL_MOTOR_LEFT_TRIM`
- `HAL_MOTOR_RIGHT_TRIM`
- `HAL_MOTOR_LEFT_SCALE`
- `HAL_MOTOR_RIGHT_SCALE`
- `HAL_MOTOR_MAX_DUTY`
- `HAL_MOTOR_DISABLED_CHANNELS`
- `HAL_MOTOR_BLOCK_ON_DISABLED_CHANNELS`
- `HAL_MOTOR_CHANNEL_SCALE_1`
- `HAL_MOTOR_CHANNEL_SCALE_2`
- `HAL_MOTOR_CHANNEL_SCALE_3`
- `HAL_MOTOR_CHANNEL_SCALE_4`

For field hardening scenarios (for example, an unhealthy CH3 path), set
`HAL_MOTOR_DISABLED_CHANNELS=3` and keep
`HAL_MOTOR_BLOCK_ON_DISABLED_CHANNELS=true` to prevent unsafe degraded motion.

For minor wheel variance or stiction tuning after hardware checks, use
`HAL_MOTOR_CHANNEL_SCALE_*` to apply per-channel multipliers without bypassing
the arbiter/HAL safety contract.

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
python3 -m pytest src/hal/test_motor.py src/hal/test_camera.py src/hal/test_sensor.py -q
```

Run HAL tests plus related safety checks:

```bash
python3 -m pytest src/hal/test_motor.py src/hal/test_camera.py src/hal/test_sensor.py src/voice/test_wake_word.py src/api/test_wake_word_api.py -q
```

Current test layout uses top-level HAL test modules under `src/hal/`
(for example, `src/hal/test_motor.py`) rather than a nested `src/hal/tests/` folder.