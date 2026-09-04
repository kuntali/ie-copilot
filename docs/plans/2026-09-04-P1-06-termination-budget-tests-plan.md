# P1-06 — max_rounds / max_tool_calls 终止测试计划

**Task:** `P1-06`  
**Method:** Superpowers test-first / TDD discipline + verification-before-completion  
**Status:** execution in progress  
**Live status:** `docs/TASKS.md`

## Goal

为两种硬预算建立明确的自动化回归测试：

1. `max_rounds` 到达后，未达成共识的审议必须结束，并报告 `stop_reason=max_rounds`；
2. `max_tool_calls` 必须限制实际 EvidenceProvider 调用次数，绝不能因同轮多个 evidence request 超过预算，并在预算耗尽且尚未共识时报告 `stop_reason=max_tool_calls`。

## Existing implementation inspected

`src/ie_copilot/graph.py` 当前已经包含：

- `gather_evidence()` 使用 `remaining = max(0, max_tool_calls - tool_calls)` 并对当前请求切片；
- `assess()` 在未达共识时检查 `tool_calls >= max_tool_calls`，随后检查 `round >= max_rounds`；
- graph 只有 `stop_reason == "continue"` 才进入下一轮。

因此本任务首先只添加测试。若测试直接通过，说明行为已经存在，不修改生产代码；“RED → GREEN”只适用于测试暴露真实缺口后需要修改生产行为的情况，不为了形式人为破坏已有正确实现。

## Test cases

### Test A — max_rounds stops persistent disagreement exactly at budget

在 `tests/test_graph.py` 增加：

- 3 个 ScriptedAgent，两个坚持 X、一个坚持 Y；
- 不产生 challenge/evidence；
- config: `agreement_threshold=1.0`, `max_rounds=2`；
- 预期：
  - `consensus.reached is False`；
  - `stop_reason == "max_rounds"`；
  - `result.rounds == 2`；
  - 每个 Agent `critique_calls == 2`、`revise_calls == 2`。

这验证不是“超过”预算后才停，而是恰好执行两轮后停止。

### Test B — max_tool_calls caps same-round evidence fan-out

增加一个 deterministic evidence fixture（可复用 `HighQualityEvidenceProvider` 的 `calls` 计数），构造至少两个 Agent 在同一轮产生 evidence request：

- persistent disagreement；
- `max_tool_calls=1`, `max_rounds` 足够大；
- 同轮至少 2 个 evidence request；
- 预期：
  - provider `calls == 1`；
  - `len(result.evidence) == 1`；
  - `stop_reason == "max_tool_calls"`；
  - `result.consensus.reached is False`；
  - `result.rounds == 1`。

## Execution

1. 只修改测试/fixture；
2. 提交后观察 CI：
   - 如果 tests 失败，保存 RED 日志，定位是测试假设错误还是生产缺口；
   - 若是生产缺口，再做最小实现并重新验证 GREEN；
   - 如果新测试直接通过，不修改生产代码；记录“existing behavior verified”。
3. Ruff + pytest 3.10/3.13 全绿后，P1-06 才能 DONE。

## Acceptance criteria

```text
max_rounds exact-boundary test = pass
max_tool_calls cap test = pass
actual evidence calls never exceed configured budget = verified
stop_reason values = verified
Ruff = pass
Python 3.10 pytest = pass
Python 3.13 pytest = pass
```
