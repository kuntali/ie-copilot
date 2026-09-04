from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.exceptions import OutputParserException

from ie_copilot.agents import LLMDebateAgent
from ie_copilot.cli import parse_cli_args
from ie_copilot.config import RuntimeSettings
from ie_copilot.models import Challenge, Severity
from ie_copilot.workspace import (
    WorkspaceEvidenceProvider,
    extract_unified_diff,
    load_workspace_files,
)


def test_runtime_settings_parse_environment() -> None:
    settings = RuntimeSettings.from_env(
        {
            "OPENAI_API_KEY": "k",
            "OPENAI_MODEL": "model-x",
            "OPENAI_BASE_URL": "http://localhost:8000/v1",
            "IE_TEMPERATURE": "0.2",
            "IE_AGENT_TIMEOUT_SECONDS": "12.5",
            "IE_STRUCTURED_OUTPUT_RETRIES": "2",
        }
    )
    assert settings.api_key == "k"
    assert settings.model == "model-x"
    assert settings.temperature == 0.2
    assert settings.agent_timeout_seconds == 12.5
    assert settings.structured_output_retries == 2


def test_cli_supports_legacy_ask_and_vibe_modes() -> None:
    legacy = parse_cli_args(["why postgres?"])
    ask = parse_cli_args(["ask", "why postgres?"])
    vibe = parse_cli_args(["vibe", "fix bug", "--file", "src/a.py"])

    assert legacy.command == "ask"
    assert ask.command == "ask"
    assert vibe.command == "vibe"
    assert vibe.files == ["src/a.py"]


def test_workspace_provider_reads_explicit_files_and_returns_matching_snippet(
    tmp_path: Path,
) -> None:
    source = tmp_path / "service.py"
    source.write_text("def retry_request():\n    return 'retry budget'\n", encoding="utf-8")
    docs = load_workspace_files([str(source)], root=tmp_path)
    provider = WorkspaceEvidenceProvider(docs)
    challenge = Challenge(
        id="chl:r1:a:0",
        challenger_agent_id="a",
        target_agent_id="b",
        round=1,
        target_claim_id="clm:b:r0:0",
        reason="verify retry behavior",
        evidence_request="retry budget",
        severity=Severity.HIGH,
    )

    evidence = pytest.run(async_fn=provider.gather("q", challenge))

    assert evidence.source.endswith("service.py")
    assert "retry budget" in evidence.content
    assert evidence.quality > 0.0


def test_extract_unified_diff_from_fenced_answer() -> None:
    answer = """Plan\n```diff\ndiff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@\n-old\n+new\n```\nTests"""
    patch = extract_unified_diff(answer)
    assert patch.startswith("diff --git")
    assert "+new" in patch


class RetryModel:
    def __init__(self) -> None:
        self.calls = 0

    def with_structured_output(self, schema):
        outer = self

        class Runnable:
            async def ainvoke(self, messages):
                outer.calls += 1
                if outer.calls == 1:
                    raise OutputParserException("bad structured output")
                return schema(
                    position="X",
                    claims=[{"statement": "claim", "confidence": 0.8}],
                    final_answer="answer",
                    confidence=0.8,
                )

        return Runnable()


@pytest.mark.asyncio
async def test_structured_output_parse_failure_retries_within_budget() -> None:
    model = RetryModel()
    agent = LLMDebateAgent(
        agent_id="a",
        model=model,
        objective="correct",
        structured_output_retries=1,
    )

    proposal = await agent.solve("q")

    assert proposal.position == "X"
    assert model.calls == 2
