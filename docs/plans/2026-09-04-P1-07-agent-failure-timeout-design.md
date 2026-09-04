# P1-07 — Agent failure / timeout 降级设计

**Task:** `P1-07`  
**Superpowers stage:** brainstorming / design decision  
**Status:** approved-by-execution baseline for this task; implementation still requires RED tests  
**Live status:** `docs/TASKS.md`

## Problem

当前 `_Runtime` 在 solve / critique / revise 中直接使用 `asyncio.gather()`。任一 Agent 抛异常会让整个 LangGraph Run 失败；同时没有 per-agent timeout，也没有结构化失败记录。

这与多 Agent 系统的目标冲突：单个模型/网络/解析故障不应自动摧毁整个审议，但降级也不能静默，因为失败会改变参与者数量和共识分母。

## Options considered

### A. Fail fast on any Agent error

优点：简单、不会隐式改变参与者集合。  
缺点：3-Agent 系统中一个瞬时故障即可让任务完全失败；没有降级能力。  
**结论：拒绝作为默认策略。**

### B. Record + isolate failed call; continue when quorum remains

规则：

- solve 阶段某 Agent 失败/超时：记录结构化 `AgentFailure`，从本次 Run 的 active proposals 中移除；
- 只要至少 2 个 Agent 成功 solve，继续审议；
- 少于 2 个 Agent 成功时明确失败，不伪造“多 Agent 共识”；
- critique 阶段失败：该 Agent 本轮不产生 challenge，但保留已有 proposal；
- revise 阶段失败：保留该 Agent 上一版 proposal，不生成虚假 Revision，相关 challenge 仍可保持未解决；
- 每次失败都写入最终结果，不能只打日志；
- timeout 与普通异常使用同一失败记录，但有 `timed_out=true`。

优点：故障隔离、因果清晰、不会把失败伪装成正常响应。  
缺点：存活 Agent 数量变化会改变投票分母；需要最终输出暴露 failure。  
**结论：采用。**

### C. 自动重试/替补 Agent

优点：成功率可能更高。  
缺点：引入隐藏额外成本、重试预算、替补身份和独立性问题；会把 P1 工程基线任务膨胀成 provider failover 策略。  
**结论：本阶段不做；留到生产化/provider failover。**

## Chosen semantics

### Quorum

`minimum_active_agents = 2`，与当前系统“至少两个 Agent”不变量一致。

- 初始 solve 后 >= 2 个成功：继续；
- < 2：抛出明确 RuntimeError，消息必须指出 active/required 数量；不生成看似可信的单 Agent consensus。

本阶段不增加动态 quorum 比例，也不要求成功 Agent 占初始 Agent 的固定百分比；这些属于后续评估/策略阶段。

### Timeout

新增 `DeliberationConfig.agent_timeout_seconds`：

- 默认 `60.0` 秒；
- 允许 `None` 表示关闭 per-call timeout；
- 应用于 Agent 的 solve / critique / revise 三类调用；
- timeout 通过 `asyncio.wait_for()` 实现；
- EvidenceProvider timeout 不在本任务，属于 P1-08/后续工具策略。

### Failure artifact

新增 `AgentFailure` 领域对象，至少包含：

```text
agent_id
phase: solve | critique | revise
round
error_type
message
timed_out
```

`FinalResult.agent_failures` 暴露完整记录；LangGraph state 中持续累积。

### Consensus implications

- consensus 分母只使用当前 `proposals` 中成功 solve 的 Agent；
- solve 失败的 Agent 不作为“反对票”或“赞成票”；
- failure 必须在 FinalResult 中暴露，调用方可据此决定是否接受降级共识；
- 本阶段不新增 `degraded_consensus` stop_reason，以避免扩大 Consensus API；failure artifact 已明确说明 Run 是降级执行。

### Later-phase failure

- critique failure：不删除 proposal；当前轮视为该 Agent 无 challenge 输出；
- revise failure：保留 previous proposal，且不创建 Revision；
- 这样不会把“模型调用失败”错误解释为“Agent 主动维持原立场”。失败记录负责区分二者。

## Observability

`debate_span` 内部继续记录异常；运行时在 span 抛出后捕获并转换为 `AgentFailure`。因此：

- Trace 看到失败 span；
- FinalResult 看到结构化 failure；
- 不保存隐藏 chain-of-thought。

## Non-goals

- retry；
- provider/model failover；
- replacement agent；
- dynamic quorum；
- failure reputation；
- EvidenceProvider failure（P1-08）。
