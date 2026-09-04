# 多智能体证据驱动审议系统 — 设计说明书 v1.0

**英文名：** Evidence-Grounded Multi-Agent Deliberation System  
**日期：** 2026-09-04  
**状态：** 初始工程设计基线

> **一句话定义：** 多个独立智能体先形成独立假设与证据集合；系统只针对关键分歧发起结构化质疑，允许智能体主动补充证据并修正立场；当多数共识、证据充分、关键异议消除和答案稳定同时满足时结束审议。

## 0. 执行摘要

本设计不是“多个 Agent 自由聊天直到投票结束”，而是一个由 LangGraph 驱动的、具备显式状态、证据约束、冲突检测、立场修正与终止条件的多智能体审议系统。

核心流程：

```text
独立求解 → 主张归一化 → 冲突检测 → 定向辩论 → 定向取证 → 立场修正 → 共识判定 → 最终综合
```

关键原则：

- Agent 交互单位是 Claim / Challenge / Evidence / Rebuttal / Revision，而不是整段自由对话。
- 只讨论有实质分歧的关键主张，避免全连接式互相反驳。
- 多数同意只是必要条件之一；还要满足证据充分、无关键未解决异议、答案稳定或预算耗尽。
- Judge 是程序性裁判，不是最终“真理 Oracle”。
- 第一版采用 3 Solver + 1 Coordinator + Evidence Retriever，最多 3 轮。

## 1. 背景与问题定义

目标问题是：同一个问题交给多个 Agent 独立执行；执行完成后围绕彼此答案发起辩论；Agent 为维护或修正自己的答案，可以反复调用检索、RAG、数据库、代码执行等工具获取新证据；当足够多的 Agent 对关键结论达成可靠共识时结束任务。

真正难点在于：**交互什么、何时交互、什么时候继续找证据、什么时候必须停止。**

### 1.1 设计目标

- 提高复杂事实判断、架构决策、开放式分析任务的可靠性。
- 让分歧、证据、立场变化、未解决异议结构化、可审计。
- 把额外计算集中在“有争议且值得查证”的地方。
- 允许 Agent 在遇到更强证据后改变答案。
- 通过预算、稳定性和关键异议规则防止无限辩论。

### 1.2 非目标

- 不模拟人类辩论风格。
- 不假设多数票天然等于正确答案。
- 不要求所有任务都进入多轮辩论。
- 第一版不引入复杂信誉系统、博弈机制或 10+ Agent 群体。

## 2. 核心设计原则

1. **先独立、后交流**：降低锚定与群体趋同。
2. **以 Claim 为最小争议单元**：精确质疑、精确挂证据、局部修正。
3. **冲突驱动而非全连接辩论**：控制 N² 通信成本。
4. **证据优先于口才**：外部事实、代码、数据库结果优先。
5. **允许 Revision**：奖励改正，不奖励坚持。
6. **多数票 + 证据 + 异议 + 稳定性**：区别“达成一致”和“可信达成一致”。
7. **Judge 只做程序性判断**：防止系统退化为 Judge 单 Agent。
8. **预算是一级状态**：成本与时延属于算法的一部分。

## 3. 总体架构

```text
User Query
    │
    ▼
Coordinator / LangGraph
    │
    ├──────── parallel ────────┐
    ▼            ▼             ▼
 Solver A     Solver B      Solver C
    └───────────┬──────────────┘
                ▼
        Structured Proposals
                ▼
        Claim Normalization
                ▼
        Conflict Detection
                │
       no conflict? ─ yes ─► Consensus Check
                │ no
                ▼
        Debate / Challenge
                ▼
        Evidence Gap Detection
            ┌───┴────┐
          yes        no
           │          │
           ▼          │
 Search/RAG/DB/Code   │
           └────┬─────┘
                ▼
         Position Revision
                ▼
         Consensus Check
           ┌────┴─────┐
         stop       continue
           │           │
           ▼           └────► next round
       Final Answer
```

## 4. Agent 角色

- **Independent Solver**：独立形成答案、主张、假设、初始证据。
- **Adversarial Critic（可选）**：主动寻找反例和隐藏前提。
- **Evidence Retriever**：只针对 evidence_gap 调用 Web/RAG/DB/Code。
- **Coordinator**：维护状态、路由、预算、终止。
- **Procedural Judge**：判断冲突、证据支持关系、异议是否解决。
- **Final Synthesizer**：只基于已经审议过的状态形成最终答案。

