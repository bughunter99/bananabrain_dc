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
