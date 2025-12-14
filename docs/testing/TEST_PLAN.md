# Test Strategy

## Layers

1. Unit Tests
- Command parsing
- Safety logic
- Updater logic

2. Replay Tests
- Audio samples (STT)
- Video samples (vision)

3. Simulation
- 2D kinematic follow tests

4. Hardware Smoke Tests
- Motors stop
- Camera frames
- E-Stop latch

## CI Rules
- Tests required for merge
- Releases manual
