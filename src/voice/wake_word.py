#!/usr/bin/env python3
"""
Wake Word Detection Engine for TurboPi

Simple, low-CPU wake word detection using pattern matching.
This module provides always-on wake word detection that arms
voice capture without triggering motor control.

Safety: Wake word detection NEVER triggers motion commands.
"""

import os
import sys
import time
import logging
import threading
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection"""
    wake_word: str = "Jarvis"
    enabled: bool = True
    case_sensitive: bool = False
    timeout_seconds: int = 5  # Timeout after wake word if no speech follows


class WakeWordEngine:
    """
    Simple wake word detection engine.
    
    This is a minimal implementation using pattern matching for low CPU usage.
    For production, this could be replaced with a more sophisticated solution
    like Porcupine or Snowboy.
    
    Safety guarantees:
    - Wake word detection never triggers motor commands
    - Only arms voice capture for STT processing
    """
    
    def __init__(self, config: Optional[WakeWordConfig] = None):
        """
        Initialize wake word engine.
        
        Args:
            config: Wake word configuration, defaults to environment-based config
        """
        self.config = config or self._load_config_from_env()
        self._armed = False
        self._armed_timestamp: Optional[float] = None
        self._callback: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        
    def _load_config_from_env(self) -> WakeWordConfig:
        """Load configuration from environment variables"""
        wake_word = os.environ.get('WAKE_WORD', 'Jarvis')
        enabled = os.environ.get('WAKE_WORD_ENABLED', 'true').lower() == 'true'
        
        # Parse timeout with error handling
        default_timeout = 5
        timeout_str = os.environ.get('WAKE_WORD_TIMEOUT', str(default_timeout))
        try:
            timeout = int(timeout_str)
        except ValueError:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Invalid WAKE_WORD_TIMEOUT value '%s'; falling back to default %d seconds",
                timeout_str,
                default_timeout,
            )
            timeout = default_timeout
        
        return WakeWordConfig(
            wake_word=wake_word,
            enabled=enabled,
            case_sensitive=False,
            timeout_seconds=timeout
        )
    
    def update_config(self, wake_word: Optional[str] = None, 
                     enabled: Optional[bool] = None) -> None:
        """
        Update wake word configuration.
        
        Args:
            wake_word: New wake word to detect (ASCII only)
            enabled: Enable/disable wake word detection
        """
        with self._lock:
            if wake_word is not None:
                # Validate ASCII-only
                if not wake_word.isascii():
                    raise ValueError("Wake word must contain ASCII characters only")
                if not wake_word.strip():
                    raise ValueError("Wake word cannot be empty")
                self.config.wake_word = wake_word.strip()
                self._logger.info(f"Wake word updated to: {self.config.wake_word}")
            
            if enabled is not None:
                self.config.enabled = enabled
                self._logger.info(f"Wake word detection {'enabled' if enabled else 'disabled'}")
    
    def get_config(self) -> WakeWordConfig:
        """Get current configuration (thread-safe copy)"""
        with self._lock:
            return WakeWordConfig(
                wake_word=self.config.wake_word,
                enabled=self.config.enabled,
                case_sensitive=self.config.case_sensitive,
                timeout_seconds=self.config.timeout_seconds
            )
    
    def process_text(self, text: str) -> bool:
        """
        Process text to detect wake word.
        
        This is a simple pattern matching implementation for low CPU usage.
        In production, this would be replaced with audio-based detection.
        
        Args:
            text: Input text to check for wake word
            
        Returns:
            True if wake word detected, False otherwise
        """
        with self._lock:
            if not self.config.enabled:
                return False
            # Normalize text for comparison
            search_text = text if self.config.case_sensitive else text.lower()
            target_word = self.config.wake_word if self.config.case_sensitive else self.config.wake_word.lower()
            
            # Check if wake word is present
            if target_word in search_text:
                self._armed = True
                self._armed_timestamp = time.time()
                self._logger.info(f"Wake word '{self.config.wake_word}' detected - voice capture armed")
                
                # Trigger callback if registered
                if self._callback:
                    try:
                        self._callback()
                    except Exception as e:
                        self._logger.error(f"Error in wake word callback: {e}")
                
                return True
            
            return False
    
    def is_armed(self) -> bool:
        """
        Check if voice capture is armed (wake word was recently detected).
        
        Returns:
            True if armed and within timeout window, False otherwise
        """
        with self._lock:
            if not self._armed:
                return False
            
            # Check timeout
            if self._armed_timestamp is not None:
                elapsed = time.time() - self._armed_timestamp
                if elapsed > self.config.timeout_seconds:
                    self._armed = False
                    self._armed_timestamp = None
                    self._logger.info("Wake word timeout - voice capture disarmed")
                    return False
            
            return True
    
    def disarm(self) -> None:
        """Disarm voice capture (called after successful STT capture)"""
        with self._lock:
            self._armed = False
            self._armed_timestamp = None
            self._logger.debug("Voice capture disarmed")
    
    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when wake word is detected.
        
        Args:
            callback: Function to call when wake word is detected
        """
        with self._lock:
            self._callback = callback
    
    def get_status(self) -> dict:
        """
        Get current status of wake word engine.
        
        Returns:
            Dictionary with status information
        """
        with self._lock:
            # Check timeout and clear armed state if expired (consistent with is_armed)
            if self._armed and self._armed_timestamp is not None:
                elapsed = time.time() - self._armed_timestamp
                if elapsed > self.config.timeout_seconds:
                    self._armed = False
                    self._armed_timestamp = None
                    self._logger.info("Wake word timeout - voice capture disarmed")
            
            time_remaining = None
            if self._armed and self._armed_timestamp:
                elapsed = time.time() - self._armed_timestamp
                time_remaining = max(0, self.config.timeout_seconds - elapsed)
            
            return {
                'enabled': self.config.enabled,
                'wake_word': self.config.wake_word,
                'armed': self._armed,
                'timeout_seconds': self.config.timeout_seconds,
                'time_remaining': time_remaining
            }


def main():
    """Main entry point for standalone testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    engine = WakeWordEngine()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Wake word engine started with wake word: {engine.config.wake_word}")
    logger.info("Testing wake word detection...")
    
    # Test cases
    test_inputs = [
        "Hello there",
        "Hey Jarvis, what's the time?",
        "jarvis turn on the lights",
        "JARVIS please help",
        "Just a random sentence"
    ]
    
    for test_input in test_inputs:
        detected = engine.process_text(test_input)
        logger.info(f"Input: '{test_input}' -> Detected: {detected}")
        
        if detected:
            status = engine.get_status()
            logger.info(f"Status: {status}")
            engine.disarm()


if __name__ == '__main__':
    main()
