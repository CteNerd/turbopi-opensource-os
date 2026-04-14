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
- Start Follow button calls POST /control/follow/start with optional target_id
- Stop Follow button calls POST /control/follow/stop
- UI polls GET /control/follow/state to display follow enabled/lost-target state
- Joystick uses WebSocket control channel (/ws/control)
- Joystick release sends stop command
- WebSocket disconnect or heartbeat timeout must stop motion immediately
- UI polls control state to display Armed, E-Stop latched, and deadman status

## Vision Page
- UI displays live MJPEG stream from GET /video/stream
- FPS is visible in the UI during streaming
- On stream error (for example API restart), UI automatically reconnects

## Voice Settings Page
- UI allows TTS preview text entry and playback test via POST /voice/tts
- UI exposes volume slider and mute toggle for TTS playback
- TTS volume/mute controls affect browser playback, not motor/safety control

## Conversation Panel
- UI sends chat messages to POST /voice/conversation and renders assistant replies
- UI can optionally speak assistant replies through POST /voice/tts
- Conversation guardrail responses are shown explicitly in the chat alert area
- Conversation mode cannot execute motor/control actions

## System Status Page
- UI displays expanded health data from GET /health (uptime, temperature, memory, disk, services)
- UI refreshes system status automatically while page is open
- "Download Diagnostics Bundle" triggers GET /diagnostics/bundle
- Diagnostics bundles must contain redacted logs/configuration data
