from __future__ import annotations

import json
from typing import Any, Mapping


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def replay_signature(state: Mapping[str, Any]) -> str:
    payload = {
        "question": state.get("question"),
        "proposals": {
            agent_id: _dump(proposal)
            for agent_id, proposal in sorted(state.get("proposals", {}).items())
        },
        "claim_clusters": [_dump(item) for item in state.get("claim_clusters", [])],
        "position_clusters": [_dump(item) for item in state.get("position_clusters", [])],
        "debate_queue": [_dump(item) for item in state.get("debate_queue", [])],
        "challenges": [_dump(item) for item in state.get("challenges", [])],
        "evidence": [_dump(item) for item in state.get("evidence", [])],
        "revisions": [_dump(item) for item in state.get("revisions", [])],
        "position_snapshots": [
            _dump(item) for item in state.get("position_snapshots", [])
        ],
        "consensus": _dump(state.get("consensus")),
        "round": state.get("round", 0),
        "tool_calls": state.get("tool_calls", 0),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
