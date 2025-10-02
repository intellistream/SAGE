# Integration Tests - QA Service

This directory contains integration tests for SAGE QA (Question Answering) services and pipelines.

## Test Files

- `test_qa_service.py` - Simple integration test for QA pipeline service

## Running Tests

### Run the QA service test:
```bash
cd packages/sage-libs
python tests/integration/test_qa_service.py
```

### Run with pytest:
```bash
pytest packages/sage-libs/tests/integration/ -v
```

## Test Coverage

These tests verify:
- QA pipeline service initialization
- Question processing and response generation
- Service interaction and communication

## Related Tests

- RAG pipeline tests: [../lib/rag/](../lib/rag/)
- Tool tests: [../lib/tools/](../lib/tools/)
- Agent tests: [../lib/agents/](../lib/agents/)

## Note

For more comprehensive QA pipeline testing, see the unit tests in `tests/lib/rag/`.
