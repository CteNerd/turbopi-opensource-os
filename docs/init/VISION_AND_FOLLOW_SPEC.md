# Vision & Follow Behavior Specification

## Vision Pipeline

1. Frame Capture (Pi Cam)
2. Detection (interval-based)
3. Tracking (per-frame)
4. Target Selection
5. Output to Behavior Layer

## Detection Requirements

- Benchmark multiple models
- Optimize for FPS + stability
- Person class required

## Tracking

- Persistent IDs
- Smooth bounding boxes
- Lost-target handling

## Follow Behavior

### Inputs
- Target bounding box
- Estimated distance
- Obstacle sensors

### Control Law
- Horizontal offset → turn rate
- Target size → forward/back
- Dead zone to prevent oscillation

### Failure Modes
- Lost target → stop or search
- Obstacle too close → override stop
