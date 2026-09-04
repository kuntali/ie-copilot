# AGENTS.md

## Purpose

This repository follows the **Superpowers** software-development methodology. These rules are mandatory for humans and coding agents working on implementation tasks.

The architecture baseline is `docs/design/multi-agent-deliberation-system-design-v1.0.md`.
The phased roadmap is `docs/EXECUTION_PLAN.md`.
The live task state is `docs/TASKS.md` and is the operational source of truth for current work.

### Instruction precedence

When repository documents overlap, interpret them by responsibility:

1. `AGENTS.md` is authoritative for **development process and execution discipline**.
2. `docs/TASKS.md` is authoritative for **current/next task state and completion evidence**.
3. `docs/EXECUTION_PLAN.md` is authoritative for **phase sequencing, gates, and roadmap**.
4. `docs/design/multi-agent-deliberation-system-design-v1.0.md` is authoritative for **system architecture and design rationale**.
5. task-specific `docs/plans/*.md` files are authoritative for **approved implementation steps within their task**, but may not override the documents above without explicitly updating them.

If an older section of a roadmap says to update progress somewhere other than `docs/TASKS.md`, the live task board rule wins.

## Mandatory Superpowers workflow

Before changing production code, use the relevant Superpowers workflow/skill when it is available in the execution environment.

1. **brainstorming** — required for new features, behavior changes, architecture changes, or requirements that are not already approved in the design baseline.
2. **using-git-worktrees** — required before implementation when the environment supports git worktrees. Never implement directly on `main`. When operating through a connector that cannot create worktrees, use an isolated feature branch and record that limitation in `docs/TASKS.md`.
3. **writing-plans** — required after design approval and before non-trivial implementation. Plans must be bite-sized, identify exact files, specify verification steps, and be stored under `docs/plans/`.
4. **subagent-driven-development** or **executing-plans** — execute the written plan task by task. Do not skip steps silently.
5. **test-driven-development** — production behavior changes follow RED → GREEN → REFACTOR. A failing test must demonstrate the intended behavior or bug before production code is changed, unless the task is documentation/configuration-only and a test is not applicable.
6. **systematic-debugging** — on any failing test, CI/build error, unexpected runtime behavior, or integration failure, investigate root cause before proposing or applying a fix.
7. **requesting-code-review** — review completed implementation against the approved plan/spec before declaring the task complete. Critical/spec-compliance issues block completion.
8. **verification-before-completion** — never claim success from code inspection alone. Run the planned verification and retain evidence.
9. **finishing-a-development-branch** — only after all planned tasks are complete and verification is green; then decide merge/PR/keep/cleanup explicitly.

Process skills take precedence over implementation convenience. Do not bypass the workflow because a change appears small.

## Dynamic task-state protocol

`docs/TASKS.md` MUST be updated continuously while work is performed.

Allowed task states:

- `TODO` — accepted but not started.
- `IN_PROGRESS` — currently being worked; only mark this immediately before starting execution.
- `BLOCKED` — cannot proceed; record blocker, evidence, root-cause status, and next action.
- `DONE` — implementation and required verification are complete.
- `CANCELLED` — intentionally removed from scope; record the reason.

Rules:

1. Before starting a task, change it from `TODO` to `IN_PROGRESS`.
2. Do not have multiple `IN_PROGRESS` tasks unless the execution plan explicitly allows parallel independent work.
3. Every meaningful state transition must update `Updated` and `Evidence/Notes` in `docs/TASKS.md`.
4. `DONE` requires concrete evidence: passing test command, CI/check URL or run ID, reviewed diff/commit, or a documented N/A reason for documentation-only work.
5. A failing verification never becomes `DONE`; use `BLOCKED` or keep `IN_PROGRESS` while performing systematic debugging.
6. If scope changes, update both the implementation plan and `docs/TASKS.md` before proceeding.
7. The task table must reflect reality at the end of every working session/turn that changes the repository.

## Definition of task completion

A coding task is complete only when all applicable items are true:

- acceptance criteria satisfied;
- RED test was observed where TDD applies;
- GREEN test passes;
- relevant regression tests pass;
- lint/type/static checks pass where configured;
- implementation matches design/plan;
- code review found no unresolved blocking issues;
- `docs/TASKS.md` is updated with completion evidence;
- documentation is updated when behavior/operations changed.

## Current project constraints

- Preserve structured deliberation semantics: `Claim`, `Challenge`, `Evidence`, `Rebuttal`, `Revision`, `Consensus`.
- Do not replace compound consensus with simple majority voting.
- Critical unresolved objections must prevent normal consensus.
- Do not treat model-generated text as external evidence.
- Keep OpenTelemetry/OpenInference vendor-neutral; Phoenix is the first backend, not the instrumentation contract.
- Do not store hidden chain-of-thought; store structured decisions, concise reason summaries, evidence references, confidence changes, and routing outcomes.
- Do not add complex agent strategies before the benchmark phase proves the baseline.

## Handoff protocol

A new agent/session must first read, in order:

1. `AGENTS.md`
2. `docs/TASKS.md`
3. `docs/EXECUTION_PLAN.md`
4. `docs/design/multi-agent-deliberation-system-design-v1.0.md`
5. the relevant file under `docs/plans/`, if one exists for the active task
6. `docs/observability.md` when observability is involved

Then review the active task critically before editing code. If the active plan has a critical gap, update/resolve the plan rather than improvising around it.
