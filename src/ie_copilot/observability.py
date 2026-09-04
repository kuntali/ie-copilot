from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry import trace


@dataclass(frozen=True)
class PhoenixSettings:
    enabled: bool = False
    project_name: str = "ie-copilot"
    endpoint: str = "http://localhost:6006/v1/traces"

    @classmethod
    def from_env(cls) -> PhoenixSettings:
        return cls(
            enabled=os.getenv("PHOENIX_ENABLED", "false").lower() in {"1", "true", "yes"},
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "ie-copilot"),
            endpoint=os.getenv(
                "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"
            ),
        )


def configure_phoenix(settings: PhoenixSettings | None = None) -> Any | None:
    """Configure Phoenix/OpenInference instrumentation when explicitly enabled."""
    settings = settings or PhoenixSettings.from_env()
    if not settings.enabled:
        return None

    from phoenix.otel import register

    return register(
        project_name=settings.project_name,
        endpoint=settings.endpoint,
        batch=True,
        auto_instrument=True,
    )


def _clean_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in attributes.items():
        if value is None:
            continue
        if isinstance(value, (str, bool, int, float)):
            clean[key] = value
        elif isinstance(value, (list, tuple)) and all(
            isinstance(item, (str, bool, int, float)) for item in value
        ):
            clean[key] = list(value)
        else:
            clean[key] = str(value)
    return clean


@contextmanager
def debate_span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    tracer = trace.get_tracer("ie_copilot.deliberation")
    with tracer.start_as_current_span(name) as span:
        span.set_attributes(_clean_attributes(attributes))
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise
