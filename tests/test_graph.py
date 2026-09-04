from __future__ import annotations

import pytest
from conftest import HighQualityEvidenceProvider, ScriptedAgent

from ie_copilot.evidence import NullEvidenceProvider
from ie_copilot.graph import DeliberationConfig, build_deliberation_graph
from ie_copilot.models import Severity


@pytest.mark.asyncio
async def test_unanimous_initial_answers_finish_without_debate() -> None:
    agents = [ScriptedAgent(f"a{i}", "X") for i in range(3)]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is True
    assert result.consensus.stop_reason == "unanimous"
    assert result.rounds == 0
    assert all(agent.critique_calls == 0 for agent in agents)


@pytest.mark.asyncio
async def test_initial_majority_still_gets_one_debate_round_when_positions_conflict() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y", revised_position="X"),
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(agreement_threshold=0.60, max_rounds=2),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.rounds == 1
    assert result.consensus.reached is True
    assert result.consensus.agreement_ratio == 1.0
    assert all(agent.critique_calls == 1 for agent in agents)


@pytest.mark.asyncio
async def test_evidence_driven_revision_reaches_consensus() -> None:
    agents = [
        ScriptedAgent(
            "a",
            "X",
            challenge_severity=Severity.CRITICAL,
            challenge_target_agent="c",
            request_evidence=True,
        ),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y", revised_position="X", resolve_received=True),
    ]
    evidence = HighQualityEvidenceProvider()
    graph = build_deliberation_graph(agents, evidence)

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is True
    assert result.consensus.unresolved_critical_objections == 0
    assert result.consensus.agreement_ratio == 1.0
    assert evidence.calls == 1
    assert len(result.evidence) == 1
    assert any(rev.agent_id == "c" and rev.new_position == "X" for rev in result.revisions)


@pytest.mark.asyncio
async def test_unresolved_critical_objection_blocks_majority_consensus() -> None:
    agents = [
        ScriptedAgent(
            "a",
            "X",
            challenge_severity=Severity.CRITICAL,
            challenge_target_agent="c",
        ),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y", resolve_received=False),
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(agreement_threshold=0.60, max_rounds=1),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is False
    assert result.consensus.stop_reason == "max_rounds"
    assert result.consensus.agreement_ratio >= 0.60
    assert result.consensus.unresolved_critical_objections >= 1
    assert result.answer.startswith("[UNRESOLVED CONSENSUS]")


@pytest.mark.asyncio
async def test_max_rounds_stops_persistent_disagreement_at_exact_budget() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y"),
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(agreement_threshold=1.0, max_rounds=2),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is False
    assert result.consensus.stop_reason == "max_rounds"
    assert result.rounds == 2
    assert all(agent.critique_calls == 2 for agent in agents)
    assert all(agent.revise_calls == 2 for agent in agents)


@pytest.mark.asyncio
async def test_max_tool_calls_caps_same_round_evidence_requests() -> None:
    agents = [
        ScriptedAgent(
            "a",
            "X",
            challenge_severity=Severity.CRITICAL,
            challenge_target_agent="c",
            request_evidence=True,
        ),
        ScriptedAgent(
            "b",
            "X",
            challenge_severity=Severity.CRITICAL,
            challenge_target_agent="c",
            request_evidence=True,
        ),
        ScriptedAgent("c", "Y", resolve_received=False),
    ]
    evidence = HighQualityEvidenceProvider()
    graph = build_deliberation_graph(
        agents,
        evidence,
        DeliberationConfig(
            agreement_threshold=1.0,
            max_rounds=3,
            max_tool_calls=1,
        ),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is False
    assert result.consensus.stop_reason == "max_tool_calls"
    assert result.rounds == 1
    assert evidence.calls == 1
    assert len(result.evidence) == 1
