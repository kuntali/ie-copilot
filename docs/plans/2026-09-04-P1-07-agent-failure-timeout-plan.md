# P1-07 — Agent failure / timeout 实施计划

**Task:** `P1-07`  
**Design:** `docs/plans/2026-09-04-P1-07-agent-failure-timeout-design.md`  
**Method:** Superpowers `writing-plans` + TDD RED→GREEN→REFACTOR + verification  
**Status:** execution in progress

## Goal

实现单 Agent 调用故障隔离和 per-agent timeout，使 3-Agent Run 在 1 个 Agent 失败/超时时可以由剩余 Agent 继续，同时结构化暴露 failure；如果初始 solve 后不足两个 Agent，则明确失败而不是生成伪共识。

## Task 1 — RED tests / fixtures

**Files:** `tests/conftest.py`, `tests/test_graph.py`

新增 deterministic fixtures：

- `FailingSolveAgent`：solve 抛 `RuntimeError`；
- `SlowSolveAgent`：solve sleep 超过配置 timeout。

新增 RED tests：

1. `test_one_solve_failure_degrades_to_remaining_agents_and_is_recorded`
   - 2 个正常 X + 1 个 solve failure；
   - 预期 Run 返回，不抛异常；
   - final proposals 只有两个正常 Agent；
   - consensus reached；
   - `agent_failures` 记录失败 Agent、phase=solve、timed_out=false。

2. `test_one_solve_timeout_degrades_and_records_timeout`
   - 2 个正常 X + 1 个 slow Agent；
   - config timeout 设很小；
   - 预期 Run 返回；failure timed_out=true/error_type 对应 timeout。

3. `test_initial_solve_requires_two_successful_agents`
   - 1 正常 + 2 failure；
   - 预期明确 RuntimeError，不能返回 single-agent consensus。

先提交测试并用 CI 保存 RED 证据。

## Task 2 — Domain model

**File:** `src/ie_copilot/models.py`

新增：

```python
class AgentFailure(BaseModel):
    agent_id: str
    phase: Literal["solve", "critique", "revise"]
    round: int
    error_type: str
    message: str
    timed_out: bool = False
```

`FinalResult` 增加 `agent_failures: list[AgentFailure] = Field(default_factory=list)`。

## Task 3 — Runtime failure isolation

**File:** `src/ie_copilot/graph.py`

1. `DeliberationState` 增加 `agent_failures`；
2. `DeliberationConfig` 增加 `agent_timeout_seconds: float | None = 60.0`；
3. `_Runtime` 增加统一的 Agent 调用 timeout/failure 转换 helper；
4. solve：
   - 并行执行并分别捕获；
   - 失败 Agent 不进入 proposals；
   - failures 累积；
   - 成功不足 2 个抛清晰 RuntimeError；
5. critique：只遍历当前 proposals 中的 active Agent；失败返回空 challenge + failure；
6. revise：只遍历 active Agent；失败保留 previous proposal、不生成 Revision + failure；
7. finalize 将 failures 放入 `FinalResult`。

不得用 `return_exceptions=True` 后静默忽略异常；必须转换成显式 failure artifact。

## Task 4 — GREEN verification

CI 需要：

```text
Ruff 3.10 = pass
Tests 3.10 = pass
Ruff 3.13 = pass
Tests 3.13 = pass
```

确认三个新测试从 RED 变 GREEN；现有 consensus/budget 测试无回归。

## Task 5 — Review

通过 GitHub diff/patch 自审：

- failure 是否显式暴露；
- failed solve Agent 是否完全不参与后续 proposal 分母；
- critique/revise failure 是否不伪造业务动作；
- timeout 是否有界且可关闭；
- 未引入 retry/hidden network；
- 不改变 evidence-provider failure 行为（留给 P1-08）。

发现 spec/blocking 问题则保持 P1-07 IN_PROGRESS。

## Acceptance criteria

- 1/3 solve failure：降级继续 + failure artifact；
- 1/3 timeout：降级继续 + timeout artifact；
- 2/3 solve failure：明确拒绝单 Agent 伪共识；
- current unit suite + new tests 全绿；
- Ruff 全绿；
- review 无 blocking issue。
