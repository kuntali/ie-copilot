# IE Copilot — Evidence-Grounded Multi-Agent Vibe Coding

IE Copilot is a LangGraph-based multi-agent deliberation runtime that can be used as a practical coding copilot: independent engineering agents propose solutions, challenge conflicting claims, retrieve evidence from user-selected source files, revise their positions, and produce an implementation-ready answer or unified diff.

It deliberately avoids the fragile pattern of "several agents free-chat until a majority agrees". Claims, challenges, evidence, revisions, position snapshots, and consensus are structured first-class objects.

## Vibe coding in 60 seconds

Requirements: Python 3.10+ and `uv`.

```bash
uv sync --extra dev
cp .env.example .env
```

Configure any OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=your-model
export OPENAI_BASE_URL=https://your-endpoint/v1   # optional
```

Ask IE Copilot to change selected code:

```bash
uv run ie-copilot vibe \
  "Add bounded retry with exponential backoff and regression tests" \
  --file src \
  --file tests/unit
```

Save the final diff without touching the worktree:

```bash
uv run ie-copilot vibe \
  "Fix the timeout bug and add regression coverage" \
  --file src \
  --file tests/unit \
  --patch-out /tmp/ie-copilot.patch
```

Explicitly apply a generated patch:

```bash
uv run ie-copilot vibe \
  "Fix the timeout bug and add regression coverage" \
  --file src \
  --file tests/unit \
  --apply
```

`--apply` is opt-in. IE Copilot rejects unsafe patch paths, runs `git apply --check -`, and only applies the patch if validation succeeds. It does not commit or push.

Full usage and safety model: [`docs/VIBE_CODING.md`](docs/VIBE_CODING.md).

## Three engineering roles

The default vibe panel contains three independent agents:

1. **Implementer** — minimizes the change surface and produces an actionable implementation.
2. **Adversarial reviewer** — attacks correctness, security, concurrency, API, and regression assumptions.
3. **Test/reliability engineer** — constrains the proposal with deterministic tests, failure cases, observability, and rollback behavior.

They solve independently before seeing one another's proposals. Initial disagreement forces at least one debate round.

## Workspace evidence

`--file` accepts files or directories. Only the user-selected workspace is available as repository evidence. Common build/vendor directories such as `.git`, `.venv`, `node_modules`, `dist`, `build`, and `target` are ignored when a directory is selected.

During debate an agent can request evidence for a disputed claim. `WorkspaceEvidenceProvider` performs deterministic matching and returns line-numbered snippets with `workspace://...` provenance. Model-generated prose is never silently treated as external evidence.

All selected paths are constrained by `--root` (default: current directory), and paths outside the root are rejected.

## General deliberation mode

The original question-answer mode remains available:

```bash
uv run ie-copilot "Which database should this workload use, and why?"
```

Equivalent explicit syntax:

```bash
uv run ie-copilot ask "Which database should this workload use, and why?"
```

## Runtime protocol

```text
START
  |
  v
solve concurrently
  |
  +--> deterministic Claim occurrence IDs
  +--> ClaimCluster / PositionCluster
  +--> explicit debate_queue
  +--> PositionSnapshot(round=0)
  |
  v
assess -------------------------------> finalize -> END
  |                                         ^
  | continue                                |
  v                                         |
begin_round                                 |
  |                                         |
  v                                         |
critique only queued conflict claims        |
  |                                         |
  v                                         |
gather evidence concurrently                |
  |                                         |
  v                                         |
revise: maintain/weaken/revise/abandon      |
  |                                         |
  +--> provenance + snapshot + clusters ----+
  |
  +---------------------> assess
```

### Core invariants

- `Claim.id` identifies one claim occurrence, not semantic equivalence.
- Cross-agent equivalent claims are represented by `ClaimCluster`.
- Positions are clustered independently by `PositionCluster`.
- Challenges must target an existing claim selected by the conflict surface.
- Evidence is bound to a target claim and `supports / attacks / neutral` relation.
- Revisions record before/after position, claim IDs, trigger challenges, evidence refs, and action.
- Consensus is computed from structured positions/evidence/objections, not answer wording.
- Deterministic fake-agent runs can be replayed with stable semantic signatures.

## Consensus policy

Default policy:

```text
agreement >= 0.67
evidence sufficiency >= 0.75
unresolved critical objections == 0
max rounds = 3
max tool/evidence calls = 24
```

Unanimous independent answers can finish at round 0. Any initial position conflict must debate before consensus is accepted.

## Structured-output reliability

The OpenAI-compatible agent uses Pydantic structured outputs. Parser/schema failures have a bounded retry budget configured by:

```text
IE_STRUCTURED_OUTPUT_RETRIES=1
```

Runtime/network failures are not retried indefinitely. Agent calls are isolated, time-bounded, and recorded as structured failures when the remaining quorum can continue.

## JSON/replay view

Use `--json` to inspect the full deliberation result:

```bash
uv run ie-copilot vibe "Fix the race" --file src --json
```

The result includes proposals, claim clusters, position clusters, debate queue, challenges, evidence, revisions, snapshots, failures, and consensus metadata.

## Phoenix / OpenTelemetry

Phoenix tracing is optional:

```bash
docker compose up -d phoenix
export PHOENIX_ENABLED=true
export PHOENIX_PROJECT_NAME=ie-copilot
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

The runtime keeps standard LangGraph/LangChain/OpenInference spans and adds `debate.*` semantic attributes for agent, round, challenge, evidence/revision, confidence, and consensus decisions. Hidden chain-of-thought is not required for observability.

See [`docs/observability.md`](docs/observability.md).

## Tests

Default tests are deterministic unit tests and require no model/API/service:

```bash
uv run pytest
uv run ruff check .
```

Physical and marker isolation:

```text
tests/unit/         default PR suite
tests/integration/ explicit integration tests
tests/e2e/         explicit live-system tests
```

CI runs lockfile verification, frozen dependency installation, Ruff, and unit tests on Python 3.10 and 3.13.

## Runtime settings

```text
OPENAI_API_KEY
OPENAI_MODEL
OPENAI_BASE_URL
IE_TEMPERATURE
IE_AGENT_TIMEOUT_SECONDS
IE_STRUCTURED_OUTPUT_RETRIES
PHOENIX_ENABLED
PHOENIX_PROJECT_NAME
PHOENIX_COLLECTOR_ENDPOINT
```

See [`.env.example`](.env.example).

## Project structure

```text
src/ie_copilot/
  agents.py          versioned structured-output LLM agents
  config.py          runtime environment settings
  factory.py         ask/vibe agent factory
  graph.py           LangGraph protocol and consensus policy
  models.py          domain/protocol schemas
  normalization.py   deterministic claim/position clustering
  evidence.py        generic evidence adapters
  workspace.py       workspace context, evidence, patch safety/apply
  replay.py          deterministic semantic replay signature
  observability.py   Phoenix/OpenTelemetry configuration
  prompts.py         versioned ask/vibe prompts and epistemic roles
  protocols.py       agent/evidence interfaces
  cli.py             ask/vibe command line interface
```

## Engineering docs

1. [`AGENTS.md`](AGENTS.md) — mandatory Superpowers/TDD workflow.
2. [`docs/TASKS.md`](docs/TASKS.md) — live execution state.
3. [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md) — phased gates/roadmap.
4. [`docs/design/multi-agent-deliberation-system-design-v1.0.md`](docs/design/multi-agent-deliberation-system-design-v1.0.md) — architecture rationale.
5. [`docs/VIBE_CODING.md`](docs/VIBE_CODING.md) — end-user coding workflow.
