from __future__ import annotations

import pytest
from pydantic import ValidationError

from ie_copilot.models import Claim, Proposal


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
