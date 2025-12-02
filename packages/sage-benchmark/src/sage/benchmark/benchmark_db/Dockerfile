# SAGE-DB-Bench Dockerfile
# 用于功能测试和开发，不推荐用于精确性能测试

FROM ubuntu:22.04

LABEL maintainer="SAGE-DB-Bench Team"
LABEL description="Streaming ANN Benchmark Framework"

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    build-essential \
    cmake \
    git \
    wget \
    curl \
    vim \
    # Python相关
    python3.10 \
    python3.10-dev \
    python3-pip \
    # 数学库
    libopenblas-dev \
    libomp-dev \
    # 其他依赖
    swig \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip3 install --upgrade pip setuptools wheel

# 设置工作目录
WORKDIR /app

# 复制requirements.txt（利用Docker缓存）
COPY requirements.txt .

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 初始化子模块
RUN git submodule update --init --recursive || echo "Warning: Failed to init submodules"

# 编译算法库（可选，注释掉可加快构建速度）
# RUN cd algorithms_impl && ./build.sh

# 创建必要的目录
RUN mkdir -p results raw_data logs

# 设置环境变量
ENV PYTHONPATH=/app:$PYTHONPATH
ENV OMP_NUM_THREADS=4

# 暴露端口（如果有web服务）
# EXPOSE 8000

# 默认命令
CMD ["/bin/bash"]

# 使用示例：
# docker build -t sage-db-bench .
# docker run -it --name sage-bench -v $(pwd)/results:/app/results sage-db-bench
