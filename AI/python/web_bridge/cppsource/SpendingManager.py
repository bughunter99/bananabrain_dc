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
    
    def spend_minerals(self, amount: int) -> bool:
        """Spend minerals, return True if successful."""
        if self.spendable_minerals_ >= amount:
            self.spendable_minerals_ -= amount
            return True
        return False
    
    def spend_gas(self, amount: int) -> bool:
        """Spend gas, return True if successful."""
        if self.spendable_gas_ >= amount:
            self.spendable_gas_ -= amount
            return True
        return False
    
    def can_spend(self, minerals: int, gas: int) -> bool:
        """Check if can spend both resources."""
        return self.spendable_minerals_ >= minerals and self.spendable_gas_ >= gas
    
    def minerals(self) -> int:
        """Get spendable minerals."""
        return self.spendable_minerals_
    
    def gas(self) -> int:
        """Get spendable gas."""
        return self.spendable_gas_
    
    def frame(self) -> None:
        """Execute spending decisions for current frame."""
        # Evaluate spending opportunities
        pass
    
    def after(self) -> None:
        """Post-frame cleanup."""
        pass
    
    def draw(self) -> None:
        """Draw spending debug information."""
        pass
