# SAGE Observability 24/7 RCA + ChatOps Demo

This example simulates a SaaS/Cloud platform producing telemetry (logs/metrics/traces) 24/7.
When an alert fires, it performs Root Cause Analysis (RCA) with RAG and proposes remediation steps,
then publishes a concise ChatOps message (Slack or terminal fallback).

Highlights:
- Synthetic telemetry stream (no Prometheus/Otel required)
- RAG over a small playbook Knowledge Base using ChromaDB (fallback: in-memory)
- Optional LLM generator (OpenAI-compatible); otherwise heuristic responses
- Clean SAGE pipeline: Batch -> Map (Alert) -> Map (RCA) -> Map (Plan) -> Sink (ChatOps)
- Forward-looking hooks to integrate sage_flow (stream runtime) and sage_db (storage/analytics)

## How to run

1) Ensure Python deps. You likely already have them in this repo; for Chroma/requests:
   - chromadb (optional)
   - requests (for Slack webhook, optional)

2) Optional: set generator for better RCA phrasing
   - export SAGE_OPENAI_BASE_URL=...   # e.g., http://localhost:8000/v1
   - export OPENAI_API_KEY=...
   - export SAGE_OPENAI_MODEL=gpt-4o-mini

3) Run

```
python examples/observability/observability_demo.py --duration 30 --alert-cpu 0.8
```

If Slack is desired, set your Incoming Webhook in code or extend the CLI to pass it.

## What you should see
- Periodic incidents on orders/db; detector flags alerts in seconds
- RCA pulls playbook snippets and proposes a plan
- ChatOps prints a compact message, or posts to Slack when configured

## Extend with middleware (roadmap)
- sage_flow: replace TelemetryBatch with real streaming source and backpressure-aware runtime
- sage_db: persist incidents, RCA, and actions for historical analytics and SLO reports
- More middlewares (feature flags, runbooks, ticketing) can plug into the remediation step

## Troubleshooting
- No ChromaDB installed? The demo falls back to in-memory KB.
- No generator configured? It prints a heuristic RCA (good enough for a demo).
- Want deterministic runs? `export SAGE_EXAMPLES_MODE=test`.
