"""Compatibility shim for legacy imports.

The actual BananaBrain policy/runtime implementation lives in brain.py.
"""

from __future__ import annotations

from brain import BananaBrain, StrategyChoice

__all__ = ["BananaBrain", "StrategyChoice"]