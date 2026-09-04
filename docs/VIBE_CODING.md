# Vibe Coding User Guide

IE Copilot can use three independent engineering agents to deliberate on a coding task, challenge each other's claims, retrieve evidence from user-selected source files, revise their positions, and return an implementation-ready answer.

## 1. Configure an OpenAI-compatible endpoint

```bash
cp .env.example .env
export OPENAI_API_KEY=your-key
export OPENAI_MODEL=your-model
export OPENAI_BASE_URL=http://localhost:8000/v1   # optional
```

The endpoint only needs to be compatible with the LangChain/OpenAI chat API used by `ChatOpenAI` and support the configured model.

## 2. Ask a general question

Legacy syntax remains valid:

```bash
uv run ie-copilot "Should this service use PostgreSQL or Elasticsearch?"
```

Equivalent explicit syntax:

```bash
uv run ie-copilot ask "Should this service use PostgreSQL or Elasticsearch?"
```

## 3. Vibe-code against selected files

Single file:

```bash
uv run ie-copilot vibe \
  "Add bounded retry with exponential backoff and tests" \
  --file src/client.py \
  --file tests/unit/test_client.py
```

Directory selection is supported. Only recognized text/code files are included; `.git`, `.venv`, `node_modules`, `dist`, `build`, and `target` are ignored.

```bash
uv run ie-copilot vibe \
  "Refactor request retries without changing the public API" \
  --file src \
  --file tests/unit
```

All paths are constrained by `--root` (default: current directory). A path outside the root is rejected.

## 4. Save a generated patch

```bash
uv run ie-copilot vibe \
  "Fix the timeout bug and add regression coverage" \
  --file src \
  --file tests/unit \
  --patch-out /tmp/ie-copilot.patch
```

This writes the final fenced unified diff but does not modify the repository.

## 5. Explicitly apply the patch

```bash
uv run ie-copilot vibe \
  "Fix the timeout bug and add regression coverage" \
  --file src \
  --file tests/unit \
  --apply
```

`--apply` is deliberately opt-in. Before modifying the workspace IE Copilot:

1. extracts the final `diff --git` patch;
2. rejects absolute paths and `..` traversal;
3. runs `git apply --check -`;
4. only if the check succeeds, runs `git apply -`.

It does **not** commit, push, delete branches, or bypass Git's patch validation.

## 6. Inspect the complete deliberation trace

```bash
uv run ie-copilot vibe \
  "Fix the race condition" \
  --file src \
  --json
```

JSON output includes proposals, claim clusters, position clusters, debate queue, challenges, evidence, revisions, position snapshots, failures, and consensus metadata.

## 7. Tune budgets

```bash
uv run ie-copilot vibe \
  "Implement the feature" \
  --file src \
  --max-rounds 3 \
  --max-tool-calls 12
```

Environment controls:

```text
IE_TEMPERATURE
IE_AGENT_TIMEOUT_SECONDS
IE_STRUCTURED_OUTPUT_RETRIES
```

Structured-output retries only cover parser/schema failures; runtime/network failures are not retried indefinitely.

## 8. How the three coding agents differ

- **Implementer** — minimizes the change surface and produces an actionable implementation.
- **Adversarial reviewer** — searches for correctness, security, concurrency, API, and regression problems.
- **Test/reliability engineer** — constrains the proposal with deterministic tests, failure cases, observability, and rollback behavior.

They solve independently before debate. Initial disagreement cannot terminate as consensus without at least one debate round.

## 9. Workspace evidence model

Only user-selected files are treated as repository evidence. During debate, a challenge can request evidence; the workspace provider performs deterministic keyword matching and returns line-numbered snippets with `workspace://...` provenance.

Model-generated text is never silently promoted to external evidence.

## 10. Recommended workflow

```text
natural-language requirement
  -> vibe with relevant source/test directories
  -> inspect answer + consensus metadata
  -> save patch
  -> review patch
  -> optionally --apply
  -> run your repository's own tests
  -> commit normally with Git
```

For high-risk changes, prefer `--patch-out` first rather than immediate `--apply`.
