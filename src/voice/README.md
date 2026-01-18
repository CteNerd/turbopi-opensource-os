# TurboPi Voice Module

## Overview

The voice module provides wake word detection and speech-to-text (STT) capabilities for TurboPi. The voice system enables voice-activated interaction while maintaining safety guarantees.

## Components

### Wake Word Engine (`wake_word.py`)

Low-CPU wake word detection engine that:
- Detects configured wake word (default: "Jarvis")
- Arms voice capture for STT processing
- **Never triggers motor control**
- Automatically times out if no speech follows

### Speech-to-Text (STT) API

Server-side STT endpoint that:
- Converts audio input to text using OpenAI Whisper API
- Requires `OPENAI_API_KEY` in `/etc/turbopi/config.env`
- Accepts audio/wav format (max 10MB)
- Returns JSON transcript
- **Server-side API calls only** (no client-side API exposure)

### API Integration

Voice functionality is integrated into the TurboPi API service with the following endpoints:

**Wake Word:**
- `GET /voice/wake-word/status` - Get current wake word detection status
- `GET /voice/wake-word/config` - Get wake word configuration
- `POST /voice/wake-word/config` - Update wake word configuration

**Speech-to-Text:**
- `POST /voice/stt` - Convert audio to text transcript

See `docs/api/OPENAPI.yaml` for full API specification.

### Standalone Service (`main.py`)

Optional standalone wake word service for dedicated wake word processing. 

**Current Deployment:** Wake word detection is integrated into the API service and automatically available when the API is running. The standalone service (`turbopi-wake-word.service`) is reserved for future use if separate wake word processing is needed (e.g., for audio pipeline integration).

**Installation:** You do **not** need to install or run the standalone service separately. When the TurboPi API service is running, wake word detection is automatically available via the API endpoints described above.

If you need to run the standalone service for advanced use cases, it can be enabled via:
```bash
sudo systemctl enable turbopi-wake-word.service
sudo systemctl start turbopi-wake-word.service
```

## Configuration

Voice settings are configured via environment variables in `/etc/turbopi/config.env`:

```bash
# Wake Word Settings
WAKE_WORD=Jarvis              # Wake word to detect
WAKE_WORD_ENABLED=true        # Enable/disable detection
WAKE_WORD_TIMEOUT=5           # Timeout in seconds after detection

# STT Settings
OPENAI_API_KEY=your-key-here  # Required for STT functionality
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

# Convert audio to text (STT)
curl -X POST http://localhost:8080/voice/stt \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
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
python3 -m unittest test_stt_api.py -v
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
         ┌────────────────────┐
         │   STT Endpoint     │
         │  (OpenAI Whisper)  │
         │  Server-side only  │
         └────────────────────┘
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
