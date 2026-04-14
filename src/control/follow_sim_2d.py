#!/usr/bin/env python3
"""Lightweight 2D simulation harness for follow behavior testing."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List

from control.follow_behavior import FollowBehavior, TargetObservation


@dataclass(frozen=True)
class Pose2D:
    """Robot pose in a 2D plane."""

    x_m: float
    y_m: float
    yaw_rad: float


@dataclass(frozen=True)
class SimulationStep:
    """One simulation sample including command outputs."""

    t_s: float
    pose: Pose2D
    linear_mps: float
    angular_rps: float
    observation_used: bool


@dataclass(frozen=True)
class TargetPoint:
    """Target world position at a timestamp."""

    t_s: float
    x_m: float
    y_m: float


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _target_observation_from_world(
    *,
    target_id: int,
    now_s: float,
    pose: Pose2D,
    target_x_m: float,
    target_y_m: float,
    horizontal_fov_rad: float,
    area_scale: float,
    max_range_m: float,
) -> TargetObservation | None:
    """Project a world target into normalized follow observation space."""
    dx = target_x_m - pose.x_m
    dy = target_y_m - pose.y_m

    # Transform world vector into robot frame.
    forward = math.cos(pose.yaw_rad) * dx + math.sin(pose.yaw_rad) * dy
    lateral = -math.sin(pose.yaw_rad) * dx + math.cos(pose.yaw_rad) * dy

    distance = math.hypot(forward, lateral)
    if forward <= 0.0 or distance > max_range_m:
        return None

    bearing = math.atan2(lateral, forward)
    half_fov = horizontal_fov_rad / 2.0
    if abs(bearing) > half_fov:
        return None

    # Map bearing [-half_fov, half_fov] to normalized [0, 1].
    center_x = _clamp(0.5 + (bearing / horizontal_fov_rad), 0.0, 1.0)
    area = _clamp(area_scale / max(distance * distance, 1e-6), 0.0, 1.0)

    return TargetObservation(
        target_id=target_id,
        center_x=center_x,
        area=area,
        timestamp=now_s,
    )


def run_follow_simulation_2d(
    *,
    behavior: FollowBehavior,
    target_track: Iterable[TargetPoint],
    dt_s: float = 0.1,
    initial_pose: Pose2D = Pose2D(x_m=0.0, y_m=0.0, yaw_rad=0.0),
    target_id: int = 1,
    horizontal_fov_rad: float = 1.2,
    area_scale: float = 0.14,
    max_range_m: float = 5.0,
) -> List[SimulationStep]:
    """Run follow behavior against a deterministic target trajectory."""
    if dt_s <= 0.0:
        raise ValueError('dt_s must be positive')

    points = sorted(list(target_track), key=lambda p: p.t_s)
    if not points:
        return []

    behavior.start(target_id=target_id)

    pose = initial_pose
    history: List[SimulationStep] = []

    for point in points:
        observation = _target_observation_from_world(
            target_id=target_id,
            now_s=point.t_s,
            pose=pose,
            target_x_m=point.x_m,
            target_y_m=point.y_m,
            horizontal_fov_rad=horizontal_fov_rad,
            area_scale=area_scale,
            max_range_m=max_range_m,
        )

        if observation is not None:
            behavior.update_observation(observation)

        command = behavior.next_command(now=point.t_s)
        linear_mps = command.linear_mps if command is not None else 0.0
        angular_rps = command.angular_rps if command is not None else 0.0

        yaw = pose.yaw_rad + (angular_rps * dt_s)
        x = pose.x_m + (linear_mps * math.cos(yaw) * dt_s)
        y = pose.y_m + (linear_mps * math.sin(yaw) * dt_s)
        pose = Pose2D(x_m=x, y_m=y, yaw_rad=yaw)

        history.append(
            SimulationStep(
                t_s=point.t_s,
                pose=pose,
                linear_mps=linear_mps,
                angular_rps=angular_rps,
                observation_used=observation is not None,
            )
        )

    return history
