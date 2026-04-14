#!/usr/bin/env python3
"""Unit tests for follow behavior control logic."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from control.follow_behavior import FollowBehavior, TargetObservation


class TestFollowBehavior(unittest.TestCase):
    def test_no_command_when_disabled(self):
        behavior = FollowBehavior()
        self.assertIsNone(behavior.next_command(now=10.0))

    def test_start_and_stop(self):
        behavior = FollowBehavior()
        self.assertEqual(behavior.start(target_id=3)['status'], 'started')
        self.assertTrue(behavior.state()['enabled'])
        self.assertEqual(behavior.stop()['status'], 'stopped')
        self.assertFalse(behavior.state()['enabled'])

    def test_generates_forward_and_turn_command(self):
        behavior = FollowBehavior(smooth_alpha=1.0)
        behavior.start(target_id=7)
        accepted = behavior.update_observation(
            TargetObservation(target_id=7, center_x=0.75, area=0.08, timestamp=20.0)
        )
        self.assertTrue(accepted)
        cmd = behavior.next_command(now=20.1)
        self.assertIsNotNone(cmd)
        self.assertGreater(cmd.linear_mps, 0.0)
        self.assertGreater(cmd.angular_rps, 0.0)

    def test_target_mismatch_is_ignored(self):
        behavior = FollowBehavior(smooth_alpha=1.0)
        behavior.start(target_id=2)
        accepted = behavior.update_observation(
            TargetObservation(target_id=9, center_x=0.5, area=0.15, timestamp=1.0)
        )
        self.assertFalse(accepted)
        cmd = behavior.next_command(now=2.0)
        self.assertEqual(cmd.linear_mps, 0.0)
        self.assertEqual(cmd.angular_rps, 0.0)

    def test_lost_target_decays_to_stop(self):
        behavior = FollowBehavior(smooth_alpha=0.5, target_timeout_s=0.5)
        behavior.start(target_id=1)
        behavior.update_observation(
            TargetObservation(target_id=1, center_x=0.9, area=0.05, timestamp=5.0)
        )
        cmd1 = behavior.next_command(now=5.1)
        self.assertGreater(abs(cmd1.linear_mps) + abs(cmd1.angular_rps), 0.0)

        cmd2 = behavior.next_command(now=6.0)
        self.assertLess(abs(cmd2.linear_mps), abs(cmd1.linear_mps))
        self.assertLess(abs(cmd2.angular_rps), abs(cmd1.angular_rps))
        self.assertTrue(behavior.state()['lost_target'])

    def test_smoothing_reduces_jump(self):
        behavior = FollowBehavior(smooth_alpha=0.2)
        behavior.start(target_id=1)
        behavior.update_observation(
            TargetObservation(target_id=1, center_x=1.0, area=0.01, timestamp=1.0)
        )
        cmd = behavior.next_command(now=1.01)
        # With smoothing alpha=0.2, command should not jump to max instantly.
        self.assertLess(abs(cmd.angular_rps), 1.0)
        self.assertLess(abs(cmd.linear_mps), 0.30)


if __name__ == '__main__':
    unittest.main()
