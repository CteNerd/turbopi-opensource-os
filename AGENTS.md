# Agent instructions (TurboPi OpenSource OS)

When working an assigned issue:
- Start by restating the acceptance criteria as a checklist in the PR.
- Identify required files from docs/* and link them in the PR description.
- Prefer incremental commits that map to acceptance criteria.
- If anything is unclear, write a short "Questions/Assumptions" section in the PR and proceed only with safe defaults.

When addressing PR feedback:
- Reply to every review comment/thread, even when no code change is required.
- For each unresolved thread, either (a) link to the exact fix commit/file or (b) explain why no change is needed.
- Do not resolve a thread without posting a reviewer-facing reply.
- If tooling reports no active PR, fall back to explicit PR number/branch and continue.

Control/WebSocket safety checklist (manual control work):
- Enforce same-host UI origin policy for control HTTP endpoints and websocket handshake.
- On websocket disconnect OR connection takeover, force immediate STOP.
- Validate API_WS_PORT and fail startup on invalid values.
- Treat websocket server dependency as required when teleoperation is enabled.
- Keep OpenAPI and websocket docs synchronized with 403/error behavior and safety semantics.
- Avoid hard-coded joystick limits in UI; derive from backend-reported limits/config.