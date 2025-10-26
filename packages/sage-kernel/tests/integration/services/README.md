# Integration Tests - Services

This directory contains integration tests for SAGE services, particularly focusing on service
lifecycle management and autostop functionality.

## Test Files

- `test_autostop_api_verification.py` - Tests for autostop API functionality
- `test_autostop_service_improved.py` - Enhanced autostop service tests
- `test_autostop_service_remote.py` - Remote autostop service tests (Ray mode)

## Running Tests

### Run all service integration tests:

```bash
cd packages/sage-kernel
pytest tests/integration/services/
```

### Run a specific test:

```bash
cd packages/sage-kernel
python tests/integration/services/test_autostop_service_remote.py
```

### Run with pytest:

```bash
pytest packages/sage-kernel/tests/integration/services/test_autostop_api_verification.py -v
```

## Test Coverage

These tests verify:

- Service initialization and cleanup
- Autostop functionality in local mode
- Autostop functionality in remote (Ray) mode
- Service lifecycle management
- Resource cleanup and garbage collection

## Related Tests

- Unit tests for core functionality: [../unit/core/](../unit/core/)
- Function tests: [../unit/core/function/](../unit/core/function/)
