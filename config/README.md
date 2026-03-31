# SAGE Configuration

Unified configuration file for SAGE project.

## File

| File | Purpose | | ------------- | ---------------------------------------------- | |
`config.yaml` | All configuration (cluster, services, runtime) |

## Quick Start

```bash
# 1. Review or edit the unified config directly
vi config/config.yaml

# 2. Inspect current local status
sage status

# 3. Inspect runtime-visible nodes
sage runtime nodes

# 4. If you integrate an external sagellm gateway, inspect the launch contract
sage serve gateway --json

# 5. Record lightweight local index metadata when needed
sage index ingest --source ./docs --index local-docs
```

## Configuration Sections

### Cluster

- `cluster_name` - Cluster identifier
- `provider.head_ip` - Head node IP
- `provider.worker_ips` - List of worker node IPs
- `auth` - SSH authentication (key-based only)
- `flutty` - Flutty runtime settings (ports, resources)
- `remote` - Remote environment (conda, paths)

### Services

- `llm` - SageLLM service settings
- `embedding` - Embedding service
- `gateway` - OpenAI-compatible API gateway
- `studio` - Web UI ports

## Directory Structure

```text
<project_root>/
├── config/              # Configuration (git tracked)
│   ├── config.yaml      # Unified config file
│   └── README.md
├── .sage/               # Temporary files (gitignored)
│   ├── build/
│   ├── cache/
│   └── logs/
```
