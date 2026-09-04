from __future__ import annotations

from collections.abc import Awaitable, Callable

from .models import Challenge, Evidence


class NullEvidenceProvider:
    """Explicit fallback: records that no external evidence backend is configured."""

    async def gather(self, question: str, challenge: Challenge) -> Evidence:
        return Evidence(
            challenge_id=challenge.id,
            source="unconfigured",
            content="No external evidence provider is configured.",
            quality=0.0,
            supports_target_claim=None,
        )


class CallableEvidenceProvider:
    """Adapter for RAG/search/tool functions without coupling the graph to a vendor."""

    def __init__(
        self,
        fn: Callable[[str, Challenge], Awaitable[Evidence]],
    ) -> None:
        self._fn = fn

    async def gather(self, question: str, challenge: Challenge) -> Evidence:
        return await self._fn(question, challenge)
