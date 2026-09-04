from __future__ import annotations

from .agents import LLMDebateAgent
from .config import RuntimeSettings
from .prompts import GENERAL_OBJECTIVES, VIBE_OBJECTIVES


def build_llm_agents(
    settings: RuntimeSettings,
    *,
    mode: str = "ask",
) -> list[LLMDebateAgent]:
    if not settings.api_key:
        raise ValueError("OPENAI_API_KEY is required")
    objectives = VIBE_OBJECTIVES if mode == "vibe" else GENERAL_OBJECTIVES
    return [
        LLMDebateAgent.from_openai_compatible(
            agent_id=f"agent-{index + 1}",
            objective=objective,
            model_name=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url,
            temperature=settings.temperature,
            mode=mode,
            structured_output_retries=settings.structured_output_retries,
        )
        for index, objective in enumerate(objectives)
    ]
