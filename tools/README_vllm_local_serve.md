# VLLM 本地服务启动脚本使用说明

## 概述

`vllm_local_serve.sh` 是一个用户友好的脚本，用于快速启动 VLLM 本地服务。该脚本提供了智能的模型管理、网络检测和用户交互功能。

## 功能特性

- ✅ **自动环境检测**: 自动检测并安装 VLLM
- ✅ **智能网络处理**: 自动检测网络连接，无法访问 HuggingFace 时自动设置国内镜像
- ✅ **模型存在检查**: 检查本地是否已有模型，避免重复下载
- ✅ **用户友好提示**: 提供详细的存储空间需求和下载提示
- ✅ **灵活模型选择**: 支持使用默认模型或指定自定义模型
- ✅ **彩色输出**: 使用不同颜色区分信息、警告和错误

## 系统要求

- Linux/macOS 操作系统
- Bash shell
- Conda 环境
- curl 命令（用于网络检测）
- 足够的磁盘空间（根据模型大小而定）

## 快速开始

### 1. 基本使用

```bash
# 使用默认模型（microsoft/DialoGPT-small，约500MB）
./vllm_local_serve.sh

# 使用指定模型
./vllm_local_serve.sh microsoft/DialoGPT-medium
```

### 2. 首次运行

首次运行时，脚本会：

1. 检查是否安装了 VLLM，如未安装会自动安装
2. 检查网络连接，必要时设置 HuggingFace 镜像
3. 检查指定模型是否存在于本地
4. 如果模型不存在，会提示用户确认下载

## 推荐模型

| 模型名称 | 大小 | 适用场景 | 内存需求 |
|---------|------|----------|----------|
| `microsoft/DialoGPT-small` | ~500MB | 轻量测试 | 2GB+ |
| `microsoft/DialoGPT-medium` | ~1.5GB | 一般对话 | 4GB+ |
| `microsoft/DialoGPT-large` | ~3GB | 高质量对话 | 8GB+ |
| `meta-llama/Llama-2-7b-chat-hf` | ~14GB | 专业应用 | 16GB+ |
| `meta-llama/Llama-2-13b-chat-hf` | ~26GB | 高端应用 | 32GB+ |

## 使用示例

### 启动小型模型（推荐新手）
```bash
./vllm_local_serve.sh microsoft/DialoGPT-small
```

### 启动中等模型
```bash
./vllm_local_serve.sh microsoft/DialoGPT-medium
```

### 启动大型 LLaMA 模型
```bash
./vllm_local_serve.sh meta-llama/Llama-2-7b-chat-hf
```

## 网络配置

### 国内用户配置

如果无法访问 HuggingFace.co，脚本会自动设置镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 手动设置镜像

如果需要手动设置镜像，可以在运行脚本前执行：

```bash
export HF_ENDPOINT=https://hf-mirror.com
./vllm_local_serve.sh
```

## API 使用

服务启动后，可以通过以下方式访问：

### 基本信息
- **服务地址**: `http://localhost:8000`
- **API Key**: `token-abc123`
- **文档地址**: `http://localhost:8000/docs`

### 使用 curl 测试

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token-abc123" \
  -d '{
    "model": "microsoft/DialoGPT-small",
    "messages": [
      {
        "role": "user", 
        "content": "Hello, how are you?"
      }
    ],
    "max_tokens": 100
  }'
```

### 使用 Python

```python
import requests

url = "http://localhost:8000/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer token-abc123"
}

data = {
    "model": "microsoft/DialoGPT-small",
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

## 故障排除

### 常见问题

#### 1. VLLM 安装失败
```bash
# 手动安装 VLLM
conda install -y -c conda-forge vllm
```

#### 2. 模型下载失败
```bash
# 检查网络连接
curl -I https://huggingface.co

# 设置镜像
export HF_ENDPOINT=https://hf-mirror.com

# 手动下载模型
huggingface-cli download microsoft/DialoGPT-small
```

#### 3. 内存不足
- 使用更小的模型：`microsoft/DialoGPT-small`
- 增加虚拟内存
- 检查系统可用内存：`free -h`

#### 4. 端口占用
```bash
# 查看端口占用
lsof -i :8000

# 终止占用进程
kill -9 <PID>
```

### 日志分析

脚本运行时会输出详细的状态信息：

- 🟢 **绿色 [INFO]**: 正常信息
- 🟡 **黄色 [WARNING]**: 警告信息
- 🔴 **红色 [ERROR]**: 错误信息

### 清理缓存

如果需要清理模型缓存：

```bash
# 查看缓存位置
echo $HF_HOME  # 如果设置了的话
# 或者默认位置
ls ~/.cache/huggingface/hub/

# 删除特定模型缓存
rm -rf ~/.cache/huggingface/hub/models--microsoft--DialoGPT-small
```

## 高级配置

### 自定义 API Key

如果需要修改 API Key，编辑脚本最后一行：

```bash
vllm serve "$MODEL" --dtype auto --api-key your-custom-key
```

### 自定义端口

```bash
vllm serve "$MODEL" --dtype auto --api-key token-abc123 --port 8080
```

### 多 GPU 支持

```bash
vllm serve "$MODEL" --dtype auto --api-key token-abc123 --tensor-parallel-size 2
```

## 安全注意事项

1. **API Key 保护**: 默认 API Key 仅用于测试，生产环境请更改
2. **网络访问**: 服务默认监听所有接口，注意防火墙设置
3. **模型安全**: 确保下载的模型来源可信

## 贡献与反馈

如有问题或建议，请：

1. 检查本文档的故障排除部分
2. 查看脚本输出的错误信息
3. 提交 Issue 或 Pull Request



**提示**: 建议首次使用时选择小型模型进行测试，确认环境正常后再使用大型模型。
