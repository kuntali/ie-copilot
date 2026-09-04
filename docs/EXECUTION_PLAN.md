# IE Copilot — 执行计划 v1.1

**项目：** `kuntali/ie-copilot`  
**日期：** 2026-09-04  
**开发基线：** `feat/multi-agent-deliberation-mvp`  
**实时状态：** `docs/TASKS.md`（唯一任务状态源）

> **核心原则：** 先证明协议正确、可测试、可回放，再接真实模型和真实检索；先建立可重复评估，再做 Prompt/Agent 策略优化。

> **执行方法：** 所有非平凡工作遵循仓库 `AGENTS.md` 中固化的 Superpowers 风格流程：design/brainstorm → writing-plan → RED → GREEN → review → verification-before-completion。测试/CI/运行异常必须先 systematic-debugging，禁止猜测式连续 patch。

---

## 1. 项目目标

构建一个基于 LangGraph 的 Evidence-Grounded Multi-Agent Deliberation System：多个 Agent 独立求解；系统对主张进行结构化对齐和冲突检测；仅针对关键冲突发起 Challenge；Agent 可请求外部证据，并基于证据维持、弱化、修正或放弃原立场；系统依据一致性、证据充分性、关键异议与预算结束审议。

系统必须同时满足：

1. **正确性**：不能把简单多数票等价为可靠共识；
2. **可解释性**：Claim / Challenge / Evidence / Revision / Consensus 可追踪；
3. **可控性**：轮次、工具调用、时间和后续 Token 预算可限制；
4. **可观测性**：最终可在 Phoenix/OpenTelemetry 重建关键决策链；
5. **可测试性**：核心协议可由 deterministic Fake Agent 重复验证。

---

## 2. 非目标

基础协议稳定前不做：

- 10+ Agent 大规模群体协作；
- 全连接 Agent 自由聊天；
- 复杂信誉/博弈/奖励机制；
- 自研 Trace 存储和 Trace UI；
- 在无 benchmark 前用 Prompt 调优证明方案有效；
- 用多数票、Judge 单次判断或模型自报 confidence 充当真理判定。

---

## 3. 当前基线状态

### 已完成

- [x] LangGraph MVP 主流程；
- [x] Claim / Challenge / Evidence / Revision / Consensus 基础模型；
- [x] 初始冲突强制至少一轮 Debate；
- [x] 复合 Consensus Policy；
- [x] EvidenceProvider 抽象；
- [x] OpenAI-compatible Agent 骨架；
- [x] Phoenix / OpenTelemetry / OpenInference 接入骨架；
- [x] `uv.lock` 与 frozen install；
- [x] GitHub Actions Python 3.10 / 3.13 matrix；
- [x] Ruff 全绿；
- [x] deterministic unit suite 全绿且不依赖外部 API；
- [x] max_rounds / max_tool_calls 边界测试；
- [x] Agent failure / timeout 降级；
- [x] EvidenceProvider failure 隔离；
- [x] structured-output failure 分类；
- [x] 空/重复 Claim schema 防护；
- [x] 并发 Agent 结果身份隔离；
- [x] unit / integration / e2e 测试物理与 marker 双层隔离；
- [x] Phase 1 最终 Gate：CI #215 (`33860081179`) Python 3.10/3.13 lock + frozen install + Ruff + unit 全绿。

### 尚未完成

- [ ] 跨 Agent Claim normalization / equivalence identity；
- [ ] Position / hypothesis clustering；
- [ ] 显式 Conflict Detector / DebateQueue；
- [ ] Evidence supports/attacks Claim 关系；
- [ ] Revision 完整 provenance；
- [ ] 每轮 Position Snapshot / deterministic replay；
- [ ] 真实模型 E2E；
- [ ] 真实 EvidenceProvider；
- [ ] Phoenix E2E Trace；
- [ ] benchmark / baselines。

**当前阶段：Phase 2 — 审议协议正确性。** 具体活动任务以 `docs/TASKS.md` 为准。

---

# 4. 分阶段路线

## Phase 0 — 架构基线与 MVP 骨架

**状态：DONE**

目标：把讨论中的“多 Agent 辩论”落成明确的状态机和领域对象，避免退化为自由聊天 + 投票。

产物：LangGraph 状态机、领域模型、Agent/Evidence 协议、Consensus Policy、Observability 规范、初始测试/CI。

---

## Phase 1 — 可信工程基线

**状态：DONE**

### Gate

```text
CI triggered = true
ruff = pass
unit tests = pass
Python 3.10 = pass
Python 3.13 compatibility = pass
no external API required for unit tests
```

最终证据：GitHub Actions #215 (`33860081179`) 全绿。

### 输出

- 可重复 `uv.lock`；
- Python 3.10/3.13 CI；
- deterministic unit tests；
- Agent/Evidence failure 结构化降级；
- structured-output failure 分类；
- Claim 基础 schema 防护；
- 并发身份隔离；
- `tests/unit`, `tests/integration`, `tests/e2e` 测试分类。

---

## Phase 2 — 审议协议正确性

**状态：IN_PROGRESS，优先级 P0**

### 目标

只使用 deterministic/Fake Agent 验证审议协议本身，不依赖真实模型“聪明程度”。最终必须能够结构化解释：哪些 Claim 等价、哪些 Position 冲突、为什么进入 Debate、谁挑战谁、什么证据改变了什么立场，以及每轮如何收敛。

### 顺序

1. **Claim identity / normalization contract**
   - 保留每个 Claim occurrence 的不可变 `Claim.id`；
   - 另建跨 Agent 等价身份/cluster，禁止重载 `Claim.id`；
   - deterministic normalizer 先行，LLM/embedding 后置。
