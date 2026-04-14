#!/usr/bin/env python3
"""Replay tests for voice command parsing sequences."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from command_intent import CommandIntentParser, CommandType


class TestVoiceReplayCommandIntent(unittest.TestCase):
    def test_replay_sequence_parses_follow_and_stop(self):
        parser = CommandIntentParser()
        replay_transcripts = [
            'follow me',
            'keep following the person',
            'uh maybe lights blue',
            'emergency stop now',
        ]

        commands = [parser.parse(text).command for text in replay_transcripts]
        self.assertEqual(commands[0], CommandType.FOLLOW)
        self.assertEqual(commands[1], CommandType.FOLLOW)
        self.assertEqual(commands[2], CommandType.UNKNOWN)
        self.assertEqual(commands[3], CommandType.STOP)

    def test_stop_priority_during_replay(self):
        parser = CommandIntentParser()
        intent = parser.parse('follow the person but stop immediately')
        self.assertEqual(intent.command, CommandType.STOP)


if __name__ == '__main__':
    unittest.main()
