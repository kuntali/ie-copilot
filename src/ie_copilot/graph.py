from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Literal, TypedDict, TypeVar

from langchain_core.exceptions import OutputParserException
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from .models import (
    AgentFailure,
    Challenge,
    ConsensusResult,
    Evidence,
    EvidenceFailure,
    FinalResult,
    Proposal,
    Revision,
)
from .observability import debate_span
from .protocols import DebateAgent, EvidenceProvider

T = TypeVar("T")


class DeliberationState(TypedDict, total=False):
    question: str
    proposals: dict[str, Proposal]
    challenges: list[Challenge]
    evidence: list[Evidence]
    evidence_failures: list[EvidenceFailure]
    revisions: list[Revision]
    agent_failures: list[AgentFailure]
    round: int
    tool_calls: int
    consensus: ConsensusResult
    final_result: FinalResult


@dataclass(frozen=True)
class DeliberationConfig:
    agreement_threshold: float = 0.67
    evidence_quality_threshold: float = 0.70
    evidence_sufficiency_threshold: float = 0.75
    max_rounds: int = 3
    max_tool_calls: int = 24
    agent_timeout_seconds: float | None = 60.0


def _canonical_position(position: str) -> str:
    return " ".join(position.lower().split())


def _position_stats(proposals: dict[str, Proposal]) -> tuple[str | None, float, float]:
    if not proposals:
        return None, 0.0, 0.0
    buckets: dict[str, int] = {}
    representative: dict[str, str] = {}
    for proposal in proposals.values():
        key = _canonical_position(proposal.position)
        buckets[key] = buckets.get(key, 0) + 1
        representative.setdefault(key, proposal.position)
    dominant_key, dominant_count = max(buckets.items(), key=lambda item: item[1])
    total = len(proposals)
    ratio = dominant_count / total
    entropy = -sum((count / total) * math.log(count / total) for count in buckets.values())
    return representative[dominant_key], ratio, entropy


def _unresolved_critical(
    challenges: list[Challenge], revisions: list[Revision]
) -> int:
    resolved = {cid for revision in revisions for cid in revision.resolved_challenge_ids}
    return sum(
        1
        for challenge in challenges
        if challenge.severity.value == "critical" and challenge.id not in resolved
    )


def _evidence_sufficiency(
    challenges: list[Challenge],
    evidence: list[Evidence],
    revisions: list[Revision],
    threshold: float,
) -> float:
    resolved = {cid for revision in revisions for cid in revision.resolved_challenge_ids}
    requested = [
        challenge
        for challenge in challenges
        if challenge.evidence_request and challenge.id not in resolved
    ]
    if not requested:
        return 1.0
    good_by_challenge = {
        item.challenge_id for item in evidence if item.quality >= threshold
    }
    return sum(1 for challenge in requested if challenge.id in good_by_challenge) / len(requested)


