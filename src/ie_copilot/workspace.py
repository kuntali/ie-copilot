from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import Challenge, Evidence

_TOKEN_RE = re.compile(r"[\w.-]+", re.UNICODE)
_DIFF_RE = re.compile(r"```diff\s*\n(?P<diff>.*?)(?:\n```)", re.DOTALL)


@dataclass(frozen=True)
class WorkspaceDocument:
    path: str
    content: str


def load_workspace_files(
    paths: list[str],
    *,
    root: str | Path = ".",
    max_bytes_per_file: int = 200_000,
) -> list[WorkspaceDocument]:
    root_path = Path(root).resolve()
    documents: list[WorkspaceDocument] = []
    for raw_path in paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = root_path / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root_path)
        except ValueError as exc:
            raise ValueError(f"workspace file is outside root: {raw_path}") from exc
        if not resolved.is_file():
            raise FileNotFoundError(raw_path)
        data = resolved.read_bytes()
        if len(data) > max_bytes_per_file:
            raise ValueError(f"workspace file exceeds size limit: {raw_path}")
        content = data.decode("utf-8")
        documents.append(
            WorkspaceDocument(
                path=resolved.relative_to(root_path).as_posix(),
                content=content,
            )
        )
    return documents


def render_workspace_context(
    documents: list[WorkspaceDocument], *, max_chars: int = 80_000
) -> str:
    chunks: list[str] = []
    used = 0
    for document in documents:
        chunk = f"# FILE: {document.path}\n{document.content}\n"
        remaining = max_chars - used
        if remaining <= 0:
            break
        chunks.append(chunk[:remaining])
        used += min(len(chunk), remaining)
    return "\n".join(chunks)


def build_vibe_question(request: str, documents: list[WorkspaceDocument]) -> str:
    context = render_workspace_context(documents)
    if not context:
        return (
            f"Software task:\n{request}\n\n"
            "No workspace files were supplied. Make assumptions explicit and do not invent "
            "repository-specific file paths or symbols."
        )
    return (
        f"Software task:\n{request}\n\n"
        "Use only the following user-selected workspace context as repository evidence:\n\n"
        f"{context}"
    )


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(value) if len(token) >= 2}


class WorkspaceEvidenceProvider:
    def __init__(self, documents: list[WorkspaceDocument], *, window_lines: int = 12) -> None:
        self.documents = documents
        self.window_lines = window_lines

    async def gather(self, question: str, challenge: Challenge) -> Evidence:
        query = challenge.evidence_request or challenge.reason or question
        query_tokens = _tokens(query)
        best: tuple[int, WorkspaceDocument, int] | None = None
        for document in self.documents:
            lines = document.content.splitlines()
            for index, line in enumerate(lines):
                score = len(query_tokens & _tokens(line))
                if best is None or score > best[0]:
                    best = (score, document, index)

        if best is None:
            return Evidence(
                challenge_id=challenge.id,
                source="workspace://empty",
                content="No user-selected workspace document is available.",
                quality=0.0,
                supports_target_claim=None,
            )

        score, document, index = best
        lines = document.content.splitlines()
        radius = max(1, self.window_lines // 2)
        start = max(0, index - radius)
        end = min(len(lines), index + radius + 1)
        numbered = [f"{line_no + 1}: {lines[line_no]}" for line_no in range(start, end)]
        quality = min(0.95, 0.35 + 0.15 * score) if score else 0.25
        return Evidence(
            challenge_id=challenge.id,
            source=f"workspace://{document.path}",
            content="\n".join(numbered),
            quality=quality,
            supports_target_claim=None,
        )


def extract_unified_diff(text: str) -> str:
    match = _DIFF_RE.search(text)
    if match:
        return match.group("diff").strip()
    marker = text.find("diff --git ")
    if marker >= 0:
        return text[marker:].strip()
    return ""
