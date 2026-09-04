# Implementation Plans

This directory stores task-specific implementation plans created under the Superpowers `writing-plans` workflow.

## Naming

Use:

```text
YYYY-MM-DD-<task-id>-<short-name>.md
```

Example:

```text
2026-09-04-P1-01-ci-root-cause-plan.md
```

## Required plan content

Each non-trivial plan should contain:

- linked task ID from `docs/TASKS.md`;
- problem/goal and acceptance criteria;
- exact files to inspect/modify/create;
- bite-sized ordered steps;
- RED test or reproduction step when applicable;
- expected failure evidence;
- minimal implementation step;
- GREEN verification command;
- regression/lint verification;
- review checkpoint;
- completion evidence to write back to `docs/TASKS.md`;
- rollback/stop conditions when relevant.

The plan does not own execution state. `docs/TASKS.md` remains the live status source.