## 5. LangGraph State

```python
class DebateState(TypedDict):
    question: str
    task_type: str
    proposals: dict[str, Proposal]
    claims: dict[str, Claim]
    positions: dict[str, Position]
    debate_queue: list[str]
    challenges: list[Challenge]
    evidence_requests: list[EvidenceRequest]
    evidence: list[Evidence]
    rebuttals: list[Rebuttal]
    revisions: list[Revision]
    consensus: ConsensusState
    budget: BudgetState
    round: int
    status: str
```

## 6. Agent 通信协议

固定五种核心事件：

- **CLAIM**：声明主张。
- **CHALLENGE**：指出漏洞并说明需要什么证据。
- **EVIDENCE**：提交支持/反对 Claim 的外部结果。
- **REBUTTAL**：用证据回应 Challenge。
- **REVISION**：修改、降级或放弃原 Claim/Position。

## 7. 生命周期与触发时机

1. **任务预判**：判断是否值得进入多 Agent。
2. **独立求解**：N 个 Solver 并行且互相隔离。
3. **主张归一化**：原子化 Claim、同义合并、Position 聚类。
4. **冲突检测**：只选择影响大的真实分歧进入 debate_queue。
5. **定向质疑**：围绕目标 Claim 产生 Challenge。
6. **定向取证**：只有出现 evidence_gap 才调用外部工具。
7. **立场修正**：MAINTAIN / WEAKEN / REVISE / ABANDON。
8. **共识判定**：多数、证据、关键异议、稳定性、预算联合判断。
9. **最终综合**：输出共识、证据、少数意见、剩余不确定性和终止原因。

### 什么时候必须取证

- 高重要度 Claim 直接冲突。
- Critical Challenge 指向未验证事实前提。
- 多数意见与高质量反证冲突。
- 高置信度但低证据覆盖。

### 什么时候停止找证据

- 新证据不再改变关键 Claim 或立场。
- Critical Challenge 已解决。
- 达到预算。
- 新来源重复/低质量。
- 任务本身不存在唯一真值。

## 8. 冲突优先级

```text
priority =
    claim_importance
  × disagreement_strength
  × confidence_weight
  × uncertainty_or_evidence_gap
  × expected_information_gain
```

## 9. 证据层

证据应评价：来源权威性、时效性、直接性、独立性、可复现性、覆盖度。

外部检索内容一律视为不可信输入；需要防提示注入、过期信息、同源转载和伪多源共识。

## 10. 立场更新

每轮新证据进入后，Agent 必须显式选择：

- **MAINTAIN**：维持。
- **WEAKEN**：弱化。
- **REVISE**：修正。
- **ABANDON**：撤回。

Prompt 原则：**目标是最大化最终正确性，而不是维护第一次答案；改变立场不会被视为失败。**

## 11. 共识与终止

```python
STOP = (
    agreement_ratio >= agreement_threshold
    and evidence_score >= evidence_threshold
    and unresolved_critical_objections == 0
    and position_stability >= stability_threshold
) or budget_exhausted
```

MVP 推荐：

- solvers = 3
- agreement_threshold = 2/3
- evidence_threshold = 0.70~0.80
- max_rounds = 3
- max_tool_calls = 20~30
- critical_objection_limit = 0
- stability_window = 2 rounds

预算耗尽时不是“宣布共识”，而是输出当前最佳答案 + 未解决异议 + 少数意见，termination_reason=budget_exhausted。

## 12. Judge 的边界

Judge 可以：

- 判断 Claim 是否语义等价或真正冲突。
- 判断 Evidence 是否相关、支持、反对或无关。
- 判断 Challenge 是否已解决。

Judge 不应该：

- 根据语言风格挑选赢家。
- 忽略证据直接拍板真理。
- 覆盖 Critical Challenge 只因为多数票够了。

## 13. LangGraph 节点

```text
START
  ↓
precheck
  ├─ simple → single_solver → FINAL
  ↓
parallel_solve
  ↓
normalize_claims
  ↓
cluster_positions
  ↓
detect_conflicts
  ├─ no conflict → consensus_check
  ↓
debate
  ↓
detect_evidence_gap
  ├─ yes → retrieve → validate_evidence ┐
  └─ no ────────────────────────────────┘
                                        ↓
                                  revise_positions
                                        ↓
                                  consensus_check
                                  ├─ stop → synthesize → FINAL
                                  └─ continue → select_next_conflicts → debate
```

