#!/usr/bin/env python3
"""
Command Intent Parser for TurboPi Voice System

Parses voice transcripts into strict command intents that route through
the safety arbiter. This parser NEVER directly controls motors.

Safety: All intents must pass through the control arbiter before execution.
"""

import re
import sys
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class CommandType(Enum):
    """Supported command types"""
    STOP = "STOP"
    FOLLOW = "FOLLOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class CommandIntent:
    """
    Parsed command intent.
    
    This represents a user's command intent that will be routed through
    the safety arbiter for validation and execution.
    """
    command: CommandType
    target: Optional[str] = None
    confidence: float = 1.0
    raw_transcript: str = ""
    
    def is_valid(self) -> bool:
        """Check if this is a valid, actionable command"""
        return self.command != CommandType.UNKNOWN
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'command': self.command.value,
            'target': self.target,
            'confidence': self.confidence,
            'raw_transcript': self.raw_transcript,
            'is_valid': self.is_valid()
        }


class CommandIntentParser:
    """
    Schema-based command intent parser.
    
    Parses voice transcripts into strict command intents using pattern matching.
    Unknown commands are rejected to prevent unintended behavior.
    
    Safety guarantees:
    - Parser NEVER directly controls motors
    - All commands routed through control arbiter
    - STOP command always recognized and valid
    - Unknown commands explicitly rejected
    """
    
    # Command patterns with capturing groups
    COMMAND_PATTERNS = {
        CommandType.STOP: [
            r'\b(stop|halt|freeze|emergency stop|e-?stop)\b',
        ],
        CommandType.FOLLOW: [
            r'\bfollow\s+(?:the\s+)?(\w+)',  # "follow the person", "follow me"
            r'\bstart\s+following\s+(?:the\s+)?(\w+)',  # "start following person"
        ],
    }
    
    def __init__(self):
        """Initialize command intent parser"""
        self._logger = logging.getLogger(__name__)
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[CommandType, list]:
        """Compile regex patterns for efficient matching"""
        compiled = {}
        for command_type, patterns in self.COMMAND_PATTERNS.items():
            compiled[command_type] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in patterns
            ]
        return compiled
    
    def parse(self, transcript: str) -> CommandIntent:
        """
        Parse a voice transcript into a command intent.
        
        Args:
            transcript: Text transcript from STT
            
        Returns:
            CommandIntent with parsed command or UNKNOWN if not recognized
        """
        if not transcript or not transcript.strip():
            self._logger.warning("Empty transcript provided")
            return CommandIntent(
                command=CommandType.UNKNOWN,
                raw_transcript=transcript,
                confidence=0.0
            )
        
        transcript = transcript.strip()
        self._logger.debug(f"Parsing transcript: {transcript}")
        
        # STOP has highest priority - check first
        stop_intent = self._check_stop_command(transcript)
        if stop_intent:
            return stop_intent
        
        # Check for FOLLOW command
        follow_intent = self._check_follow_command(transcript)
        if follow_intent:
            return follow_intent
        
        # Unknown command - reject
        self._logger.info(f"Unknown command rejected: {transcript}")
        return CommandIntent(
            command=CommandType.UNKNOWN,
            raw_transcript=transcript,
            confidence=0.0
        )
    
    def _check_stop_command(self, transcript: str) -> Optional[CommandIntent]:
        """
        Check if transcript contains STOP command.
        
        STOP is always valid and has highest priority.
        """
        patterns = self._compiled_patterns.get(CommandType.STOP, [])
        
        for pattern in patterns:
            match = pattern.search(transcript)
            if match:
                self._logger.info(f"STOP command detected: {transcript}")
                return CommandIntent(
                    command=CommandType.STOP,
                    target=None,
                    confidence=1.0,
                    raw_transcript=transcript
                )
        
        return None
    
    def _check_follow_command(self, transcript: str) -> Optional[CommandIntent]:
        """Check if transcript contains FOLLOW command"""
        patterns = self._compiled_patterns.get(CommandType.FOLLOW, [])
        
        for pattern in patterns:
            match = pattern.search(transcript)
            if match:
                # Extract target from capturing group
                target = match.group(1) if match.lastindex else None
                
                # Normalize target
                if target:
                    target = target.lower().strip()
                    # Map common variations
                    if target in ['me', 'myself']:
                        target = 'person'
                
                confidence = 0.9  # High confidence for pattern match
                
                self._logger.info(
                    f"FOLLOW command detected: target={target}, transcript={transcript}"
                )
                
                return CommandIntent(
                    command=CommandType.FOLLOW,
                    target=target,
                    confidence=confidence,
                    raw_transcript=transcript
                )
        
        return None
    
    def get_supported_commands(self) -> list:
        """Get list of supported command types"""
        return [cmd for cmd in CommandType if cmd != CommandType.UNKNOWN]


def main():
    """Main entry point for standalone testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    parser = CommandIntentParser()
    logger = logging.getLogger(__name__)
    
    logger.info("Command Intent Parser Test")
    logger.info(f"Supported commands: {[c.value for c in parser.get_supported_commands()]}")
    logger.info("")
    
    # Test cases
    test_transcripts = [
        "stop now",
        "emergency stop",
        "halt",
        "follow the person",
        "follow me",
        "start following the dog",
        "turn on the lights",  # Unknown command
        "go forward",  # Unknown command
        "",  # Empty
        "Please stop right now",  # Stop in context
    ]
    
    for transcript in test_transcripts:
        intent = parser.parse(transcript)
        logger.info(f"Input: '{transcript}'")
        logger.info(f"  Command: {intent.command.value}")
        logger.info(f"  Target: {intent.target}")
        logger.info(f"  Valid: {intent.is_valid()}")
        logger.info(f"  Confidence: {intent.confidence}")
        logger.info("")


if __name__ == '__main__':
    main()
