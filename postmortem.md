# LLM Postmortem

## Executive summary

Analyzed **5** calls. **4** were marked as failures (**80.0%**).

## Failure modes

| Failure mode | Incidents | Share of failures |
| --- | ---: | ---: |
| tool failure | 1 | 25.0% |
| format error | 1 | 25.0% |
| hallucination | 1 | 25.0% |
| retrieval failure | 1 | 25.0% |

## Recommended next actions

1. **Tool Failure** — Validate tool arguments against a schema, return recoverable tool errors, and add a retry prompt containing the exact error.
   - `t-004`: tool_call calendar.create failed: invalid start_time
2. **Format Error** — Use structured outputs or JSON schema validation, then retry once with the validation error included.
   - `t-001`: name: Ada, email: ada@example.com
3. **Hallucination** — Require grounded citations for factual answers and add an explicit 'insufficient evidence' path.
   - `t-002`: The handbook gives 90 days paid leave.
4. **Retrieval Failure** — Inspect recall before changing the prompt: tune chunking, top-k, reranking, and metadata filters.
   - `t-003`: I can't find a relevant document in the supplied context.

## Model health

| Model | Calls | Failures | Avg latency | Avg cost |
| --- | ---: | ---: | ---: | ---: |
| gpt-4.1 | 1 | 1 | 810.0 ms | $0.00800 |
| gpt-4.1-mini | 4 | 3 | 460.0 ms | $0.00127 |