2. **Position / hypothesis clustering**
   - 独立于 Claim cluster；
   - 显式 supporter Agent 集合。
3. **Conflict Detector / DebateQueue**
   - 输出结构化冲突；
   - 只入队 material conflict。
4. **Targeted Challenge routing**
   - 仅有冲突的 Claim 被质疑；
   - 禁止 all-pairs/free-chat。
5. **Evidence → Claim relation**
   - `supports / attacks / neutral`；
   - provenance 可审计。
6. **Revision provenance**
   - before / after / trigger challenge / evidence refs。
7. **Explicit belief update outcome**
   - MAINTAIN / WEAKEN / REVISE / ABANDON。
8. **Consensus 与 final text 解耦**
   - 从结构化 Position/Evidence/Objection 计算。
9. **Round Position Snapshot**
   - 每轮状态不可变快照。
10. **Deterministic replay / invariants**
   - 固定 Fake Agents 重跑得到相同协议轨迹（除随机 runtime IDs 外可 canonicalize）。

### 核心不变量

```text
Claim.id 表示 occurrence，而不是跨 Agent 语义等价类
任何 Challenge 都有 target_claim_id
任何 Evidence 都有 source + target claim relation
任何 Revision 都可追溯到 previous position + trigger
critical objection 未解决时不能正常 consensus
budget exhausted 必须有明确 stop_reason
同一 deterministic scenario 可重建每轮 position evolution
```

### Gate

固定 Fake Agent 行为下：

- protocol state deterministic；
- conflict queue 可解释；
- challenge/evidence/revision 因果链完整；
- 每轮 position snapshot 可重建；
- 全部 unit tests Python 3.10/3.13 通过。

---

## Phase 3 — 真实模型接入

**状态：TODO，优先级 P1**

### 目标

不改变 Graph 协议逻辑，将 Fake Agent 替换成真实 OpenAI-compatible 模型。

### 任务

- ModelProvider / AgentFactory；
- base URL / model / temperature / timeout 配置；
- 所有领域输出 structured output；
- schema retry budget；
- 区分模型错误、网络错误、业务“不知道”；
- Prompt 版本化；
- model/prompt/generation metadata 可观测。

### Gate

至少一个 OpenAI-compatible endpoint 无人工介入完成：

```text
question → proposals → conflict → challenge → revision → consensus/fallback
```

---

## Phase 4 — Evidence Retrieval 闭环

**状态：TODO，优先级 P1**

### 目标

从“模型互相说服”升级为真正 evidence-grounded deliberation。

### 任务

- 至少一个真实 EvidenceProvider（企业 RAG 或 Search）；
- source URI/title/snippet/timestamp/provenance；
- 证据去重与基础 quality/trust；
- evidence request/query normalization；
- 同一 artifact 可被多个 Claim 引用；
- 证据冲突保留双方；
- Evidence budget；
- 第一版低信息增益停止。

### Gate

演示：Challenge → 外部取证 → 证据反驳原假设 → Agent X→Y Revision → Consensus 改变。

---

## Phase 5 — 可观测性 E2E

**状态：TODO，优先级 P1**

### 目标

给定 `run_id` 能回答“谁基于什么证据在第几轮改变了什么立场，为什么停止”。

### 任务

- Phoenix self-host/local 跑通；
- LangGraph/LLM/Tool spans；
- 固化 `debate.*` semantic convention；
- agent/round/claim/challenge/evidence/revision/consensus attributes；
- 不保存隐藏 chain-of-thought；
- reason summary 与敏感信息脱敏；
- trace parent-child 校验；
- 可重复 observability demo。

### Gate

Phoenix Trace 可独立回答 Proposal→Challenge→Evidence→Revision→Consensus 全链问题，而无需翻应用日志。

---

## Phase 6 — Benchmark / Baselines

**状态：TODO，优先级 P1**

对照：Single Agent、Best-of-N+Vote、Static Debate、Debate+Shared Retrieval、本项目协议。

核心指标：Accuracy、Latency、Tokens、LLM/Tool Calls、Rounds、Agreement、Entropy、Consensus Rate、**False Consensus Rate**、**Useful Revision Rate**、Evidence Utilization、Cost per Correct Answer。

Gate：必须用固定 benchmark 证明新增机制带来的准确率/可靠性收益与成本。

---

## Phase 7 — 策略优化

**状态：TODO**

基于 Phase 6 数据优化：动态 Agent 数、Top-K conflicts、expected information gain、early stopping、证据缓存/批处理、异构 Agent/模型等。禁止无 benchmark 的“凭感觉优化”。

---

## Phase 8 — 生产化与企业集成

**状态：TODO**

安全、权限、审计、数据保留、限流、SLA、provider failover、部署、成本控制、长期事件分析、企业 RAG/ES/内部工具接入。

---

# 5. 每个任务的统一验收模板

任何 `DONE` 必须具备：

```text
1. Design / Plan（非平凡任务）
2. RED evidence（行为变化/TDD 任务）
3. Minimal GREEN implementation
4. Review / scope audit
5. Fresh verification
6. docs/TASKS.md evidence update
```

CI/测试失败时不得跨任务继续堆功能；先记录根因并恢复可信基线。

---

# 6. 后续 Agent 接手入口

后续 Codex/Agent 开始工作前必须依次读取：

```text
AGENTS.md
docs/TASKS.md
docs/EXECUTION_PLAN.md
docs/design/multi-agent-deliberation-system-design-v1.0.md
当前 active task 对应 docs/plans/*.md
```

然后只执行 `docs/TASKS.md` 的 Active task，不自行跳阶段。