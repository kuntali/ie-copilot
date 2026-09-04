# P1-05 — Unit pytest 全绿且无外部 API 依赖计划

**Task:** `P1-05`  
**Method:** Superpowers `writing-plans` + `verification-before-completion`  
**Status:** execution in progress  
**Live status:** `docs/TASKS.md`

## Goal

确认当前 unit suite 在 Python 3.10 基线上全绿，同时证明测试执行不需要 OpenAI、Phoenix、Web/Search 或其他外部服务/API。Python 3.13 作为兼容性验证。

## Baseline evidence

CI run #77 (`33854605030`) 已经显示：

- Python 3.10: `Ruff = success`, `Tests = success`;
- Python 3.13: `Ruff = success`, `Tests = success`;
- frozen dependency install 先于测试成功完成。

本任务进一步验证测试边界，而不是因为已有绿灯就直接宣布完成。

## Steps

1. **Inventory unit tests**
   - 列出 `tests/` 下测试文件和 fixture；
   - 确认当前 pytest discovery 范围。

2. **External dependency audit**
   - 搜索 unit tests 对 OpenAI/HTTP/socket/web/Phoenix/真实环境变量/API key 的直接引用；
   - 检查 fixture 是否使用 `ScriptedAgent`、fake/null evidence provider 等确定性实现；
   - 若发现真实网络依赖，先将 P1-05 保持 IN_PROGRESS，并按 TDD/测试隔离修复。

3. **Fresh verification after task start**
   - 使用本任务启动后的新提交触发 CI；
   - Python 3.10 Tests step 必须 success；
   - Python 3.13 Tests step应 success；
   - CI 不配置外部 API secret 作为 unit suite 前置条件。

4. **Handoff**
   - 验证通过后将 P1-05 标记 DONE，并记录 run/job 证据；
   - 下一任务 `P1-06` 必须先写 TDD 计划并从 RED test 开始。

## Acceptance criteria

```text
pytest Python 3.10 = pass
pytest Python 3.13 = pass
unit tests call external network/API = no
unit tests require API secrets = no
fixtures are deterministic/local = yes
```

## Non-goals

- 本任务不新增 Phase 1 缺失的 failure-path tests；它们属于 P1-06～P1-11。
- 不接真实 OpenAI/Phoenix/RAG。
- 不把 integration/e2e 测试混入当前 unit suite；测试分层规范由 P1-12 完成。
