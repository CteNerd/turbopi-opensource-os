#!/usr/bin/env python3
"""
Unit tests for Command Intent Parser

Tests validate strict schema-based parsing, STOP command priority,
and rejection of unknown commands.
"""

import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from command_intent import CommandIntentParser, CommandIntent, CommandType


class TestCommandType(unittest.TestCase):
    """Tests for CommandType enum"""
    
    def test_command_types_defined(self):
        """Test that required command types are defined"""
        self.assertEqual(CommandType.STOP.value, "STOP")
        self.assertEqual(CommandType.FOLLOW.value, "FOLLOW")
        self.assertEqual(CommandType.UNKNOWN.value, "UNKNOWN")


class TestCommandIntent(unittest.TestCase):
    """Tests for CommandIntent dataclass"""
    
    def test_valid_stop_intent(self):
        """Test STOP intent is valid"""
        intent = CommandIntent(
            command=CommandType.STOP,
            confidence=1.0,
            raw_transcript="stop"
        )
        self.assertTrue(intent.is_valid())
        self.assertEqual(intent.command, CommandType.STOP)
        self.assertIsNone(intent.target)
    
    def test_valid_follow_intent(self):
        """Test FOLLOW intent is valid"""
        intent = CommandIntent(
            command=CommandType.FOLLOW,
            target="person",
            confidence=0.9,
            raw_transcript="follow the person"
        )
        self.assertTrue(intent.is_valid())
        self.assertEqual(intent.command, CommandType.FOLLOW)
        self.assertEqual(intent.target, "person")
    
    def test_unknown_intent_invalid(self):
        """Test UNKNOWN intent is not valid"""
        intent = CommandIntent(
            command=CommandType.UNKNOWN,
            confidence=0.0,
            raw_transcript="turn on lights"
        )
        self.assertFalse(intent.is_valid())
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        intent = CommandIntent(
            command=CommandType.FOLLOW,
            target="person",
            confidence=0.92,
            raw_transcript="follow me"
        )
        d = intent.to_dict()
        
        self.assertEqual(d['command'], "FOLLOW")
        self.assertEqual(d['target'], "person")
        self.assertEqual(d['confidence'], 0.92)
        self.assertEqual(d['raw_transcript'], "follow me")
        self.assertTrue(d['is_valid'])


class TestCommandIntentParser(unittest.TestCase):
    """Tests for CommandIntentParser"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_parser_initialization(self):
        """Test parser initializes correctly"""
        self.assertIsNotNone(self.parser)
        supported = self.parser.get_supported_commands()
        self.assertIn(CommandType.STOP, supported)
        self.assertIn(CommandType.FOLLOW, supported)
        self.assertNotIn(CommandType.UNKNOWN, supported)


class TestStopCommand(unittest.TestCase):
    """Tests for STOP command parsing"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_stop_simple(self):
        """Test simple 'stop' command"""
        intent = self.parser.parse("stop")
        self.assertEqual(intent.command, CommandType.STOP)
        self.assertTrue(intent.is_valid())
        self.assertEqual(intent.confidence, 1.0)
    
    def test_stop_variations(self):
        """Test various STOP command variations"""
        variations = [
            "stop",
            "STOP",
            "halt",
            "freeze",
            "emergency stop",
            "e-stop",
            "estop",
        ]
        
        for variation in variations:
            with self.subTest(variation=variation):
                intent = self.parser.parse(variation)
                self.assertEqual(intent.command, CommandType.STOP)
                self.assertTrue(intent.is_valid())
    
    def test_stop_in_context(self):
        """Test STOP command within longer phrases"""
        phrases = [
            "please stop now",
            "can you stop",
            "stop right there",
            "I need you to halt",
            "emergency stop immediately",
        ]
        
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                intent = self.parser.parse(phrase)
                self.assertEqual(intent.command, CommandType.STOP)
                self.assertTrue(intent.is_valid())
    
    def test_stop_case_insensitive(self):
        """Test STOP command is case-insensitive"""
        cases = ["stop", "STOP", "Stop", "sToP"]
        
        for case in cases:
            with self.subTest(case=case):
                intent = self.parser.parse(case)
                self.assertEqual(intent.command, CommandType.STOP)
    
    def test_stop_always_valid(self):
        """Test STOP command is always recognized as valid"""
        intent = self.parser.parse("stop")
        self.assertTrue(intent.is_valid())
        self.assertEqual(intent.confidence, 1.0)


