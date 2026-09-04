from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from .models import (
    Challenge,
    ChallengeDraft,
    Claim,
    Evidence,
    Proposal,
    RevisionAction,
    RevisionDecision,
)
from .prompts import (
    PROMPT_VERSION,
    critique_system_prompt,
    revise_system_prompt,
    solve_system_prompt,
)

StructuredT = TypeVar("StructuredT", bound=BaseModel)


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
    action: RevisionAction | None = None
    position: str
    claims: list[_ClaimDraft]
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    resolved_challenge_ids: list[str] = Field(default_factory=list)


@dataclass
class LLMDebateAgent:
    """OpenAI-compatible debate agent with versioned structured outputs."""

    agent_id: str
    model: ChatOpenAI
    objective: str
    mode: str = "ask"
    structured_output_retries: int = 1
    model_name: str | None = None
    temperature: float | None = None
    prompt_version: str = PROMPT_VERSION

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
        mode: str = "ask",
        structured_output_retries: int = 1,
    ) -> LLMDebateAgent:
        kwargs = {
            "model": model_name,
            "api_key": api_key,
            "temperature": temperature,
        }
        if base_url:
            kwargs["base_url"] = base_url
        return cls(
            agent_id=agent_id,
            model=ChatOpenAI(**kwargs),
            objective=objective,
            mode=mode,
            structured_output_retries=structured_output_retries,
            model_name=model_name,
            temperature=temperature,
        )

    async def _invoke_structured(
        self,
        schema: type[StructuredT],
        messages: list[BaseMessage],
    ) -> StructuredT:
        structured = self.model.with_structured_output(schema)
        last_error: Exception | None = None
        for attempt in range(self.structured_output_retries + 1):
            try:
                return await structured.ainvoke(messages)
            except (ValidationError, OutputParserException) as exc:
                last_error = exc
                if attempt >= self.structured_output_retries:
                    raise
        assert last_error is not None
        raise last_error

    async def solve(self, question: str) -> Proposal:
        result = await self._invoke_structured(
            _ProposalDraft,
            [
                SystemMessage(content=solve_system_prompt(self.objective, self.mode)),
                HumanMessage(content=question),
            ],
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
        payload = {
            "question": question,
            "round": round_number,
            "own_proposal": own_proposal.model_dump(mode="json"),
            "other_proposals": [p.model_dump(mode="json") for p in other_proposals],
        }
        result = await self._invoke_structured(
            _ChallengeBatch,
            [
                SystemMessage(content=critique_system_prompt(self.mode)),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ],
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
        payload = {
            "question": question,
            "round": round_number,
            "proposal": proposal.model_dump(mode="json"),
            "challenges": [c.model_dump(mode="json") for c in challenges],
            "evidence": [e.model_dump(mode="json") for e in evidence],
        }
        result = await self._invoke_structured(
            _RevisionDraft,
            [
                SystemMessage(content=revise_system_prompt(self.mode)),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ],
        )
        valid_challenges = {c.id for c in challenges}
        valid_evidence = {e.id for e in evidence}
        return RevisionDecision(
            action=result.action,
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
