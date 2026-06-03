"""Python counterpart of C++ Dll.cpp."""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional


class DllBridge:
    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}
        self._incoming: Deque[Dict[str, Any]] = deque()
        self._outgoing: Deque[Dict[str, Any]] = deque()

    def set_state(self, state: Dict[str, Any]) -> None:
        self._state = dict(state or {})

    def state(self) -> Dict[str, Any]:
        return dict(self._state)

    def push_incoming(self, message: Dict[str, Any]) -> None:
        self._incoming.append(dict(message or {}))

    def push_outgoing(self, message: Dict[str, Any]) -> None:
        self._outgoing.append(dict(message or {}))

    def drain_incoming(self) -> List[Dict[str, Any]]:
        messages = list(self._incoming)
        self._incoming.clear()
        return messages

    def drain_outgoing(self) -> List[Dict[str, Any]]:
        messages = list(self._outgoing)
        self._outgoing.clear()
        return messages

    def has_pending_messages(self) -> bool:
        return bool(self._incoming or self._outgoing)
