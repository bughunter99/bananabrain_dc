"""Unit training management.

C++ equivalent: TrainingManager.cpp/TrainingManager.h

Manages:
- Unit production queue
- Production facility selection
- Worker training
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional


@dataclass
class TrainingManager:
    """Singleton for unit training coordination."""
    
    _instance: ClassVar[Optional['TrainingManager']] = None
    
    training_queue_: List[Dict] = field(default_factory=list, init=False)
    
    @classmethod
    def Instance(cls) -> 'TrainingManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init(self) -> None:
        """Initialize training manager."""
        self.training_queue_ = []
    
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
