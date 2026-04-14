#!/usr/bin/env python3
"""Unit tests for the 2D follow behavior simulation harness."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from control.follow_behavior import FollowBehavior
from control.follow_sim_2d import Pose2D, TargetPoint, run_follow_simulation_2d


class TestFollowSimulation2D(unittest.TestCase):
    def test_robot_closes_distance_to_stationary_target(self):
        behavior = FollowBehavior(smooth_alpha=0.8)
        track = [TargetPoint(t_s=i * 0.1, x_m=2.0, y_m=0.4) for i in range(30)]

        history = run_follow_simulation_2d(
            behavior=behavior,
            target_track=track,
            dt_s=0.1,
            initial_pose=Pose2D(x_m=0.0, y_m=0.0, yaw_rad=0.0),
        )

        self.assertGreater(len(history), 5)
        self.assertTrue(any(step.observation_used for step in history))
        self.assertGreater(history[-1].pose.x_m, history[0].pose.x_m)

    def test_lost_target_yields_stop_command(self):
        behavior = FollowBehavior(smooth_alpha=1.0, target_timeout_s=0.15)
        track = [
            TargetPoint(t_s=0.0, x_m=1.5, y_m=0.0),
            TargetPoint(t_s=0.1, x_m=1.5, y_m=0.0),
            # Target leaves FOV after this point.
            TargetPoint(t_s=0.3, x_m=-1.5, y_m=0.0),
            TargetPoint(t_s=0.5, x_m=-1.5, y_m=0.0),
        ]

        history = run_follow_simulation_2d(
            behavior=behavior,
            target_track=track,
            dt_s=0.1,
            initial_pose=Pose2D(x_m=0.0, y_m=0.0, yaw_rad=0.0),
        )

        self.assertGreater(history[1].linear_mps, 0.0)
        self.assertEqual(history[-1].linear_mps, 0.0)
        self.assertEqual(history[-1].angular_rps, 0.0)


if __name__ == '__main__':
    unittest.main()
