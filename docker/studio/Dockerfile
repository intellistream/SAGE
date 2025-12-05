# SAGE Studio Docker Image
# 基于 NVIDIA CUDA 镜像，支持 GPU 加速
#
# 构建: docker build -t sage-studio:latest -f docker/studio/Dockerfile .
# 运行: docker run -d --gpus all -p 5173:5173 -p 8888:8888 sage-studio:latest

ARG CUDA_VERSION=12.1.0
ARG UBUNTU_VERSION=22.04

FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

LABEL maintainer="SAGE Team"
LABEL description="SAGE Studio - AI/LLM Data Processing Pipeline Editor"

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# Python 和 Node.js 版本
ENV PYTHON_VERSION=3.11
ENV NODE_VERSION=20

# SAGE 配置
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# HuggingFace 镜像（中国区加速）
ENV HF_ENDPOINT=https://hf-mirror.com

# 端口配置
ENV STUDIO_PORT=5173
ENV GATEWAY_PORT=8888
ENV LLM_PORT=8901
ENV EMBEDDING_PORT=8090

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    curl \
    wget \
    git \
    build-essential \
    cmake \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-distutils \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 默认版本
RUN update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

# 安装 pip
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION}

# 安装 Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 复制依赖文件（利用 Docker 缓存）
COPY packages/sage-common/pyproject.toml packages/sage-common/
COPY packages/sage-platform/pyproject.toml packages/sage-platform/
COPY packages/sage-kernel/pyproject.toml packages/sage-kernel/
COPY packages/sage-libs/pyproject.toml packages/sage-libs/
COPY packages/sage-middleware/pyproject.toml packages/sage-middleware/
COPY packages/sage-apps/pyproject.toml packages/sage-apps/
COPY packages/sage-studio/pyproject.toml packages/sage-studio/
COPY packages/sage-gateway/pyproject.toml packages/sage-gateway/
COPY packages/sage-cli/pyproject.toml packages/sage-cli/
COPY packages/sage-tools/pyproject.toml packages/sage-tools/
COPY packages/sage/pyproject.toml packages/sage/

# 复制完整源码
COPY . .

# 配置 PyPI 镜像（清华源）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 安装 SAGE（标准安装，非 editable）
# 按依赖顺序安装
RUN pip install ./packages/sage-common \
    && pip install ./packages/sage-platform \
    && pip install ./packages/sage-kernel \
    && pip install ./packages/sage-libs \
    && pip install ./packages/sage-middleware \
    && pip install ./packages/sage-apps \
    && pip install ./packages/sage-studio \
    && pip install ./packages/sage-gateway \
    && pip install ./packages/sage-cli \
    && pip install ./packages/sage-tools \
    && pip install ./packages/sage

# 安装前端依赖并构建
WORKDIR /app/packages/sage-studio/src/sage/studio/frontend
RUN npm ci --prefer-offline \
    && npm run build \
    && mv dist /app/studio-dist

# 清理构建缓存
RUN rm -rf node_modules .npm

# 回到工作目录
WORKDIR /app

# 创建启动脚本
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting SAGE Studio..."
echo ""
echo "Configuration:"
echo "  - Studio Port: ${STUDIO_PORT:-5173}"
echo "  - Gateway Port: ${GATEWAY_PORT:-8888}"
echo "  - LLM Port: ${LLM_PORT:-8901}"
echo "  - Embedding Port: ${EMBEDDING_PORT:-8090}"
echo ""

# 检查 GPU 可用性
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Status:"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
    echo ""
fi

# 启动 Studio（包含 Gateway + LLM + Embedding + Frontend）
exec sage studio start \
    --prod \
    --host 0.0.0.0 \
    --port ${STUDIO_PORT:-5173} \
    -y
EOF
RUN chmod +x /app/start.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:${STUDIO_PORT:-5173}/ || exit 1

# 暴露端口
EXPOSE 5173 8888 8901 8090

# 启动命令
CMD ["/app/start.sh"]
