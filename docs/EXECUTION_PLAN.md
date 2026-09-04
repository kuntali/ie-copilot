# IE Copilot — 执行计划 v1.0

**项目：** `kuntali/ie-copilot`  
**日期：** 2026-09-04  
**适用分支：** 当前 MVP 开发以 `feat/multi-agent-deliberation-mvp` 为基线，稳定后合入 `main`  
**用途：** 作为后续开发、评审、测试和 Agent/Codex 执行的统一引导文件。

> **核心原则：** 先证明“流程正确、可测试、可观测”，再接真实模型和真实检索；先建立可重复评估，再优化提示词和多 Agent 策略。

> **执行方法：** 后续实现必须遵循仓库根目录 `AGENTS.md` 中定义的 Superpowers 工作流。`docs/TASKS.md` 是唯一实时任务状态源；本文件负责阶段目标与 Gate，不再承担实时进度记录。

### Superpowers 执行约束

后续非平凡开发统一遵循：

```text
brainstorming（需求/设计变化时）
  → using-git-worktrees / isolated feature branch
  → writing-plans
  → executing-plans / subagent-driven-development
  → test-driven-development (RED → GREEN → REFACTOR)
  → requesting-code-review
  → verification-before-completion
  → finishing-a-development-branch
```

遇到测试、CI、构建、集成或运行异常时，必须先进入 `systematic-debugging`，完成根因调查后再修改。不得通过猜测式连续 patch 解决问题。

动态任务规则：

- 开始执行前：`docs/TASKS.md` 将对应任务标记为 `IN_PROGRESS`；
- 验证失败：保持 `IN_PROGRESS` 或标记 `BLOCKED`，并记录根因调查证据；
- 验证通过：附上测试/CI/commit 等证据后才能标记 `DONE`；
- 每次改变仓库状态的工作结束时，Task Board 必须与真实状态一致；
- 当前 Phase Gate 未完成前，不进入下一阶段，除非计划明确允许独立并行任务。

---

## 1. 项目目标

构建一个基于 LangGraph 的证据驱动多智能体审议系统：多个 Agent 独立求解，同一问题出现实质冲突时进入结构化辩论；Agent 可针对争议点请求外部证据，并基于证据维持、降低置信度、修正或放弃原有立场；系统在满足复合共识条件或预算耗尽时结束。

最终系统必须同时满足四类要求：

1. **正确性**：不会把简单多数票误当成可靠共识。
2. **可解释性**：Claim、Challenge、Evidence、Revision、Consensus 可追踪。
3. **可控性**：轮次、工具调用、Token、时间均有预算和终止规则。
4. **可观测性**：能够在 Phoenix/OpenTelemetry 中重建一次完整 Run 的关键决策链。

---

## 2. 不做什么

以下事项不应在基础能力稳定前提前引入：

- 10+ Agent 大规模群体协作；
- 复杂信誉/博弈/奖励机制；
- 全连接 Agent-to-Agent 自由聊天；
- 为可观测性自研 Trace 存储和 Trace UI；
- 在没有可重复 benchmark 前依赖 Prompt 调优证明效果；
- 将多数票、Judge 单次判断或模型自报 confidence 当成“真理判定”。

---

## 3. 当前基线状态

截至本计划建立时：

- [x] 仓库初始化；
- [x] LangGraph MVP 主流程已提交；
- [x] Claim / Challenge / Evidence / Revision / Consensus 数据模型；
- [x] 冲突答案必须进入至少一轮 Debate；
- [x] 复合 Consensus Policy；
- [x] EvidenceProvider 抽象；
- [x] OpenAI-compatible Agent；
- [x] Phoenix / OpenTelemetry / OpenInference 接入骨架；
- [x] 基础 pytest；
- [x] GitHub Actions workflow 文件；
- [x] 本地静态编译；
- [x] Pydantic 模型测试；
- [ ] GitHub Actions 实际产生 workflow run 并绿灯；
- [ ] 完整 LangGraph 测试在 Python 3.10 环境通过；
- [ ] Phoenix E2E Trace 验证；
- [ ] 真实 Evidence Provider；
- [ ] 可重复 benchmark 与 baseline 对照实验。

因此当前项目处于：**Phase 0 完成，Phase 1 待完成。**

---

# 4. 分阶段执行路线

## Phase 0 — 架构基线与 MVP 骨架

**状态：已完成。**

### 目标

把讨论中的系统设计转换为明确代码边界，避免后续开发退化为“多个 Agent 聊天 + 投票”。

### 产物

- LangGraph 状态机；
- 领域对象模型；
- Agent/Evidence 协议；
- Consensus Policy；
- Observability 语义规范；
- 初始测试与 CI 文件。