## 14. 最终输出

应包含：Consensus、Agreement、Confidence、Strongest Evidence、Minority Position、Remaining Uncertainty、Termination Reason。

## 15. 典型失败模式

- 伪共识 → 独立首轮 + 高风险一致结论仍可外部验证。
- 律师化坚持 → 强制 Revision 机制。
- 全连接爆炸 → conflict-driven debate。
- 搜证据上瘾 → evidence_gap + 全局预算。
- Judge 单点化 → 程序性 Judge。
- 证据污染 → 来源评分、时效、同源去重、不可信输入隔离。
- 无唯一真值强行共识 → 允许条件化结论和保留少数意见。

## 16. 适用边界

高适用：复杂事实核验、技术选型、故障诊断、代码设计。  
中等：开放式规划。  
低适用：简单问答、格式转换、纯创作、极低延迟请求。

## 17. MVP

**3 Solver + Coordinator + Evidence Retriever + Procedural Judge，最多 3 轮。**

实现顺序：

1. Pydantic 数据结构。
2. LangGraph DebateState + reducer。
3. parallel_solve。
4. Claim Normalizer + Position Clusterer。
5. Conflict Detector + debate_queue。
6. Challenge / Rebuttal。
7. EvidenceRequest + Retriever。
8. Evidence Validator。
9. Revision 四态动作。
10. Composite Consensus Checker。
11. Final Synthesizer。
12. 建立实验基线。

## 18. 评估

Baseline：

- B0 Single Agent
- B1 Best-of-N + Majority Vote
- B2 Static Multi-Agent Debate
- B3 Debate + Shared Retrieval
- B4 Proposed Method

指标：Accuracy、False Consensus Rate、Useful Revision Rate、Harmful Revision Rate、Evidence Utilization、Debate Rounds、Tool Calls、Token/Latency/Cost、Disagreement Resolution Rate。

## 19. 演进路线

- Phase 1：验证“质疑 → 补证 → 改判”。
- Phase 2：效率优化。
- Phase 3：降低伪共识与错误改判。
- Phase 4：任务自适应 Agent 数与预算。
- Phase 5：从历史审议轨迹学习路由/质疑策略。

## 20. ADR 摘要

- ADR-001：结构化审议协议，不以自由聊天为核心协议。
- ADR-002：初始求解强制隔离。
- ADR-003：冲突驱动，不做全连接辩论。
- ADR-004：显式允许 Revision。
- ADR-005：多数票不能单独终止。
- ADR-006：Judge 不是真理 Oracle。
- ADR-007：预算和终止原因进入 State。
- ADR-008：MVP 限制为 3 Solver / 3 rounds。

## 21. 推荐配置基线

```yaml
deliberation:
  solvers: 3
  max_rounds: 3
  max_conflicts_per_round: 3

consensus:
  agreement_threshold: 0.6667
  evidence_threshold: 0.75
  unresolved_critical_objections: 0
  stability_window: 2

budget:
  max_tool_calls: 24
  max_total_tokens: <按部署模型设定>
  max_wall_time_seconds: <按产品 SLA 设定>

evidence:
  require_source_metadata: true
  deduplicate_sources: true
  prefer_primary_sources: true

revision:
  actions: [MAINTAIN, WEAKEN, REVISE, ABANDON]
  reward_correct_revision: true
```

## 22. 最终设计定义

本系统是一种 **Evidence-Grounded Multi-Agent Deliberation（证据驱动的多智能体审议）** 架构：多个独立智能体首先形成独立假设和证据集合，系统对其主张进行结构化对齐和冲突检测；仅针对存在分歧的关键主张发起基于证据的交叉质疑。智能体在受到挑战时可以主动调用外部工具补充证据，并基于新证据维持、弱化、修正或放弃原有立场。系统持续评估主张一致性、证据充分性、未解决关键异议和答案稳定性；满足复合终止条件时结束审议，否则在预算范围内继续下一轮。

---

> **设计基线：** 后续任何改动都应回答两个问题：它是否提升“正确解决分歧”的能力？它是否以可接受的 token、工具调用和时延成本实现？如果只是让 Agent 说更多话，而没有提升证据质量或有效改判率，应谨慎加入。
