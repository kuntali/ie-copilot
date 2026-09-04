from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .models import (
    Challenge,
    ChallengeDraft,
    Claim,
    Evidence,
    Proposal,
    RevisionDecision,
)


class _ClaimDraft(BaseModel):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)


class _ProposalDraft(BaseModel):
    position: str
    claims: list[_ClaimDraft]
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)


class _ChallengeBatch(BaseModel):
    challenges: list[ChallengeDraft] = Field(default_factory=list)


class _RevisionDraft(BaseModel):
    position: str
    claims: list[_ClaimDraft]
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    resolved_challenge_ids: list[str] = Field(default_factory=list)


@dataclass
class LLMDebateAgent:
    """OpenAI-compatible debate agent with structured outputs."""

    agent_id: str
    model: ChatOpenAI
    objective: str

    @classmethod
    def from_openai_compatible(
        cls,
        *,
        agent_id: str,
        objective: str,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.1,
    ) -> "LLMDebateAgent":
        kwargs = {
            "model": model_name,
            "api_key": api_key,
            "temperature": temperature,
        }
        if base_url:
            kwargs["base_url"] = base_url
        return cls(agent_id=agent_id, model=ChatOpenAI(**kwargs), objective=objective)

    async def solve(self, question: str) -> Proposal:
        structured = self.model.with_structured_output(_ProposalDraft)
        result = await structured.ainvoke(
            [
                SystemMessage(
                    content=(
                        "You are one member of an independent deliberation panel. "
                        "Do not assume other agents' answers. Produce a concrete position, "
                        "atomic claims, assumptions, uncertainties, and calibrated confidence. "
                        f"Your epistemic objective is: {self.objective}"
                    )
                ),
                HumanMessage(content=question),
            ]
        )
        return Proposal(
            agent_id=self.agent_id,
            position=result.position,
            claims=[Claim(statement=c.statement, confidence=c.confidence) for c in result.claims],
            assumptions=result.assumptions,
            uncertainties=result.uncertainties,
            final_answer=result.final_answer,
            confidence=result.confidence,
        )

    async def critique(
        self,
        question: str,
        own_proposal: Proposal,
        other_proposals: Sequence[Proposal],
        round_number: int,
    ) -> list[ChallengeDraft]:
        structured = self.model.with_structured_output(_ChallengeBatch)
        payload = {
            "question": question,
            "round": round_number,
            "own_proposal": own_proposal.model_dump(mode="json"),
            "other_proposals": [p.model_dump(mode="json") for p in other_proposals],
        }
        result = await structured.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Identify only material disagreements or weak claims in other agents' "
                        "proposals. Target an existing claim_id exactly. Ask for external evidence "
                        "when a factual uncertainty could change the answer. Do not challenge merely "
                        "for stylistic differences."
                    )
                ),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        valid_claim_ids = {claim.id for p in other_proposals for claim in p.claims}
        return [c for c in result.challenges if c.target_claim_id in valid_claim_ids]

    async def revise(
        self,
        question: str,
        proposal: Proposal,
        challenges: Sequence[Challenge],
        evidence: Sequence[Evidence],
        round_number: int,
    ) -> RevisionDecision:
        structured = self.model.with_structured_output(_RevisionDraft)
        payload = {
            "question": question,
            "round": round_number,
            "proposal": proposal.model_dump(mode="json"),
            "challenges": [c.model_dump(mode="json") for c in challenges],
            "evidence": [e.model_dump(mode="json") for e in evidence],
        }
        result = await structured.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Re-evaluate your position using the challenges and evidence. You may keep, "
                        "weaken, revise, or abandon your position. Resolve a challenge only when the "
                        "available evidence or reasoning actually addresses it. Never defend a prior "
                        "answer merely for consistency."
                    )
                ),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        valid_challenges = {c.id for c in challenges}
        valid_evidence = {e.id for e in evidence}
        return RevisionDecision(
            position=result.position,
            claims=[Claim(statement=c.statement, confidence=c.confidence) for c in result.claims],
            final_answer=result.final_answer,
            confidence=result.confidence,
            reason=result.reason,
            evidence_refs=[ref for ref in result.evidence_refs if ref in valid_evidence],
            resolved_challenge_ids=[
                cid for cid in result.resolved_challenge_ids if cid in valid_challenges
            ],
        )
