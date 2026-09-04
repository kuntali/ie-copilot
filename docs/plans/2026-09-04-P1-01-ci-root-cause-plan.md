# P1-01 — GitHub Actions 未触发根因调查计划

**Task:** `P1-01`  
**Method:** Superpowers `systematic-debugging` + `writing-plans`  
**Status:** planned; execution has not started  
**Live status:** `docs/TASKS.md`

## Goal

确定 `.github/workflows/ci.yml` 已存在但 PR/commit 没有产生 GitHub Actions workflow run 的根因。此任务只负责根因调查和可复现证据，不在没有根因的情况下直接修改 workflow。

## Acceptance criteria

- 明确是否存在 workflow 文件识别、Actions 启用状态、事件触发条件、权限/仓库设置、默认分支安全限制或 GitHub 平台侧原因；
- 得到至少一条可验证的根因证据；
- 如果根因可由仓库代码修复，给出最小修复方案供 `P1-02` 执行；
- 如果根因属于 GitHub 仓库设置/权限且当前连接器无法修改，`P1-01` 标记 `BLOCKED` 并明确需要的人工作业；
- 不通过“随便改一下 YAML 看看”来诊断。

## Files / resources to inspect

- `.github/workflows/ci.yml`
- repository metadata/default branch
- current PR #1 head/base
- commit status/checks
- workflow-runs API results
- Actions/ruleset information available through GitHub APIs
- relevant GitHub Actions event semantics only when repository evidence requires it

## Steps

1. **Task state** — 将 `P1-01` 从 `TODO` 更新为 `IN_PROGRESS`，记录开始调查。
2. **Reproduce/confirm symptom** — 获取 PR #1 当前 head SHA；查询该 SHA 的 workflow runs 和 combined checks，保存“无 Actions run”的证据。
3. **Validate workflow presence** — 读取 feature branch 上 `.github/workflows/ci.yml`，确认路径、YAML 基本结构和 `on` 触发定义。
4. **Check branch/event facts** — 确认 workflow 是在何时被加入、PR 创建/更新发生在什么 SHA、pull_request 是否应被触发。
5. **Check repository-side constraints** — 查询能够读取的 Actions/ruleset/repository metadata，判断 Actions 是否被禁用、workflow 权限是否受限，或是否存在默认分支/首次 workflow 的安全行为。
6. **Form one root-cause hypothesis at a time** — 对每个假设列出支持/反对证据；没有证据时不改文件。
7. **Root cause conclusion** — 将最可信根因和证据写回 `docs/TASKS.md`。
8. **Handoff to P1-02** — 若可修复，写出最小修复步骤与验证方式；若不可由代码修复，标记 `BLOCKED` 并写明外部操作。

## Verification

P1-01 的验证不是“CI 变绿”，而是：

```text
symptom reproduced = yes
root cause supported by evidence = yes
speculative workflow edits = no
P1-02 has a concrete minimal fix or explicit external blocker = yes
```

`P1-02` 才负责实际修复并验证新的 workflow run。

## Stop conditions

立即停止猜测式修改并保留 `BLOCKED/IN_PROGRESS` 状态，如果：

- GitHub API 明确显示 Actions/Workflow 由仓库设置禁用且当前工具无修改权限；
- 需要账户级/仓库级人工授权；
- 可观测信息不足以区分两个关键根因。

此时记录已验证事实和下一步所需信息，不用随机 patch 代替证据。
