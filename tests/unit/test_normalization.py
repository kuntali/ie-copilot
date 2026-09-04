from __future__ import annotations

from ie_copilot.models import Claim, Proposal, RevisionAction
from ie_copilot.normalization import build_claim_clusters


def test_equivalent_claims_cluster_without_sharing_occurrence_identity() -> None:
    proposals = {
        "a": Proposal(
            agent_id="a",
            position="X",
            claims=[Claim(id="a-c1", statement="Postgres uses MVCC", confidence=0.8)],
            final_answer="x",
            confidence=0.8,
        ),
        "b": Proposal(
            agent_id="b",
            position="X",
            claims=[Claim(id="b-c1", statement=" postgres   USES mvcc ", confidence=0.7)],
            final_answer="x",
            confidence=0.7,
        ),
    }

    clusters = build_claim_clusters(proposals)

    assert len(clusters) == 1
    assert set(clusters[0].claim_ids) == {"a-c1", "b-c1"}
    assert clusters[0].agent_ids == ["a", "b"]


def test_revision_action_contract_has_four_explicit_outcomes() -> None:
    assert {action.value for action in RevisionAction} == {
        "maintain",
        "weaken",
        "revise",
        "abandon",
    }
