# Self-Hosted Runner 配置指南 - LibAMM 编译

**Date**: 2025-11-14 **Author**: SAGE Development Team **Summary**: 配置 GitHub Actions self-hosted
runner 用于在高内存环境下编译 LibAMM wheel 包的完整指南

## 概述

LibAMM 需要在高内存环境下编译，因此我们使用 self-hosted GitHub Actions runner 来构建 wheel 包。

## Runner 要求

### 硬件要求

| 资源     | 最低配置 | 推荐配置   |
| -------- | -------- | ---------- |
| **CPU**  | 4 核     | 8+ 核      |
| **内存** | 16GB     | 32GB+      |
| **存储** | 50GB     | 100GB+ SSD |
| **网络** | 10Mbps   | 100Mbps+   |

### 软件要求

- **OS**: Linux (Ubuntu 20.04/22.04 推荐)
- **Docker**: 20.10+ (可选，推荐用于隔离环境)
- **Git**: 2.30+
- **Python**: 3.9-3.12 (通过 actions/setup-python 自动安装)

## 设置步骤

### 1. 准备服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget build-essential cmake

# 安装 Python 构建依赖
sudo apt install -y python3-dev python3-pip python3-venv

# 可选：安装 Docker（用于隔离构建环境）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

### 2. 增加 Swap（如果内存 < 32GB）

```bash
# 创建 16GB swap
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 验证
free -h
```

### 3. 配置 GitHub Actions Runner

#### 3.1 在 GitHub 仓库中添加 Runner

1. 访问仓库设置：`https://github.com/intellistream/SAGE/settings/actions/runners/new`
1. 选择 **Linux** 作为操作系统
1. 复制提供的下载和配置命令

#### 3.2 在服务器上安装 Runner

```bash
# 创建 runner 目录
mkdir -p ~/actions-runner && cd ~/actions-runner

# 下载最新版本的 runner（替换为 GitHub 提供的实际版本）
curl -o actions-runner-linux-x64-2.311.0.tar.gz \
  -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# 解压
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# 配置 runner
./config.sh --url https://github.com/intellistream/SAGE \
  --token <YOUR_TOKEN> \
  --name libamm-builder \
  --labels self-hosted,linux,x64,high-memory \
  --work _work

# 安装为系统服务（推荐）
sudo ./svc.sh install
sudo ./svc.sh start
```

### 4. 配置 Runner 标签

确保 runner 有以下标签：

- `self-hosted`
- `linux`
- `x64`
- `high-memory` ⬅️ 关键标签，用于 LibAMM 编译

### 5. 测试 Runner

手动触发 workflow 测试：

```bash
# 在 GitHub 网页界面
Actions -> Build LibAMM Wheels -> Run workflow
```

或者推送代码触发：

```bash
cd /path/to/SAGE
git commit --allow-empty -m "test: trigger LibAMM build"
git push origin main-dev
```

## Workflow 使用

### 自动触发

Workflow 会在以下情况自动运行：

1. **推送到 main/main-dev 且修改了 LibAMM 相关文件**
1. **创建 GitHub Release**

### 手动触发

在 GitHub Actions 页面：

1. 选择 **Build LibAMM Wheels** workflow
1. 点击 **Run workflow**
1. 配置参数：
   - Python versions: 默认 `3.9,3.10,3.11,3.12`
   - Upload to release: 是否上传到 GitHub Release

### 产物下载

编译完成后：

1. **从 Actions artifacts 下载**（保留 30 天）

   - 访问 workflow run 页面
   - 在 "Artifacts" 部分下载对应 Python 版本的 wheel

1. **从 GitHub Release 下载**（如果启用了上传）

   - 访问 Releases 页面
   - 下载对应的 `.whl` 文件

## 高级配置

### 使用 Docker 隔离构建环境

创建 `Dockerfile.libamm`:

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    build-essential cmake git curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip setuptools wheel build
RUN pip3 install torch --index-url https://download.pytorch.org/whl/cpu

WORKDIR /workspace
```

修改 workflow 使用 Docker:

```yaml
jobs:
  build-wheels:
    runs-on: [self-hosted, linux, x64, high-memory]
    container:
      image: ghcr.io/intellistream/libamm-builder:latest
      options: --memory=16g --cpus=4
```

### 并行构建优化

如果 runner 有足够资源，可以增加并行度：

```yaml
env:
  CMAKE_BUILD_PARALLEL_LEVEL: '4'  # 根据 CPU 核心数调整
```

### 监控构建过程

在 runner 服务器上监控：

```bash
# 实时监控内存使用
watch -n 1 'free -h; ps aux | grep cc1plus | grep -v grep'

# 查看 runner 日志
sudo journalctl -u actions.runner.* -f
```

## 故障排除

### 问题 1: OOM Killed

**症状**: 编译过程中进程被杀

**解决**:

```bash
# 增加 swap
sudo swapoff -a
sudo fallocate -l 24G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 降低并行度
# 在 workflow 中设置: CMAKE_BUILD_PARALLEL_LEVEL: '1'
```

### 问题 2: Runner 离线

**症状**: Runner 在 GitHub 显示为 offline

**解决**:

```bash
# 检查服务状态
sudo ./svc.sh status

# 重启服务
sudo ./svc.sh stop
sudo ./svc.sh start

# 查看日志
sudo journalctl -u actions.runner.* -n 50
```

### 问题 3: PyTorch 版本冲突

**症状**: 编译时找不到 torch 头文件

**解决**:

```bash
# 确保安装 CPU 版本的 PyTorch
pip install torch==2.5.0 --index-url https://download.pytorch.org/whl/cpu

# 验证
python -c "import torch; print(torch.__file__)"
```

## 安全建议

1. **使用专用用户**运行 runner，不要用 root
1. **限制 runner 权限**，只授予必要的仓库访问
1. **定期更新** runner 软件
1. **监控资源使用**，防止滥用
1. **使用 secrets** 管理敏感信息

## 成本估算

假设使用云服务器（AWS/GCP/阿里云）：

| 配置            | 实例类型   | 月费用（约） |
| --------------- | ---------- | ------------ |
| 16GB RAM, 4 CPU | t3.xlarge  | $120         |
| 32GB RAM, 8 CPU | t3.2xlarge | $240         |

**建议**: 使用按需实例，仅在需要编译时启动，可大幅降低成本。

## 相关资源

- [GitHub Actions Self-hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [LibAMM 编译文档](../../../packages/sage-libs/README_LIBAMM.md)
- [内存优化笔记](../dev-notes/l3-libs/libamm-memory-optimization.md)
