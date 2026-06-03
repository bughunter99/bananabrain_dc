"""Unit training management.

C++ equivalent: TrainingManager.cpp/TrainingManager.h

Manages:
- Unit production queue
- Production facility selection
- Worker training
- Larva distribution for Zerg
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional


@dataclass
class TrainDistribution:
    """Distribution of larva across unit types."""
    
    distribution_: Dict[str, float] = field(default_factory=dict, init=False)
    
    def set(self, unit_type: str, ratio: float) -> None:
        """Set training ratio for unit type."""
        self.distribution_[unit_type] = ratio
    
    def get(self, unit_type: str) -> float:
        """Get training ratio for unit type."""
        return self.distribution_.get(unit_type, 0.0)
    
    def clear(self) -> None:
        """Clear all distributions."""
        self.distribution_.clear()
    
    def is_empty(self) -> bool:
        """Check if no distributions set."""
        return len(self.distribution_) == 0


@dataclass
class TrainingManager:
    """Singleton for unit training coordination."""
    
    _instance: ClassVar[Optional['TrainingManager']] = None
    
    training_queue_: List[Dict] = field(default_factory=list, init=False)
    unit_counts_: Dict[str, int] = field(default_factory=dict, init=False)
    larva_distribution_: TrainDistribution = field(default_factory=TrainDistribution, init=False)
    
    @classmethod
    def Instance(cls) -> 'TrainingManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self) -> None:
        """Initialize training manager."""
        self.training_queue_ = []
        self.unit_counts_ = {}
        self.larva_distribution_ = TrainDistribution()
    
    def train_unit(self, unit_type: str) -> None:
        """Queue unit for training."""
        self.training_queue_.append({
            "unit_type": unit_type,
            "queued_frame": 0,
            "started_frame": -1,
        })
    
    def clear_queue(self) -> None:
        """Clear training queue."""
        self.training_queue_ = []
    
    def queue_size(self) -> int:
        """Get number of units in training queue."""
        return len(self.training_queue_)
    
    def queue(self) -> List[Dict]:
        """Get current training queue."""
        return list(self.training_queue_)
    
    def unit_count(self, unit_type: str) -> int:
        """Get count of units of specified type."""
        return self.unit_counts_.get(unit_type, 0)
    
    def set_unit_count(self, unit_type: str, count: int) -> None:
        """Set count of units of specified type."""
        self.unit_counts_[unit_type] = count
    
    def larva_train_distribution(self) -> TrainDistribution:
        """Get larva training distribution."""
        return self.larva_distribution_
    
    def frame(self) -> None:
        """Execute training decisions for current frame."""
        if self.training_queue_:
            # Process first item in queue
            current = self.training_queue_[0]
            if current.get("started_frame") == -1:
                current["started_frame"] = 0  # Would be current frame in real implementation
    
    def draw(self) -> None:
        """Draw training debug information."""
        pass
