"""Lightweight opening catalog loader for the BananaBrain Python mirror."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List

_OPENING_CATALOG: Dict[str, Any] = {
    "races": {
        "Protoss": [],
        "Terran": [],
        "Zerg": [],
    }
}

_OPENING_ROOTS = [
    Path(__file__).resolve().parent / "openings",
]


def opening_catalog() -> Dict[str, Any]:
    return _OPENING_CATALOG


def discover_opening_modules() -> List[Path]:
    modules: List[Path] = []
    for root in _OPENING_ROOTS:
        if root.exists():
            modules.extend(sorted(root.glob("**/*.py")))
    return modules


def reload_opening_modules() -> None:
    """Reload any opening modules found under the Python mirror tree."""
    for module_path in discover_opening_modules():
        spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
