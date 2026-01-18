#!/usr/bin/env python3
"""
Unit tests for Wake Word Detection Engine
"""

import os
import sys
import time
import unittest
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from wake_word import WakeWordEngine, WakeWordConfig


class TestWakeWordConfig(unittest.TestCase):
    """Tests for WakeWordConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = WakeWordConfig()
        self.assertEqual(config.wake_word, "Jarvis")
        self.assertTrue(config.enabled)
        self.assertFalse(config.case_sensitive)
        self.assertEqual(config.timeout_seconds, 5)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = WakeWordConfig(
            wake_word="Computer",
            enabled=False,
            case_sensitive=True,
            timeout_seconds=10
        )
        self.assertEqual(config.wake_word, "Computer")
        self.assertFalse(config.enabled)
        self.assertTrue(config.case_sensitive)
        self.assertEqual(config.timeout_seconds, 10)


class TestWakeWordEngine(unittest.TestCase):
    """Tests for WakeWordEngine"""
    
    def test_default_initialization(self):
        """Test engine initialization with default config"""
        with patch.dict(os.environ, {}, clear=True):
            engine = WakeWordEngine()
            config = engine.get_config()
            self.assertEqual(config.wake_word, "Jarvis")
            self.assertTrue(config.enabled)
    
    def test_initialization_from_env(self):
        """Test engine initialization from environment variables"""
        with patch.dict(os.environ, {
            'WAKE_WORD': 'Computer',
            'WAKE_WORD_ENABLED': 'false',
            'WAKE_WORD_TIMEOUT': '10'
        }):
            engine = WakeWordEngine()
            config = engine.get_config()
            self.assertEqual(config.wake_word, "Computer")
            self.assertFalse(config.enabled)
            self.assertEqual(config.timeout_seconds, 10)
    
    def test_custom_config_initialization(self):
        """Test engine initialization with custom config"""
        custom_config = WakeWordConfig(wake_word="Custom", enabled=False)
        engine = WakeWordEngine(config=custom_config)
        config = engine.get_config()
        self.assertEqual(config.wake_word, "Custom")
        self.assertFalse(config.enabled)
    
    def test_process_text_case_insensitive(self):
        """Test wake word detection is case-insensitive by default"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Test various cases
        self.assertTrue(engine.process_text("Hey Jarvis, hello"))
        engine.disarm()
        
        self.assertTrue(engine.process_text("jarvis"))
        engine.disarm()
        
        self.assertTrue(engine.process_text("JARVIS"))
        engine.disarm()
        
        self.assertTrue(engine.process_text("JaRvIs"))
        engine.disarm()
    
    def test_process_text_no_match(self):
        """Test wake word detection returns false when no match"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        self.assertFalse(engine.process_text("Hello there"))
        self.assertFalse(engine.process_text("Computer, turn on lights"))
        self.assertFalse(engine.process_text("Just a random sentence"))
    
    def test_process_text_disabled(self):
        """Test wake word detection disabled when config.enabled is False"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis", enabled=False))
        
        # Even with correct wake word, should return false when disabled
        self.assertFalse(engine.process_text("Hey Jarvis"))
        self.assertFalse(engine.is_armed())
    
    def test_arming_on_detection(self):
        """Test that voice capture is armed when wake word is detected"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Initially not armed
        self.assertFalse(engine.is_armed())
        
        # Detect wake word
        engine.process_text("Hey Jarvis")
        
        # Now should be armed
        self.assertTrue(engine.is_armed())
    
    def test_disarm(self):
        """Test manual disarming of voice capture"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Arm by detecting wake word
        engine.process_text("Jarvis")
        self.assertTrue(engine.is_armed())
        
        # Disarm manually
        engine.disarm()
        self.assertFalse(engine.is_armed())
    
    def test_timeout(self):
        """Test that armed state times out after configured duration"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis", timeout_seconds=1))
        
        # Detect wake word
        engine.process_text("Jarvis")
        self.assertTrue(engine.is_armed())
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Should no longer be armed
        self.assertFalse(engine.is_armed())
    
    def test_update_config_wake_word(self):
        """Test updating wake word configuration"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Update wake word
        engine.update_config(wake_word="Computer")
        
        # Old wake word should not work
        self.assertFalse(engine.process_text("Jarvis"))
        
        # New wake word should work
        self.assertTrue(engine.process_text("Computer"))
    
    def test_update_config_enabled(self):
        """Test enabling/disabling wake word detection"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis", enabled=True))
        
        # Initially enabled, should detect
        self.assertTrue(engine.process_text("Jarvis"))
        engine.disarm()
        
        # Disable detection
        engine.update_config(enabled=False)
        
        # Should not detect when disabled
        self.assertFalse(engine.process_text("Jarvis"))
    
    def test_update_config_validation_ascii(self):
        """Test wake word validation - ASCII only"""
        engine = WakeWordEngine()
        
        # Non-ASCII characters should raise ValueError
        with self.assertRaises(ValueError) as context:
            engine.update_config(wake_word="こんにちは")
        
        self.assertIn("ASCII", str(context.exception))
    
    def test_update_config_validation_empty(self):
        """Test wake word validation - not empty"""
        engine = WakeWordEngine()
        
        # Empty string should raise ValueError
        with self.assertRaises(ValueError) as context:
            engine.update_config(wake_word="   ")
        
        self.assertIn("empty", str(context.exception))
    
    def test_callback_registration(self):
        """Test callback is called when wake word is detected"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Register callback
        callback_called = []
        def callback():
            callback_called.append(True)
        
        engine.register_callback(callback)
        
        # Detect wake word
        engine.process_text("Jarvis")
        
        # Callback should have been called
        self.assertEqual(len(callback_called), 1)
    
    def test_callback_error_handling(self):
        """Test that callback errors are handled gracefully"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Register callback that raises exception
        def bad_callback():
            raise RuntimeError("Callback error")
        
        engine.register_callback(bad_callback)
        
        # Should not raise exception, but still detect wake word
        self.assertTrue(engine.process_text("Jarvis"))
    
    def test_get_status(self):
        """Test getting engine status"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis", enabled=True, timeout_seconds=5))
        
        # Initial status
        status = engine.get_status()
        self.assertTrue(status['enabled'])
        self.assertEqual(status['wake_word'], "Jarvis")
        self.assertFalse(status['armed'])
        self.assertEqual(status['timeout_seconds'], 5)
        self.assertIsNone(status['time_remaining'])
        
        # After detection
        engine.process_text("Jarvis")
        status = engine.get_status()
        self.assertTrue(status['armed'])
        self.assertIsNotNone(status['time_remaining'])
        self.assertGreater(status['time_remaining'], 0)
        self.assertLessEqual(status['time_remaining'], 5)
    
    def test_thread_safety(self):
        """Test that engine operations are thread-safe"""
        import threading
        
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        results = []
        
        def worker():
            for _ in range(10):
                detected = engine.process_text("Jarvis")
                if detected:
                    results.append(True)
                engine.disarm()
        
        # Run multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have detected wake word multiple times without errors
        self.assertGreater(len(results), 0)


