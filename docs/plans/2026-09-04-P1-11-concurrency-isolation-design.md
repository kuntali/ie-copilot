# P1-11 — 并发 Agent 结果隔离设计

**Task:** `P1-11`  
**Superpowers stage:** brainstorming / design decision  
**Live status:** `docs/TASKS.md`

## Problem

solve 阶段通过 `asyncio.gather()` 并发执行多个 Agent。当前实现最后使用 `proposal.agent_id` 作为 proposals 字典键。

这存在两个不同问题：

1. 并发完成顺序不同，结果必须仍正确归属调用它的 Agent；
2. 自定义 `DebateAgent` 可以返回一个与自身 `agent.agent_id` 不一致的 `Proposal.agent_id`，从而冒充/覆盖其他 Agent。

第二点是实际隔离漏洞：orchestrator 不应信任 Agent 输出中的身份字段。

## Chosen invariants

### Orchestrator owns identity

Agent 身份由 runtime 注册时的 `agent.agent_id` 决定，而不是由模型/Agent 返回内容决定。

solve 返回后必须验证：

```text
proposal.agent_id == invoked_agent.agent_id
```

不一致则该 solve 调用失败，记录 `AgentFailure`，且错误 Agent 的 Proposal 不进入 state。

### Out-of-order completion

不同 Agent 可以任意先后完成；最终：

- proposals key 与 Agent 身份一一对应；
- 每个 Proposal 的 claim/final_answer 必须来自对应 Agent；
- completion order 不改变关联关系。

### Failure classification

identity mismatch 是 orchestration/protocol runtime failure：

```text
failure_kind = runtime
error_type = RuntimeError
```

本任务不新增新的 failure kind。

### Quorum

复用 P1-07：

- identity mismatch Agent 被隔离；
- 剩余 >=2 个 successful proposals 时继续；
- <2 时明确 quorum failure。

## Why not silently rewrite proposal.agent_id

将 spoofed `Proposal.agent_id` 静默改回调用方 ID 会掩盖 Agent 实现错误，而且可能让已经构造的 Claim/审计信息看起来合法。

因此采用“验证 + 失败隔离”，而不是自动修正。

## Non-goals

- 多进程/分布式锁；
- LangGraph checkpoint 并发；
- 同一 Agent 实例被多个 Run 同时复用的线程安全；
- cross-run session isolation；
- provider 级并发限制。
