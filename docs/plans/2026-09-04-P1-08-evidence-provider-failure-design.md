# P1-08 — EvidenceProvider failure 降级设计

**Task:** `P1-08`  
**Superpowers stage:** brainstorming / design decision  
**Live status:** `docs/TASKS.md`

## Problem

当前 `gather_evidence` 对本轮所有 evidence request 直接执行 `asyncio.gather()`。任一 `EvidenceProvider.gather()` 抛异常会让整个 LangGraph node 失败，导致：

- 同批次已经成功的 Evidence 无法进入 state；
- 整个 deliberation run 被单个检索/工具故障击穿；
- 最终结果无法区分“没有证据”与“取证执行失败”；
- tool budget 只统计成功 Evidence，不统计已经实际发生但失败的外部调用。

这与 evidence-driven deliberation 的可审计性要求冲突。

## Options considered

### A. Fail fast on any EvidenceProvider error

优点：简单、错误显式。  
缺点：一个检索失败即可摧毁整个多 Agent run；并行成功结果被浪费。  
**结论：拒绝作为默认策略。**

### B. 将 failure 转成 `Evidence(quality=0)`

优点：无需增加新模型。  
缺点：语义错误。`quality=0` 表示“取得了一个质量很差的 evidence artifact”，而 provider exception 表示“没有取得 evidence”。把二者混合会污染引用、评估和审计。  
**结论：拒绝。**

### C. Isolate + record failure + preserve successful siblings

规则：

- 每个 evidence request 独立执行、独立捕获异常；
- 成功调用正常生成 `Evidence`；
- 失败调用不生成任何 `Evidence`；
- 失败生成结构化 `EvidenceFailure`；
- 同批次其他成功结果必须保留；
- failed attempt 仍计入 `tool_calls`，因为外部调用已经发生；
- consensus/evidence sufficiency 继续基于真实 Evidence，不能把 failure 当作支持或反驳证据。

**结论：采用。**

## Chosen semantics

### EvidenceFailure artifact

新增领域对象：

```text
challenge_id
round
provider
error_type
message
```

其中 `provider` 当前使用 provider class name，例如 `FailingEvidenceProvider`。后续真实 RAG/Search provider 可扩展稳定 provider id，但本阶段不修改 `EvidenceProvider` Protocol。

`FinalResult.evidence_failures` 暴露完整失败列表；LangGraph state 持续累积。

### Tool budget

`tool_calls` 表示 **attempted external evidence calls**，而不是成功返回的 Evidence 数量。

因此：

```text
2 requests
├─ 1 success
└─ 1 failure

=> tool_calls += 2
=> evidence += 1
=> evidence_failures += 1
```

理由：

- 失败调用同样消耗时间/费用/外部容量；
- 防止失败 provider 在预算模型中形成无限免费重试空间；
- 与 `max_tool_calls` 作为资源 guard 的定义一致。

本任务不实现自动 retry。

### Consensus implications

- provider failure 本身不投票、不生成 evidence；
- 未成功取得 evidence 的 evidence request 仍然是 evidence gap；
- `_evidence_sufficiency` 只读取真实 `Evidence`，因此 failure 不会提高 sufficiency；
- 如果相关 critical objection 仍未解决，现有 consensus policy 会继续阻止 consensus；
- 若 tool budget 已耗尽且仍无 consensus，则现有 `max_tool_calls` stop reason 生效。

### Parallel isolation

同一轮多个 evidence request 中一个失败时：

- 不能取消/丢弃其他成功结果；
- node 返回成功，并同时携带 `Evidence[]` 与 `EvidenceFailure[]`；
- 后续 revise 只接收到真实成功 Evidence。

## Observability

保留当前 `debate.evidence.retrieve` span。Provider exception 在 span 内被记录后由 runtime 捕获并转换为 `EvidenceFailure`，因此：

- Phoenix/OTel Trace 能看到 failed span；
- FinalResult 能看到结构化 failure；
- 不将错误字符串伪装成 Evidence content。

## Non-goals

- provider retry；
- provider/model failover；
- evidence-provider timeout configuration；
- circuit breaker；
- provider health/reputation；
- fallback RAG/search routing。

这些留到后续工具策略/生产化阶段。

## Acceptance cases

1. 两个 evidence request：一个成功、一个 provider exception：run 继续；成功 Evidence 保留；一个 `EvidenceFailure`；`tool_calls == 2`。
2. 唯一 evidence request 失败且耗尽 `max_tool_calls=1`：run 不崩溃；Evidence 为空；failure 被记录；若 consensus 未达成，则以 `max_tool_calls` 停止。
3. Python 3.10 / 3.13 Ruff + unit tests 全绿。
