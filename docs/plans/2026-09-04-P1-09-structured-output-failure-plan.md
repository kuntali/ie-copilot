# P1-09 — Structured-output parse/schema failure 实施计划

**Task:** `P1-09`  
**Method:** Superpowers-style TDD + systematic debugging + verification-before-completion

## Goal

在不调用真实外部模型的前提下，验证并实现 structured-output schema/parser failure 的稳定分类，同时复用 P1-07 已有的 Agent 降级行为。

设计依据：`docs/plans/2026-09-04-P1-09-structured-output-failure-design.md`。

## Task 1 — RED fixture

在 `tests/conftest.py` 新增 `MalformedStructuredOutputAgent`：

- solve 中调用 `Proposal.model_validate(...)`；
- 提供超范围 confidence，确定性触发真实 Pydantic `ValidationError`；
- 不访问任何 API。

## Task 2 — RED tests

在 `tests/test_graph.py`：

1. 新增 structured-output solve failure 测试：
   - 两个正常 Agent + 一个 malformed Agent；
   - graph 继续完成；
   - malformed Agent 从 proposals 移除；
   - failure error type 为 `ValidationError`；
   - 断言 `failure_kind == "structured_output"`。
2. 扩展已有 solve RuntimeError 测试：`failure_kind == "runtime"`。
3. 扩展已有 timeout 测试：`failure_kind == "timeout"`。

## Task 3 — Observe RED

提交 tests/fixtures，不改生产代码。

必须看到：

- Ruff pass；
- Tests fail；
- 失败来自 `AgentFailure` 缺少 `failure_kind` 或分类不正确；
- malformed Agent 的 `ValidationError` 已由现有 P1-07 degradation 边界捕获，而不是击穿整个 graph。

## Task 4 — GREEN implementation

### `models.py`

给 `AgentFailure` 增加：

```python
failure_kind: Literal["runtime", "timeout", "structured_output"] = "runtime"
```

默认 `runtime` 保持序列化兼容。

### `graph.py`

新增 structured-output classifier：

- Pydantic `ValidationError`；
- LangChain `OutputParserException`；
- 检查异常自身及 `__cause__` / `__context__` chain；
- timeout 优先分类为 `timeout`；
- 其余 `runtime`。

`_agent_failure()` 填充 `failure_kind`，不改变 solve/critique/revise 降级控制流。

## Task 5 — GREEN verification

Fresh GitHub Actions 必须：

- Python 3.10 Ruff + Tests pass；
- Python 3.13 Ruff + Tests pass。

## Task 6 — Review

确认：

- 没有新增 retry；
- 没有把普通 provider/API 错误误标为 structured-output；
- 原始 `error_type/message` 保留；
- existing P1-07 failure semantics 无回归；
- task diff 不扩展到 prompts/provider routing。

## Completion gate

Fresh 双版本 CI 全绿 + review 无未解决问题后：

```text
P1-09: IN_PROGRESS -> DONE
P1-10: TODO -> IN_PROGRESS
```
