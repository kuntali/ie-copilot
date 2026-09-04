# Phase 2 — 审议协议正确性批次设计

## Goal

一次性固化 Phase 2 的协议不变量，让后续真实模型只是替换 Agent 实现，而不再改变审议语义。

## Invariants

1. `Claim.id` 表示一次具体输出中的 occurrence，不表示跨 Agent 语义等价。
2. Orchestrator 拥有运行时 ID：Claim/Challenge/Evidence/Revision 在固定 Agent 行为下必须可重复。
3. 跨 Agent 等价 Claim 使用 `ClaimCluster.id`；Position 使用独立 `PositionCluster.id`。
4. 冲突检测产出显式 `DebateItem`/`debate_queue`，只允许 queue 中的 target claim 被挑战。
5. Evidence 必须显式绑定 `target_claim_id` 与 `relation=supports|attacks|neutral`。
6. Revision 必须记录 action、before/after、trigger challenge IDs、evidence refs。
7. action 语义为 `MAINTAIN | WEAKEN | REVISE | ABANDON`，未显式提供时 runtime 以结构化 before/after 推导。
8. Consensus 只读取结构化 Position/Challenge/Evidence/Revision，不读取 final answer 文本。
9. Round 0 和每轮 revision 后都记录 `PositionSnapshot`。
10. 固定 Fake Agent 行为两次运行必须得到相同的 semantic replay trace。

## Deterministic baseline

Phase 2 不使用 embedding/LLM 做 normalization。baseline：Unicode/大小写/空白归一；相同 canonical text 聚类。语义近似聚类留给后续可插拔 normalizer。

## Debate queue baseline

若存在多个 Position clusters，则每个 Agent 的 claims 都属于 material conflict surface。队列按 claim occurrence 建 item，记录 opposing position cluster IDs。后续 Phase 7 再引入重要性/信息增益排序。

## Compatibility

保留现有 `supports_target_claim` 作为兼容输入字段；runtime 将其投影为新的 Evidence relation。现有 ScriptedAgent 无需立即输出 action，runtime 可推导。
