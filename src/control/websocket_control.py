#!/usr/bin/env python3
"""WebSocket control bridge for manual teleoperation messages."""

import json
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class ControlWebSocketBridge:
    """Protocol bridge between websocket messages and the control arbiter."""

    def __init__(self, arbiter):
        self.arbiter = arbiter
        self.active_connection_id: Optional[int] = None

    def connect(self, connection_id: int) -> None:
        """Register a new active control connection, replacing any old one."""
        if self.active_connection_id is not None and self.active_connection_id != connection_id:
            self.arbiter.on_disconnect()
        self.active_connection_id = connection_id
        self.arbiter.heartbeat()

    def disconnect(self, connection_id: int) -> dict:
        """Handle control disconnect and force immediate stop for safety."""
        if self.active_connection_id != connection_id:
            return {'status': 'ignored'}
        self.active_connection_id = None
        return self.arbiter.on_disconnect()

    def handle_text(self, connection_id: int, payload: str) -> dict:
        """Process JSON control messages and route them through safety checks."""
        if self.active_connection_id != connection_id:
            return {'status': 'ignored', 'message': 'inactive_connection'}

        try:
            message = json.loads(payload)
        except json.JSONDecodeError:
            return {'status': 'error', 'message': 'invalid_json'}

        message_type = message.get('type')
        if message_type == 'heartbeat':
            self.arbiter.heartbeat()
            return {'status': 'ok', 'type': 'heartbeat'}

        if message_type == 'stop':
            return self.arbiter.stop()

        if message_type == 'drive':
            self.arbiter.heartbeat()
            try:
                linear = float(message.get('linear', 0.0))
                angular = float(message.get('angular', 0.0))
            except (TypeError, ValueError):
                return {'status': 'error', 'message': 'invalid_drive_values'}
            return self.arbiter.apply_drive(linear, angular)

        logger.warning('Unknown control websocket message type: %s', message_type)
        return {'status': 'error', 'message': 'unknown_message_type'}