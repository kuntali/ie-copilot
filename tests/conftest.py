from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

from ie_copilot.models import (
    Challenge,
    ChallengeDraft,
    Claim,
    Evidence,
    Proposal,
    RevisionDecision,
    Severity,
)


@dataclass
class ScriptedAgent:
    agent_id: str
    initial_position: str
    revised_position: str | None = None
    challenge_severity: Severity | None = None
    challenge_target_agent: str | None = None
    request_evidence: bool = False
    resolve_received: bool = True
    critique_calls: int = 0
    revise_calls: int = 0
    _seen_proposals: dict[str, Proposal] = field(default_factory=dict)

    async def solve(self, question: str) -> Proposal:
        proposal = Proposal(
            agent_id=self.agent_id,
            position=self.initial_position,
            claims=[
                Claim(
                    statement=f"{self.agent_id} supports {self.initial_position}",
                    confidence=0.8,
                )
            ],
            final_answer=f"answer:{self.initial_position}",
            confidence=0.8,
        )
        self._seen_proposals[self.agent_id] = proposal
        return proposal

    async def critique(
        self,
        question: str,
        own_proposal: Proposal,
        other_proposals: Sequence[Proposal],
        round_number: int,
    ) -> list[ChallengeDraft]:
        self.critique_calls += 1
        if self.challenge_severity is None:
            return []
        targets = [
            p for p in other_proposals if p.agent_id == self.challenge_target_agent
        ] or list(other_proposals)
        if not targets:
            return []
        target = targets[0]
        return [
            ChallengeDraft(
                target_claim_id=target.claims[0].id,
                reason=f"challenge from {self.agent_id}",
                evidence_request="verify externally" if self.request_evidence else None,
                severity=self.challenge_severity,
            )
        ]

    async def revise(
        self,
        question: str,
        proposal: Proposal,
        challenges: Sequence[Challenge],
        evidence: Sequence[Evidence],
        round_number: int,
    ) -> RevisionDecision:
        self.revise_calls += 1
        new_position = self.revised_position or proposal.position
        resolved = [c.id for c in challenges] if self.resolve_received else []
        evidence_refs = [e.id for e in evidence]
        return RevisionDecision(
            position=new_position,
            claims=[Claim(statement=f"{self.agent_id} supports {new_position}", confidence=0.85)],
            final_answer=f"answer:{new_position}",
            confidence=0.85,
            reason="scripted revision",
            evidence_refs=evidence_refs,
            resolved_challenge_ids=resolved,
        )


@dataclass
class FailingSolveAgent(ScriptedAgent):
    async def solve(self, question: str) -> Proposal:
        raise RuntimeError(f"solve failed for {self.agent_id}")


@dataclass
class SlowSolveAgent(ScriptedAgent):
    delay_seconds: float = 0.1

    async def solve(self, question: str) -> Proposal:
        await asyncio.sleep(self.delay_seconds)
        return await super().solve(question)


@dataclass
class FailingCritiqueAgent(ScriptedAgent):
    async def critique(
        self,
        question: str,
        own_proposal: Proposal,
        other_proposals: Sequence[Proposal],
        round_number: int,
    ) -> list[ChallengeDraft]:
        raise RuntimeError(f"critique failed for {self.agent_id}")


@dataclass
class FailingReviseAgent(ScriptedAgent):
    async def revise(
        self,
        question: str,
        proposal: Proposal,
        challenges: Sequence[Challenge],
        evidence: Sequence[Evidence],
        round_number: int,
    ) -> RevisionDecision:
        raise RuntimeError(f"revise failed for {self.agent_id}")


class HighQualityEvidenceProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def gather(self, question: str, challenge: Challenge) -> Evidence:
        self.calls += 1
        return Evidence(
            challenge_id=challenge.id,
            source="test-source",
            content="verified fact",
            quality=0.95,
            supports_target_claim=False,
        )


class SelectiveFailingEvidenceProvider:
    def __init__(self, fail_for_challenger: str) -> None:
        self.fail_for_challenger = fail_for_challenger
        self.calls = 0

    async def gather(self, question: str, challenge: Challenge) -> Evidence:
        self.calls += 1
        if challenge.challenger_agent_id == self.fail_for_challenger:
            raise RuntimeError(f"evidence failed for {challenge.id}")
        return Evidence(
            challenge_id=challenge.id,
            source="test-source",
            content="verified sibling evidence",
            quality=0.95,
            supports_target_claim=False,
        )


class FailingEvidenceProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def gather(self, question: str, challenge: Challenge) -> Evidence:
        self.calls += 1
        raise RuntimeError(f"evidence failed for {challenge.id}")