### Gate

已经满足：代码可静态编译，核心模型测试可运行。

---

## Phase 1 — 建立可信工程基线

**优先级：P0，下一步必须先做。**

### 目标

让仓库具备“任何改动都可以被自动验证”的能力。在这一阶段完成前，不继续堆 Agent 能力。

### 任务

1. 查明 GitHub Actions 未触发的原因；
2. 让 CI 在至少 Python 3.10 上运行；
3. 推荐保留 3.10 + 3.13 compatibility matrix；
4. `uv sync` / lockfile 固化依赖；
5. `ruff check .` 全绿；
6. `pytest` 全绿；
7. 确认无真实 API key 时全部测试可运行；
8. 将外部模型、搜索和 Phoenix 集成测试显式标记为 integration/e2e；
9. 确认测试不会因网络偶发失败而污染 unit suite。

### 必须覆盖的测试

- unanimous fast-path；
- 2/3 初始多数但存在冲突时仍必须 Debate；
- critical objection 阻止 consensus；
- evidence 后 Agent revision；
- max_rounds 终止；
- max_tool_calls 终止；
- Agent failure / timeout 的降级行为；
- EvidenceProvider failure；
- 结构化输出解析失败；
- 空/重复 Claim；
- 并发 Agent 结果不会相互覆盖。

### 验收 Gate

以下全部满足才能进入 Phase 2：

```text
CI triggered = true
ruff = pass
unit tests = pass
Python 3.10 = pass
no external API required for unit tests
```

### 输出

- 绿色 CI；
- `uv.lock`；
- 测试分层规范；
- 已知限制列表。

---

## Phase 2 — 审议协议正确性

**优先级：P0。**

### 目标

验证多 Agent 审议本身，而不是模型聪明程度。

这一阶段优先使用 Deterministic/Fake Agent，通过预设输出严格验证状态机。

### 任务

1. 完善 Claim identity 与去重；
2. 增加 Position / hypothesis clustering；
3. Conflict Detector 输出显式 `debate_queue`；
4. 只让有冲突的 Claim 进入质疑；
5. Challenge 必须指向 target claim；
6. Evidence 必须绑定 supports/attacks 的 Claim；
7. Revision 必须记录 before / after / trigger / evidence refs；
8. 实现“维持立场”与“修改立场”的同等合法输出；
9. Consensus 计算从最终文本中解耦；
10. 记录每轮 position snapshot。

### 核心不变量

必须测试：

```text
任何 Challenge 都有 target_claim_id
任何 Evidence 都有来源和目标关系
任何 Revision 都能追溯到旧立场
critical objection 未解决时不能正常 consensus
预算耗尽必须有明确 stop_reason
```

### Gate

给定固定 Fake Agent 行为，运行结果必须确定且可重复；测试可以完整重建每一轮立场变化。

---

## Phase 3 — 真实模型接入

**优先级：P1。**

### 目标

在不改变 Graph 逻辑的情况下替换 Fake Agent 为真实 OpenAI-compatible 模型。

### 任务

1. 统一 ModelProvider/AgentFactory；
2. 支持配置 base URL / model / temperature / timeout；
3. 所有领域消息使用 structured output；
4. 对 schema validation failure 做重试，但设置严格 retry budget；
5. 区分模型错误、网络错误、业务“不知道”；
6. 固定可测试的 system prompt 版本；
7. Prompt 独立版本化，不散落在节点代码中；
8. 记录 model name、prompt version 和 generation parameters。

### Gate

至少用一个 OpenAI-compatible endpoint 完成：

```text
question
→ 3 independent proposals
→ conflict
→ challenge
→ revision
→ consensus/fallback
```

且一次 Run 无人工介入能够结束。

---

## Phase 4 — Evidence Retrieval 闭环

**优先级：P1。**

### 目标

把系统从“LLM 相互说服”升级为真正 Evidence-Grounded Deliberation。

### 原则

模型生成内容不能自动被视为外部证据。

### 任务

1. 接入至少一个真实 EvidenceProvider；
2. 建议优先实现：Web/Search 或企业 RAG 其中一个；
3. Evidence 记录 source URI / title / snippet / timestamp / provenance；
4. 去重；
5. source trust/quality 初步评分；
6. 对 evidence request 做 query normalization；
7. 同一 evidence 可被多个 claim 引用，但只存一次 artifact；
8. 证据冲突时保留双方，不由 Retriever 直接裁决；
9. Evidence budget 纳入 runtime state；
10. 引入低信息增益停止规则的第一版。

### Gate

必须出现一个 E2E 用例：

