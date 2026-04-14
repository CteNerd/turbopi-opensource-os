# Hiwonder TurboPi Readiness Plan (Field Intake)

## Purpose

This document captures hardware/software facts verified from available TurboPi vendor manuals,
the current repository readiness status, blocking gaps, and a concrete plan to complete
robot bring-up safely.

## Source Inputs Used

- Vendor manual pages and tutorial PDFs exported from Google Drive bundle roots:
  - `1. Tutorials`
  - `2. Software Tools`
  - `3. Source  Code & System Image`
- Publicly viewable vendor PDF in Drive:
  - `Raspberry Pi Expansion Board Introduction.pdf`

## Verified Findings

### Hardware profile

- Platform: Raspberry Pi 5 based kit.
- Chassis: Mecanum wheel base.
- Vision: 2-DOF pan-tilt camera setup.
- Sensors/features called out in docs: ultrasonic obstacle detection, line-following, color/object tracking.

### Field intake from live vendor OS session (2026-04-14)

- Runtime platform observed on robot:
  - Debian 12 (bookworm)
  - Kernel `6.6.20+rpt-rpi-2712` on Raspberry Pi 5
  - Python `3.11.2`
- Camera contract observed on robot:
  - USB camera detected (`lsusb` shows `32e6:9005 icSpring`)
  - Vendor camera code opens camera via `cv2.VideoCapture(-1)`
  - Vendor defaults set to `640x480`, `30 FPS`, YUYV fourcc
- Servo configuration observed from vendor files:
  - `servo1: 1535`
  - `servo2: 1500`
- Vendor drivetrain mapping observed from `HiwonderSDK/mecanum.py`:
  - Motor channels are `1..4`
  - Vendor wheel layout comment maps channels to positions:
    - `1`: front-left
    - `2`: front-right
    - `3`: rear-left
    - `4`: rear-right
  - Vendor sign convention in mixed command is:
    - `1`: inverted (`-v1`)
    - `2`: non-inverted (`v2`)
    - `3`: inverted (`-v3`)
    - `4`: non-inverted (`v4`)
- Motor probe on physical robot (wheels lifted, low duty) indicated:
  - Channels `1`, `2`, `4` respond
  - Channel `3` initially produced stuck/noise behavior and did not spin normally
  - Follow-up isolation indicates issue is localized to the rear-left wheel path (wheel starts after light tap), not a global drive-stack failure

### Expansion board capabilities (verified from vendor PDF)

- Expansion board family used by TurboPi references board type A.
- Motor control chip: `SA8339` (4-channel motor control context in vendor material).
- Interfaces called out:
  - 4-channel motor interface
  - 2-channel bus servo interface
  - 6-channel PWM servo interface
  - 3-channel I2C
  - 2-channel GPIO
  - buzzer/status LEDs/keys

### Runtime and operations behavior from tutorial set

- Battery low-voltage warning threshold appears at approximately `7.1V`.
- App-based network setup is documented (default hotspot flow and mode switching).
- VNC and image flashing workflows are provided in tutorial PDFs.
- Vendor image workflow assumes a prebuilt OS image path.

## Current Repo Readiness (This Repository)

### Ready/strong

- Safety architecture, arbiter patterns, and stop semantics are present and documented.
- Dual networking architecture and update model are documented and partially implemented.
- API/control/voice/vision software scaffolding exists with broad test coverage.

### Not ready for physical deployment yet

- HAL remains simulation-first in current codebase for core hardware paths.
- No complete board-specific driver integration verified yet for:
  - SA8339 motor channels
  - Servo channel mapping and pulse limits
  - Sensor pin/bus mapping
  - Camera hardware path validation on target kit

### Implementation status update (this repository)

- Added a config-selectable motor HAL backend with safe fallback:
  - `HAL_MOTOR_BACKEND=sim` (default)
  - `HAL_MOTOR_BACKEND=vendor` (Hiwonder SDK when available)
- Added vendor-proven motor channel/sign mapping in HAL adapter:
  - `1:-left`, `2:right`, `3:-left`, `4:right`
- Added hardening control for unhealthy channels:
  - `HAL_MOTOR_DISABLED_CHANNELS` (for example `3`)
  - `HAL_MOTOR_BLOCK_ON_DISABLED_CHANNELS=true` to fail safe on degraded path
- Added optional per-channel scaling for hardening/tuning:
  - `HAL_MOTOR_CHANNEL_SCALE_1..4`
- Added strict vendor backend startup option:
  - `HAL_MOTOR_VENDOR_REQUIRED=true` fails startup when vendor backend is unavailable
