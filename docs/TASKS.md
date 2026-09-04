# IE Copilot — Live Task Board

**Purpose:** single operational source of truth for task execution state.  
**Workflow:** Superpowers. See `AGENTS.md`.  
**Last updated:** 2026-09-04  

## Status legend

| Status | Meaning |
|---|---|
| `TODO` | Accepted, not started |
| `IN_PROGRESS` | Actively being executed |
| `BLOCKED` | Cannot proceed; blocker/root-cause/next step recorded |
| `DONE` | Acceptance criteria and verification completed |
| `CANCELLED` | Removed from scope with reason |

## Current focus

**Current product milestone:** Vibe Coding MVP — `DONE`  
**Current research roadmap:** Phase 4+ remains optional follow-on work; do not confuse it with end-user MVP readiness.  
**Parallel execution:** disabled unless an implementation plan explicitly marks tasks independent.

## Phase 0 — 架构基线与 MVP 骨架

| ID | Task | Status | Evidence / Notes |
|---|---|---|---|
| P0-01 | 仓库 / feature branch 初始化 | DONE | `kuntali/ie-copilot`, `feat/multi-agent-deliberation-mvp`, PR #1 |
| P0-02 | LangGraph MVP 主流程 | DONE | solve → assess → debate/evidence/revise → finalize |
| P0-03 | Claim / Challenge / Evidence / Revision / Consensus 模型 | DONE | Pydantic structured domain model |
| P0-04 | 复合 Consensus Policy | DONE | agreement + evidence + critical objections + budget |
| P0-05 | EvidenceProvider 抽象 | DONE | protocol + Null/Callable adapters |
| P0-06 | OpenAI-compatible Agent 骨架 | DONE | structured-output `ChatOpenAI` adapter |
| P0-07 | Phoenix / OpenTelemetry / OpenInference 骨架 | DONE | `docs/observability.md` + runtime instrumentation |
| P0-08 | 设计基线 / 执行计划 / Superpowers 规范 / Task Board | DONE | `docs/design`, `docs/EXECUTION_PLAN.md`, `AGENTS.md`, this file |

## Phase 1 — 可信工程基线

| ID | Task | Status | Evidence / Notes |
|---|---|---|---|
| P1-01..03 | CI 根因调查、触发验证、`uv.lock` / frozen install | DONE | CI runner path verified; `uv lock --check` + `uv sync --frozen` |
| P1-04 | Ruff 全绿 | DONE | Python 3.10/3.13 CI |
| P1-05 | deterministic unit pytest、无外部 API | DONE | unit suite uses test doubles only |
| P1-06 | max_rounds / max_tool_calls 终止测试 | DONE | exact-boundary coverage |
| P1-07 | Agent failure / timeout 降级 | DONE | structured `AgentFailure`, quorum degradation |
| P1-08 | EvidenceProvider failure 隔离 | DONE | structured `EvidenceFailure`, attempted-call accounting |
| P1-09 | structured-output parse failure | DONE | runtime/timeout/structured_output classification |
| P1-10 | 空/重复 Claim | DONE | deterministic schema validation |
| P1-11 | 并发 Agent 结果隔离 | DONE | out-of-order safe; proposal identity spoofing rejected |
| P1-12 | unit / integration / e2e 分层 | DONE | physical directories + strict markers; default only unit |
| P1-GATE | CI + Ruff + unit + Python 3.10 | DONE | final Phase 1 fresh CI #215 (`33860081179`) success on 3.10/3.13 |

## Phase 2 — 审议协议正确性

Phase 2 was implemented as one TDD protocol-correctness batch. Design/plan:

- `docs/plans/2026-09-04-phase2-protocol-correctness-design.md`
- `docs/plans/2026-09-04-phase2-protocol-correctness-plan.md`

| ID | Task | Status | Evidence / Notes |
|---|---|---|---|
| P2-01 | Claim occurrence identity 与跨 Agent normalization | DONE | orchestrator-owned deterministic `clm:{agent}:r{round}:{index}` + `ClaimCluster` |
| P2-02 | Position / hypothesis clustering | DONE | deterministic `PositionCluster` independent from Claim clusters |
| P2-03 | 显式 `debate_queue` | DONE | `DebateItem`; queue represents next round's pending conflicts |
| P2-04 | 只允许 conflict Claim 进入 Challenge | DONE | critique filters to existing + queued target claim IDs |
| P2-05 | Evidence → Claim relation | DONE | `target_claim_id` + `supports/attacks/neutral` |
| P2-06 | Revision provenance | DONE | before/after position + claim IDs + triggers + evidence refs |
| P2-07 | MAINTAIN / WEAKEN / REVISE / ABANDON | DONE | explicit `RevisionAction`; runtime inference preserves old agents |
| P2-08 | Consensus 与 final text 解耦 | DONE | consensus uses structured positions/evidence/objections |
| P2-09 | 每轮 Position Snapshot | DONE | round 0 + each revision round |
| P2-10 | Deterministic replay | DONE | stable occurrence/protocol IDs + `replay_signature` tests |
| P2-GATE | deterministic protocol correctness + replayable rounds | DONE | Phase 2 GREEN CI #239 (`33887022335`) passed Ruff + unit on Python 3.10/3.13; later contract CI also remains green |

