# WebSocket Control Protocol

## Endpoint
/ws/control

## Purpose
Low-latency manual control channel for teleoperation.

## Connection Rules
- Only one active control connection allowed
- Disconnect triggers immediate STOP
- Messages are ignored unless robot is ARMED

---

## Message Types

### Drive Command
{
  "type": "drive",
  "linear": 0.3,
  "angular": -0.2
}

### Stop Command
{
  "type": "stop"
}

### Heartbeat
{
  "type": "heartbeat"
}

---

## Safety
- Missing heartbeat > timeout triggers STOP
- E-Stop overrides all messages
