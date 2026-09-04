# Deliberation Observability Convention

The application uses standard OpenTelemetry/OpenInference traces for runtime mechanics and reserves the `debate.*` namespace for domain semantics.

## Principles

1. **Do not store hidden chain-of-thought.** Store claims, decisions, concise reasons, evidence references, confidence changes, and routing outcomes.
2. **Preserve causality.** Revision spans identify the agent, round, before/after position, and before/after confidence. Evidence spans identify the challenge they answer.
3. **Keep tracing vendor-neutral.** Phoenix is the first backend, not the instrumentation contract.
4. **Replay from durable domain data.** Production persistence should retain the structured final state and event/artifact references separately from the tracing backend.

## Span hierarchy

```text
LangGraph invocation
├── solve
│   ├── debate.agent.solve [agent-1]
│   ├── debate.agent.solve [agent-2]
│   └── debate.agent.solve [agent-3]
├── assess
│   └── debate.consensus.check
├── critique
│   ├── debate.agent.critique [agent-1]
│   └── ...
├── gather_evidence
│   └── debate.evidence.retrieve [challenge-id]
├── revise
│   ├── debate.agent.revise [agent-1]
│   └── ...
└── assess
    └── debate.consensus.check
```

## Required custom attributes

| Attribute | Meaning |
| --- | --- |
| `debate.agent.id` | Stable agent identity within a run |
| `debate.round` | Debate round, with independent solve as 0 |
| `debate.challenge.id` | Challenge identifier |
| `debate.challenge.target` | Target claim identifier |
| `debate.revision.from` | Position before revision |
| `debate.revision.to` | Position after revision |
| `debate.confidence.before` | Confidence before revision |
| `debate.confidence.after` | Confidence after revision |
| `debate.consensus.agreement` | Dominant-position share |
| `debate.consensus.entropy` | Distribution entropy of positions |
| `debate.consensus.evidence_sufficiency` | Share of unresolved evidence requests with good evidence |
| `debate.consensus.critical_objections` | Unresolved critical challenges |
| `debate.consensus.reached` | Whether the compound stop policy passed |
| `debate.consensus.stop_reason` | consensus/unanimous/budget/continue |
