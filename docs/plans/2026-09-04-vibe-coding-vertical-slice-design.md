# Vibe Coding Vertical Slice — Design

## User goal

让用户可以直接把自然语言编码需求和若干本地源码文件交给 IE Copilot，得到经过多 Agent 审议后的实现方案和可保存的 unified diff，而不是只能调用一个通用问答 Demo。

## CLI

保留兼容：

```bash
ie-copilot "question"
```

新增：

```bash
ie-copilot ask "question"
ie-copilot vibe "implement feature" --file src/a.py --file tests/test_a.py
ie-copilot vibe "fix bug" --file src/a.py --patch-out /tmp/change.patch
```

`vibe` 默认三个 epistemic roles：

1. implementer：最小、可维护实现；
2. reviewer：主动寻找 correctness/security/regression 问题；
3. tester：以测试和可验证性约束方案。

最终答案要求包含：implementation plan、unified diff、tests、risks。

## Local evidence

`WorkspaceEvidenceProvider` 对用户显式传入的文件做只读检索。Challenge 提出 evidence request 时，provider 以关键词匹配返回最相关代码片段；不读取用户未提供的文件，不联网，不把模型文本伪装成 evidence。

## Configuration

统一环境变量读取：model/base_url/api_key/temperature/agent timeout/structured-output retry budget。Prompt 文本集中在 `prompts.py` 并带 `PROMPT_VERSION`。

## Structured output retry

LLM structured-output validation/parser failure允许有限次数重试；网络/运行时错误不做无限重试。retry budget 可配置，默认 1 次额外尝试。

## Patch safety

本批次只支持 `--patch-out` 写出 patch，不自动修改工作区。自动 apply 留给后续显式 opt-in 命令，避免把未经验证的模型输出直接写入仓库。

## Acceptance

- unit tests 不需要真实 API；
- CLI parser 支持 legacy/ask/vibe；
- workspace provider 可确定性返回源码 evidence；
- diff 可从最终文本提取并保存；
- OpenAI-compatible Agent 仍是 structured output；
- fresh Python 3.10/3.13 CI green。
