# WebSocket Control Protocol

## Endpoint
/ws/control

## URL
- ws://<robot-ip>:8765/ws/control (default)
- Port is configurable via API_WS_PORT

## Purpose
Low-latency manual control channel for teleoperation.

## Connection Rules
- Only one active control connection allowed
- Disconnect triggers immediate STOP
- Messages are ignored unless robot is ARMED
- Drive messages are clamped to configured safety limits

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

### Server Acknowledgement (example)
{
  "status": "ok"
}

---

## Safety
- Missing heartbeat > timeout triggers STOP
- E-Stop overrides all messages
- Deadman timeout is configured via DEADMAN_TIMEOUT_MS
- Speed limits are configured via MAX_LINEAR_SPEED and MAX_ANGULAR_SPEED
