# TurboPi OpenSource OS — Copilot Instructions

These instructions apply to Copilot Chat, Copilot code review, and tasks assigned to Copilot in this repository.

## 0) Source of truth and conflicts
- Treat repository docs as authoritative. If instructions conflict, prefer this order:
  1) docs/init/*
  2) docs/api/*
  3) docs/control/*
  4) docs/updater/*
  5) docs/voice/*
  6) docs/config/*
  7) Issue description / acceptance criteria
- If you cannot comply due to missing info, STOP and ask for clarification in the issue/PR notes (do not guess).

## 1) Scope discipline
- Implement only what the assigned issue requests.
- Do not introduce new features, new endpoints, or refactors unrelated to the issue.
- Keep PRs small and reviewable; one concern per PR.

## 2) Safety is non-negotiable (robot control)
- Default state is motors DISARMED.
- E-STOP must override everything and be fast and reliable.
- Voice/LLM output must NEVER directly control motors.
- All motion commands must go through the safety arbiter and HAL.
- Disconnects/timeouts must cause STOP.

## 3) Networking rules (Recovery Plane vs Operational Plane)
- Emergency AP (recovery access) must remain independent and always available.
- Home Wi-Fi client logic must not break or disable the Emergency AP.
- Do not merge recovery-plane and operational-plane responsibilities in a single PR unless the issue explicitly says so.

## 4) Update and release rules (supply chain)
- Updates install only promoted stable releases (no auto-update unless explicitly enabled).
- Verify integrity (checksum and/or signature when specified).
- Installs must be atomic and support automatic rollback on failed health checks.
- “Update Now” may restart services or reboot if required; explain behavior in UI text where relevant.
- Never hardcode secrets or tokens.

## 5) Configuration rules
- All runtime configuration is via `/etc/turbopi/config.env` (loaded by systemd EnvironmentFile).
- Never commit secrets; use placeholder values in docs/examples.
- Validate config before applying; fail safely.

## 6) API + protocol rules
- Backend endpoints must match docs/api/OPENAPI.yaml.
- WebSocket messages must match docs/api/WEBSOCKET_SPEC.md.
- If an endpoint/protocol change is required, update the spec and explain in the PR.

## 7) Testing expectations
- Add unit tests for non-trivial logic (parsers, safety, updater, state machines).
- Avoid hardware assumptions in unit tests; use mocks/fakes.
- Ensure failure paths are covered (network down, bad checksum, missing config).

## 8) PR hygiene (required)
- PR title format: "(#ISSUE) <short description>"
- PR description must include: "Closes #ISSUE" (or Fixes/Resolves) and a checklist of acceptance criteria.
- If behavior changes, update the relevant docs.

## 9) Logging and diagnostics
- Prefer structured logs; avoid logging secrets.
- Add useful diagnostics to help operate without SSH (where applicable).

## 10) Shell scripting best practices
- Always quote variables to prevent word splitting: use `"$VAR"` not `$VAR`
- Use `set -e` to exit on errors; add traps for meaningful error messages
- Validate inputs and check for required files/interfaces before proceeding
- When displaying configuration values (passwords, SSIDs), ensure they match the actual config files
  - Extract values from config files with validation (check length, format)
  - Never hardcode displayed values that could drift from actual config
- Use word boundaries in grep patterns: `grep -qw "pattern"` not `grep -q "pattern"` to avoid partial matches
- For placeholder values in config files (like `<MAC>`, `<PASSWORD>`):
  - Prefer automatic generation/replacement during installation when safe and possible
  - If placeholders would break functionality, auto-generate values or fail installation with clear error
  - Manual post-install configuration contradicts "always-on" or "zero-config" goals
  - If manual replacement required, make this explicit and provide clear examples
- Make scripts automation-friendly:
  - Detect non-interactive environments with `[ -t 0 ]` before using `read` prompts
  - Add timeouts to `read` commands: use `read -t 30` to prevent hanging in CI/automated deployments
  - Provide sensible defaults or fail fast with clear errors in non-interactive mode
- String extraction pitfalls:
  - When extracting MAC address suffixes, be precise: for last 4 hex digits from `aa:bb:cc:dd:ee:ff`, use `tr -d ':' | tr '[:lower:]' '[:upper:]' | tail -c 5 | head -c 4` to get `EEFF`
  - `tail -c N` includes the newline in the count; for 4 chars use `tail -c 5 | head -c 4`
  - Test extraction logic with sample inputs before deployment
- Service management:
  - For systemd `Type=forking`, background daemons started in ExecStartPost must use `--daemon` flag to fork properly
  - Verify processes before sending kill signals: check `/proc/$PID/comm` to prevent PID recycling issues
  - Use polling loops with timeouts instead of hardcoded sleeps when waiting for services
  - Make service startup timeouts configurable via environment variables (e.g., `SERVICE_START_TIMEOUT`)
  - Always verify service is active after polling timeout and provide clear troubleshooting commands
- Documentation consistency:
  - When describing MAC address formats or other technical identifiers in multiple places, use consistent precise language
  - For MAC suffixes: always specify "last 4 hex digits after removing colons" with concrete example (e.g., `EEFF` from `aa:bb:cc:dd:ee:ff`)
  - Avoid ambiguous phrases like "last 4 characters" which could mean characters with colons or without
  - Update all documentation locations (README, docs/init, etc.) when clarifying technical details
  - Keep numbered steps sequential without duplicates; verify step numbering when adding/removing steps
- Privacy and logging:
  - Disable privacy-sensitive logging by default (DNS queries, DHCP transactions logging MAC addresses/hostnames)
  - Add comments explaining how to enable for troubleshooting
  - Balance debugging needs with privacy concerns
- Configuration extraction and validation:
  - Extract and validate configuration values (passwords, SSIDs) before service startup when possible
  - Check config files exist before extraction to provide better error messages
  - Validate extracted values meet requirements before displaying to users