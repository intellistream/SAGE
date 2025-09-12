# SAGE Common Utilities

Core common utilities for the SAGE project. This package contains the essential shared components that are used across all SAGE packages.

## Core Modules

- **utils.config**: Configuration management utilities
- **utils.logging**: Logging framework and formatters  
- **utils.network**: Network utilities and TCP clients/servers
- **utils.serialization**: Serialization utilities including dill support
- **utils.system**: System utilities for environment and process management
- **_version**: Version management

## Installation

```bash
pip install isage-common
```

## Usage

```python
from sage.common.utils.logging.custom_logger import get_logger
from sage.common.utils.config.loader import ConfigLoader

logger = get_logger(__name__)
config = ConfigLoader("config.yaml")
```
