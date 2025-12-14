# Voice System Specification

## Overview

The voice system provides speech-based interaction while ensuring that
robot safety and real-time control are never compromised.

Voice is divided into distinct pipelines to reduce complexity and risk.

---

## Voice Pipelines

1. Wake Word Detection
2. Speech-to-Text (STT)
3. Command Intent Parsing
4. Conversational Processing
5. Text-to-Speech (TTS)

Each pipeline operates independently and communicates through explicit interfaces.

---

## Wake Word

### Default
- Wake word: Jarvis

### Requirements
- Runs locally on the robot
- Always-on, low CPU usage
- Configurable via UI
- Case-insensitive

### Behavior
- Wake word arms voice capture
- Does NOT trigger motion
- Times out if no speech follows

### UI Controls
- Change wake word
- Enable/disable wake word
- Sensitivity (future)

---

## Speech-to-Text (STT)

### Purpose
Convert speech into text for command parsing or conversation.

### Implementation
- Cloud-based STT (OpenAI API)
- Audio captured locally
- Requests routed server-side only

### Output
Plain text transcript

---

## Command Intent Parsing

### Rules
- Strict schema-based commands
- Unknown phrases are rejected
- STOP command always valid

### Example Intent
Intent: FOLLOW
Target: person
Confidence: 0.92

---

## Conversation Processing

### Purpose
Enable natural conversation without affecting robot motion.

### Rules
- Asynchronous only
- Cannot emit motor commands
- Responses may trigger TTS output

### Deployment Phases
- Phase 1: Cloud LLM
- Phase 2: Home server LLM
- Phase 3: Optional on-device fallback

---

## Text-to-Speech (TTS)

### Purpose
Provide audible feedback and conversation responses.

### Providers
- OpenAI TTS (default)
- ElevenLabs (optional)

### Use Cases
- Status confirmations
- Update notifications
- Conversational replies

---

## Safety Guarantees

- Voice cannot bypass control arbiter
- Wake word never arms motors
- E-Stop overrides all voice input
