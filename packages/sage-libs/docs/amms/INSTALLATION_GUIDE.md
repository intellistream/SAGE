# isage-amms 安装指南（简化版）

## 快速安装

### 1. CPU-only 版本（推荐大多数用户）

```bash
pip install isage-amms
```

**特性**：

- ✅ 适用所有机器
- ✅ 自动检测 PAPI（如果有 libpapi-dev）
- ✅ 最小体积 (~50-100MB)

### 2. GPU 加速版本

```bash
# Step 1: 安装支持 CUDA 的 PyTorch
pip install torch --index-url https://download.pytorch.org/whl/cu121  # CUDA 12.1

# Step 2: 从源码构建（CUDA 自动检测）
pip install isage-amms --no-binary :all:
```

**特性**：

- ✅ 自动检测 PyTorch CUDA 支持
- ✅ GPU 加速
- ✅ PAPI 自动检测

**原理**：setup.py 通过 `torch.cuda.is_available()` 自动检测 CUDA 支持

### 3. 启用 PAPI 性能分析

```bash
# 安装系统库
sudo apt-get install libpapi-dev

# 重新安装（自动检测 PAPI）
pip install isage-amms --no-binary :all:
```

## 智能检测机制

### CUDA 检测

```python
# setup.py 自动检测逻辑
import torch
enable_cuda = torch.cuda.is_available()
```

**环境变量覆盖**：

- `ENABLE_CUDA=1`: 强制启用
- `ENABLE_CUDA=0`: 强制禁用
- `ENABLE_CUDA=auto`（默认）: 自动检测

### PAPI 检测

```python
# setup.py 自动检测逻辑
# 1. pkg-config --exists papi
# 2. 查找 /usr/lib/libpapi.so
```

**环境变量覆盖**：

- `ENABLE_AMMS_PAPI=1`: 强制启用
- `ENABLE_AMMS_PAPI=0`: 强制禁用
- `ENABLE_AMMS_PAPI=auto`（默认）: 自动检测

## PyPI 发布策略

### 发布版本：CPU-only 预编译 wheel

```bash
# PyPI 上传的包
pip install isage-amms  # CPU-only, 最大兼容性
```

### 用户场景矩阵

| 场景            | 命令                                       | CUDA    | PAPI    | 说明       |
| --------------- | ------------------------------------------ | ------- | ------- | ---------- |
| **标准用户**    | `pip install isage-amms`                   | ❌      | ⚙️ 自动 | PyPI wheel |
| 有 libpapi-dev  | `pip install isage-amms --no-binary :all:` | ❌      | ✅ 自动 | 从源码     |
| 有 CUDA PyTorch | `pip install isage-amms --no-binary :all:` | ✅ 自动 | ⚙️ 自动 | 从源码     |
| GPU + PAPI      | 安装 libpapi-dev + CUDA PyTorch            | ✅      | ✅      | 全自动     |
| 强制 CPU        | `ENABLE_CUDA=0 pip install`                | ❌      | ⚙️      | 覆盖       |

## 与其他库的对比

| 库             | CPU 默认 | GPU 安装方式            | 原理       |
| -------------- | -------- | ----------------------- | ---------- |
| **PyTorch**    | ✅       | `--index-url .../cu121` | 不同 wheel |
| **TensorFlow** | ✅       | `tensorflow[and-cuda]`  | extras     |
| **FAISS**      | ✅       | `faiss-gpu`             | 独立包     |
| **isage-amms** | ✅       | 自动检测 PyTorch CUDA   | 智能检测   |

**优势**：

- ✅ 无需记忆 extras 语法
- ✅ 自动跟随 PyTorch 配置
- ✅ 统一的安装命令

## 配置摘要

| 选项 | PyPI 默认 | 检测方式                    | 用户覆盖               |
| ---- | --------- | --------------------------- | ---------------------- |
| CUDA | ❌        | `torch.cuda.is_available()` | `ENABLE_CUDA=1/0`      |
| PAPI | ⚙️ 自动   | pkg-config + 库文件         | `ENABLE_AMMS_PAPI=1/0` |
| HDF5 | ✅        | N/A                         | `ENABLE_HDF5=0`        |

## 故障排除

### CUDA 未检测到

**问题**: 明明有 GPU 但 CUDA 未启用

**解决**:

```bash
# 检查 PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# 如果返回 False，需要重装 PyTorch
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 强制启用 CUDA
ENABLE_CUDA=1 pip install isage-amms --no-binary :all:
```

### PAPI 未检测到

**问题**: 安装了 libpapi-dev 但未启用

**解决**:

```bash
# 检查 pkg-config
pkg-config --exists papi && echo "PAPI found" || echo "PAPI not found"

# 如果未找到，检查库文件
ls -l /usr/lib/libpapi.so
ls -l /usr/lib/x86_64-linux-gnu/libpapi.so

# 强制启用
ENABLE_AMMS_PAPI=1 pip install isage-amms --no-binary :all:
```

## 开发者文档

### 测试自动检测

```bash
# 测试 CUDA 检测
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 测试 PAPI 检测
pkg-config --exists papi && echo "PAPI: True" || echo "PAPI: False"

# 完整构建测试
pip install -e . --no-build-isolation -v
```

### 添加新的检测逻辑

在 `setup.py` 的 `build_extension` 方法中添加：

```python
def check_feature_available():
    """检测某个特性是否可用"""
    # 实现检测逻辑
    return True/False

enable_feature = check_feature_available()
cmake_args.append("-DENABLE_FEATURE=ON" if enable_feature else "-DENABLE_FEATURE=OFF")
```

## 总结

**关键原则**：

1. ✅ **智能检测优先**：自动检测 CUDA 和 PAPI
1. ✅ **优雅降级**：缺少依赖时自动禁用，不影响安装
1. ✅ **用户友好**：一条命令，无需额外配置
1. ✅ **遵循最佳实践**：参考 PyTorch/TensorFlow 策略
1. ✅ **可覆盖**：环境变量允许手动控制

**用户体验**：

- 标准用户：`pip install isage-amms` → 一切自动
- GPU 用户：安装 CUDA PyTorch → 自动检测 → 无需配置
- 性能分析：安装 libpapi-dev → 自动检测 → 无需配置
