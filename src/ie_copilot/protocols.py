from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import Challenge, ChallengeDraft, Evidence, Proposal, RevisionDecision


class DebateAgent(Protocol):
    agent_id: str

    async def solve(self, question: str) -> Proposal: ...

    async def critique(
        self,
        question: str,
        own_proposal: Proposal,
        other_proposals: Sequence[Proposal],
        round_number: int,
    ) -> list[ChallengeDraft]: ...

    async def revise(
        self,
        question: str,
        proposal: Proposal,
        challenges: Sequence[Challenge],
        evidence: Sequence[Evidence],
        round_number: int,
    ) -> RevisionDecision: ...


class EvidenceProvider(Protocol):
    async def gather(self, question: str, challenge: Challenge) -> Evidence: ...
