from __future__ import annotations

import pytest
from conftest import (
    FailingCritiqueAgent,
    FailingEvidenceProvider,
    FailingReviseAgent,
    FailingSolveAgent,
    HighQualityEvidenceProvider,
    MalformedStructuredOutputAgent,
    ScriptedAgent,
    SelectiveFailingEvidenceProvider,
    SlowSolveAgent,
)

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


@pytest.mark.asyncio
async def test_one_solve_failure_degrades_to_remaining_agents_and_is_recorded() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        FailingSolveAgent("c", "Y"),
    ]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert set(result.proposals) == {"a", "b"}
    assert result.consensus.reached is True
    assert len(result.agent_failures) == 1
    failure = result.agent_failures[0]
    assert failure.agent_id == "c"
    assert failure.phase == "solve"
    assert failure.timed_out is False
    assert failure.error_type == "RuntimeError"
    assert failure.failure_kind == "runtime"


@pytest.mark.asyncio
async def test_structured_output_failure_is_classified_and_degraded() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        MalformedStructuredOutputAgent("c", "Y"),
    ]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert set(result.proposals) == {"a", "b"}
    assert result.consensus.reached is True
    assert len(result.agent_failures) == 1
    failure = result.agent_failures[0]
    assert failure.agent_id == "c"
    assert failure.phase == "solve"
    assert failure.error_type == "ValidationError"
    assert failure.failure_kind == "structured_output"


@pytest.mark.asyncio
async def test_one_solve_timeout_degrades_and_records_timeout() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        SlowSolveAgent("c", "Y", delay_seconds=0.05),
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(agent_timeout_seconds=0.001),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert set(result.proposals) == {"a", "b"}
    assert result.consensus.reached is True
    assert len(result.agent_failures) == 1
    failure = result.agent_failures[0]
    assert failure.agent_id == "c"
    assert failure.phase == "solve"
    assert failure.timed_out is True
    assert failure.error_type == "TimeoutError"
    assert failure.failure_kind == "timeout"


@pytest.mark.asyncio
async def test_initial_solve_requires_two_successful_agents() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        FailingSolveAgent("b", "X"),
        FailingSolveAgent("c", "Y"),
    ]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())

    with pytest.raises(RuntimeError, match="at least two agents must complete initial solve"):
        await graph.ainvoke({"question": "q"})


@pytest.mark.asyncio
async def test_critique_failure_records_failure_without_fabricating_challenge() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        FailingCritiqueAgent("c", "Y", revised_position="X"),
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(agreement_threshold=0.60, max_rounds=1),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is True
    assert result.proposals["c"].position == "X"
    assert all(challenge.challenger_agent_id != "c" for challenge in state["challenges"])
    failures = [
        failure
        for failure in result.agent_failures
        if failure.agent_id == "c" and failure.phase == "critique"
    ]
    assert len(failures) == 1
    assert failures[0].round == 1
    assert failures[0].error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_revise_failure_preserves_previous_proposal_without_revision() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        FailingReviseAgent("c", "Y"),
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(agreement_threshold=0.60, max_rounds=1),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert result.consensus.reached is True
    assert result.proposals["c"].position == "Y"
    assert all(revision.agent_id != "c" for revision in result.revisions)
    failures = [
        failure
        for failure in result.agent_failures
        if failure.agent_id == "c" and failure.phase == "revise"
    ]
    assert len(failures) == 1
    assert failures[0].round == 1
    assert failures[0].error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_partial_evidence_failure_preserves_successful_sibling_and_counts_attempts() -> None:
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
    evidence = SelectiveFailingEvidenceProvider(fail_for_challenger="a")
    graph = build_deliberation_graph(
        agents,
        evidence,
        DeliberationConfig(agreement_threshold=1.0, max_rounds=2, max_tool_calls=2),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert state["tool_calls"] == 2
    assert evidence.calls == 2
    assert len(result.evidence) == 1
    assert result.evidence[0].source == "test-source"
    assert len(result.evidence_failures) == 1
    failure = result.evidence_failures[0]
    assert failure.round == 1
    assert failure.provider == "SelectiveFailingEvidenceProvider"
    assert failure.error_type == "RuntimeError"
    failed_challenge = next(
        challenge for challenge in state["challenges"] if challenge.id == failure.challenge_id
    )
    assert failed_challenge.challenger_agent_id == "a"


@pytest.mark.asyncio
async def test_evidence_failure_at_exact_budget_stops_without_fake_evidence() -> None:
    agents = [
        ScriptedAgent(
            "a",
            "X",
            challenge_severity=Severity.CRITICAL,
            challenge_target_agent="c",
            request_evidence=True,
        ),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y", resolve_received=False),
    ]
    evidence = FailingEvidenceProvider()
    graph = build_deliberation_graph(
        agents,
        evidence,
        DeliberationConfig(agreement_threshold=1.0, max_rounds=3, max_tool_calls=1),
    )

    state = await graph.ainvoke({"question": "q"})
    result = state["final_result"]

    assert state["tool_calls"] == 1
    assert evidence.calls == 1
    assert result.evidence == []
    assert len(result.evidence_failures) == 1
    assert result.consensus.reached is False
    assert result.consensus.stop_reason == "max_tool_calls"