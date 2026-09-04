# IE Copilot — Live Task Board

**Purpose:** single operational source of truth for task execution state.  
**Workflow:** Superpowers. See `AGENTS.md`.  
**Last updated:** 2026-09-04 16:10 +08:00

## Status legend

| Status | Meaning |
|---|---|
| `TODO` | Accepted, not started |
| `IN_PROGRESS` | Actively being executed |
| `BLOCKED` | Cannot proceed; blocker/root-cause/next step must be recorded |
| `DONE` | Acceptance criteria and verification completed |
| `CANCELLED` | Removed from scope with reason |

## Current focus

**Current phase:** Phase 1 — 建立可信工程基线  
**Next executable task:** `P1-01`  
**Parallel execution:** disabled unless an implementation plan explicitly marks tasks independent.

## Phase 0 — 架构基线与 MVP 骨架

| ID | Task | Status | Updated | Evidence / Notes |
|---|---|---|---|---|
| P0-01 | 初始化 `kuntali/ie-copilot` 仓库与功能分支 | DONE | 2026-09-04 | `main` initialized; `feat/multi-agent-deliberation-mvp` created |
| P0-02 | LangGraph MVP 主流程 | DONE | 2026-09-04 | Submitted in PR #1; local static compile passed before push |
| P0-03 | Claim / Challenge / Evidence / Revision / Consensus 模型 | DONE | 2026-09-04 | Pydantic model tests: 2 passed locally |
| P0-04 | 复合 Consensus Policy 与冲突后至少一轮 Debate | DONE | 2026-09-04 | Covered by initial unit-test implementation; full CI verification pending Phase 1 |
| P0-05 | EvidenceProvider 抽象 | DONE | 2026-09-04 | MVP interface/adapter committed in PR #1 |
| P0-06 | OpenAI-compatible Agent 骨架 | DONE | 2026-09-04 | MVP implementation committed in PR #1 |
| P0-07 | Phoenix / OpenTelemetry / OpenInference 接入骨架 | DONE | 2026-09-04 | `docs/observability.md` + runtime instrumentation code committed |
| P0-08 | 设计基线落盘 | DONE | 2026-09-04 | `docs/design/multi-agent-deliberation-system-design-v1.0.md`; docs-only, test N/A |
| P0-09 | 分阶段执行计划落盘 | DONE | 2026-09-04 | `docs/EXECUTION_PLAN.md`; Superpowers/task-state rules linked; docs-only, test N/A |
| P0-10 | 固化 Superpowers 工作流规范 | DONE | 2026-09-04 | `AGENTS.md`, README and `docs/plans/README.md` define mandatory workflow/plan convention; docs-only, test N/A |
| P0-11 | 建立动态 Task 状态板 | DONE | 2026-09-04 | `docs/TASKS.md` established as live execution-state source; docs-only, test N/A |

## Phase 1 — 建立可信工程基线

| ID | Task | Status | Updated | Evidence / Notes |
|---|---|---|---|---|
| P1-01 | 系统化调查 GitHub Actions 未产生 workflow run 的根因 | TODO | 2026-09-04 | Plan: `docs/plans/2026-09-04-P1-01-ci-root-cause-plan.md`; use systematic-debugging; no speculative fix before root cause |
| P1-02 | 修复 CI 触发问题并验证 workflow run 实际产生 | TODO | 2026-09-04 | Depends on P1-01 |
| P1-03 | 固化 `uv.lock` 与可重复依赖安装 | TODO | 2026-09-04 | Verify Python 3.10 baseline |
| P1-04 | Ruff 全绿 | TODO | 2026-09-04 | `ruff check .` evidence required |
| P1-05 | Unit pytest 全绿且不依赖外部 API | TODO | 2026-09-04 | Python 3.10 required; 3.13 compatibility preferred |
| P1-06 | 补 max_rounds / max_tool_calls 终止测试 | TODO | 2026-09-04 | TDD required |
| P1-07 | 补 Agent failure / timeout 降级测试 | TODO | 2026-09-04 | TDD required |
| P1-08 | 补 EvidenceProvider failure 测试 | TODO | 2026-09-04 | TDD required |
| P1-09 | 补 structured-output parse failure 测试 | TODO | 2026-09-04 | TDD required |
| P1-10 | 补空/重复 Claim 测试 | TODO | 2026-09-04 | TDD required |
| P1-11 | 补并发 Agent 结果隔离测试 | TODO | 2026-09-04 | TDD required |
| P1-12 | 分离 unit / integration / e2e 测试标签 | TODO | 2026-09-04 | External service tests must not contaminate unit suite |
| P1-GATE | Phase 1 gate: CI triggered + Ruff pass + unit pass + Python 3.10 pass | TODO | 2026-09-04 | Cannot start Phase 2 until gate is DONE |

## Later phases

Detailed scope and gates remain in `docs/EXECUTION_PLAN.md`. Tasks for the next phase are expanded here only when the previous phase gate is complete or when planning that phase under Superpowers `writing-plans`.

| Phase | Status | Entry condition |
|---|---|---|
| Phase 2 — 审议协议正确性 | TODO | `P1-GATE = DONE` |
| Phase 3 — 真实模型接入 | TODO | Phase 2 gate complete |
| Phase 4 — Evidence Retrieval 闭环 | TODO | Phase 3 gate complete |
| Phase 5 — 可观测性 E2E | TODO | Required runtime prerequisites available |
| Phase 6 — Benchmark / Baselines | TODO | Stable E2E system |
| Phase 7 — 策略优化 | TODO | Benchmark established |
| Phase 8 — 生产化/企业集成 | TODO | Core quality/cost behavior validated |

## Update protocol

Every coding session/turn that changes repository state must update this file as part of the same logical work:

1. mark the selected task `IN_PROGRESS` before implementation/investigation;
2. add concise evidence as it is discovered;
3. mark `BLOCKED` immediately when a blocker prevents progress and record the root-cause investigation status;
4. mark `DONE` only after planned verification passes;
5. update **Last updated** whenever any task state/evidence changes;
6. do not advance to a later phase while the current phase gate is incomplete unless the plan explicitly authorizes independent parallel work.

## Completion evidence examples

Valid evidence includes:

- exact test/lint command and passing result;
- GitHub Actions run/check identifier and result;
- commit/PR reference plus verification result;
- for docs-only tasks, path + review confirmation and an explicit `test N/A` note.

A statement such as “code looks correct” is not completion evidence.
