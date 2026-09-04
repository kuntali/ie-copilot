# P1-11 — 并发 Agent 结果隔离实施计划

**Task:** `P1-11`  
**Method:** Superpowers-style TDD + verification-before-completion

## Goal

验证并发完成顺序不会串线，并阻止 Agent 通过返回伪造 `Proposal.agent_id` 污染其他 Agent 的结果。

设计依据：`docs/plans/2026-09-04-P1-11-concurrency-isolation-design.md`。

## Task 1 — RED fixtures

在 `tests/conftest.py` 新增：

- `DelayedSolveAgent`：不同 delay，返回自身唯一 claim/final_answer；
- `SpoofingSolveAgent`：自身 `agent_id=c`，但返回 `Proposal(agent_id="a")`。

全部 deterministic，不访问外部 API。

## Task 2 — RED tests

在 `tests/test_graph.py` 新增：

1. out-of-order completion test：
   - a/b/c 使用不同 delay；
   - 完成顺序故意与输入顺序不同；
   - 最终 proposals 的 key、proposal.agent_id、claim 文本全部正确对应。
2. identity spoof test：
   - a/b 正常，c 冒充 a；
   - c 的 Proposal 不得覆盖 a；
   - final proposals 只能包含 a/b；
   - 记录 c 的 `AgentFailure`，`failure_kind=runtime`。

## Task 3 — Observe RED

提交 tests/fixtures，不改生产代码。

预期：

- out-of-order test 可能直接 GREEN，作为回归基线；
- spoof test 必须 RED，因为当前 runtime 信任 `proposal.agent_id`。

## Task 4 — GREEN implementation

仅修改 solve 的单 Agent wrapper：

```python
proposal = await ...
if proposal.agent_id != agent.agent_id:
    raise RuntimeError(...)
```

随后复用现有 `_agent_failure()` 与 quorum degradation。

禁止：

- 静默重写 `proposal.agent_id`；
- 引入锁；
- 改 asyncio.gather 策略；
- 改 consensus 算法。

## Task 5 — GREEN verification

Fresh GitHub Actions：

- Python 3.10 Ruff + Tests pass；
- Python 3.13 Ruff + Tests pass。

## Task 6 — Review

确认：

- identity 由 orchestrator 掌控；
- completion order 不影响映射；
- spoofed result 不会覆盖合法 sibling；
- 复用 P1-07 failure/quorum 语义；
- task diff 不扩展到 cross-run/thread safety。

## Completion gate

Fresh 双版本 CI 全绿 + review 后：

```text
P1-11: IN_PROGRESS -> DONE
P1-12: TODO -> IN_PROGRESS
```
