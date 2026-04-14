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

## Implemented Suites

- Vision replay pipeline tests: `src/vision/test_replay_pipeline.py`
- Voice command replay tests: `src/voice/test_replay_command_intent.py`
- 2D follow behavior simulation tests: `src/control/test_follow_sim_2d.py`

## CI Rules
- Tests required for merge
- Releases manual