```text
Agent A 初始结论 X
→ Agent B 提出 Challenge
→ A 请求真实外部证据
→ Evidence 与原假设冲突
→ A Revision X → Y
→ Consensus 改变
```

这将是本项目最关键的 MVP Demo。

---

## Phase 5 — 可观测性 E2E

**优先级：P1。**

### 目标

给定一个 `run_id`，能够重建“谁在什么时候基于什么证据改变了什么立场”。

### 任务

1. Phoenix 本地部署跑通；
2. 验证 LangGraph/LLM/Tool 自动 spans；
3. 固化 `debate.*` semantic convention；
4. 在 span 上增加：
   - agent.id
   - round
   - claim.id
   - challenge.id / target
   - evidence.id / source
   - revision.before / after
   - confidence.before / after
   - consensus.*
5. 不保存模型隐藏 chain-of-thought；
6. 保存结构化 reason summary；
7. 对敏感输入定义脱敏策略；
8. 校验 trace parent-child 关系；
9. 建立一个可重复的 observability demo run。

### Gate

在 Phoenix 中人工打开一个 Trace，能够回答：

- 哪个 Agent 提出了最终主张？
- 谁挑战了它？
- 为什么发生检索？
- 检索到了什么证据？
- 哪个 Agent 改变了立场？
- 第几轮达到共识？
- 为什么停止？

如果任何一个问题只能靠翻应用日志回答，则本阶段未完成。

---

## Phase 6 — 评估体系与 Baseline

**优先级：P1，属于“证明方案是否值得”的阶段。**

### 目标

不再凭感觉判断多 Agent Debate 是否有效，而是通过对照实验回答。

### Baseline

至少实现：

1. Single Agent；
2. Best-of-N + Majority Vote；
3. Multi-Agent Debate（无外部取证）；
4. Multi-Agent + Shared Retrieval；
5. 本项目：Conflict-driven + Evidence-seeking + Revision + Consensus Policy。

### 指标

必须记录：

- task accuracy / rubric score；
- latency；
- input/output tokens；
- LLM calls；
- tool calls；
- debate rounds；
- agreement ratio；
- position entropy；
- consensus rate；
- **False Consensus Rate**；
- **Useful Revision Rate**；
- evidence utilization；
- cost per correct answer。

### 两个一级指标

#### False Consensus Rate

系统宣布已达成可靠共识，但答案最终被判定错误的比例。

#### Useful Revision Rate

Agent 因 Challenge/Evidence 修改立场，并且修改后的立场更接近正确答案的比例。

### Gate

必须形成一份可重复运行的 benchmark 脚本和结果文件，而不是手工 Demo。

---

## Phase 7 — 策略优化

**优先级：P2。只有 Phase 6 建立 benchmark 后才能开始。**

### 可能优化项

- Agent epistemic objective 多样化；
- 动态选择参与 Debate 的 Agent；
- 动态 round budget；
- evidence information gain；
- challenge ranking；
- evidence quality evaluator；
- minority report；
- stubbornness / flip-flop / tool addiction 检测；
- judge/moderator 程序性规则增强；
- Prompt / model routing。

### 原则

每个优化必须通过 benchmark 证明：质量提升，或在质量基本不降的情况下明显降低成本/时延。

禁止仅因为“看起来更聪明”就合并策略。

---

## Phase 8 — 生产化与企业集成

**优先级：P2。**

### 任务

- LangGraph checkpointer / persistence；
- run resume；
- idempotency；
- timeout/circuit breaker；
- permission-aware EvidenceProvider；
- secrets management；
- PII/data redaction；
- audit retention；
- Prometheus/Grafana runtime metrics；
- ES 长期事件搜索（可选）；
- k3s deployment；
- air-gapped dependency packaging；
- model/provider failover；
- Human-in-the-loop for unresolved critical objection。

### Gate

形成可部署、可恢复、可审计、权限受控的企业运行版本。

---

# 5. 开发执行规则

## 5.1 每次只推进一个 Gate

开发不是：

```text
想到功能 → 直接实现
```

而是：

```text
选择当前 Phase
→ 明确当前 Gate
→ 写/补测试
→ 最小实现
→ 验证
→ 更新文档
→ 进入下一 Gate
```

## 5.2 不因为真实 LLM 不稳定降低单元测试要求

核心状态机必须通过 Fake/Deterministic Agent 测试。

真实模型测试的作用是 Integration Validation，而不是替代 unit tests。

## 5.3 新功能需要回答四个问题

每增加一个功能，PR 必须说明：

1. 它解决什么失败模式？
2. 它改变哪个 state / protocol？
3. 如何测试？
4. 哪个指标可以验证它真的有价值？

