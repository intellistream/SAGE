# SAGE Common - Utilities, CLI, Development Tools & Frontend

This package provides the core utilities, command-line interface, development tools, and web frontend for the SAGE (Stream Analytics in Go-like Environments) framework.

## Features

### 🛠️ Core Utilities (`sage.utils`)
- Configuration management with YAML/TOML support
- Flexible logging system with multiple backends
- Platform-specific directory management
- Type validation with Pydantic models
- Common data structures and helpers

### 💻 Command Line Interface (`sage.cli`)
- Rich CLI with auto-completion support
- Interactive questionnaires and prompts
- Beautiful table formatting and progress bars
- Cross-platform shell integration
- Core SAGE system management commands

### 🔧 Development Toolkit (`sage.dev`)
- Automated testing with pytest integration
- Code quality tools (black, isort, mypy, ruff)
- Package management and publishing
- Performance profiling and benchmarking
- Documentation generation tools

### 🌐 Web Frontend (`sage.frontend`)
- FastAPI-based web server and dashboard
- Real-time websocket communication
- Interactive data visualization
- Authentication and security features
- RESTful API endpoints

## Installation

```bash
# 基础安装 (仅 utils 核心功能)
pip install isage-common

# 基础 + CLI 工具
pip install isage-common[cli]
# 或者
pip install isage-common[basic]

# CLI + 开发工具
pip install isage-common[tools]

# 开发环境完整安装
pip install isage-common[dev]

# Frontend/Web 功能
pip install isage-common[frontend]
# 或者
pip install isage-common[web]

# 文档生成工具
pip install isage-common[docs]

# 完整安装 (所有功能)
pip install isage-common[full]
```

## Quick Start

### Using Utilities

```python
from sage.utils.config import load_config
from sage.utils.logging import get_logger

# Load configuration
config = load_config("my_config.yaml")

# Set up logging
logger = get_logger("my_app")
logger.info("Hello SAGE!")
```

### Using CLI

```bash
# Basic SAGE commands
sage --help
sage config show
sage status

# Core system management
sage-core start
sage-core status
sage-core stop
```

### Using Development Tools

```bash
# Run tests
sage-dev test

# Code analysis
sage-dev analyze

# Package management
sage-dev package build
sage-dev package publish

# Generate reports
sage-dev report coverage
sage-dev report performance
```

### Using Frontend

```bash
# Start SAGE web server
sage-frontend

# Start dashboard  
sage-dashboard

# Start server with custom config
sage-server --config my_config.yaml
```

## Package Structure

```
src/sage/
├── utils/           # Core utilities
│   ├── config/      # Configuration management
│   ├── logging/     # Logging system
│   ├── types/       # Type definitions
│   └── helpers/     # Helper functions
├── cli/             # Command line interface
│   ├── commands/    # CLI command implementations
│   ├── prompts/     # Interactive prompts
│   └── formatters/  # Output formatting
├── dev/             # Development tools
│   ├── testing/     # Test automation
│   ├── quality/     # Code quality tools
│   ├── packaging/   # Package management
│   └── docs/        # Documentation tools
└── frontend/        # Web frontend and dashboard
    ├── web_ui/ # FastAPI server implementation
    ├── static/      # Static web assets
    └── templates/   # HTML templates
```

## Contributing

This package is part of the SAGE monorepo. Please see the main [SAGE repository](https://github.com/intellistream/SAGE) for contribution guidelines.

## License

MIT License - see the [LICENSE](../../LICENSE) file for details.
