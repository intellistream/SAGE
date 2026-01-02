# SAGE Studio Docker 部署

## 快速开始

### 前提条件

- Docker 20.10+
- Docker Compose v2
- NVIDIA Container Toolkit（GPU 支持）
- Cloudflare Tunnel 已配置（指向 127.0.0.1:5173）

### 构建和启动

```bash
# 从项目根目录
cd /path/to/SAGE

# 构建镜像（首次约 10-15 分钟）
docker-compose -f docker/studio/docker-compose.yml build

# 启动服务
docker-compose -f docker/studio/docker-compose.yml up -d

# 查看日志
docker-compose -f docker/studio/docker-compose.yml logs -f

# 停止服务
docker-compose -f docker/studio/docker-compose.yml down
```

### 访问地址

| 服务              | 地址                       | 说明            |
| ----------------- | -------------------------- | --------------- |
| Studio 前端       | http://localhost:5173      | 可视化编辑器    |
| Gateway API       | http://localhost:8889      | OpenAI 兼容 API |
| Cloudflare Tunnel | https://studio.sage.org.ai | 公网访问        |

## 架构

```
Internet
    │
    ▼
Cloudflare (CDN)
    │
    ▼
cloudflared (Host systemd service)
    │ 127.0.0.1:5173
    ▼
┌─────────────────────────────────────┐
│  Docker Container (sage-studio)     │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Vite Preview (5173)         │   │
│  │ - Studio 前端               │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Gateway (8889)              │   │
│  │ - OpenAI 兼容 API           │   │
│  │ - Control Plane 调度        │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ vLLM (8901)                 │   │
│  │ - Qwen2.5-7B-Instruct       │   │
│  │ - GPU 加速                  │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Embedding (8090)            │   │
│  │ - BAAI/bge-m3               │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 配置

### 环境变量

在 `docker-compose.yml` 中配置：

```yaml
environment:
  # LLM 模型
  - SAGE_STUDIO_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
  - SAGE_STUDIO_LLM_GPU_MEMORY=0.9

  # 云端 API 备用（可选）
  - SAGE_CHAT_API_KEY=sk-xxx
  - SAGE_CHAT_MODEL=qwen-turbo-2025-02-11
```

### 数据持久化

Docker volumes 用于持久化数据：

| Volume           | 路径                     | 说明                 |
| ---------------- | ------------------------ | -------------------- |
| sage-models      | /root/.cache/huggingface | HuggingFace 模型缓存 |
| sage-data        | /root/.sage              | SAGE 配置和日志      |
| sage-local-share | /root/.local/share/sage  | 用户数据             |
| sage-local-state | /root/.local/state/sage  | 运行状态             |

### GPU 配置

确保已安装 NVIDIA Container Toolkit：

```bash
# Ubuntu
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

验证 GPU 支持：

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## CI/CD 集成

### GitHub Actions Workflow

```yaml
name: Deploy SAGE Studio (Docker)

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - 'packages/sage-studio/**'
      - 'docker/studio/**'

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/studio/Dockerfile
          push: true
          tags: ghcr.io/intellistream/sage-studio:latest

  deploy:
    needs: build-and-push
    runs-on: [self-hosted, A100]
    steps:
      - name: Pull and restart
        run: |
          docker pull ghcr.io/intellistream/sage-studio:latest
          docker-compose -f docker/studio/docker-compose.yml up -d
```

## 故障排除

### 容器无法启动

```bash
# 查看日志
docker logs sage-studio

# 检查 GPU
docker exec sage-studio nvidia-smi
```

### LLM 模型下载慢

镜像已配置 `HF_ENDPOINT=https://hf-mirror.com`（中国镜像）。

首次启动可能需要下载模型（~14GB），请耐心等待。

### 端口被占用

```bash
# 检查端口占用
lsof -i:5173
lsof -i:8889

# 停止占用进程
fuser -k 5173/tcp
```

### Cloudflare Tunnel 502 错误

确保：

1. Docker 容器正在运行：`docker ps | grep sage-studio`
1. 容器健康检查通过：`docker inspect sage-studio | jq '.[0].State.Health'`
1. 端口正确暴露：`curl http://localhost:5173`
