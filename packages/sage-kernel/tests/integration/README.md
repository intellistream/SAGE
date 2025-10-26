# Integration Tests

This directory contains integration tests for SAGE kernel services and components.

## Structure

```
integration/
├── services/          # Service-level integration tests
│   ├── test_autostop_api_verification.py
│   ├── test_autostop_service_improved.py
│   └── test_autostop_service_remote.py
└── README.md         # This file
```

## Running Integration Tests

From the repository root:

```bash
# Run all integration tests
pytest packages/sage-kernel/tests/integration/ -v

# Run only service tests
pytest packages/sage-kernel/tests/integration/services/ -v

# Run a specific test file
python packages/sage-kernel/tests/integration/services/test_autostop_service_remote.py
```

## Test Categories

### Services Tests

Tests for SAGE service lifecycle management, including:

- Service initialization and cleanup
- Autostop functionality (local and remote modes)
- Resource management and garbage collection

See [services/README.md](services/README.md) for more details.

## Related Test Directories

- [../unit/](../unit/) - Unit tests for kernel components
- [../../sage-libs/tests/](../../sage-libs/tests/) - Library-level tests
- [../../sage-middleware/tests/](../../sage-middleware/tests/) - Middleware tests
