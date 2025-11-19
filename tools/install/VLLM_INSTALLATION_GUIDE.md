# SAGE vLLM 安装指南

## 📋 版本要求

**重要**: vLLM 0.10.x+ 需要特定的 PyTorch 版本

| vLLM 版本   | 所需 Torch 版本 | Python 版本 | 备注                         |
| ----------- | --------------- | ----------- | ---------------------------- |
| 0.11.x      | >= 2.5.0        | >= 3.9      | 最新版                       |
| 0.10.x      | >= 2.4.0        | >= 3.9      | 需要 torch.\_inductor.config |
| 0.9.x       | >= 2.3.0        | >= 3.8      |                              |
| 0.4.x-0.8.x | >= 2.2.0        | >= 3.8      | 稳定版                       |

## 🚀 快速安装

### 方法 1: 使用 quickstart.sh（推荐）

```bash
# 默认安装 + 准备 VLLM 环境
./quickstart.sh --vllm

# 开发者安装 + 准备 VLLM 环境
./quickstart.sh --dev --vllm
```

安装脚本会自动：

- ✅ 检查并修复依赖版本冲突
- ✅ 安装兼容的 torch 和 vllm 版本
- ✅ 验证安装结果

### 方法 2: 使用自动修复脚本

```bash
# 一键修复版本冲突
./tools/install/fix_vllm_torch.sh

# 非交互模式（CI/CD）
./tools/install/fix_vllm_torch.sh --non-interactive
```

### 方法 3: 使用锁定的依赖版本

```bash
# 安装锁定版本（确保兼容性）
pip install -r tools/install/requirements-vllm-lock.txt
```

### 方法 4: 手动安装

```bash
# 卸载旧版本
pip uninstall -y torch torchaudio torchvision vllm xformers outlines

# 安装 vLLM（会自动安装兼容的 torch）
pip install vllm==0.10.1.1

# 验证安装
python tools/install/verify_dependencies.py
```

## ⚠️ 常见问题

### 错误: `module 'torch._inductor' has no attribute 'config'`

**原因**: torch 版本太旧（< 2.4.0）

**解决方案**:

```bash
./tools/install/fix_vllm_torch.sh
```

详细说明请参考:
[docs/dev-notes/l0-infra/vllm-torch-version-conflict.md](../../docs/dev-notes/l0-infra/vllm-torch-version-conflict.md)

### 错误: `outlines_core` 版本冲突

**原因**: outlines 和 vllm 对 outlines_core 的版本要求冲突

**解决方案**:

```bash
# 卸载 outlines（如果不需要）
pip uninstall -y outlines

# 保持 outlines_core==0.2.10（vllm 需要）
pip install outlines_core==0.2.10
```

## ✅ 验证安装

运行依赖验证脚本：

```bash
python tools/install/verify_dependencies.py
```

预期输出：

```
✅ 所有检查通过！
```

测试 vLLM 导入：

```bash
python -c "import vllm; print(f'vLLM version: {vllm.__version__}')"
python -c "import torch._inductor.config; print('✅ torch._inductor.config 可用')"
```

## 📚 新增功能

`quickstart.sh` 脚本现在支持 `--vllm` 选项，用于准备 VLLM 使用环境。实际的 VLLM 安装将在首次使用 `vllm_local_serve.sh` 时自动完成。

## 使用方法

### 基本用法

```bash
# 默认安装 + 准备 VLLM 环境
./quickstart.sh --vllm

# 标准安装 + 准备 VLLM 环境
./quickstart.sh --standard --vllm

# 核心安装 + 准备 VLLM 环境
./quickstart.sh --core --vllm

# 开发者安装 + 准备 VLLM 环境 + pip 环境
./quickstart.sh --dev --vllm --pip
```

### 功能特性

- ✅ **自动依赖检查**: 安装后自动检查并修复版本冲突
- ✅ **环境准备**: 确保 VLLM 启动脚本可执行并提供使用指南
- ✅ **延迟安装**: VLLM 在首次使用时自动安装，避免不必要的安装时间
- ✅ **智能检测**: vllm_local_serve.sh 会自动检测 CUDA 支持并安装对应版本
- ✅ **使用指南**: 安装完成后提供详细的使用提示和推荐模型
- ✅ **状态验证**: 检查 VLLM 当前安装状态

### 工作流程

1. **环境准备阶段**（quickstart.sh --vllm）：

   - 检查 `vllm_local_serve.sh` 脚本是否存在
   - 设置脚本执行权限
   - **检查依赖版本兼容性**（新增）
   - **自动修复版本冲突**（新增）
   - 检查当前 VLLM 安装状态
   - 显示使用指南和推荐模型

1. **实际安装阶段**（首次运行 vllm_local_serve.sh）：

   - 自动检测和安装 VLLM
   - 智能网络检测和镜像设置
   - 模型下载和缓存管理

### 安装后使用

安装完成后，推荐使用 SAGE CLI 的阻塞式 VLLM 服务与模型管理功能：

```bash
# 查看本地与远程模型信息（包含大小、路径、缓存状态）
sage llm model show

# 预下载或删除模型（默认会放到 ~/.cache/sage/vllm）
sage llm model download meta-llama/Llama-2-7b-chat-hf
sage llm model delete microsoft/DialoGPT-small

# 运行阻塞式推理服务（支持流式或一次性输出）
sage llm run --model meta-llama/Llama-2-7b-chat-hf --prompt "Hello"

# 占位命令：微调流程将在后续版本开放
sage llm fine-tune --help
```

如果仍需兼容旧的后台服务管理命令，可继续使用 `sage llm start|status|stop`，但这些命令会打印弃用提示并将在未来移除。

> ⚠️ **重要**：传统的 `tools/vllm` 脚本已被废弃，请使用新的 `sage llm` CLI 功能。

### 推荐模型

| 模型名称                        | 大小   | 适用场景   | 内存需求 |
| ------------------------------- | ------ | ---------- | -------- |
| `microsoft/DialoGPT-small`      | ~500MB | 轻量测试   | 2GB+     |
| `microsoft/DialoGPT-medium`     | ~1.5GB | 一般对话   | 4GB+     |
| `microsoft/DialoGPT-large`      | ~3GB   | 高质量对话 | 8GB+     |
| `meta-llama/Llama-2-7b-chat-hf` | ~14GB  | 专业应用   | 16GB+    |

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

1. **内存不足**

   - 使用更小的模型（如 DialoGPT-small）
   - 关闭其他占用内存的程序

1. **网络连接问题**

   - 脚本会自动设置 HuggingFace 镜像
   - 手动设置：`export HF_ENDPOINT=https://hf-mirror.com`

1. **安装验证失败**

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
