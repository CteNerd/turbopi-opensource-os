# Skill: TurboPi Hardware Readiness Intake

Use this skill when validating whether the repository is ready for physical robot deployment.

## Goal

Build an evidence-based readiness assessment from vendor documentation, identify blocking unknowns,
and produce a safe, phased implementation plan.

## Inputs

- Vendor manual/tutorial bundle exports (typically folders like `1. Tutorials`, `2. Software Tools`, `3. Source  Code & System Image`)
- Any board photos showing chip labels and revision marks
- Repository state (HAL/control/api/ui implementation and tests)

## Workflow

### 1) Inventory evidence
- Enumerate vendor files first; prioritize board/controller/pinout docs.
- Extract text from PDFs and search for: motor chip, channel map, I2C/GPIO/PWM/bus-servo interfaces, camera path, battery thresholds, network defaults.

### 2) Separate facts from assumptions
- Create two lists:
  - Verified facts (with evidence source)
  - Unknowns/blockers (must not be guessed)

### 3) Map against repository implementation
- Compare vendor hardware requirements against current HAL/control/voice/vision capabilities.
- Flag missing adapters or simulation-only implementations.

### 4) Produce phased plan
- Phase 0: evidence lock (pin/channel maps, board revision)
- Phase 1: hardware HAL adapters
- Phase 2: safety/control integration validation
- Phase 3: vision/voice/UI hardening
- Phase 4: deployment acceptance testing

### 5) Persist findings
- Update `docs/init/HIWONDER_TURBOPI_READINESS_PLAN.md`.
- Store durable memories for stable facts and repeated workflow optimizations.

## Non-negotiables

- Never bypass safety arbiter/HAL contracts.
- Never infer hardware pin mapping without explicit documentation.
- Keep E-STOP and disconnect/deadman STOP semantics intact during bring-up.

## Deliverables

- Readiness verdict (`ready`, `not ready`, or `conditionally ready`)
- Top blockers list
- Information still required
- Ordered next actions with exit criteria