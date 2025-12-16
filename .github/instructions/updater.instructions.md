---
applyTo: "src/**/updater/**,.github/workflows/**,docs/updater/**"
---
# Updater instructions
- Follow docs/updater/PROTOCOL.md exactly.
- Use atomic install + rollback on failed health checks.
- Never auto-update unless explicitly enabled by user config/UI.
- Log progress clearly and redact secrets.