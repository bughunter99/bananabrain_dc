from __future__ import annotations

from typing import Any, Dict

OPENING_NAME = "ZvZ_12pool"

PROFILE: Dict[str, Any] = {
    "mode": "",
    "placement": {},
    "build_requests": [],
}


def get_profile(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    # Edit this opening profile to customize behavior for this specific opening.
    return dict(PROFILE)
