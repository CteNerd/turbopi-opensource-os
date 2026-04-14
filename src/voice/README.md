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

### Text-to-Speech (TTS)

Provider abstraction and OpenAI-backed TTS synthesis:
- `tts_provider.py` defines the provider contract and OpenAI implementation
- `POST /voice/tts` synthesizes text to audio/mpeg
- Requires `OPENAI_API_KEY` in `/etc/turbopi/config.env`
- Designed for audible UI/system feedback only (no direct motor control path)

### Command Intent Parser (`command_intent.py`)

Schema-based command parser that:
- Parses STT transcripts into strict command intents
- **STOP command always recognized and valid** (highest priority)
- Rejects unknown commands for safety
- Supports FOLLOW commands with target extraction
- **Never directly controls motors** - outputs intents for safety arbiter
- Provides confidence scores and audit trail

### API Integration

Voice functionality is integrated into the TurboPi API service with the following endpoints:

**Wake Word:**
- `GET /voice/wake-word/status` - Get current wake word detection status
- `GET /voice/wake-word/config` - Get wake word configuration
- `POST /voice/wake-word/config` - Update wake word configuration

**Speech-to-Text:**
- `POST /voice/stt` - Convert audio to text transcript

**Command Parsing:**
- `POST /voice/command` - Parse voice transcript into command intent for safety arbiter

**Text-to-Speech:**
- `POST /voice/tts` - Synthesize text to audio/mpeg for UI playback

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

# TTS Settings
# Uses OPENAI_API_KEY via server-side requests
```

## Safety Guarantees

1. **No Motor Control**: Wake word detection and command parser have no interface to motor control systems
2. **Voice Capture Only**: Wake word only arms STT voice capture
3. **Intent-Based Commands**: Command parser outputs intents only - execution requires safety arbiter approval
4. **STOP Always Works**: STOP command has highest priority and is always recognized
5. **Unknown Commands Rejected**: Unrecognized commands are explicitly rejected, not guessed
6. **Timeout Protection**: Armed state automatically times out after configured duration
7. **ASCII Only**: Wake words are validated to be ASCII-only
8. **Thread Safe**: All operations are thread-safe
9. **Audit Trail**: All parsed commands preserve raw transcript for logging and review

## Usage

### Programmatic Usage

#### Wake Word Detection

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

#### Command Intent Parsing

```python
from command_intent import CommandIntentParser, CommandType

# Create parser
parser = CommandIntentParser()

# Parse transcript from STT
transcript = "follow the person"
intent = parser.parse(transcript)

if intent.is_valid():
    print(f"Command: {intent.command.value}")
    print(f"Target: {intent.target}")
    print(f"Confidence: {intent.confidence}")
    
    # Route through safety arbiter (NOT shown - this is external)
    # arbiter.process_voice_intent(intent)
else:
    print(f"Unknown command rejected: {transcript}")

# STOP command always works
stop_intent = parser.parse("emergency stop")
assert stop_intent.command == CommandType.STOP
assert stop_intent.is_valid()
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

# Parse voice command from transcript
curl -X POST http://localhost:8080/voice/command \
  -H "Content-Type: application/json" \
  -d '{"transcript": "follow the person"}'

# Synthesize TTS audio
curl -X POST http://localhost:8080/voice/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "System ready."}' \
  -o speech.mp3
```

## Testing

### Unit Tests

```bash
cd src/voice

# Test wake word engine
python3 -m unittest test_wake_word.py -v

# Test command intent parser
python3 -m unittest test_command_intent.py -v

# Run all tests
python3 -m unittest discover -v
```

### API Integration Tests

```bash
cd src/api
python3 -m unittest test_wake_word_api.py -v
python3 -m unittest test_stt_api.py -v
```

### Standalone Testing

```bash
cd src/voice

# Test wake word engine
python3 wake_word.py

# Test command intent parser
python3 command_intent.py
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
         └────────┬───────────┘
                  │
                  │ Transcript
                  ▼
         ┌────────────────────┐
         │  Command Intent    │
         │      Parser        │
         │  (Schema-based)    │
         └────────┬───────────┘
                  │
                  │ Command Intent
                  │ (NOT motor commands)
                  ▼
         ┌────────────────────┐
         │  Safety Arbiter    │
         │  (External module) │
         └────────────────────┘
```

## Supported Commands

### STOP Command
- **Priority**: Highest (always checked first)
- **Variations**: stop, halt, freeze, emergency stop, e-stop
- **Target**: None
- **Behavior**: Immediately recognized, confidence = 1.0

### FOLLOW Command
- **Variations**: follow [target], start following [target]
- **Target**: Extracted from command (e.g., "person", "dog", "cat")
- **Special Cases**: "follow me" normalizes to target="person"
- **Confidence**: ~0.9 for pattern matches

### Unknown Commands
- **Behavior**: Explicitly rejected with UNKNOWN type
- **Confidence**: 0.0
- **Safety**: Prevents unintended actions

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
