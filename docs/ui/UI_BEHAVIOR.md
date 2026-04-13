# UI Behavior Specification

## Pages
- Setup
- Control
- Vision
- System
- Updates
- Voice Settings

## Update Page
- Check updates
- Update Now
- Restart Services
- Reboot Bot
- Explain differences clearly

## Safety Indicators
- Armed / Disarmed
- E-Stop Active
- Control Mode

## Control Page
- Arm button calls POST /control/arm
- Disarm button calls POST /control/disarm
- E-Stop button calls POST /control/estop
- Reset E-Stop button calls POST /control/estop/reset
- Joystick uses WebSocket control channel (/ws/control)
- Joystick release sends stop command
- WebSocket disconnect or heartbeat timeout must stop motion immediately
- UI polls control state to display Armed, E-Stop latched, and deadman status

## Vision Page
- UI displays live MJPEG stream from GET /video/stream
- FPS is visible in the UI during streaming
- On stream error (for example API restart), UI automatically reconnects
