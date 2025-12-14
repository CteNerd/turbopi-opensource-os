# Control and Safety Specification

## Purpose

This document defines how motion control and safety mechanisms are enforced
within TurboPi OpenSource OS.

Safety mechanisms always override control commands.

---

## Control Modes

- Disabled (E-Stop)
- Manual Control
- Autonomous Control

Only one control mode may be active at a time.

---

## Safety Priority Order

1. Emergency Stop
2. Deadman Timeout
3. Safety Guardrails
4. Manual Control
5. Autonomous Behaviors

Higher-priority systems always override lower-priority ones.

---

## Emergency Stop (E-Stop)

### Characteristics
- Latched state
- Requires explicit reset
- Cannot be overridden

### Triggers
- UI button
- API endpoint
- Voice command
- Hardware GPIO (future)

---

## Deadman Timeout

### Purpose
Ensure the robot stops if control input is lost.

### Behavior
- Timer resets on valid control input
- Timeout stops all motors
- Timeout duration configurable

---

## Speed and Acceleration Limits

### Speed Caps
- Maximum linear speed
- Maximum rotational speed

### Acceleration Limits
- Prevent sudden jumps
- Enforced in HAL layer

---

## Safe Startup State

- Motors disabled on boot
- Requires explicit arm command
- UI clearly indicates armed state

---

## Failure Handling

- Any control module crash triggers stop
- Vision or voice failures never affect manual control
