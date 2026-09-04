# Vibe Coding Vertical Slice — Implementation Plan

## RED

新增 unit tests：

1. workspace context 只读取显式文件且 provider 返回匹配 snippet；
2. unified diff extraction；
3. CLI parser 支持 legacy/ask/vibe；
4. environment settings 解析；
5. structured-output retry 对 parser/validation failure 重试并最终成功。

## GREEN

1. `config.py`：RuntimeSettings。
2. `prompts.py`：versioned general/vibe prompts。
3. `workspace.py`：context collection + WorkspaceEvidenceProvider + diff extraction。
4. `agents.py`：prompt version、structured-output retry budget、generation metadata。
5. `cli.py`：legacy/ask/vibe，`--file`、`--json`、`--patch-out`。
6. README/.env.example 更新可运行说明。

## Verification

Fresh CI Python 3.10/3.13：lock check、frozen install、Ruff、unit tests 全绿；不使用真实 API key。
