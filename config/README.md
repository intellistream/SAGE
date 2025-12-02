# SAGE Configuration

Unified configuration file for SAGE project.

## File

| File          | Purpose                                        |
| ------------- | ---------------------------------------------- |
| `config.yaml` | All configuration (cluster, services, runtime) |

## Quick Start

```bash
# 1. Initialize config (interactive)
sage cluster init

# 2. Or edit directly
vi config/config.yaml

# 3. Setup SSH keys to worker nodes
sage cluster setup-ssh

# 4. Start cluster
sage cluster start
```

## Configuration Sections

### Cluster

- `cluster_name` - Cluster identifier
- `provider.head_ip` - Head node IP
- `provider.worker_ips` - List of worker node IPs
- `auth` - SSH authentication (key-based only)
- `ray` - Ray settings (ports, resources)
- `remote` - Remote environment (conda, paths)

### Services

- `llm` - vLLM service settings
- `embedding` - Embedding service
- `gateway` - OpenAI-compatible API gateway
- `studio` - Web UI ports

## Directory Structure

```
<project_root>/
├── config/              # Configuration (git tracked)
│   ├── config.yaml      # Unified config file
│   └── README.md
├── .sage/               # Temporary files (gitignored)
│   ├── build/
│   ├── cache/
│   └── logs/
```
