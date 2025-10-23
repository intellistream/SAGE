# sage-common: Foundation Layer (L1)

## Overview

`sage-common` provides foundational utilities and data types used across the entire SAGE system.

## Key Components

### Data Types
- **BaseDocument**: Foundation for all document types
- **Vector Types**: Dense and sparse vector representations
- **Metadata**: Document metadata management

### Utilities
- **Logger**: Structured logging system
- **Config**: Configuration management
- **Exceptions**: Custom exception hierarchy

### Core Interfaces
- Common protocols and abstract base classes
- Serialization/deserialization interfaces
- Type definitions and validators

## Architecture

```
sage-common/
├── types/          # Data type definitions
├── utils/          # Utility functions
├── config/         # Configuration management
└── exceptions/     # Exception classes
```

## Usage

```python
from sage.common.types import BaseDocument
from sage.common.utils import get_logger

logger = get_logger(__name__)

class MyDocument(BaseDocument):
    """Custom document type."""
    pass
```

## Dependencies

- **External**: None (foundation layer)
- **Internal**: None

## See Also

- [Architecture Overview](../../architecture/overview.md)
- [Package Structure](../../architecture/package-structure.md)
- [sage-platform Documentation](../platform/overview.md)
