# Control Arbiter

## Priority Order
1. Emergency Stop
2. Deadman Timeout
3. Safety Guardrails
4. Manual Control
5. Autonomous Behaviors

## Inputs
- WebSocket manual commands
- Voice command intents
- Autonomy outputs
- Follow behavior target observations (`target_id`, `center_x`, `area`)

## Behavior Interface
- Autonomous behaviors emit `BehaviorCommand` envelopes with `behavior`, `linear_mps`, and `angular_rps`
- Behaviors implement the `BehaviorProvider` contract and can yield `None` when no motion is requested
- The arbiter is responsible for all clamping, safety checks, and final HAL writes

## Output
- Velocity command to HAL

## Rules
- Only one output active per cycle
- Invalid commands are dropped
- Safety overrides never bypassed
- Manual commands override autonomy for the configured manual override window
- Autonomous commands are accepted only when the robot is armed and manual override is inactive
- Follow behavior outputs are smoothed and routed through `ControlArbiter.apply_autonomy()`
- Lost target handling must force zero motion until a fresh observation is available
