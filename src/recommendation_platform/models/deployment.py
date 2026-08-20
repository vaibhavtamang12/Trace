from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CanaryRollout:
    """State machine for guarded rollout percentages."""

    steps: tuple[int, ...] = (10, 25, 50, 100)
    current_index: int = -1
    active_model: str = "production"

    @property
    def traffic_percent(self) -> int:
        return self.steps[self.current_index] if self.current_index >= 0 else 0

    def advance(self, healthy: bool, candidate_model: str) -> str:
        if not healthy:
            return self.rollback()
        self.current_index += 1
        self.current_index = min(self.current_index, len(self.steps) - 1)
        if self.traffic_percent == 100:
            self.active_model = candidate_model
        return self.active_model

    def rollback(self) -> str:
        self.current_index = -1
        self.active_model = "production"
        return self.active_model
