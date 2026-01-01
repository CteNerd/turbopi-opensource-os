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

AUTO_UPDATE=false
DOWNLOAD_DIR=/opt/turbopi/downloads

## Rules

- Secrets never committed
- Loaded via systemd EnvironmentFile
- UI edits must validate before write
