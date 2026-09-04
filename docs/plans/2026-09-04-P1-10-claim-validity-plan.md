# P1-10 — 空/重复 Claim 实施计划

**Task:** `P1-10`  
**Method:** Superpowers-style TDD + verification-before-completion

## Goal

以确定性 schema validation 阻止空 Claim、空 claims 列表和同一 Agent 输出中的重复 Claim，同时复用 P1-09 structured-output failure 降级机制。

设计依据：`docs/plans/2026-09-04-P1-10-claim-validity-design.md`。

## Task 1 — RED model tests

在 `tests/test_models.py` 新增：

1. `Claim(statement="")` 必须 ValidationError；
2. `Claim(statement="   ")` 必须 ValidationError；
3. `Proposal(claims=[])` 必须 ValidationError；
4. 同一 Proposal 内 `"Same claim"` 与 `" same   CLAIM "` 必须 ValidationError；
5. `RevisionDecision` 同样禁止空 claims / canonical duplicate claims。

## Task 2 — RED graph test

新增 deterministic `EmptyClaimsOutputAgent` 或 `DuplicateClaimsOutputAgent`，通过 `Proposal.model_validate(...)` 产生真实 ValidationError。

断言：

- 其余两个 Agent 正常时 graph 继续；
- malformed Agent 不进入 proposals；
- `AgentFailure.failure_kind == "structured_output"`；
- 不新增特殊降级逻辑。

## Task 3 — Observe RED

提交 tests/fixtures，不改生产模型。

必须看到：

- Ruff pass；
- 新 model tests 因当前 schema 接受无效输入而失败；
- graph invalid-claim test 证明现有 P1-09 分类路径可复用。

## Task 4 — GREEN implementation

### `Claim`

新增 field validator：

```python
if not statement.strip():
    raise ValueError("claim statement must not be blank")
```

不改写合法 statement 文本。

### `Proposal` / `RevisionDecision`

- `claims` 使用 `Field(min_length=1)`；
- validator 使用 canonical key：`" ".join(statement.lower().split())`；
- 检测到 duplicate 时抛 `ValueError`；
- helper 共享，避免两套规则漂移。

## Task 5 — GREEN verification

Fresh GitHub Actions 必须：

- Python 3.10 Ruff + Tests pass；
- Python 3.13 Ruff + Tests pass。

## Task 6 — Review

确认：

- schema 层没有静默删除/合并 Claim；
- 合法 statement 原文本未被重写；
- 不进行 semantic/embedding 去重；
- Claim ID/evidence refs 不被隐式合并；
- P1-09 failure classification 无回归。

## Completion gate

Fresh 双版本 CI 全绿 + review 无未解决问题后：

```text
P1-10: IN_PROGRESS -> DONE
P1-11: TODO -> IN_PROGRESS
```
