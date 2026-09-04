from __future__ import annotations

import pytest
from pydantic import ValidationError

from ie_copilot.models import Claim, Proposal, RevisionDecision


def test_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Claim(statement="bad", confidence=1.2)


def test_proposal_has_runtime_claim_ids() -> None:
    proposal = Proposal(
        agent_id="a",
        position="X",
        claims=[Claim(statement="c", confidence=0.5)],
        final_answer="x",
        confidence=0.5,
    )
    assert proposal.claims[0].id.startswith("clm_")


def test_claim_statement_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        Claim(statement="", confidence=0.5)


def test_claim_statement_must_not_be_whitespace_only() -> None:
    with pytest.raises(ValidationError):
        Claim(statement="   ", confidence=0.5)


def test_proposal_requires_at_least_one_claim() -> None:
    with pytest.raises(ValidationError):
        Proposal(
            agent_id="a",
            position="X",
            claims=[],
            final_answer="x",
            confidence=0.5,
        )


def test_proposal_rejects_canonical_duplicate_claims() -> None:
    with pytest.raises(ValidationError):
        Proposal(
            agent_id="a",
            position="X",
            claims=[
                Claim(statement="Same claim", confidence=0.5),
                Claim(statement=" same   CLAIM ", confidence=0.6),
            ],
            final_answer="x",
            confidence=0.5,
        )


def test_revision_decision_requires_at_least_one_claim() -> None:
    with pytest.raises(ValidationError):
        RevisionDecision(
            position="X",
            claims=[],
            final_answer="x",
            confidence=0.5,
            reason="test",
        )


def test_revision_decision_rejects_canonical_duplicate_claims() -> None:
    with pytest.raises(ValidationError):
        RevisionDecision(
            position="X",
            claims=[
                Claim(statement="Same claim", confidence=0.5),
                Claim(statement=" same   CLAIM ", confidence=0.6),
            ],
            final_answer="x",
            confidence=0.5,
            reason="test",
        )
