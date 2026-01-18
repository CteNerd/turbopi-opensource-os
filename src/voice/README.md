# TurboPi Voice Module

## Overview

The voice module provides wake word detection capabilities for TurboPi. The wake word system enables voice-activated interaction while maintaining safety guarantees.

## Components

### Wake Word Engine (`wake_word.py`)

Low-CPU wake word detection engine that:
- Detects configured wake word (default: "Jarvis")
- Arms voice capture for STT processing
- **Never triggers motor control**
- Automatically times out if no speech follows

### API Integration

Wake word functionality is integrated into the TurboPi API service with the following endpoints:

- `GET /voice/wake-word/status` - Get current wake word detection status
- `GET /voice/wake-word/config` - Get wake word configuration
- `POST /voice/wake-word/config` - Update wake word configuration

See `docs/api/OPENAPI.yaml` for full API specification.

### Standalone Service (`main.py`)

Optional standalone wake word service for future use. Currently, wake word detection is integrated into the API service.

## Configuration

Wake word settings are configured via environment variables in `/etc/turbopi/config.env`:

```bash
WAKE_WORD=Jarvis              # Wake word to detect
WAKE_WORD_ENABLED=true        # Enable/disable detection
WAKE_WORD_TIMEOUT=5           # Timeout in seconds after detection
```

## Safety Guarantees

1. **No Motor Control**: Wake word detection has no interface to motor control systems
2. **Voice Capture Only**: Wake word only arms STT voice capture
3. **Timeout Protection**: Armed state automatically times out after configured duration
4. **ASCII Only**: Wake words are validated to be ASCII-only
5. **Thread Safe**: All operations are thread-safe

## Usage

### Programmatic Usage

```python
from wake_word import WakeWordEngine

# Create engine
engine = WakeWordEngine()

# Process text (in production, this would be audio-based)
detected = engine.process_text("Hey Jarvis, turn on the lights")

if detected:
    print("Wake word detected!")
    
    # Check if still armed
    if engine.is_armed():
        # Trigger STT capture
        pass
    
    # Disarm after processing
    engine.disarm()
```

### API Usage

```bash
# Get wake word status
curl http://localhost:8080/voice/wake-word/status

# Update wake word
curl -X POST http://localhost:8080/voice/wake-word/config \
  -H "Content-Type: application/json" \
  -d '{"wake_word": "Computer"}'

# Disable wake word detection
curl -X POST http://localhost:8080/voice/wake-word/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Testing

### Unit Tests

```bash
cd src/voice
python3 -m unittest test_wake_word.py -v
```

### API Integration Tests

```bash
cd src/api
python3 -m unittest test_wake_word_api.py -v
```

## Architecture

```
┌─────────────────────────────────────┐
│     Wake Word Detection Engine     │
│  (Always-on, Low CPU, Thread-safe) │
└─────────────────┬───────────────────┘
                  │
                  │ Arms voice capture only
                  │ (NO motor control)
                  ▼
         ┌────────────────┐
         │  STT Service   │
         │  (Future)      │
         └────────────────┘
```

## Future Enhancements

1. **Audio-based Detection**: Replace text pattern matching with actual audio processing
2. **Advanced Engines**: Integration with Porcupine, Snowboy, or other wake word libraries
3. **Custom Wake Words**: Training custom wake word models
4. **Sensitivity Control**: Adjustable detection sensitivity
5. **Multi-wake Words**: Support for multiple wake words

## Limitations

Current implementation:
- Text-based pattern matching (not real audio processing)
- Single wake word support
- Case-insensitive matching only
- ASCII characters only

These limitations are intentional for the initial implementation to keep CPU usage low and implementation simple.