class TestFollowCommand(unittest.TestCase):
    """Tests for FOLLOW command parsing"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_follow_person(self):
        """Test 'follow the person' command"""
        intent = self.parser.parse("follow the person")
        self.assertEqual(intent.command, CommandType.FOLLOW)
        self.assertEqual(intent.target, "person")
        self.assertTrue(intent.is_valid())
        self.assertGreater(intent.confidence, 0.0)
    
    def test_follow_me(self):
        """Test 'follow me' normalizes to 'person'"""
        intent = self.parser.parse("follow me")
        self.assertEqual(intent.command, CommandType.FOLLOW)
        self.assertEqual(intent.target, "person")
        self.assertTrue(intent.is_valid())
    
    def test_follow_variations(self):
        """Test various FOLLOW command variations"""
        test_cases = [
            ("follow the person", "person"),
            ("follow me", "person"),
            ("follow the dog", "dog"),
            ("start following the cat", "cat"),
            ("start following me", "person"),
        ]
        
        for transcript, expected_target in test_cases:
            with self.subTest(transcript=transcript):
                intent = self.parser.parse(transcript)
                self.assertEqual(intent.command, CommandType.FOLLOW)
                self.assertEqual(intent.target, expected_target)
                self.assertTrue(intent.is_valid())
    
    def test_follow_case_insensitive(self):
        """Test FOLLOW command is case-insensitive"""
        cases = [
            "follow the person",
            "FOLLOW THE PERSON",
            "Follow The Person",
        ]
        
        for case in cases:
            with self.subTest(case=case):
                intent = self.parser.parse(case)
                self.assertEqual(intent.command, CommandType.FOLLOW)
                self.assertTrue(intent.is_valid())
    
    def test_follow_without_target(self):
        """Test 'follow' without target may still parse"""
        # This tests the robustness of the parser
        # The exact behavior depends on pattern matching
        intent = self.parser.parse("follow")
        # Should either be UNKNOWN or FOLLOW with None target
        # Either is acceptable for this edge case
        self.assertIn(intent.command, [CommandType.UNKNOWN, CommandType.FOLLOW])


class TestUnknownCommands(unittest.TestCase):
    """Tests for unknown command rejection"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_unknown_command_rejected(self):
        """Test unknown commands are rejected"""
        unknown_commands = [
            "turn on the lights",
            "go forward",
            "move backward",
            "rotate left",
            "dance",
            "play music",
            "hello there",
        ]
        
        for command in unknown_commands:
            with self.subTest(command=command):
                intent = self.parser.parse(command)
                self.assertEqual(intent.command, CommandType.UNKNOWN)
                self.assertFalse(intent.is_valid())
                self.assertEqual(intent.confidence, 0.0)
    
    def test_empty_transcript(self):
        """Test empty transcript is rejected"""
        intent = self.parser.parse("")
        self.assertEqual(intent.command, CommandType.UNKNOWN)
        self.assertFalse(intent.is_valid())
    
    def test_whitespace_only(self):
        """Test whitespace-only transcript is rejected"""
        intent = self.parser.parse("   \n\t  ")
        self.assertEqual(intent.command, CommandType.UNKNOWN)
        self.assertFalse(intent.is_valid())
    
    def test_gibberish(self):
        """Test gibberish is rejected"""
        gibberish = [
            "asdf qwer zxcv",
            "123 456 789",
            "!@#$%^&*()",
        ]
        
        for text in gibberish:
            with self.subTest(text=text):
                intent = self.parser.parse(text)
                self.assertEqual(intent.command, CommandType.UNKNOWN)
                self.assertFalse(intent.is_valid())


