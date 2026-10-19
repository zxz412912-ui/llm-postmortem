# llm-postmortem

**Turn messy LLM call logs into a short, actionable incident report — locally.**

When an LLM feature is flaky, the raw traces are rarely useful on their own. `llm-postmortem` reads a JSONL export, groups recurring failures, surfaces representative examples, and suggests the next engineering action.

It is intentionally small, deterministic, and local-first: no telemetry, API key, or model call required.

## What it finds

- Tool and function-call failures
- Broken JSON / structured-output contracts
- Hallucination signals
- Retrieval and grounding failures
- Refusals and timeouts
- Per-model failure, latency, and cost summaries

## Quick start

Requires Python 3.10+.

```bash
pip install -e .
llm-postmortem examples/demo.jsonl --output postmortem.md
# Or produce a self-contained, filterable browser report
llm-postmortem examples/demo.jsonl --output postmortem.html
```

The resulting `postmortem.md` includes a ranked failure table, trace snippets, and targeted recommendations such as adding schema validation or investigating retrieval recall.

## Input format

One JSON object per line. The schema is permissive; only failure signals are required. Common fields include:

```json
{
  "trace_id": "call-42",
  "model": "gpt-4.1-mini",
  "prompt": "Return customer data as JSON",
  "response": "...",
  "status": "failed",
  "feedback": "JSON schema validation failed",
  "latency_ms": 430,
  "cost_usd": 0.0012
}
```

A call is treated as a failure if `status` is `error`, `failed`, `failure`, or `timeout`; `passed` is `false`; `score` is below `0.5`; or an `error` field is present.

### Automatic adapters

The CLI also accepts these JSONL shapes without an extra dependency:

- **Ollama `/api/generate`** logs — maps `total_duration` to milliseconds.
- **OpenAI Responses-style** wrapper logs — reads nested `response.id`, `response.model`, `response.output`, and `response.usage`.
- **LangChain run exports** — maps `run_id`, `inputs`, `outputs`, `extra.invocation_params`, and `error`.

For production traffic, write one JSON object per completed call to a `.jsonl` file, then point `llm-postmortem` at that file. Keep secrets and full end-user PII out of logs before sharing a report.

## Why this is useful

Most LLM observability tools capture traces. This project focuses on the next question: **what should I fix first?** The classifier is rule-based on purpose, so every conclusion is auditable and the tool remains useful with sensitive local logs.

## Roadmap

- [ ] Custom labeling rules in YAML
- [ ] OpenTelemetry and Langfuse exporters
- [x] Self-contained HTML report with trace filtering
- [ ] Optional LLM-assisted clustering, kept opt-in

## Contributing

Issues with anonymized failure patterns and proposed classification rules are especially welcome.

## License

MIT