class _Runtime:
    def __init__(
        self,
        agents: list[DebateAgent],
        evidence_provider: EvidenceProvider,
        config: DeliberationConfig,
    ) -> None:
        if len(agents) < 2:
            raise ValueError("At least two agents are required")
        agent_ids = [agent.agent_id for agent in agents]
        if len(set(agent_ids)) != len(agent_ids):
            raise ValueError("agent_id values must be unique")
        if config.agent_timeout_seconds is not None and config.agent_timeout_seconds <= 0:
            raise ValueError("agent_timeout_seconds must be positive or None")
        self.agents = agents
        self.agents_by_id = {agent.agent_id: agent for agent in agents}
        self.evidence_provider = evidence_provider
        self.config = config

    async def _await_agent(self, awaitable: Awaitable[T]) -> T:
        timeout = self.config.agent_timeout_seconds
        if timeout is None:
            return await awaitable
        return await asyncio.wait_for(awaitable, timeout=timeout)

    @staticmethod
    def _failure_kind(
        exc: Exception,
    ) -> Literal["runtime", "timeout", "structured_output"]:
        chain: list[BaseException] = []
        current: BaseException | None = exc
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            chain.append(current)
            current = current.__cause__ or current.__context__

        if any(isinstance(item, asyncio.TimeoutError) for item in chain):
            return "timeout"
        if any(
            isinstance(item, (ValidationError, OutputParserException)) for item in chain
        ):
            return "structured_output"
        return "runtime"

    def _agent_failure(
        self,
        *,
        agent_id: str,
        phase: Literal["solve", "critique", "revise"],
        round_number: int,
        exc: Exception,
    ) -> AgentFailure:
        failure_kind = self._failure_kind(exc)
        timed_out = failure_kind == "timeout"
        message = str(exc)
        if timed_out and not message:
            message = f"{phase} timed out after {self.config.agent_timeout_seconds} seconds"
        return AgentFailure(
            agent_id=agent_id,
            phase=phase,
            round=round_number,
            error_type=type(exc).__name__,
            message=message,
            timed_out=timed_out,
            failure_kind=failure_kind,
        )

    async def solve(self, state: DeliberationState) -> dict:
        async def run(agent: DebateAgent) -> tuple[Proposal | None, AgentFailure | None]:
            try:
                with debate_span(
                    "debate.agent.solve",
                    **{"debate.agent.id": agent.agent_id, "debate.round": 0},
                ):
                    proposal = await self._await_agent(agent.solve(state["question"]))
                return proposal, None
            except Exception as exc:
                return None, self._agent_failure(
                    agent_id=agent.agent_id,
                    phase="solve",
                    round_number=0,
                    exc=exc,
                )

        results = await asyncio.gather(*(run(agent) for agent in self.agents))
        proposals = {
            proposal.agent_id: proposal
            for proposal, _ in results
            if proposal is not None
        }
        failures = [failure for _, failure in results if failure is not None]
        if len(proposals) < 2:
            raise RuntimeError(
                "at least two agents must complete initial solve; "
                f"completed={len(proposals)}, required=2"
            )
        return {
            "proposals": proposals,
            "challenges": [],
            "evidence": [],
            "evidence_failures": [],
            "revisions": [],
            "agent_failures": failures,
            "round": 0,
            "tool_calls": 0,
        }

    async def critique(self, state: DeliberationState) -> dict:
        round_number = state["round"]
        proposals = state["proposals"]
        active_agents = [
            self.agents_by_id[agent_id]
            for agent_id in proposals
            if agent_id in self.agents_by_id
        ]

        async def run(agent: DebateAgent) -> tuple[list[Challenge], AgentFailure | None]:
            own = proposals[agent.agent_id]
            others = [p for aid, p in proposals.items() if aid != agent.agent_id]
            try:
                with debate_span(
                    "debate.agent.critique",
                    **{"debate.agent.id": agent.agent_id, "debate.round": round_number},
                ):
                    drafts = await self._await_agent(
                        agent.critique(state["question"], own, others, round_number)
                    )
            except Exception as exc:
                return [], self._agent_failure(
                    agent_id=agent.agent_id,
                    phase="critique",
                    round_number=round_number,
                    exc=exc,
                )
            claim_owner = {
                claim.id: proposal.agent_id
                for proposal in others
                for claim in proposal.claims
            }
            challenges = [
                Challenge(
                    challenger_agent_id=agent.agent_id,
                    target_agent_id=claim_owner[draft.target_claim_id],
                    round=round_number,
                    target_claim_id=draft.target_claim_id,
                    reason=draft.reason,
                    evidence_request=draft.evidence_request,
                    severity=draft.severity,
                )
                for draft in drafts
                if draft.target_claim_id in claim_owner
            ]
            return challenges, None

        groups = await asyncio.gather(*(run(agent) for agent in active_agents))
        current = [challenge for group, _ in groups for challenge in group]
        failures = [failure for _, failure in groups if failure is not None]
        return {
            "challenges": state.get("challenges", []) + current,
            "agent_failures": state.get("agent_failures", []) + failures,
        }

    async def gather_evidence(self, state: DeliberationState) -> dict:
        round_number = state["round"]
        current = [
            challenge
            for challenge in state.get("challenges", [])
            if challenge.round == round_number and challenge.evidence_request
        ]
        remaining = max(0, self.config.max_tool_calls - state.get("tool_calls", 0))
        current = current[:remaining]

        async def run(
            challenge: Challenge,
        ) -> tuple[Evidence | None, EvidenceFailure | None]:
            try:
                with debate_span(
                    "debate.evidence.retrieve",
                    **{
                        "debate.round": round_number,
                        "debate.challenge.id": challenge.id,
                        "debate.challenge.target": challenge.target_claim_id,
                    },
                ):
                    evidence = await self.evidence_provider.gather(
                        state["question"], challenge
                    )
                return evidence, None
            except Exception as exc:
                return None, EvidenceFailure(
                    challenge_id=challenge.id,
                    round=round_number,
                    provider=type(self.evidence_provider).__name__,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )

        results = await asyncio.gather(*(run(challenge) for challenge in current))
        new_evidence = [evidence for evidence, _ in results if evidence is not None]
        failures = [failure for _, failure in results if failure is not None]
        return {
            "evidence": state.get("evidence", []) + new_evidence,
            "evidence_failures": state.get("evidence_failures", []) + failures,
            "tool_calls": state.get("tool_calls", 0) + len(current),
        }

    async def revise(self, state: DeliberationState) -> dict:
        round_number = state["round"]
        proposals = state["proposals"]
        active_agents = [
            self.agents_by_id[agent_id]
            for agent_id in proposals
            if agent_id in self.agents_by_id
        ]
        current_challenges = [
            challenge
            for challenge in state.get("challenges", [])
            if challenge.round == round_number
        ]
        evidence_by_challenge = {
            item.challenge_id: item for item in state.get("evidence", [])
        }

        async def run(
            agent: DebateAgent,
        ) -> tuple[Proposal, Revision | None, AgentFailure | None]:
            proposal = proposals[agent.agent_id]
            received = [
                challenge
                for challenge in current_challenges
                if challenge.target_agent_id == agent.agent_id
            ]
            related_evidence = [
                evidence_by_challenge[challenge.id]
                for challenge in received
                if challenge.id in evidence_by_challenge
            ]
            try:
                with debate_span(
                    "debate.agent.revise",
                    **{"debate.agent.id": agent.agent_id, "debate.round": round_number},
                ) as span:
                    decision = await self._await_agent(
                        agent.revise(
                            state["question"],
                            proposal,
                            received,
                            related_evidence,
                            round_number,
                        )
                    )
                    span.set_attribute("debate.revision.from", proposal.position)
                    span.set_attribute("debate.revision.to", decision.position)
                    span.set_attribute("debate.confidence.before", proposal.confidence)
                    span.set_attribute("debate.confidence.after", decision.confidence)
            except Exception as exc:
                return proposal, None, self._agent_failure(
                    agent_id=agent.agent_id,
                    phase="revise",
                    round_number=round_number,
                    exc=exc,
                )

            revised = Proposal(
                agent_id=agent.agent_id,
                position=decision.position,
                claims=decision.claims,
                assumptions=proposal.assumptions,
                uncertainties=proposal.uncertainties,
                final_answer=decision.final_answer,
                confidence=decision.confidence,
            )
            revision = Revision(
                agent_id=agent.agent_id,
                round=round_number,
                previous_position=proposal.position,
                new_position=decision.position,
                previous_confidence=proposal.confidence,
                new_confidence=decision.confidence,
                reason=decision.reason,
                evidence_refs=decision.evidence_refs,
                resolved_challenge_ids=decision.resolved_challenge_ids,
            )
            return revised, revision, None

        results = await asyncio.gather(*(run(agent) for agent in active_agents))
        revised_proposals = {proposal.agent_id: proposal for proposal, _, _ in results}
        revisions = [revision for _, revision, _ in results if revision is not None]
        failures = [failure for _, _, failure in results if failure is not None]
        return {
            "proposals": revised_proposals,
            "revisions": state.get("revisions", []) + revisions,
            "agent_failures": state.get("agent_failures", []) + failures,
        }

    async def assess(self, state: DeliberationState) -> dict:
        dominant, agreement, entropy = _position_stats(state["proposals"])
        critical = _unresolved_critical(
            state.get("challenges", []), state.get("revisions", [])
        )
        sufficiency = _evidence_sufficiency(
            state.get("challenges", []),
            state.get("evidence", []),
            state.get("revisions", []),
            self.config.evidence_quality_threshold,
        )

        unanimous = agreement == 1.0
        distinct_positions = {
            _canonical_position(p.position) for p in state["proposals"].values()
        }
        initial_conflict = state.get("round", 0) == 0 and len(distinct_positions) > 1
        reached = (
            agreement >= self.config.agreement_threshold
            and sufficiency >= self.config.evidence_sufficiency_threshold
            and critical == 0
            and not initial_conflict
        )

        if unanimous and state.get("round", 0) == 0:
            stop_reason = "unanimous"
            reached = True
        elif reached:
            stop_reason = "consensus"
        elif state.get("tool_calls", 0) >= self.config.max_tool_calls:
            stop_reason = "max_tool_calls"
        elif state.get("round", 0) >= self.config.max_rounds:
            stop_reason = "max_rounds"
        else:
            stop_reason = "continue"

        result = ConsensusResult(
            reached=reached,
            dominant_position=dominant,
            agreement_ratio=agreement,
            position_entropy=entropy,
            evidence_sufficiency=sufficiency,
            unresolved_critical_objections=critical,
            reason=(
                f"agreement={agreement:.2f}, evidence={sufficiency:.2f}, "
                f"critical_objections={critical}"
            ),
            stop_reason=stop_reason,
        )
        with debate_span(
            "debate.consensus.check",
            **{
                "debate.round": state.get("round", 0),
                "debate.consensus.agreement": agreement,
                "debate.consensus.entropy": entropy,
                "debate.consensus.evidence_sufficiency": sufficiency,
                "debate.consensus.critical_objections": critical,
                "debate.consensus.reached": reached,
                "debate.consensus.stop_reason": stop_reason,
            },
        ):
            pass
        return {"consensus": result}

    async def begin_round(self, state: DeliberationState) -> dict:
        return {"round": state.get("round", 0) + 1}

    async def finalize(self, state: DeliberationState) -> dict:
        consensus = state["consensus"]
        dominant_key = (
            _canonical_position(consensus.dominant_position)
            if consensus.dominant_position
            else None
        )
        candidates = [
            proposal
            for proposal in state["proposals"].values()
            if dominant_key is not None
            and _canonical_position(proposal.position) == dominant_key
        ]
        if not candidates:
            candidates = list(state["proposals"].values())
        best = max(candidates, key=lambda p: p.confidence)
        prefix = "" if consensus.reached else "[UNRESOLVED CONSENSUS] "
        final = FinalResult(
            answer=prefix + best.final_answer,
            consensus=consensus,
            proposals=state["proposals"],
            rounds=state.get("round", 0),
            evidence=state.get("evidence", []),
            revisions=state.get("revisions", []),
            agent_failures=state.get("agent_failures", []),
            evidence_failures=state.get("evidence_failures", []),
        )
        return {"final_result": final}


