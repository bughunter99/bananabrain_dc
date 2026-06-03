"""Unit micromanagement system.

C++ equivalent: Micro.cpp/Micro.h

Implements:
- Individual unit control
- Potential fields for unit movement
- Combat tactics (stim, focus fire, positioning)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple

# Import from Micro module (where MicroManager is the full implementation)
from cppsource.Micro import (
    MicroManager as BaseMicroManager,
    CombatState,
    CombatUnitTarget,
    SiegeTankState,
    VultureState,
    DragoonState,
    UnstickState,
    TentativeEffect,
    UnitBehavior,
    EngagementLogic,
    FormationManager,
    RetreatSystem,
    TargetPrioritization,
    MicroCoordinator,
)


class MicroManager(BaseMicroManager):
    """Wrapper for base MicroManager providing unit-level micromanagement."""
    
    def __init__(self) -> None:
        super().__init__()
    
    @classmethod
    def Instance(cls) -> 'MicroManager':
        """Get singleton instance."""
        # Use parent's singleton pattern
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ========== PHASE 7 EXTENSIONS ==========
    
    def create_unit_behavior(self, unit_id: Any) -> UnitBehavior:
        """Create behavior controller for individual unit."""
        return UnitBehavior(unit_id)
    
    def get_engagement_logic(self) -> EngagementLogic:
        """Get engagement and targeting system."""
        if not hasattr(self, '_engagement'):
            self._engagement = EngagementLogic()
        return self._engagement
    
    def get_formation_manager(self) -> FormationManager:
        """Get formation control system."""
        if not hasattr(self, '_formation'):
            self._formation = FormationManager()
        return self._formation
    
    def get_retreat_system(self) -> RetreatSystem:
        """Get retreat and regroup system."""
        if not hasattr(self, '_retreat'):
            self._retreat = RetreatSystem()
        return self._retreat
    
    def get_target_prioritization(self) -> TargetPrioritization:
        """Get target prioritization AI."""
        if not hasattr(self, '_targeting'):
            self._targeting = TargetPrioritization()
        return self._targeting
    
    def get_coordinator(self) -> MicroCoordinator:
        """Get integrated micro coordinator."""
        if not hasattr(self, '_coordinator'):
            self._coordinator = MicroCoordinator()
        return self._coordinator
    
    def execute_advanced_micro(self, own_units: list, enemy_units: list, 
                              current_frame: int) -> dict:
        """Execute advanced micro control frame."""
        coordinator = self.get_coordinator()
        return coordinator.execute_micro_frame(own_units, enemy_units, current_frame)
    
    def set_formation_type(self, formation: str) -> None:
        """Set unit formation type (loose, tight, spread, defensive)."""
        self.get_formation_manager().set_formation(formation)
    
    def set_focus_fire_target(self, enemy_unit: Any) -> None:
        """Set focus fire on specific enemy."""
        self.get_target_prioritization().add_focus_fire_target(enemy_unit)
    
    def add_retreat_unit(self, unit_id: Any) -> None:
        """Mark unit to begin retreat."""
        self.get_retreat_system().add_regrouping_unit(unit_id)
