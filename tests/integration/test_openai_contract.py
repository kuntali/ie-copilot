from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ie_copilot.config import RuntimeSettings
from ie_copilot.evidence import NullEvidenceProvider
from ie_copilot.factory import build_llm_agents
from ie_copilot.graph import DeliberationConfig, build_deliberation_graph


def _schema_properties(payload: dict) -> dict:
    tools = payload.get("tools") or []
    if tools:
        return tools[0]["function"]["parameters"].get("properties", {})
    response_format = payload.get("response_format") or {}
    json_schema = response_format.get("json_schema") or {}
    return (json_schema.get("schema") or {}).get("properties", {})


def _structured_payload(request: dict) -> dict:
    properties = _schema_properties(request)
    messages = request.get("messages") or []
    system = " ".join(
        str(message.get("content", ""))
        for message in messages
        if message.get("role") == "system"
    )
    human = next(
        (
            str(message.get("content", ""))
            for message in reversed(messages)
            if message.get("role") == "user"
        ),
        "",
    )

    if "challenges" in properties:
        return {"challenges": []}

    if "reason" in properties and "resolved_challenge_ids" in properties:
        try:
            context = json.loads(human)
            previous = context["proposal"]["position"]
        except (KeyError, TypeError, json.JSONDecodeError):
            previous = "X"
        return {
            "action": "revise" if previous.casefold().strip() != "x" else "maintain",
            "position": "X",
            "claims": [{"statement": "contract agent supports X", "confidence": 0.9}],
            "final_answer": "Implementation Plan\nUse X.\n\nTests\nRun the contract test.",
            "confidence": 0.9,
            "reason": "contract revision",
            "evidence_refs": [],
            "resolved_challenge_ids": [],
        }

    position = "Y" if "adversarial code reviewer" in system else "X"
    return {
        "position": position,
        "claims": [{"statement": f"contract agent supports {position}", "confidence": 0.8}],
        "assumptions": [],
        "uncertainties": [],
        "final_answer": f"Implementation Plan\nUse {position}.",
        "confidence": 0.8,
    }


class _OpenAIContractHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:
        return

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        structured = _structured_payload(request)
        tools = request.get("tools") or []
        if tools:
            tool_name = tools[0]["function"]["name"]
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_contract",
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(structured),
                        },
                    }
                ],
            }
            finish_reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": json.dumps(structured)}
            finish_reason = "stop"
        body = json.dumps(
            {
                "id": "chatcmpl-contract",
                "object": "chat.completion",
                "created": 1,
                "model": request.get("model", "contract-model"),
                "choices": [
                    {
                        "index": 0,
                        "message": message,
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.mark.asyncio
async def test_chatopenai_contract_runs_full_conflict_revision_consensus() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAIContractHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        settings = RuntimeSettings(
            api_key="test-key",
            model="contract-model",
            base_url=f"http://{host}:{port}/v1",
            temperature=0.0,
            agent_timeout_seconds=5.0,
            structured_output_retries=0,
        )
        agents = build_llm_agents(settings, mode="vibe")
        graph = build_deliberation_graph(
            agents,
            NullEvidenceProvider(),
            DeliberationConfig(max_rounds=2, agent_timeout_seconds=5.0),
        )

        state = await graph.ainvoke({"question": "Implement the contract feature"})
        result = state["final_result"]

        assert result.rounds == 1
        assert result.consensus.reached is True
        assert result.consensus.agreement_ratio == 1.0
        assert len(result.position_snapshots) == 2
        assert any(revision.new_position == "X" for revision in result.revisions)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
