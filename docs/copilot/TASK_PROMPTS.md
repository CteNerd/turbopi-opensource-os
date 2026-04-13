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
"Implement WebSocket control per docs/api/WEBSOCKET_SPECIAL.md.
Require same-host UI origin checks, enforce takeover/disconnect STOP behavior,
and ensure UI drive limits are sourced from backend control state/config."

---

## Example Prompt: Address PR Feedback
"Address all unresolved comments on PR #<N>.
Reply to every thread (including no-change explanations), implement required fixes,
run targeted tests, then resolve each thread with references to updated files/commits."

---

## Example Prompt: Voice
"Implement wake word system per docs/voice/WAKE_WORD.md.
Wake word arms STT only and never bypasses safety."
