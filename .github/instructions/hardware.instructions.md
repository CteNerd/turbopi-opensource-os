---
applyTo: "src/**/hal/**,src/**/control/**,src/**/vision/**,src/**/voice/**,docs/init/**"
---
# Hardware readiness instructions
- Use evidence-first integration: verify board/chip/pin/channel details from vendor docs before coding.
- Do not assume motor channel ordering, servo limits, or sensor pin mappings.
- Keep all motion output routed through control arbiter and HAL safety contracts.
- Capture verified facts, unresolved gaps, and phased plan updates in `docs/init/HIWONDER_TURBOPI_READINESS_PLAN.md`.
- Treat restricted vendor source/image bundles as unavailable unless explicitly provided by the user.