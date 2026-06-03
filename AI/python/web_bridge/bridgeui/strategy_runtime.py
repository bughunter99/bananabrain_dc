from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RuntimeState:
    enabled: bool = False
    strategy: str = "balanced"


class StrategyRuntime:
    def __init__(self) -> None:
        self.state = RuntimeState()

    def start(self, strategy: str = "balanced") -> RuntimeState:
        self.state.enabled = True
        self.state.strategy = strategy or "balanced"
        return self.state

    def stop(self) -> RuntimeState:
        self.state.enabled = False
        return self.state

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.state.enabled,
            "strategy": self.state.strategy,
        }

    def decide(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.state.enabled:
            return []

        event_name = str(event.get("event", ""))
        payload = event.get("payload") or {}

        if event_name == "onStart":
            return [{"type": "send_text", "text": "Python strategy runtime started."}]

        if event_name == "onFrame":
            try:
                minerals = int(payload.get("minerals", 0))
            except (TypeError, ValueError):
                minerals = 0
            try:
                supply_used = int(payload.get("supply_used", 0))
                supply_total = int(payload.get("supply_total", 0))
            except (TypeError, ValueError):
                supply_used = 0
                supply_total = 0

            if self.state.strategy == "econ" and minerals >= 300:
                return [{"type": "send_text", "text": "[econ] minerals high, continue macro."}]

            if self.state.strategy == "aggressive" and supply_total > 0 and supply_used * 100 >= supply_total * 90:
                return [{"type": "send_text", "text": "[aggressive] near max supply, push now."}]

        if event_name == "onNukeDetect":
            return [{"type": "send_text", "text": "Nuke detected. Spread units."}]

        return []


strategy_runtime = StrategyRuntime()
