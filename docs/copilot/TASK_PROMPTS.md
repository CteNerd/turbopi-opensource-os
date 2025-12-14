# Copilot Task Prompts

## General Rules
- Follow docs/init and docs/api strictly
- Do not invent APIs
- Safety > Features
- No secrets in code

---

## Example Prompt: Updater
"Implement updater service according to docs/updater/PROTOCOL.md.
Respect atomic install, checksum verification, rollback, and reboot rules."

---

## Example Prompt: Teleop
"Implement WebSocket control per docs/api/WEBSOCKET_SPEC.md.
Ensure disconnect triggers STOP and respects arbiter priority."

---

## Example Prompt: Voice
"Implement wake word system per docs/voice/WAKE_WORD.md.
Wake word arms STT only and never bypasses safety."
