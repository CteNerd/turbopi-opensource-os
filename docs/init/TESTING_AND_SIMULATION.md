# Testing & Simulation Strategy

## Test Layers

1. Unit Tests
2. Replay Tests (audio/video)
3. Control Math Simulation
4. Hardware Smoke Tests

## Simulation

- 2D kinematic simulation
- Fake sensors and targets
- Used to validate follow logic

## CI Expectations

- Tests must pass for merge
- Builds created on main
- Releases created manually
