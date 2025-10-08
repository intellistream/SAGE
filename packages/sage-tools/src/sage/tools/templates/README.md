# SAGE Application Templates

This package curates runnable pipeline templates that are derived from the scripts under `examples/`. Each template is backed by a `PipelineBlueprint` so it can render full pipeline plans and graph views that plug into the CLI builders.

## Included templates

- `rag-simple-demo` – Customer support style FAQ assistant built from `examples/rag/rag_simple.py`.
- `hello-world-batch` – Introductory batch pipeline that uppercases greetings.
- `hello-world-log` – Variation that uses `PrintSink` for structured logging output.
- `rag-multimodal-fusion` – Multimodal landmark QA workflow combining text and synthetic image embeddings.

Use `sage.tools.templates.list_templates()` to enumerate templates and `match_templates()` to surface candidates for a set of requirements. Each template exposes `pipeline_plan()` and `graph_plan()` helpers that return deep copies suitable for further customization.
