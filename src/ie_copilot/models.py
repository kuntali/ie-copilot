from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: new_id("clm"))
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


class Proposal(BaseModel):
    agent_id: str
    position: str
    claims: list[Claim]
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)


class ChallengeDraft(BaseModel):
    target_claim_id: str
    reason: str
    evidence_request: str | None = None
    severity: Severity = Severity.MEDIUM


class Challenge(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chl"))
    challenger_agent_id: str
    target_agent_id: str
    round: int = Field(ge=1)
    target_claim_id: str
    reason: str
    evidence_request: str | None = None
    severity: Severity = Severity.MEDIUM


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ev"))
    challenge_id: str
    source: str
    content: str
    quality: float = Field(ge=0.0, le=1.0)
    supports_target_claim: bool | None = None


class EvidenceFailure(BaseModel):
    challenge_id: str
    round: int = Field(ge=1)
    provider: str
    error_type: str
    message: str


class RevisionDecision(BaseModel):
    position: str
    claims: list[Claim]
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    resolved_challenge_ids: list[str] = Field(default_factory=list)


class Revision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rev"))
    agent_id: str
    round: int
    previous_position: str
    new_position: str
    previous_confidence: float
    new_confidence: float
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    resolved_challenge_ids: list[str] = Field(default_factory=list)


class AgentFailure(BaseModel):
    agent_id: str
    phase: Literal["solve", "critique", "revise"]
    round: int = Field(ge=0)
    error_type: str
    message: str
    timed_out: bool = False
    failure_kind: Literal["runtime", "timeout", "structured_output"] = "runtime"


class ConsensusResult(BaseModel):
    reached: bool
    dominant_position: str | None
    agreement_ratio: float = Field(ge=0.0, le=1.0)
    position_entropy: float = Field(ge=0.0)
    evidence_sufficiency: float = Field(ge=0.0, le=1.0)
    unresolved_critical_objections: int = Field(ge=0)
    reason: str
    stop_reason: Literal[
        "consensus",
        "unanimous",
        "max_rounds",
        "max_tool_calls",
        "continue",
    ]


class FinalResult(BaseModel):
    answer: str
    consensus: ConsensusResult
    proposals: dict[str, Proposal]
    rounds: int
    evidence: list[Evidence]
    revisions: list[Revision]
    agent_failures: list[AgentFailure] = Field(default_factory=list)
    evidence_failures: list[EvidenceFailure] = Field(default_factory=list)
