# P1-10 — 空/重复 Claim 有效性设计

**Task:** `P1-10`  
**Superpowers stage:** brainstorming / design decision  
**Live status:** `docs/TASKS.md`

## Problem

Claim 是后续 challenge/evidence/revision 的最小引用单元。当前模型允许：

- `statement=""`；
- `statement="   "`；
- `Proposal.claims=[]`；
- 同一 Proposal 内重复的 Claim statement。

这些输入不会立即破坏 Python 类型，但会破坏审议语义：空 Claim 无法被验证，重复 Claim 会制造重复 challenge/evidence 路径，并让可观测性中的 claim 数量失真。

## Options considered

### A. 静默清理/去重

运行时自动删除空 Claim、合并重复 Claim。

优点：Run 更容易继续。  
缺点：修改了 Agent 原始输出；重复 Claim 的 ID/evidence refs 合并规则不明确；模型质量问题被隐藏。  
**结论：不采用。**

### B. Schema 层严格拒绝无效 Claim

规则：

- Claim statement `strip()` 后不能为空；
- Proposal / RevisionDecision 至少包含 1 个 Claim；
- 同一 claims 列表内，statement 经 `lower + whitespace collapse` 后不得重复；
- 违反规则产生 Pydantic `ValidationError`；
- 通过 P1-09 已有 structured-output failure 分类进入降级路径。

优点：失败边界清晰、可观察、不会静默改变模型输出。  
缺点：更严格，可能降低单次 Agent 成功率。  
**结论：采用。**

### C. 语义相似度去重

用 embedding/LLM 判断两个 Claim 是否语义等价。

优点：能处理真正的语义重复。  
缺点：非确定性、增加成本，而且这是后续 `normalize_claims` 的职责，不应成为基础 schema validator。  
**结论：本任务不做。**

## Chosen semantics

### Claim statement

`Claim.statement`：

- 空字符串拒绝；
- 纯空白拒绝；
- 非空内容保持原文本，不在 schema 层改写其表达。

### Claims list

`Proposal.claims` 与 `RevisionDecision.claims`：

- 最少 1 条；
- canonical key：`" ".join(statement.lower().split())`；
- 同一列表中 canonical key 重复即 ValidationError；
- 不跨 Agent 去重；
- 不做标点、同义词、embedding 级语义归并。

### Why reject instead of dedupe

Claim ID 是 challenge/evidence/revision 的引用键。静默去重必须决定：

- 保留哪个 Claim ID；
- evidence_refs 如何合并；
- confidence 如何合并。

这些都是审议协议层的策略，不应该由 schema validator 偷偷决定。因此 schema 只做确定性合法性检查。

## Failure semantics

无效 Claim 属于 structured-output/schema failure：

```text
ValidationError
  -> AgentFailure.failure_kind = structured_output
  -> reuse P1-07 degradation
```

不新增新的 failure kind。

## Non-goals

- 跨 Agent claim normalization；
- embedding 相似度去重；
- 自动合并 confidence/evidence refs；
- 句子原子化拆分；
- claim importance scoring。