def build_deliberation_graph(
    agents: list[DebateAgent],
    evidence_provider: EvidenceProvider,
    config: DeliberationConfig | None = None,
):
    """Build a compiled LangGraph for evidence-grounded multi-agent deliberation."""
    runtime = _Runtime(agents, evidence_provider, config or DeliberationConfig())

    builder = StateGraph(DeliberationState)
    builder.add_node("solve", runtime.solve)
    builder.add_node("assess", runtime.assess)
    builder.add_node("begin_round", runtime.begin_round)
    builder.add_node("critique", runtime.critique)
    builder.add_node("gather_evidence", runtime.gather_evidence)
    builder.add_node("revise", runtime.revise)
    builder.add_node("finalize", runtime.finalize)

    builder.add_edge(START, "solve")
    builder.add_edge("solve", "assess")

    def route_after_assess(state: DeliberationState) -> Literal["begin_round", "finalize"]:
        return "begin_round" if state["consensus"].stop_reason == "continue" else "finalize"

    builder.add_conditional_edges("assess", route_after_assess)
    builder.add_edge("begin_round", "critique")
    builder.add_edge("critique", "gather_evidence")
    builder.add_edge("gather_evidence", "revise")
    builder.add_edge("revise", "assess")
    builder.add_edge("finalize", END)
    return builder.compile()
