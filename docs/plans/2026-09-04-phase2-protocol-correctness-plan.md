# Phase 2 — 审议协议正确性实施计划

## Method

TDD: characterization → RED protocol tests → GREEN minimal protocol/runtime changes → fresh CI → diff review → Phase 2 gate.

## RED tests

新增 `tests/unit/test_protocol.py`，覆盖：

- occurrence IDs 由 orchestrator 确定且跨 Agent 不共享；
- canonical-equal claims 进入同一 ClaimCluster；
- positions 独立聚类；
- conflict 时显式产生 debate_queue；
- 非 queue claim 的 Challenge 被过滤；
- Evidence 绑定 target claim + supports/attacks relation；
- Revision 记录 action/before/after/trigger/evidence；
- Round 0 + subsequent position snapshots；
- consensus 不受 final_answer 文本变化影响；
- 两次固定 Fake Agent 运行 replay signature 相同。

## GREEN

1. 扩展 `models.py` 的协议数据模型。
2. 新增 `normalization.py` deterministic baseline。
3. 扩展 `DeliberationState`。
4. `solve` 后建立 clusters/queue/snapshot。
5. `critique` 只接受 queue target claims。
6. evidence/revision 由 runtime 补齐 provenance 与 deterministic IDs。
7. 每轮 revise 后刷新 clusters/queue + snapshot。
8. final result 暴露 protocol trace 数据。

## Gate

Python 3.10/3.13 fresh CI：lock + frozen install + Ruff + unit 全绿；protocol tests 可重复。
