from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSettings:
    api_key: str | None
    model: str = "gpt-5-mini"
    base_url: str | None = None
    temperature: float = 0.1
    agent_timeout_seconds: float = 60.0
    structured_output_retries: int = 1

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RuntimeSettings:
        source = os.environ if env is None else env
        temperature = float(source.get("IE_TEMPERATURE", "0.1"))
        timeout = float(source.get("IE_AGENT_TIMEOUT_SECONDS", "60"))
        retries = int(source.get("IE_STRUCTURED_OUTPUT_RETRIES", "1"))
        if timeout <= 0:
            raise ValueError("IE_AGENT_TIMEOUT_SECONDS must be > 0")
        if retries < 0:
            raise ValueError("IE_STRUCTURED_OUTPUT_RETRIES must be >= 0")
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("IE_TEMPERATURE must be between 0 and 2")
        return cls(
            api_key=source.get("OPENAI_API_KEY") or None,
            model=source.get("OPENAI_MODEL", "gpt-5-mini"),
            base_url=source.get("OPENAI_BASE_URL") or None,
            temperature=temperature,
            agent_timeout_seconds=timeout,
            structured_output_retries=retries,
        )
