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

### Studio Deployment (cluster.yaml)

Multi-node SAGE Studio deployment configuration:

```yaml
studio:
  enabled: true
  nodes:
    - host: 192.168.1.100
      role: primary        # Primary node with Cloudflare Tunnel
      port: 5173
      tunnel_domain: studio.sage.org.ai
    - host: 192.168.1.101
      role: replica        # Additional nodes
      port: 5173
  llm:
    enabled: true
    model: Qwen/Qwen2.5-0.5B-Instruct
  embedding:
    enabled: true
    model: BAAI/bge-m3
  deploy:
    branch: main           # Stable branch to deploy
```

**Required GitHub Secrets for cluster deployment:**

- `CLUSTER_SSH_PRIVATE_KEY` - SSH private key for accessing nodes
- `CLOUDFLARE_TUNNEL_TOKEN` - Cloudflare Tunnel token (for primary node)
- `DASHSCOPE_API_KEY`, `OPENAI_API_KEY`, `HF_TOKEN` - API keys

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
