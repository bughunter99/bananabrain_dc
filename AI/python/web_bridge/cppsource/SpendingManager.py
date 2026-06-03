"""Resource spending decisions.

C++ equivalent: SpendingManager.cpp/SpendingManager.h

Decides:
- Unit production
- Building construction  
- Upgrade priorities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional


@dataclass
class SpendingManager:
    """Singleton for resource spending management."""
    
    _instance: ClassVar[Optional['SpendingManager']] = None
    
    spendable_minerals_: int = 0
    spendable_gas_: int = 0
    
    @classmethod
    def Instance(cls) -> 'SpendingManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def init_spendable(self, minerals: int, gas: int) -> None:
        """Initialize available resources."""
        self.spendable_minerals_ = minerals
        self.spendable_gas_ = gas
    
    def frame(self) -> None:
        """Execute spending decisions for current frame."""
        pass
    
    def after(self) -> None:
        """Post-frame cleanup."""
        pass
    
    def draw(self) -> None:
        """Draw spending debug information."""
        pass