class TestCommandPriority(unittest.TestCase):
    """Tests for command priority"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_stop_has_priority(self):
        """Test STOP command has highest priority"""
        # Even if other commands are present, STOP should be detected
        transcripts = [
            "stop following",
            "follow then stop",
            "please stop and then follow me",
        ]
        
        for transcript in transcripts:
            with self.subTest(transcript=transcript):
                intent = self.parser.parse(transcript)
                self.assertEqual(intent.command, CommandType.STOP)


class TestSafety(unittest.TestCase):
    """Safety tests - ensure parser never triggers motion"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_no_motor_control_interface(self):
        """Test that parser has no motor control methods"""
        parser = CommandIntentParser()
        
        # List of forbidden method names related to motion
        forbidden_methods = [
            'arm_motors', 'disarm_motors', 'move', 'rotate',
            'forward', 'backward', 'turn', 'stop_motors',
            'set_speed', 'set_velocity', 'execute', 'run'
        ]
        
        method_names = [m for m in dir(parser) if not m.startswith('_')]
        
        for forbidden in forbidden_methods:
            self.assertNotIn(forbidden, method_names,
                           f"Parser should not have {forbidden} method")
    
    def test_parse_only_returns_intent(self):
        """Test that parse only returns intent, doesn't execute"""
        intent = self.parser.parse("follow me")
        
        # Should return CommandIntent, not execute anything
        self.assertIsInstance(intent, CommandIntent)
        self.assertEqual(intent.command, CommandType.FOLLOW)
        
        # Verify parser state hasn't changed
        intent2 = self.parser.parse("stop")
        self.assertIsInstance(intent2, CommandIntent)
        self.assertEqual(intent2.command, CommandType.STOP)
    
    def test_raw_transcript_preserved(self):
        """Test raw transcript is preserved for audit trail"""
        transcript = "follow the person please"
        intent = self.parser.parse(transcript)
        
        self.assertEqual(intent.raw_transcript, transcript)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and robustness"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_very_long_transcript(self):
        """Test parser handles very long transcripts"""
        long_transcript = "please " * 100 + "stop"
        intent = self.parser.parse(long_transcript)
        self.assertEqual(intent.command, CommandType.STOP)
    
    def test_special_characters(self):
        """Test parser handles special characters"""
        transcripts = [
            "stop!",
            "stop.",
            "stop?",
            "stop!!!",
            "follow-me",
        ]
        
        for transcript in transcripts:
            # Should not crash
            intent = self.parser.parse(transcript)
            self.assertIsInstance(intent, CommandIntent)
    
    def test_unicode_characters(self):
        """Test parser handles unicode gracefully"""
        transcripts = [
            "stop 停止",
            "follow 跟随",
            "stop café",
        ]
        
        for transcript in transcripts:
            # Should not crash
            intent = self.parser.parse(transcript)
            self.assertIsInstance(intent, CommandIntent)
    
    def test_multiple_commands(self):
        """Test behavior with multiple commands in one transcript"""
        # STOP should have priority
        intent = self.parser.parse("follow me then stop")
        self.assertEqual(intent.command, CommandType.STOP)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def setUp(self):
        """Set up test parser"""
        self.parser = CommandIntentParser()
    
    def test_end_to_end_valid_commands(self):
        """Test end-to-end flow with valid commands"""
        test_cases = [
            ("stop", CommandType.STOP, None),
            ("follow the person", CommandType.FOLLOW, "person"),
            ("emergency stop", CommandType.STOP, None),
            ("start following me", CommandType.FOLLOW, "person"),
        ]
        
        for transcript, expected_cmd, expected_target in test_cases:
            with self.subTest(transcript=transcript):
                intent = self.parser.parse(transcript)
                
                # Check intent is valid
                self.assertTrue(intent.is_valid())
                
                # Check command type
                self.assertEqual(intent.command, expected_cmd)
                
                # Check target if applicable
                if expected_target:
                    self.assertEqual(intent.target, expected_target)
                
                # Check confidence
                self.assertGreater(intent.confidence, 0.0)
                self.assertLessEqual(intent.confidence, 1.0)
                
                # Check raw transcript preserved
                self.assertEqual(intent.raw_transcript, transcript)
    
    def test_end_to_end_invalid_commands(self):
        """Test end-to-end flow with invalid commands"""
        invalid_commands = [
            "turn on lights",
            "go forward",
            "",
            "hello",
        ]
        
        for transcript in invalid_commands:
            with self.subTest(transcript=transcript):
                intent = self.parser.parse(transcript)
                
                # Check intent is invalid
                self.assertFalse(intent.is_valid())
                
                # Check command is UNKNOWN
                self.assertEqual(intent.command, CommandType.UNKNOWN)
                
                # Check confidence is 0
                self.assertEqual(intent.confidence, 0.0)


if __name__ == '__main__':
    unittest.main()
