# P1-12 — Unit / Integration / E2E 测试分层设计

**Task:** `P1-12`  
**Superpowers stage:** design decision  
**Live status:** `docs/TASKS.md`

## Problem

当前所有测试位于 `tests/` 根目录，`pyproject.toml` 的 `testpaths=["tests"]`，CI 直接运行裸 `pytest`。现在所有测试都是 deterministic unit tests，因此暂时安全；但后续真实模型、Phoenix、RAG/Search 集成测试加入后，裸 `pytest` 会把它们自动纳入默认 CI，可能导致：

- 访问真实网络/API；
- 需要 secrets/服务却在普通 PR 中执行；
- unit suite 变慢、不稳定；
- 无法区分代码回归与环境/服务故障。

## Options

### A. 只使用 pytest marker

所有文件仍在一个目录，以 `@pytest.mark.unit/integration/e2e` 区分。

优点：改动小。  
缺点：新测试漏 marker 时容易污染默认 suite。  
**不单独采用。**

### B. 只使用目录

`tests/unit`, `tests/integration`, `tests/e2e`。

优点：物理边界清晰。  
缺点：缺乏 pytest 层的机器可读分类；跨目录选择不够灵活。  
**不单独采用。**

### C. 目录 + marker 双重隔离

采用：

```text
tests/
  conftest.py
  unit/
  integration/
  e2e/
```

并注册 `unit`, `integration`, `e2e` markers。

**结论：采用。**

## Taxonomy

### unit

必须满足全部条件：

- deterministic；
- 不访问网络；
- 不调用真实 OpenAI-compatible endpoint；
- 不要求 Phoenix/DB/RAG 等外部服务；
- 使用 ScriptedAgent/fake provider 等 test doubles；
- 普通 PR 必跑。

### integration

验证两个或多个真实组件之间的集成，但范围受控，例如：

- LLMDebateAgent + mock/local OpenAI-compatible server；
- OTel exporter + local collector；
- EvidenceProvider + local test backend。

可以依赖本地进程/容器，但不应默认进入 unit suite。

### e2e

从 question 到 final result 的真实系统链路，可依赖：

- model endpoint；
- Phoenix；
- retrieval/backend services；
- credentials/secrets。

必须显式 opt-in。

## Default behavior

默认 `pytest` 必须只执行 `tests/unit`。

实现双保险：

1. `testpaths = ["tests/unit"]`；
2. CI 显式执行 `pytest tests/unit -m unit`。

即使未来创建 `tests/integration`/`tests/e2e`，也不会被普通 CI 裸跑。

## Marker policy

注册：

```text
unit
integration
e2e
```

启用 `--strict-markers`，拼错/未注册 marker 立即失败。

当前 unit test modules 使用 module-level：

```python
pytestmark = pytest.mark.unit
```

未来 integration/e2e 同理。

## Commands

```bash
# default / unit
pytest
pytest tests/unit -m unit

# explicit integration
pytest tests/integration -m integration

# explicit e2e
pytest tests/e2e -m e2e
```

当 integration/e2e 目录尚无测试时，不在普通 CI 中创建空 job。

## Shared fixtures

`tests/conftest.py` 保留在 `tests/` 根目录，供三个层级继承。Fixture 本身不得在 import/collection 阶段启动网络或外部服务。

## Non-goals

- 本任务不新增真实 integration/e2e 测试；
- 不启动 Docker/Phoenix；
- 不配置 secrets；
- 不建立 nightly E2E workflow；
- 这些在 Phase 3/5 对应任务中增加。
