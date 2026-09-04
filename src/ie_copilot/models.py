from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _canonical_claim_statement(statement: str) -> str:
    return " ".join(statement.lower().split())


def _validate_unique_claims(claims: list[Claim]) -> list[Claim]:
    seen: set[str] = set()
    for claim in claims:
        key = _canonical_claim_statement(claim.statement)
        if key in seen:
            raise ValueError("claims must not contain canonical duplicates")
        seen.add(key)
    return claims


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    ATTACKS = "attacks"
    NEUTRAL = "neutral"


class RevisionAction(str, Enum):
    MAINTAIN = "maintain"
    WEAKEN = "weaken"
    REVISE = "revise"
    ABANDON = "abandon"


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: new_id("clm"))
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("statement")
    @classmethod
    def statement_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("claim statement must not be blank")
        return value


class ClaimCluster(BaseModel):
    id: str
    canonical_statement: str
    claim_ids: list[str] = Field(min_length=1)
    agent_ids: list[str] = Field(min_length=1)


class PositionCluster(BaseModel):
    id: str
    canonical_position: str
    representative_position: str
    agent_ids: list[str] = Field(min_length=1)


class DebateItem(BaseModel):
    id: str
    round: int = Field(ge=0)
    target_claim_id: str
    target_agent_id: str
    target_position_cluster_id: str
    opposing_position_cluster_ids: list[str] = Field(min_length=1)
    priority: float = Field(default=1.0, ge=0.0, le=1.0)


class Proposal(BaseModel):
    agent_id: str
    position: str
    claims: list[Claim] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("claims")
    @classmethod
    def claims_must_be_unique(cls, value: list[Claim]) -> list[Claim]:
        return _validate_unique_claims(value)


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
    target_claim_id: str | None = None
    relation: EvidenceRelation | None = None
    source: str
    content: str
    quality: float = Field(ge=0.0, le=1.0)
    supports_target_claim: bool | None = None

    @model_validator(mode="after")
    def derive_relation_from_legacy_flag(self) -> Evidence:
        if self.relation is not None:
            return self
        if self.supports_target_claim is True:
            self.relation = EvidenceRelation.SUPPORTS
        elif self.supports_target_claim is False:
            self.relation = EvidenceRelation.ATTACKS
        else:
            self.relation = EvidenceRelation.NEUTRAL
        return self


class EvidenceFailure(BaseModel):
    challenge_id: str
    round: int = Field(ge=1)
    provider: str
    error_type: str
    message: str


class RevisionDecision(BaseModel):
    action: RevisionAction | None = None
    position: str
    claims: list[Claim] = Field(min_length=1)
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    resolved_challenge_ids: list[str] = Field(default_factory=list)

    @field_validator("claims")
    @classmethod
    def claims_must_be_unique(cls, value: list[Claim]) -> list[Claim]:
        return _validate_unique_claims(value)


class Revision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rev"))
    agent_id: str
    round: int = Field(ge=1)
    action: RevisionAction = RevisionAction.MAINTAIN
    previous_position: str
    new_position: str
    previous_confidence: float
    new_confidence: float
    before_position: str
    after_position: str
    before_claim_ids: list[str] = Field(default_factory=list)
    after_claim_ids: list[str] = Field(default_factory=list)
    trigger_challenge_ids: list[str] = Field(default_factory=list)
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    resolved_challenge_ids: list[str] = Field(default_factory=list)


class PositionSnapshot(BaseModel):
    round: int = Field(ge=0)
    positions: dict[str, str]
    confidences: dict[str, float]
    claim_ids_by_agent: dict[str, list[str]]


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
    claim_clusters: list[ClaimCluster] = Field(default_factory=list)
    position_clusters: list[PositionCluster] = Field(default_factory=list)
    debate_queue: list[DebateItem] = Field(default_factory=list)
    position_snapshots: list[PositionSnapshot] = Field(default_factory=list)
    agent_failures: list[AgentFailure] = Field(default_factory=list)
    evidence_failures: list[EvidenceFailure] = Field(default_factory=list)
