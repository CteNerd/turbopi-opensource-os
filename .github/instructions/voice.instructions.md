---
applyTo: "src/**/voice/**,docs/voice/**,src/api/main.py"
---
# Voice instructions
- Voice/LLM outputs must NEVER directly control motors or trigger safety-critical actions.
- Wake word detection only arms voice capture - it does not trigger any robot actions.
- STT endpoint must use server-side API calls only (no client-side API key exposure).
- All voice API keys (OPENAI_API_KEY) must be loaded from environment/config.env.
- Audio processing must have size limits to prevent memory exhaustion (currently 10MB max).
- Error messages must not leak API keys or sensitive information from cloud providers.
