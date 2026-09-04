from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .config import RuntimeSettings
from .evidence import NullEvidenceProvider
from .factory import build_llm_agents
from .graph import DeliberationConfig, build_deliberation_graph
from .observability import configure_phoenix
from .workspace import (
    WorkspaceEvidenceProvider,
    apply_unified_diff,
    build_vibe_question,
    extract_unified_diff,
    load_workspace_files,
)


def _add_runtime_budget_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--max-tool-calls", type=int, default=24)
    parser.add_argument("--json", action="store_true", dest="json_output")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evidence-grounded multi-agent deliberation and vibe coding"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="deliberate on a general question")
    ask.add_argument("question")
    _add_runtime_budget_args(ask)

    vibe = subparsers.add_parser(
        "vibe",
        help="deliberate on a coding task using user-selected workspace files as evidence",
    )
    vibe.add_argument("question", help="natural-language coding task")
    vibe.add_argument(
        "--file",
        action="append",
        default=[],
        dest="files",
        help="workspace file or directory to include; repeat for multiple inputs",
    )
    vibe.add_argument("--root", default=".", help="workspace root used to constrain file access")
    vibe.add_argument(
        "--patch-out",
        help="write the final fenced unified diff to this path without applying it",
    )
    vibe.add_argument(
        "--apply",
        action="store_true",
        dest="apply_patch",
        help="validate with git apply --check, then apply the final unified diff",
    )
    _add_runtime_budget_args(vibe)
    return parser


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] not in {"ask", "vibe", "-h", "--help"}:
        args = ["ask", *args]
    return _build_parser().parse_args(args)


def _build_config(args: argparse.Namespace, settings: RuntimeSettings) -> DeliberationConfig:
    if args.max_rounds < 0:
        raise ValueError("--max-rounds must be >= 0")
    if args.max_tool_calls < 0:
        raise ValueError("--max-tool-calls must be >= 0")
    return DeliberationConfig(
        max_rounds=args.max_rounds,
        max_tool_calls=args.max_tool_calls,
        agent_timeout_seconds=settings.agent_timeout_seconds,
    )


async def _run(args: argparse.Namespace) -> int:
    try:
        settings = RuntimeSettings.from_env()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not settings.api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    configure_phoenix()
    mode = args.command
    try:
        agents = build_llm_agents(settings, mode=mode)
        config = _build_config(args, settings)
        if mode == "vibe":
            documents = load_workspace_files(args.files, root=args.root)
            question = build_vibe_question(args.question, documents)
            evidence_provider = (
                WorkspaceEvidenceProvider(documents) if documents else NullEvidenceProvider()
            )
        else:
            question = args.question
            evidence_provider = NullEvidenceProvider()
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    graph = build_deliberation_graph(agents, evidence_provider, config)
    try:
        state = await graph.ainvoke({"question": question})
    except Exception as exc:
        print(f"deliberation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    result = state["final_result"]
    if args.json_output:
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        print(result.answer)
        print(
            "\n---\n"
            f"consensus={result.consensus.reached} "
            f"agreement={result.consensus.agreement_ratio:.2f} "
            f"rounds={result.rounds} "
            f"stop={result.consensus.stop_reason}",
            file=sys.stderr,
        )

    if mode == "vibe" and (args.patch_out or args.apply_patch):
        patch = extract_unified_diff(result.answer)
        if not patch:
            print("final answer does not contain a unified diff", file=sys.stderr)
            return 3
        if args.patch_out:
            patch_path = Path(args.patch_out)
            patch_path.parent.mkdir(parents=True, exist_ok=True)
            patch_path.write_text(patch + "\n", encoding="utf-8")
            print(f"patch written to {patch_path}", file=sys.stderr)
        if args.apply_patch:
            try:
                apply_unified_diff(patch, root=args.root)
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"patch not applied: {exc}", file=sys.stderr)
                return 4
            print("patch applied successfully", file=sys.stderr)
    return 0


def main() -> None:
    args = parse_cli_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
