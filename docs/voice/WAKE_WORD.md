# Wake Word System

## Default
Jarvis

## Behavior
- Always-on
- Arms voice capture only
- Does not arm motors
- Times out if no speech follows
- Integrates with STT endpoint for audio transcription

## UI
- Editable wake word
- Enable/disable toggle
- Saved to config.env

## Constraints
- ASCII words only (initially)
- Case-insensitive

## Voice Pipeline Integration

Wake word detection is the first step in the voice pipeline:
1. Wake word detected → arms voice capture
2. Audio captured → sent to `/voice/stt` endpoint
3. STT returns transcript → processed for commands or conversation
4. Response (if any) → TTS output

See `src/voice/README.md` for complete voice system documentation.