回答不了，不进入实现。

## 5.4 不允许隐式 Agent 通信

Agent 之间交换的信息必须落入结构化协议，不能靠共享长对话历史隐式传播。

---

# 6. Definition of Done

一个功能只有满足以下条件才算完成：

```text
[ ] code implemented
[ ] unit tests added/updated
[ ] tests passing
[ ] lint passing
[ ] no hidden external network dependency in unit tests
[ ] observability semantics updated if needed
[ ] README/docs updated if behavior changed
[ ] failure path tested
[ ] budget/termination impact considered
[ ] PR description explains design impact
```

涉及多 Agent 行为的功能还必须检查：

```text
[ ] does not introduce free-form all-to-all debate
[ ] does not treat majority as truth
[ ] does not create unbounded loops
[ ] does not silently discard minority/critical objections
[ ] evidence provenance remains traceable
```

---

# 7. 推荐分支策略

```text
main
  │
  ├── feat/multi-agent-deliberation-mvp   # 当前基线 PR
  │
  ├── feat/claim-conflict-engine
  ├── feat/evidence-retrieval
  ├── feat/phoenix-e2e
  ├── feat/benchmark-suite
  └── feat/production-runtime
```

不要让一个 PR 同时实现 Phase 2～5。

推荐：

> **一个 PR 对应一个明确 Gate 或一个紧密相关的小能力集。**

---

# 8. 下一次继续开发时的起手动作

任何 Agent/开发者继续当前项目时，第一步不是写代码，而是：

```text
1. 读取 docs/design/multi-agent-deliberation-system-design-v1.0.md
2. 读取 docs/EXECUTION_PLAN.md
3. 检查当前分支与 PR 状态
4. 检查 CI / tests
5. 找到当前尚未通过的最近 Gate
6. 只解决这个 Gate
```

当前最近 Gate 是：

> **Phase 1 / CI engineering baseline**

当前第一任务：

> **查明 `.github/workflows/ci.yml` 为什么未产生 GitHub Actions workflow run，并使 Python 3.10 CI 真正运行。**

在这个问题解决前，不建议继续实现新的 Agent 能力。

---

# 9. 后续 Agent 最小引导 Prompt

可以直接将下面内容交给后续 Codex/Agent：

```text
你正在继续开发 kuntali/ie-copilot。

在做任何修改前：
1. 阅读 docs/design/multi-agent-deliberation-system-design-v1.0.md；
2. 阅读 docs/EXECUTION_PLAN.md；
3. 阅读 docs/observability.md；
4. 检查当前 branch / PR / CI / tests 状态；
5. 明确当前 Phase 和尚未通过的 Gate。

不要跳过 Phase Gate，不要同时实现多个后续阶段。
核心设计约束：
- Agent 独立求解后才允许看到其他 Agent 结构化观点；
- 交互以 Claim / Challenge / Evidence / Rebuttal / Revision 为单位；
- 只针对冲突 Claim 辩论；
- Majority 不是 Truth；
- critical objection 未解决不能正常结束；
- 必须有 round/tool/token/time budget；
- 外部 Evidence 必须有 provenance；
- 不记录隐藏 chain-of-thought；
- OpenTelemetry/OpenInference 是 instrumentation contract，Phoenix 是 backend；
- 所有核心 Graph 行为必须可用 Fake Agent 确定性测试。

当前优先执行 docs/EXECUTION_PLAN.md 中最靠前且 Gate 未完成的任务。
完成后更新计划状态和测试证据。
```

---

# 10. 最终目标形态

项目成熟后应形成：

```text
Question
   │
   ▼
Independent Solvers
   │
   ▼
Claim Normalization / Clustering
   │
   ▼
Conflict Detector
   │
   ▼
Debate Queue
   │
   ▼
Challenge
   │
   ▼
Evidence Gap Detection
   │
   ├──► RAG / Search / DB / Code
   │
   ▼
Evidence Validation
   │
   ▼
Belief / Position Revision
   │
   ▼
Consensus Policy
   │
   ├── continue
   │
   └── finish
          │
          ▼
Answer + Evidence + Minority Report + Trace
```

同时：

```text
Runtime
  ↓
OpenInference / OpenTelemetry
  ↓
Phoenix
  ↓
Evaluation / Benchmark
  ↓
Policy Optimization
```

最终验证的核心研究问题不是“多个 Agent 能不能聊天”，而是：

> **冲突驱动的结构化审议 + 主动取证 + 允许立场修正 + 复合共识终止，是否能够以可接受的计算成本，显著降低错误答案和错误共识。**