- Control arbiter now constructs motor HAL through config-driven factory (no bypass of arbiter/HAL contract).
- Added control observability fields exposed via `/control/state`:
  - `motor_backend`, `motor_disabled_channels`, `motor_degraded`, `motor_degraded_reason`
- Added bench-validation utility:
  - `system/motor_channel_probe.py` for manual-step low-duty channel tests

## Blocking Information Still Needed

The following are required before safe production deployment on physical hardware:

1. Final physical confirmation of channel-to-wheel mapping and direction sign on this assembled unit under floor-load conditions.
2. Servo channel-to-joint assignment (`servo1` vs `servo2` to pan/tilt) and safe bounds for this build.
3. Complete board pinout/address map for I2C/GPIO/PWM/bus-servo interfaces.
4. Confirmed vendor-side fail-safe expectations (disconnect/watchdog behavior if any).
5. Hardening pass for rear-left wheel stiction/variance (mechanical check plus optional `HAL_MOTOR_CHANNEL_SCALE_3` tuning if required).

## Staged Completion Plan

## Phase 0: Evidence Lock (must complete first)

1. Collect and archive board-level pinout and channel maps.
2. Record exact hardware revision identifiers from board silkscreen/manual.
3. Record canonical runtime defaults (network mode, credentials flow, battery thresholds).
4. Complete motor channel `3` isolation test (swap-test method) and record root cause.

Exit criteria:
- Pin/channel map is explicit and reviewable.
- Unknown hardware assumptions are reduced to zero for motor/servo/sensor routing.
- All four drive channels are validated as operational (or hardware repair path is documented and resolved).

## Phase 1: HAL Hardware Adapter Bring-Up

1. Implement board-specific motor adapter that maps arbiter velocity output to SA8339 channels.
2. Implement pan/tilt servo adapter with clamped safe bounds.
3. Implement sensor adapters used by current behaviors (at minimum ultrasonic + line follower).
4. Keep safe startup state disarmed and preserve E-STOP precedence.

Exit criteria:
- Unit tests for mapping, clamping, and disarm/estop behavior pass.
- Bench tests validate wheel direction correctness and immediate stop behavior.

## Phase 2: Integration with Safety + Control

1. Wire hardware HAL into control arbiter path only (no bypasses).
2. Validate disconnect-stop, deadman timeout, and takeover-stop on real hardware.
3. Verify network transitions do not break emergency access expectations.

Exit criteria:
- Teleop and stop semantics behave consistently under normal and failure scenarios.
- No direct motor commands outside arbiter/HAL contract.

## Phase 3: Vision/Voice/UX Hardening

1. Validate camera pipeline performance and frame reliability.
2. Complete TTS pathway and verify voice cannot bypass safety arbitration.
3. Improve UI state visibility for armed/disarmed/estop/deadman and low voltage conditions.

Exit criteria:
- End-to-end operator flow works from boot to safe teleop and controlled autonomy.

## Phase 4: Deployment Readiness

1. Add hardware-in-the-loop smoke tests and acceptance checklist automation where possible.
2. Validate installation scripts and service startup on clean image.
3. Freeze baseline config and produce reproducible install procedure.

Exit criteria:
- Repeatable install on fresh image.
- Acceptance tests pass on physical hardware.

## Immediate Next Actions

1. Run and record the M3/M4 swap isolation test result to classify channel `3` issue as board-path vs motor/cable-path.
2. Record final channel-to-wheel and polarity table from live probe results after isolation.
3. Start Phase 1 coding with a hardware adapter that uses the vendor-proven channel/sign convention and keeps disarmed startup.
4. Gate hardware activation behind config and keep simulation fallback path intact.
5. Run safety regression tests focused on estop/deadman/disconnect before any floor motion tests.

Status update:

- Software integration work is complete for staged bring-up through hardware-backed motor HAL and safety integration.
- Remaining completion risk is now narrowed to physical hardening/tuning of the rear-left wheel path under load.

## CH3 Hardening Note

- Current field intake indicates channel `3` may be unhealthy on the tested unit.
- Use this temporary safety gate during bring-up:
  - `HAL_MOTOR_BACKEND=vendor`
  - `HAL_MOTOR_DISABLED_CHANNELS=3`
  - `HAL_MOTOR_BLOCK_ON_DISABLED_CHANNELS=true`
- This intentionally blocks non-zero motion commands touching channel `3` until hardware isolation/repair is complete.

## Notes on Vendor Source/Image Access

- If `3. Source  Code & System Image` only contains `Important Notice 25.pdf`, treat source/image bundle as restricted.
- Proceed using available manuals and user-provided assets; do not assume private source availability.
