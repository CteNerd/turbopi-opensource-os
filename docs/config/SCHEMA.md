# Configuration Schema

All configuration is stored in `/etc/turbopi/config.env`.

## Required Fields

ROBOT_NAME=Jarvis
WAKE_WORD=Jarvis

## Optional Fields

OPENAI_API_KEY=***
TTS_PROVIDER=openai
STT_PROVIDER=openai

MAX_LINEAR_SPEED=0.5
MAX_ANGULAR_SPEED=1.2
DEADMAN_TIMEOUT_MS=500

HAL_MOTOR_LEFT_TRIM=0.0
HAL_MOTOR_RIGHT_TRIM=0.0
HAL_MOTOR_LEFT_SCALE=1.0
HAL_MOTOR_RIGHT_SCALE=1.0

HAL_CAMERA_WIDTH=640
HAL_CAMERA_HEIGHT=480
HAL_CAMERA_FPS=30
HAL_CAMERA_PIXEL_FORMAT=rgb24

HAL_SENSOR_DISTANCE_OFFSET_CM=0.0

AUTO_UPDATE=false
DOWNLOAD_DIR=/opt/turbopi/downloads

## Rules

- Secrets never committed
- Loaded via systemd EnvironmentFile
- UI edits must validate before write
- HAL calibration values should fail safe if missing or invalid by falling back to conservative defaults
