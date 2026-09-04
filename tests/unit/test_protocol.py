from __future__ import annotations

import pytest
from conftest import HighQualityEvidenceProvider, ScriptedAgent

from ie_copilot.evidence import NullEvidenceProvider
from ie_copilot.graph import DeliberationConfig, build_deliberation_graph
from ie_copilot.models import EvidenceRelation, RevisionAction, Severity
from ie_copilot.replay import replay_signature


@pytest.mark.asyncio
async def test_claim_occurrence_identity_and_cross_agent_clusters_are_separate() -> None:
    agents = [ScriptedAgent("a", "X"), ScriptedAgent("b", "X"), ScriptedAgent("c", "X")]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())
    state = await graph.ainvoke({"question": "q"})

    claim_ids = [proposal.claims[0].id for proposal in state["proposals"].values()]
    assert len(set(claim_ids)) == 3
    assert set(claim_ids) == {"clm:a:r0:0", "clm:b:r0:0", "clm:c:r0:0"}
    assert all(cluster.claim_ids for cluster in state["claim_clusters"])


@pytest.mark.asyncio
async def test_position_clusters_and_debate_queue_are_explicit_on_conflict() -> None:
    agents = [ScriptedAgent("a", " X "), ScriptedAgent("b", "x"), ScriptedAgent("c", "Y")]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())
    state = await graph.ainvoke({"question": "q"})

    assert len(state["position_clusters"]) == 2
    assert state["debate_queue"]
    assert {item.target_claim_id for item in state["debate_queue"]} <= {
        claim.id for p in state["proposals"].values() for claim in p.claims
    }


@pytest.mark.asyncio
async def test_evidence_is_bound_to_target_claim_with_relation() -> None:
    agents = [
        ScriptedAgent(
            "a",
            "X",
            challenge_severity=Severity.CRITICAL,
            challenge_target_agent="c",
            request_evidence=True,
        ),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y", revised_position="X"),
    ]
    graph = build_deliberation_graph(agents, HighQualityEvidenceProvider())
    state = await graph.ainvoke({"question": "q"})
    evidence = state["evidence"][0]
    challenge = next(c for c in state["challenges"] if c.id == evidence.challenge_id)

    assert evidence.target_claim_id == challenge.target_claim_id
    assert evidence.relation == EvidenceRelation.ATTACKS


@pytest.mark.asyncio
async def test_revision_has_explicit_action_and_causal_provenance() -> None:
    agents = [
        ScriptedAgent("a", "X"),
        ScriptedAgent("b", "X"),
        ScriptedAgent("c", "Y", revised_position="X"),
    ]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())
    state = await graph.ainvoke({"question": "q"})
    revision = next(r for r in state["revisions"] if r.agent_id == "c")

    assert revision.action == RevisionAction.REVISE
    assert revision.before_position == "Y"
    assert revision.after_position == "X"
    assert revision.trigger_challenge_ids == revision.resolved_challenge_ids
    assert revision.id == "rev:c:r1"


@pytest.mark.asyncio
async def test_round_snapshots_make_semantic_replay_deterministic() -> None:
    def agents() -> list[ScriptedAgent]:
        return [
            ScriptedAgent("a", "X"),
            ScriptedAgent("b", "X"),
            ScriptedAgent("c", "Y", revised_position="X"),
        ]

    graph1 = build_deliberation_graph(
        agents(), NullEvidenceProvider(), DeliberationConfig(max_rounds=2)
    )
    graph2 = build_deliberation_graph(
        agents(), NullEvidenceProvider(), DeliberationConfig(max_rounds=2)
    )
    state1 = await graph1.ainvoke({"question": "q"})
    state2 = await graph2.ainvoke({"question": "q"})

    assert [s.round for s in state1["position_snapshots"]] == [0, 1]
    assert replay_signature(state1) == replay_signature(state2)


@pytest.mark.asyncio
async def test_consensus_uses_structured_position_not_final_answer_wording() -> None:
    agents = [ScriptedAgent("a", "X"), ScriptedAgent("b", " X "), ScriptedAgent("c", "x")]
    graph = build_deliberation_graph(agents, NullEvidenceProvider())
    state = await graph.ainvoke({"question": "q"})

    assert state["consensus"].reached is True
    assert state["consensus"].agreement_ratio == 1.0
