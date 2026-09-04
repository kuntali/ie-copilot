from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from .agents import LLMDebateAgent
from .evidence import NullEvidenceProvider
from .graph import DeliberationConfig, build_deliberation_graph
from .observability import configure_phoenix


OBJECTIVES = [
    "maximize factual correctness and make assumptions explicit",
    "actively falsify weak assumptions and search for counterexamples",
    "develop a genuinely independent alternative hypothesis before converging",
]


async def _run(question: str) -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    configure_phoenix()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    base_url = os.getenv("OPENAI_BASE_URL") or None

    agents = [
        LLMDebateAgent.from_openai_compatible(
            agent_id=f"agent-{index + 1}",
            objective=objective,
            model_name=model,
            api_key=api_key,
            base_url=base_url,
        )
        for index, objective in enumerate(OBJECTIVES)
    ]
    graph = build_deliberation_graph(
        agents,
        NullEvidenceProvider(),
        DeliberationConfig(),
    )
    state = await graph.ainvoke({"question": question})
    print(json.dumps(state["final_result"].model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the multi-agent deliberation MVP")
    parser.add_argument("question", help="Question all agents should independently solve")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.question)))


if __name__ == "__main__":
    main()
