# P1-09 — Structured-output parse/schema failure 设计

**Task:** `P1-09`  
**Superpowers stage:** brainstorming / design decision  
**Live status:** `docs/TASKS.md`

## Problem

`LLMDebateAgent` 的 solve / critique / revise 都依赖 `with_structured_output(...)`。当模型输出无法满足 Pydantic schema 或 parser 无法解析时，异常会进入运行时。

P1-07 已经保证单个 Agent exception 不会击穿整个 run，但当前 `AgentFailure` 只记录 `error_type`，无法稳定区分：

- timeout；
- structured-output schema / parse failure；
- 普通 runtime / provider / model-call failure。

这会削弱故障统计、告警和后续 provider/model 选择策略。

## Chosen semantics

给 `AgentFailure` 增加：

```text
failure_kind: runtime | timeout | structured_output
```

分类规则：

1. `asyncio.TimeoutError` -> `timeout`；
2. Pydantic `ValidationError` -> `structured_output`；
3. LangChain `OutputParserException` -> `structured_output`；
4. 若上述异常被一层异常包装，沿 `__cause__` / `__context__` 检查；
5. 其他异常 -> `runtime`。

`error_type` 和 `message` 继续保留原始异常信息；`failure_kind` 只做稳定的高层分类，不覆盖原异常类型。

## Why classification belongs in runtime

Runtime 是所有 Agent implementation 的统一故障边界：

- `LLMDebateAgent` 使用 LangChain/Pydantic structured output；
- 后续其他 Agent implementation 也可能使用不同 provider 但仍产生 schema validation error；
- 在 runtime 分类，可避免每个 Agent 重复包装异常。

## Degradation semantics

不改变 P1-07 的行为：

- solve structured-output failure：该 Agent 本次 solve 失败并从 active proposals 移除；quorum >= 2 时继续；
- critique structured-output failure：本轮该 Agent 不产生 challenge，保留 proposal；
- revise structured-output failure：保留 previous proposal，不创建 Revision；
- failure 始终进入 `FinalResult.agent_failures`。

## Test strategy

使用 deterministic fake Agent 在 solve 中通过 `Proposal.model_validate(...)` 构造真实 Pydantic `ValidationError`，不调用外部模型/API。

断言：

- graph 继续由剩余两个 Agent 完成；
- failure `error_type == "ValidationError"`；
- `failure_kind == "structured_output"`；
- 现有 RuntimeError failure 被分类为 `runtime`；
- 现有 timeout failure 被分类为 `timeout`。

## Non-goals

- 自动修复 malformed JSON；
- parser retry；
- prompt retry；
- provider native structured-output fallback；
- 将所有 HTTP/provider 4xx 错误猜测成 parse failure；
- 记录模型原始隐藏 reasoning。
