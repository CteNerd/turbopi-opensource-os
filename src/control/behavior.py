#!/usr/bin/env python3
"""Behavior interface and command envelope for autonomous control sources."""

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class BehaviorCommand:
    """A normalized autonomy command emitted by behavior modules."""

    behavior: str
    linear_mps: float
    angular_rps: float


class BehaviorProvider(Protocol):
    """Contract for autonomous behaviors that can propose motion commands."""

    def name(self) -> str:
        """Return stable behavior identifier used for observability/UI."""

    def next_command(self) -> Optional[BehaviorCommand]:
        """Return the next command, or None when no motion should be requested."""
