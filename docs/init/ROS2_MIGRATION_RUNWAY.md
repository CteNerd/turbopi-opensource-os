# ROS 2 Migration Runway

## Purpose

Define migration boundaries and a safe, phased plan to adopt ROS 2 without regressing current TurboPi safety guarantees.

This runway does not change runtime behavior. It documents interfaces and sequencing for future implementation work.

## Non-Negotiable Safety Constraints

- Motors remain disarmed by default on startup.
- E-STOP semantics remain latched and highest priority.
- Voice/LLM outputs never bypass control contracts.
- All motion commands continue to flow through the safety arbiter and HAL.
- Disconnect/timeout behavior must still force STOP.

## Interface Boundaries (Current -> ROS 2)

### 1) UI/API Boundary

Current contract:
- HTTP endpoints in `docs/api/OPENAPI.yaml`
- Control WebSocket in `docs/api/WEBSOCKET_SPECIAL.md`

ROS 2 boundary:
- Keep UI contract stable during migration.
- API service becomes an adapter that translates UI/API requests to ROS 2 service/topic calls.
- No browser client should require ROS-specific changes.

### 2) Control/Safety Boundary

Current contract:
- `ControlArbiter` remains the only motion path.
- Behavior outputs call arbiter methods; HAL writes happen only after arbiter checks.

ROS 2 boundary:
- Introduce ROS-facing wrappers around arbiter inputs/outputs.
- Do not publish direct motor commands from voice, conversation, or UI-facing adapters.
- Preserve explicit precedence: E-STOP > deadman > manual > autonomy.

### 3) HAL Boundary

Current contract:
- HAL modules abstract camera, motor, and sensors.

ROS 2 boundary:
- HAL implementations remain local device drivers/adapters.
- ROS nodes consume HAL-facing abstractions rather than directly touching device files where possible.
- Maintain fail-safe behavior when device reads/writes fail.

### 4) Vision Boundary

Current contract:
- Detection/tracking/target-selection feed follow behavior inputs.

ROS 2 boundary:
- Vision runtime can become ROS publishers, but output schema must map to existing target observation semantics (`target_id`, `center_x`, `area`, timestamp).
- Follow behavior logic stays deterministic and testable outside ROS.

### 5) Voice Boundary

Current contract:
- Wake word arms capture only.
- STT + intent parser produce structured intents.

ROS 2 boundary:
- Voice nodes may publish intents/events, not raw motor commands.
- Intent-to-action mapping still routes through control safety contracts.

### 6) Updater/Operations Boundary

Current contract:
- Updater service handles stable-release installation and rollback.

ROS 2 boundary:
- ROS package artifacts/versioning must align with existing promoted-release model.
- Upgrade and rollback remain atomic at system level.

## Migration Plan (Phased)

### Phase 0: Contract Freeze and Mapping

Deliverables:
- Freeze external UI/API contracts for control and status paths.
- Define ROS interface mapping table (topics/services/actions) for each current module boundary.
- Define naming/versioning conventions for messages and services.

Exit criteria:
- Mapping table reviewed and approved.
- No required breaking changes to current UI/API contract.

### Phase 1: ROS 2 Adapter Skeletons (No Behavior Change)

Deliverables:
- Add optional ROS adapter layer beside current direct-call pathways.
- Add feature flags for adapter activation in development only.
- Keep default runtime on existing non-ROS path.

Exit criteria:
- API/UI behavior unchanged when adapters disabled.
- Adapter unit tests pass with mocks.

### Phase 2: Control and Teleop Bridging

Deliverables:
- Route manual control and follow observations through ROS adapters in test mode.
- Enforce single active control session and disconnect-stop semantics through adapter path.

Exit criteria:
- Existing control safety tests pass unchanged.
- New adapter-path tests demonstrate identical stop and clamp behavior.

### Phase 3: Vision/Voice Bridging

Deliverables:
- Publish normalized vision observations via ROS.
- Publish voice intents via ROS.
- Maintain parser and guardrail behavior independent of ROS runtime availability.

Exit criteria:
- Replay tests remain deterministic.
- Safety regressions absent under voice/vision failures.

### Phase 4: Operational Hardening

Deliverables:
- Add startup dependency checks and clear failure diagnostics.
- Document deployment modes (non-ROS default, ROS-enabled).
- Define rollback behavior when ROS components fail health checks.

Exit criteria:
- CI covers both modes.
- Production default remains safe and recoverable.

## Test Strategy During Migration

- Preserve existing unit/replay/simulation suites as baseline conformance checks.
- Add adapter conformance tests that compare ROS-path outputs vs current-path outputs for identical inputs.
- Add failure-mode tests: ROS graph unavailable, delayed messages, dropped connections, and stale commands.
- Add startup validation tests for invalid ROS-related configuration values.

## Risks and Mitigations

- Risk: Safety semantics divergence between direct and ROS paths.
  Mitigation: Golden-path conformance tests and shared arbiter logic.

- Risk: Operational complexity and startup races.
  Mitigation: Explicit dependency checks, clear logs, fail-fast in ROS-enabled mode.

- Risk: UI/API contract drift.
  Mitigation: Keep API adapter boundary stable and spec-first changes only.

## Definition of Done for Future ROS Implementation Epics

- Existing safety and control tests still pass.
- Interface mappings implemented without bypassing arbiter/HAL constraints.
- OpenAPI and WebSocket behavior remain consistent or explicitly versioned.
- Rollback path documented and verified.
