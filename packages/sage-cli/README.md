# SAGE CLI

> **Unified Command Line Interface for SAGE Platform**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](../../LICENSE)

SAGE CLI (`sage-cli`) is the unified command-line interface for the SAGE (Streaming-Augmented
Generative Execution) platform. It provides a comprehensive set of commands for managing clusters,
deploying applications, and developing with SAGE.

## 🧭 Governance / 团队协作制度

- `docs/governance/TEAM.md`
- `docs/governance/MAINTAINERS.md`
- `docs/governance/DEVELOPER_GUIDE.md`
- `docs/governance/PR_CHECKLIST.md`
- `docs/governance/SELF_HOSTED_RUNNER.md`
- `docs/governance/TODO.md`

## 📋 Overview

**SAGE CLI** is the unified command-line interface for SAGE platform, providing commands for:

- **Cluster Management**: Start/stop Ray clusters, manage head/worker nodes
- **LLM Services**: Launch and manage LLM inference services
- **Development**: Tools for testing, quality checks, and project management
- **Monitoring**: System diagnostics and status checks

## ✨ Features

- **Unified Interface**: Single `sage` command for all platform operations
- **Cluster Orchestration**: Full Ray cluster lifecycle management
- **LLM Integration**: Start LLM services with automatic model loading
- **Interactive Chat**: Built-in chat interface for testing
- **Development Tools**: Via separate `sage-dev` command from sage-tools package

## 🚀 Installation

```bash
# From source
cd packages/sage-cli
pip install -e .

# Or install from PyPI (when published)
pip install sage-cli
```

## 📋 Command Structure

SAGE CLI organizes commands into two main categories:

### Platform Commands

Manage SAGE infrastructure and system components:

- `sage cluster` - Ray cluster management
- `sage head` - Head node management
- `sage worker` - Worker node management
- `sage job` - Job management
- `sage jobmanager` - JobManager service
- `sage config` - Configuration management
- `sage doctor` - System diagnostics
- `sage version` - Version information
- `sage extensions` - C++ extension management

### Application Commands

Application-level functionality:

- `sage llm` - LLM service management
- `sage chat` - Interactive chat interface
- `sage embedding` - Embedding service management
- `sage pipeline` - Pipeline builder
- `sage studio` - Visual pipeline editor

### Development Commands

**Note:** Development commands are provided by the `sage-tools` package separately via the
`sage-dev` command.

To use development tools:

```bash
# Install sage-tools (if not already installed)
pip install sage-tools

# Use sage-dev command
sage-dev quality check
sage-dev project test
sage-dev maintain doctor
```

Development command groups include:

- `sage-dev quality` - Code quality checks
- `sage-dev project` - Project management
- `sage-dev maintain` - Maintenance tools
- `sage-dev package` - Package management
- `sage-dev resource` - Resource management
- `sage-dev github` - GitHub utilities

## 📖 Quick Start

### Basic Commands

```bash
# Check system status
sage doctor

# View version
sage version

# Get help
sage --help
sage <command> --help
```

### Cluster Management

```bash
# Start a cluster
sage cluster start

# View cluster status
sage cluster status

# Stop cluster
sage cluster stop
```

### LLM Service

```bash
# Start LLM service
sage llm start --model Qwen/Qwen2.5-7B-Instruct

# Check status
sage llm status

# Interactive chat
sage chat
```

### Development Tools

For development commands, install `sage-tools`:

```bash
pip install sage-tools

# Run development checks
sage-dev quality check

# Run tests
sage-dev project test
```

## � Configuration

SAGE CLI reads configuration from:

- `~/.sage/config.yaml` - User configuration
- `./config/config.yaml` - Project configuration
- Environment variables: `SAGE_*`

```yaml
# config.yaml example
cluster:
  head_node: localhost
  workers: 4

llm:
  model: Qwen/Qwen2.5-7B-Instruct
  port: 8001
```

## 📦 Package Structure

```
sage-cli/
├── src/
│   └── sage/
│       └── cli/
│           ├── commands/      # Command implementations
│           ├── cluster/       # Cluster management
│           └── llm/           # LLM service commands
├── tests/
├── pyproject.toml
└── README.md
```

## 🧪 Testing

```bash
# Run CLI tests
pytest packages/sage-cli/tests/

# Test specific command
sage --help
sage cluster --help

# Run integration tests
sage-dev project test --package sage-cli
```

## �📚 Documentation

For detailed documentation, see:

- [SAGE Documentation](https://intellistream.github.io/SAGE)
- [CLI Package Plan](../../docs/dev-notes/architecture/SAGE_CLI_PACKAGE_PLAN.md)

## 🏗️ Architecture

SAGE CLI is part of the L5 (Interface Layer) in the SAGE architecture:

```
L1: sage-common          (Foundation)
L2: sage-platform        (Platform Core)
L3: sage-kernel, sage-libs
L4: sage-middleware
L5: sage-cli, sage-tools
    ├── sage-cli: Production CLI via `sage` command
    └── sage-tools: Development tools via `sage-dev` command
```

**Independent Repositories:**

- sage-benchmark: Benchmark suites
- sage-examples: Applications and tutorials
- sage-studio: Visual interface
- sageLLM: LLM inference engine

**Command Separation:**

- **sage** (from sage-cli): User-facing production commands

  - Platform: cluster, head, worker, job, jobmanager, config, doctor, version, extensions
  - Apps: llm, chat, embedding, pipeline

- **sage-dev** (from sage-tools): Developer-only commands

  - quality, project, maintain, package, resource, github

Both packages are independent and can be installed separately.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## 📄 License

Apache License 2.0 - see [LICENSE](../../LICENSE) for details.

## 🔗 Related Packages

- `sage-tools` - Development tools and `sage-dev` commands
- `sage-platform` - SAGE platform core
- `sage-apps` - SAGE applications
- `sage-studio` - Visual pipeline editor