## Phase 3 — 真实 OpenAI-Compatible 模型接入

| ID | Task | Status | Evidence / Notes |
|---|---|---|---|
| P3-01 | RuntimeSettings / AgentFactory | DONE | `config.py` + `factory.py`; model/base URL/temp/timeout/retry centralized |
| P3-02 | 版本化 Prompt | DONE | `prompts.py`, `PROMPT_VERSION`, ask/vibe role sets |
| P3-03 | 所有 Agent 领域输出 structured output | DONE | proposal/challenge/revision schemas |
| P3-04 | bounded structured-output retry | DONE | retries only Pydantic/parser failures; strict configured budget |
| P3-05 | 模型调用 metadata 可观测 | DONE | model, temperature, prompt version, schema, retry attempt on `debate.llm.structured_output` spans |
| P3-06 | OpenAI-compatible HTTP contract integration | DONE | local HTTP contract server drives actual `ChatOpenAI` through conflict → revision → consensus |
| P3-GATE | OpenAI-compatible structured-output chain verified | DONE | CI #287 (`33888534171`) `openai-contract` success; Python 3.10/3.13 unit also success, no external key required |

## Vibe Coding MVP — End-user vertical slice

Design/plan:

- `docs/plans/2026-09-04-vibe-coding-vertical-slice-design.md`
- `docs/plans/2026-09-04-vibe-coding-vertical-slice-plan.md`
- user guide: `docs/VIBE_CODING.md`

| ID | Capability | Status | Evidence / Notes |
|---|---|---|---|
| VIBE-01 | `ie-copilot ask` + legacy positional command | DONE | parser unit coverage |
| VIBE-02 | `ie-copilot vibe` with implementer/reviewer/tester roles | DONE | `VIBE_OBJECTIVES` + versioned prompts |
| VIBE-03 | 用户显式文件/目录作为代码上下文 | DONE | root-constrained selection; ignored build/vendor dirs; file/size caps |
| VIBE-04 | WorkspaceEvidenceProvider | DONE | deterministic keyword retrieval, line-numbered `workspace://` evidence |
| VIBE-05 | 输出 implementation-ready answer / unified diff | DONE | vibe prompt contract + diff extraction |
| VIBE-06 | `--patch-out` | DONE | saves final unified diff without modifying worktree |
| VIBE-07 | explicit safe `--apply` | DONE | reject unsafe paths → `git apply --check` → `git apply`; never commit/push |
| VIBE-08 | `--json` deliberation trace | DONE | proposals/clusters/queue/challenges/evidence/revisions/snapshots/failures/consensus |
| VIBE-09 | bounded runtime budgets and parser retries | DONE | CLI + env settings |
| VIBE-10 | deterministic unit + OpenAI contract CI | DONE | unit GREEN #277 (`33888237088`); OpenAI contract GREEN #287 (`33888534171`) |
| VIBE-GATE | End-user can execute evidence-grounded vibe coding from CLI | DONE | `README.md` + `docs/VIBE_CODING.md`; no repository write unless explicit `--apply` |

## Research / enterprise follow-on roadmap

These are **not required for the Vibe Coding MVP** and are intentionally not marked complete without real evidence.

| Phase | Status | Remaining scope / entry condition |
|---|---|---|
| Phase 4 — General Evidence Retrieval 闭环 | TODO | add web/enterprise-RAG provider, artifact dedup, source trust/freshness, information-gain stopping; workspace provider is already production-usable for vibe mode |
| Phase 5 — Phoenix 可观测性 E2E | TODO | runtime instrumentation exists; gate requires an actual Phoenix service and manual/replay trace verification |
| Phase 6 — Benchmark / Baselines | TODO | build repeatable evaluation corpus and compare Single / Majority / static debate / retrieval / proposed protocol |
| Phase 7 — 策略优化 | TODO | only after benchmark; dynamic agent count, expected information gain, adaptive debate |
| Phase 8 — 企业生产化 | TODO | auth/DBAC, persistence, deployment policy, enterprise evidence providers, SLOs and governance |

## Update protocol

Every coding session/turn that changes repository state must update this file as part of the same logical work:

1. mark selected work `IN_PROGRESS` before non-trivial implementation;
2. record RED/GREEN or root-cause evidence;
3. mark `BLOCKED` if an external prerequisite prevents verification;
4. mark `DONE` only after planned verification passes;
5. do not claim external/live-system validation when only mocks or local contracts were exercised.
