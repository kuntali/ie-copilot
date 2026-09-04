# P1-08 — EvidenceProvider failure 实施计划

**Task:** `P1-08`  
**Method:** Superpowers-style TDD + systematic debugging + verification-before-completion

## Goal

让 EvidenceProvider 单次失败不会击穿整个 deliberation run，同时保证：

- 不伪造 Evidence；
- 同批次成功 Evidence 被保留；
- failure 结构化进入最终结果；
- failed attempt 消耗 tool budget；
- 现有 consensus/evidence sufficiency 语义不被污染。

设计依据：`docs/plans/2026-09-04-P1-08-evidence-provider-failure-design.md`。

## Task 1 — RED fixtures

修改 `tests/conftest.py`：

- `SelectiveFailingEvidenceProvider`
  - 根据 `challenge.challenger_agent_id` 对指定请求抛 `RuntimeError`；
  - 其他请求返回高质量 Evidence；
  - 记录总 calls。
- `FailingEvidenceProvider`
  - 所有请求均抛 `RuntimeError`；
  - 记录总 calls。

只使用 deterministic local doubles，不访问外部服务。

## Task 2 — RED tests

修改 `tests/test_graph.py`，新增至少两条测试：

### Case A — partial batch failure isolation

3 agents 产生两个 evidence requests；provider 对一个失败、一个成功。

断言：

- graph 不抛 provider exception；
- `state["tool_calls"] == 2`；
- 真实 Evidence 数量为 1；
- `result.evidence_failures` 数量为 1；
- failure challenge/provider/error type 可审计；
- 成功 sibling Evidence 未丢失。

### Case B — all requested evidence fails at exact tool budget

仅一个 evidence request，provider 失败，`max_tool_calls=1`，critical objection 保持 unresolved。

断言：

- graph 不因 provider exception 崩溃；
- `tool_calls == 1`；
- `result.evidence == []`；
- failure 被记录；
- consensus 未达成；
- `stop_reason == "max_tool_calls"`。

## Task 3 — Observe RED

提交测试后等待 GitHub Actions。

必须确认：

- Ruff 通过；
- Tests 失败；
- 失败原因来自当前 `asyncio.gather()` 传播 provider exception / 缺失 `EvidenceFailure` API，而不是测试拼写或 import 错误。

记录 run id 作为 RED evidence。

## Task 4 — GREEN model/state changes

最小生产改动：

### `models.py`

新增：

```python
class EvidenceFailure(BaseModel):
    challenge_id: str
    round: int
    provider: str
    error_type: str
    message: str
```

`FinalResult` 新增：

```python
evidence_failures: list[EvidenceFailure] = Field(default_factory=list)
```

### `graph.py`

`DeliberationState` 新增 `evidence_failures`。

`solve()` 初始化为空列表。

`gather_evidence()`：

- 每个 challenge 独立 try/except；
- 返回 `(Evidence | None, EvidenceFailure | None)`；
- `asyncio.gather()` 不再因普通 provider exception 传播失败；
- 成功 Evidence 追加；
- failures 追加；
- `tool_calls += len(attempted_challenges)`，不是 `len(successful_evidence)`。

`finalize()` 将 `evidence_failures` 写入 FinalResult。

不修改 EvidenceProvider protocol，不实现 retry。

## Task 5 — GREEN verification

等待 fresh GitHub Actions run。

要求：

- Python 3.10 Ruff pass；
- Python 3.10 Tests pass；
- Python 3.13 Ruff pass；
- Python 3.13 Tests pass。

## Task 6 — Review

对 Task 4 前后 commit 做 diff review：

- 没有把 failure 转成 fake Evidence；
- failed attempts 确实计入 budget；
- successful siblings 不丢失；
- 无 retry/failover scope creep；
- FinalResult 暴露 failure；
- 旧测试无回归。

如 review 发现覆盖缺口，先补测试再完成。

## Completion gate

只有 fresh CI 双版本全绿 + review 无未解决问题，才能：

```text
P1-08: IN_PROGRESS -> DONE
P1-09: TODO -> IN_PROGRESS
```
