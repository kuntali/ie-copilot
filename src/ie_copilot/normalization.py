from __future__ import annotations

import hashlib

from .models import ClaimCluster, DebateItem, PositionCluster, Proposal


def canonical_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def build_claim_clusters(proposals: dict[str, Proposal]) -> list[ClaimCluster]:
    buckets: dict[str, list[tuple[str, str]]] = {}
    for agent_id, proposal in proposals.items():
        for claim in proposal.claims:
            key = canonical_text(claim.statement)
            buckets.setdefault(key, []).append((agent_id, claim.id))

    clusters = []
    for canonical, members in sorted(buckets.items()):
        clusters.append(
            ClaimCluster(
                id=_stable_id("cc", canonical),
                canonical_statement=canonical,
                claim_ids=[claim_id for _, claim_id in members],
                agent_ids=sorted({agent_id for agent_id, _ in members}),
            )
        )
    return clusters


def build_position_clusters(proposals: dict[str, Proposal]) -> list[PositionCluster]:
    buckets: dict[str, list[str]] = {}
    representatives: dict[str, str] = {}
    for agent_id, proposal in proposals.items():
        key = canonical_text(proposal.position)
        buckets.setdefault(key, []).append(agent_id)
        representatives.setdefault(key, proposal.position)

    clusters = []
    for canonical, agent_ids in sorted(buckets.items()):
        clusters.append(
            PositionCluster(
                id=_stable_id("pc", canonical),
                canonical_position=canonical,
                representative_position=representatives[canonical],
                agent_ids=sorted(agent_ids),
            )
        )
    return clusters


def build_debate_queue(
    proposals: dict[str, Proposal],
    position_clusters: list[PositionCluster],
    round_number: int,
) -> list[DebateItem]:
    if len(position_clusters) <= 1:
        return []

    next_round = round_number + 1
    cluster_by_agent = {
        agent_id: cluster.id
        for cluster in position_clusters
        for agent_id in cluster.agent_ids
    }
    all_cluster_ids = {cluster.id for cluster in position_clusters}
    queue: list[DebateItem] = []
    for agent_id in sorted(proposals):
        proposal = proposals[agent_id]
        target_cluster = cluster_by_agent[agent_id]
        opposing = sorted(all_cluster_ids - {target_cluster})
        for claim in proposal.claims:
            queue.append(
                DebateItem(
                    id=f"dbq:r{next_round}:{claim.id}",
                    round=next_round,
                    target_claim_id=claim.id,
                    target_agent_id=agent_id,
                    target_position_cluster_id=target_cluster,
                    opposing_position_cluster_ids=opposing,
                )
            )
    return queue
