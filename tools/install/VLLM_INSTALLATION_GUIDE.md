# SAGE 快速安装脚本 - VLLM 环境准备

## 新增功能

`quickstart.sh` 脚本现在支持 `--vllm` 选项，用于准备 VLLM 使用环境。实际的 VLLM 安装将在首次使用 `vllm_local_serve.sh` 时自动完成。

## 使用方法

### 基本用法

```bash
# 默认安装 + 准备 VLLM 环境
./quickstart.sh --vllm

# 标准安装 + 准备 VLLM 环境
./quickstart.sh --standard --vllm

# 最小安装 + 准备 VLLM 环境
./quickstart.sh --minimal --vllm

# 开发者安装 + 准备 VLLM 环境 + pip 环境
./quickstart.sh --dev --vllm --pip
```

### 功能特性

- ✅ **环境准备**: 确保 VLLM 启动脚本可执行并提供使用指南
- ✅ **延迟安装**: VLLM 在首次使用时自动安装，避免不必要的安装时间
- ✅ **智能检测**: vllm_local_serve.sh 会自动检测 CUDA 支持并安装对应版本
- ✅ **使用指南**: 安装完成后提供详细的使用提示和推荐模型
- ✅ **状态验证**: 检查 VLLM 当前安装状态

### 工作流程

1. **环境准备阶段**（quickstart.sh --vllm）：
   - 检查 `vllm_local_serve.sh` 脚本是否存在
   - 设置脚本执行权限
   - 检查当前 VLLM 安装状态
   - 显示使用指南和推荐模型

2. **实际安装阶段**（首次运行 vllm_local_serve.sh）：
   - 自动检测和安装 VLLM
   - 智能网络检测和镜像设置
   - 模型下载和缓存管理

### 安装后使用

安装完成后，推荐使用 SAGE CLI 启动 VLLM 服务：

```bash
# 推荐方式：使用 SAGE CLI（默认 vllm 服务）
sage llm start                                    # 使用默认模型（microsoft/DialoGPT-small）
sage llm start --model microsoft/DialoGPT-medium  # 使用指定模型
sage llm start --background                       # 后台运行
sage llm status                                   # 查看服务状态
sage llm stop                                     # 停止服务
```

**传统方式（已废弃）：**
```bash
# 传统脚本方式（不再推荐使用）
# ./tools/vllm/vllm_local_serve.sh                   # 使用默认模型
# ./tools/vllm/vllm_local_serve.sh microsoft/DialoGPT-medium  # 使用指定模型
```

> ⚠️ **重要**：传统的 `tools/vllm` 脚本已被废弃，请使用 `sage llm` 命令。

### 推荐模型

| 模型名称 | 大小 | 适用场景 | 内存需求 |
|---------|------|----------|----------|
| `microsoft/DialoGPT-small` | ~500MB | 轻量测试 | 2GB+ |
| `microsoft/DialoGPT-medium` | ~1.5GB | 一般对话 | 4GB+ |
| `microsoft/DialoGPT-large` | ~3GB | 高质量对话 | 8GB+ |
| `meta-llama/Llama-2-7b-chat-hf` | ~14GB | 专业应用 | 16GB+ |

### 验证安装

```bash
# 验证 VLLM 安装
python -c "import vllm; print(vllm.__version__)"

# 验证相关依赖
python -c "import transformers, torch, accelerate; print('All dependencies OK')"
```

### 系统要求

- **操作系统**: Linux/macOS
- **Python**: 3.8+
- **内存**: 最少 4GB，推荐 8GB+
- **存储**: 根据模型大小，至少预留 2GB
- **GPU**: 可选，支持 CUDA 11.0+ 的 NVIDIA GPU

### 网络要求

- 首次运行时需要下载模型（大小根据模型而定）
- 脚本自动检测网络连接，必要时使用 HuggingFace 镜像
- 支持离线使用（模型下载完成后）

### 故障排除

1. **CUDA 检测失败**
   ```bash
   # 检查 NVIDIA 驱动
   nvidia-smi
   
   # 检查 CUDA 版本
   nvcc --version
   ```

2. **内存不足**
   - 使用更小的模型（如 DialoGPT-small）
   - 关闭其他占用内存的程序

3. **网络连接问题**
   - 脚本会自动设置 HuggingFace 镜像
   - 手动设置：`export HF_ENDPOINT=https://hf-mirror.com`

4. **安装验证失败**
   ```bash
   # 手动验证
   python -c "import vllm; print('VLLM installed successfully')"
   
   # 查看安装日志
   cat install.log | grep -i vllm
   ```

## 文件结构

新增的文件和修改：

```
tools/install/installation_table/vllm_installer.sh  # VLLM 安装模块
tools/install/download_tools/argument_parser.sh     # 修改：添加 --vllm 参数支持
tools/install/installation_table/main_installer.sh  # 修改：集成 VLLM 安装
quickstart.sh                                       # 修改：传递 VLLM 参数
```

## 更多信息

- SAGE CLI 帮助：`sage llm --help`
- VLLM 服务状态：`sage llm status`
- 安装日志：`install.log`
