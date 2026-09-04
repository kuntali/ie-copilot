from __future__ import annotations

import pytest
from conftest import DelayedSolveAgent, ScriptedAgent, SpoofingSolveAgent

from ie_copilot.evidence import NullEvidenceProvider
from ie_copilot.graph import build_deliberation_graph


@pytest.mark.asyncio
async def test_out_of_order_solve_completion_preserves_agent_result_mapping() -> None:
    completion_log: list[str] = []
    agents = [
        DelayedSolveAgent(
            "a",
            "X",
            delay_seconds=0.03,
            completion_log=completion_log,
        ),
        DelayedSolveAgent(
            "b",
            "X",
            delay_seconds=0.0,
            completion_log=completion_log,
        ),
        DelayedSolveAgent(
            "c",
            "X",
            delay_seconds=0.015,
            completion_log=completion_log,
        ),
    ]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert completion_log == ["b", "c", "a"]
    assert set(result.proposals) == {"a", "b", "c"}
    for agent_id, proposal in result.proposals.items():
        assert proposal.agent_id == agent_id
        assert proposal.claims[0].statement == f"{agent_id} supports X"
        assert proposal.final_answer == "answer:X"


@pytest.mark.asyncio
async def test_spoofed_proposal_identity_is_rejected_without_overwriting_sibling() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        SpoofingSolveAgent("c", "X", spoofed_agent_id="a"),
    ]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert set(result.proposals) == {"a", "b"}
    assert result.proposals["a"].claims[0].statement == "a supports X"
    failures = [failure for failure in result.agent_failures if failure.agent_id == "c"]
    assert len(failures) == 1
    assert failures[0].phase == "solve"
    assert failures[0].error_type == "RuntimeError"
    assert failures[0].failure_kind == "runtime"
