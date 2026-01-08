# sage-llm-core Examples

Examples demonstrating LLM inference capabilities via the Control Plane.

## Examples

| File                           | Description                                          |
| ------------------------------ | ---------------------------------------------------- |
| `unified_client_demo.py`       | UnifiedInferenceClient usage (chat, generate, embed) |
| `speculative_decoding_demo.py` | Speculative decoding strategies for faster inference |

## Running Examples

```bash
# From package directory
cd packages/sage-llm-core

# Run specific example
python examples/unified_client_demo.py

# Or from repo root
python packages/sage-llm-core/examples/unified_client_demo.py
```

## Prerequisites

1. Start the Gateway and LLM engine:

   ```bash
   sage gateway start
   sage llm engine start Qwen/Qwen2.5-7B-Instruct --engine-kind llm
   ```

1. Set environment variables (optional):

   ```bash
   export HF_TOKEN=your_token  # For model downloads
   ```

## Related Documentation

- [LLM & Embedding Services](../../../docs-public/docs_src/dev-notes/l1-llm-core/README.md)
- [Control Plane Architecture](../../../docs-public/docs_src/concepts/control-plane.md)
