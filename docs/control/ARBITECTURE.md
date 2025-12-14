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

## Output
- Velocity command to HAL

## Rules
- Only one output active per cycle
- Invalid commands are dropped
- Safety overrides never bypassed