class TestWakeWordSafety(unittest.TestCase):
    """Safety tests - ensure wake word never triggers motion"""
    
    def test_no_motor_control_interface(self):
        """Test that WakeWordEngine has no motor control methods"""
        engine = WakeWordEngine()
        
        # Should not have any methods related to motor control
        method_names = [m for m in dir(engine) if not m.startswith('_')]
        
        # List of forbidden method names related to motion
        forbidden_methods = ['arm_motors', 'disarm_motors', 'move', 'rotate', 
                            'forward', 'backward', 'turn', 'stop_motors',
                            'set_speed', 'set_velocity']
        
        for forbidden in forbidden_methods:
            self.assertNotIn(forbidden, method_names,
                           f"Wake word engine should not have {forbidden} method")
    
    def test_only_arms_voice_capture(self):
        """Test that wake word only arms voice capture, not motors"""
        engine = WakeWordEngine(WakeWordConfig(wake_word="Jarvis"))
        
        # Detect wake word
        engine.process_text("Jarvis")
        
        # Check status - should only show armed for voice capture
        status = engine.get_status()
        self.assertTrue(status['armed'])
        
        # Status should not contain any motor-related fields
        self.assertNotIn('motors_armed', status)
        self.assertNotIn('motion_enabled', status)
        self.assertNotIn('speed', status)


if __name__ == '__main__':
    unittest.main()
