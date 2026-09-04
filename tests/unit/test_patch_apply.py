from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ie_copilot.workspace import apply_unified_diff, validate_unified_diff_paths


def test_patch_path_validation_rejects_parent_traversal() -> None:
    patch = """diff --git a/../secret.txt b/../secret.txt
--- a/../secret.txt
+++ b/../secret.txt
@@ -1 +1 @@
-old
+new
"""
    with pytest.raises(ValueError, match="unsafe patch path"):
        validate_unified_diff_paths(patch)


def test_apply_unified_diff_checks_before_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("ie_copilot.workspace.subprocess.run", fake_run)
    patch = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1 @@
-old
+new
"""

    apply_unified_diff(patch, root=tmp_path)

    assert calls == [["git", "apply", "--check", "-"], ["git", "apply", "-"]]
