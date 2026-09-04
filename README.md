# IE Copilot — Evidence-Grounded Multi-Agent Deliberation

A LangGraph MVP for multi-agent deliberation where agents solve independently, challenge conflicting claims, gather evidence, revise positions, and stop only when the consensus policy is satisfied.

## Start here

Before changing the architecture or implementation, read these documents in order:

1. [`AGENTS.md`](AGENTS.md) — mandatory Superpowers development workflow, TDD/debugging/verification rules, and handoff protocol.
2. [`docs/TASKS.md`](docs/TASKS.md) — **live task board and single source of truth for current execution status**.
3. [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md) — phased roadmap, acceptance gates, and Definition of Done.
4. [`docs/design/multi-agent-deliberation-system-design-v1.0.md`](docs/design/multi-agent-deliberation-system-design-v1.0.md) — architecture baseline, rationale, lifecycle, consensus rules, boundaries, and ADR summary.
5. [`docs/observability.md`](docs/observability.md) — OpenTelemetry/OpenInference and `debate.*` observability conventions.

`docs/TASKS.md` answers **what is being done now and what is actually complete**. `docs/EXECUTION_PLAN.md` answers **what phase comes next and what gate must be satisfied**. The design document answers **why the system is shaped this way**.

All non-trivial implementation follows Superpowers: design/brainstorm when needed → isolated workspace → written plan → TDD execution → review → verification → branch completion. Task status must be updated continuously, not reconstructed after the work is over.

## Why this design

This project deliberately avoids a free-form "agents chatting until a majority agrees" loop. The runtime separates independent solving from debate and uses structured domain objects:

- `Claim`
- `Challenge`
- `Evidence`
- `Revision`
- `ConsensusResult`

A conflicting initial majority is **not** allowed to terminate immediately. At least one debate round is required when positions disagree. Consensus requires the configured agreement threshold, sufficient evidence for unresolved evidence requests, and zero unresolved critical objections. Hard round/tool budgets prevent infinite epistemic loops.

## Runtime flow

```text
START
  |
  v
solve (agents run concurrently)
  |
  v
assess ---------------------> finalize -> END
  |                              ^
  | continue                     |
  v                              |
begin_round                      |
  |                              |
  v                              |
critique (concurrent)            |
  |                              |
  v                              |
gather_evidence (concurrent)     |
  |                              |
  v                              |
revise (concurrent)              |
  |                              |
  +-----------> assess ----------+
```

## Observability

The project uses OpenTelemetry/OpenInference conventions instead of building a tracing platform from scratch. Phoenix is opt-in and LangGraph/LangChain instrumentation is enabled with `auto_instrument=True`.

Custom deliberation semantics are attached as `debate.*` span attributes, including:

```text
debate.agent.id
debate.round
debate.challenge.id
debate.challenge.target
debate.revision.from
debate.revision.to
debate.confidence.before
debate.confidence.after
debate.consensus.agreement
debate.consensus.entropy
debate.consensus.evidence_sufficiency
debate.consensus.critical_objections
debate.consensus.reached
debate.consensus.stop_reason
```

Phoenix has first-class LangGraph support through the OpenInference LangChain instrumentor, so graph/LLM/tool spans remain standard while the project only owns its domain semantics.

## Quick start

Requirements: Python 3.10+ and `uv`.

```bash
uv sync --extra dev
cp .env.example .env
```

Set an OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://your-endpoint/v1   # optional
export OPENAI_MODEL=your-model
```

Run:

```bash
uv run ie-copilot "Which database should this workload use, and why?"
```

### Phoenix tracing

Start local Phoenix:

```bash
docker compose up -d phoenix
```

Then enable tracing:

```bash
export PHOENIX_ENABLED=true
export PHOENIX_PROJECT_NAME=ie-copilot
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

Phoenix UI is available on port `6006`.

## Evidence backends

The graph depends on the `EvidenceProvider` protocol, not a specific search/RAG vendor. `NullEvidenceProvider` is intentionally explicit and returns quality `0.0`; production should inject a RAG/search/tool-backed provider using `CallableEvidenceProvider` or a custom implementation.

This prevents the system from pretending model-generated text is external evidence.

## Consensus policy

Default MVP policy:

```text
agreement >= 0.67
evidence sufficiency >= 0.75
unresolved critical objections == 0
max rounds = 3
max evidence/tool calls = 24
```

Unanimous independent answers can finish at round 0. Any initial disagreement forces a debate round before consensus can be accepted.

## Tests

```bash
uv run pytest
uv run ruff check .
```

The suite covers:

- unanimous fast-path
- initial-majority-but-conflicting answers still entering debate
- evidence-driven position revision
- critical objection blocking majority consensus
- Pydantic confidence validation and runtime claim IDs

CI runs the suite on Python 3.10 and 3.13.

## Project structure

```text
src/ie_copilot/
  agents.py          OpenAI-compatible structured-output agents
  evidence.py        evidence provider adapters
  graph.py           LangGraph state machine and consensus policy
  models.py          claim/challenge/evidence/revision schemas
  observability.py   Phoenix + OpenTelemetry configuration
  protocols.py       agent/evidence interfaces
  cli.py             runnable MVP

tests/
.github/workflows/ci.yml
```

## Next increments

The MVP intentionally stops before adding vendor-specific retrieval. Recommended next steps are claim semantic clustering, evidence deduplication/source trust scoring, persistent checkpoints, human review for unresolved critical objections, and Phoenix evaluators for false-consensus and useful-revision metrics.
