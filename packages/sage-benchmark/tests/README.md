# SAGE Benchmark Tests

This directory contains tests for the SAGE benchmark package.

## Structure

```
tests/
├── rag/              # RAG benchmark tests
└── experiments/      # Experiment framework tests
```

## Running Tests

```bash
# Run all tests
pytest packages/sage-benchmark/

# Run specific test module
pytest packages/sage-benchmark/tests/rag/

# Run with verbose output
pytest packages/sage-benchmark/ -v
```
