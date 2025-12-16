---
applyTo: "src/**/control/**,src/**/hal/**,src/**/safety/**"
---
# Control/Safety instructions
- Safety arbiter is the only path to motion output.
- Enforce deadman timeout and disconnect-stop behavior.
- Add tests for safety state transitions and failure modes.
- Never permit voice/LLM outputs to bypass control contracts.