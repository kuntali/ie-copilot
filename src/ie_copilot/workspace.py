from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import Challenge, Evidence

_TOKEN_RE = re.compile(r"[\w.-]+", re.UNICODE)
_DIFF_RE = re.compile(r"```diff\s*\n(?P<diff>.*?)(?:\n```)", re.DOTALL)
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(?P<a>\S+) b/(?P<b>\S+)$", re.MULTILINE)
_DEFAULT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".kts",
    ".md",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
_IGNORED_DIRS = {".git", ".venv", "build", "dist", "node_modules", "target"}


@dataclass(frozen=True)
class WorkspaceDocument:
    path: str
    content: str


def _resolve_inside_root(raw_path: str | Path, root_path: Path) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"workspace file is outside root: {raw_path}") from exc
    return resolved


def _expand_inputs(paths: list[str], root_path: Path, *, max_files: int) -> list[Path]:
    resolved_files: list[Path] = []
    for raw_path in paths:
        resolved = _resolve_inside_root(raw_path, root_path)
        if resolved.is_file():
            resolved_files.append(resolved)
            continue
        if not resolved.is_dir():
            raise FileNotFoundError(raw_path)
        for candidate in sorted(resolved.rglob("*")):
            if not candidate.is_file():
                continue
            relative_parts = candidate.relative_to(root_path).parts
            if any(part in _IGNORED_DIRS for part in relative_parts):
                continue
            if candidate.suffix.casefold() not in _DEFAULT_EXTENSIONS:
                continue
            resolved_files.append(candidate.resolve())
            if len(resolved_files) > max_files:
                raise ValueError(f"workspace selection exceeds {max_files} files")
    deduplicated = list(dict.fromkeys(resolved_files))
    if len(deduplicated) > max_files:
        raise ValueError(f"workspace selection exceeds {max_files} files")
    return deduplicated


def load_workspace_files(
    paths: list[str],
    *,
    root: str | Path = ".",
    max_bytes_per_file: int = 200_000,
    max_files: int = 50,
) -> list[WorkspaceDocument]:
    root_path = Path(root).resolve()
    documents: list[WorkspaceDocument] = []
    for resolved in _expand_inputs(paths, root_path, max_files=max_files):
        data = resolved.read_bytes()
        if len(data) > max_bytes_per_file:
            raise ValueError(
                f"workspace file exceeds size limit: {resolved.relative_to(root_path)}"
            )
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


def _validate_patch_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts or path.startswith(("/", "\\")):
        raise ValueError(f"unsafe patch path: {path}")


def validate_unified_diff_paths(patch: str) -> None:
    headers = list(_DIFF_HEADER_RE.finditer(patch))
    if not headers:
        raise ValueError("patch must contain diff --git headers")
    for header in headers:
        _validate_patch_path(header.group("a"))
        _validate_patch_path(header.group("b"))


def apply_unified_diff(patch: str, *, root: str | Path = ".") -> None:
    validate_unified_diff_paths(patch)
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(root)
    encoded = patch.encode("utf-8")
    common = {
        "cwd": root_path,
        "input": encoded,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "check": False,
    }
    check_result = subprocess.run(["git", "apply", "--check", "-"], **common)
    if check_result.returncode != 0:
        message = check_result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git apply --check failed: {message}")
    apply_result = subprocess.run(["git", "apply", "-"], **common)
    if apply_result.returncode != 0:
        message = apply_result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git apply failed after successful check: {message}")
