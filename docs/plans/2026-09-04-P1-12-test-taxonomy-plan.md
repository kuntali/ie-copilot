# P1-12 — Unit / Integration / E2E 测试分层实施计划

**Task:** `P1-12`  
**Method:** Superpowers-style plan + characterization + verification-before-completion

## Goal

让默认本地测试与普通 PR CI 只能执行 deterministic unit suite，同时为后续 integration/e2e 提供明确、可机器验证的入口。

设计：`docs/plans/2026-09-04-P1-12-test-taxonomy-design.md`。

## Task 1 — Characterize current state

确认：

- `testpaths=["tests"]`；
- CI 使用裸 `pytest`；
- 当前 test files 全在 `tests/` 根目录；
- 当前 tests 均为 deterministic unit。

本任务是测试基础设施重构，不人为制造业务 RED；“当前没有隔离边界”本身即待修配置事实。

## Task 2 — Physical separation

保留：

```text
tests/conftest.py
```

移动：

```text
tests/test_models.py                -> tests/unit/test_models.py
tests/test_graph.py                 -> tests/unit/test_graph.py
tests/test_concurrency_isolation.py -> tests/unit/test_concurrency_isolation.py
```

创建：

```text
tests/unit/README.md
tests/integration/README.md
tests/e2e/README.md
```

## Task 3 — Marker separation

`pyproject.toml` 注册：

- unit
- integration
- e2e

并开启 `--strict-markers`。

根 `tests/conftest.py` 使用 `pytest_collection_modifyitems` 根据测试路径自动增加对应 marker。采用根 hook 而非子目录 conftest，是因为现有 tests 直接从 `conftest` 导入 deterministic test doubles；子目录同名 conftest 会产生 Python module shadowing。

映射：

```text
tests/unit/**        -> unit
tests/integration/** -> integration
tests/e2e/**         -> e2e
```

## Task 4 — Default test policy

`pyproject.toml`：

```toml
testpaths = ["tests/unit"]
addopts = "-q --strict-markers"
```

默认 `pytest` 因 `testpaths` 只发现 unit。

CI Tests step 改成显式：

```bash
pytest tests/unit -m unit
```

注意：CI 的显式路径 + marker 是第二层保护。

## Task 5 — Verification

Fresh CI 必须满足 Python 3.10 / 3.13：

- lock check pass；
- frozen install pass；
- Ruff pass；
- unit Tests pass。

另外 review 必须确认：

- 普通 CI 没有 integration/e2e command；
- integration/e2e 目录不会被 default `testpaths` 收集；
- shared root conftest 无 collection-time network side effects；
- 所有当前测试都位于 unit 目录并自动获得 unit marker；
- 不存在子目录 conftest shadowing。

## Completion gate

验证通过后：

```text
P1-12: IN_PROGRESS -> DONE
P1-GATE: TODO -> validation
```

随后执行 Phase 1 gate 的最终 fresh CI/状态审计，不自动进入 Phase 2，直到 gate 明确 DONE。
