# isage-amms PyPI 构建和发布策略

## 问题分析

### 1. PAPI 系统依赖问题

**问题**：libpapi-dev 是系统级 C/C++ 库，无法通过 pip 自动安装

**解决方案**：

- ✅ **智能检测**：setup.py 自动检测系统是否有 libpapi-dev
- ✅ **自动启用**：如果检测到 libpapi-dev，自动启用 PAPI
- ✅ **优雅降级**：如果未检测到，自动禁用但不影响安装
- ✅ **可覆盖**：通过 `ENABLE_AMMS_PAPI=1/0` 强制启用/禁用

**检测逻辑**：

```python
def check_papi_available():
    # 方法1: pkg-config --exists papi
    # 方法2: 查找 /usr/lib/libpapi.so
    return True/False

env_papi = os.environ.get("ENABLE_AMMS_PAPI", "auto")
if env_papi == "auto":
    enable_papi = check_papi_available()  # 自动检测
else:
    enable_papi = env_papi == "1"  # 用户指定
```

**用户场景**：

```bash
# 场景1: 有 libpapi-dev（自动启用）
sudo apt-get install libpapi-dev
pip install isage-amms --no-binary :all:
# ✓ PAPI support auto-enabled (libpapi-dev detected)

# 场景2: 无 libpapi-dev（自动禁用）
pip install isage-amms --no-binary :all:
# ℹ PAPI support auto-disabled (libpapi-dev not found)
# ✓ 安装仍然成功

# 场景3: 强制启用（用于 CI/测试）
ENABLE_AMMS_PAPI=1 pip install isage-amms --no-binary :all:

# 场景4: 强制禁用
ENABLE_AMMS_PAPI=0 pip install isage-amms --no-binary :all:
```

### 2. CUDA vs CPU-only 构建策略

**问题**：PyPI 包应该包含 CUDA 支持还是仅 CPU？

**推荐策略：CPU-only（与主流 PyTorch 扩展一致）**

#### 理由：

1. **兼容性最广**

   - CPU-only 可在所有机器上运行（包括没有 GPU 的机器）
   - CUDA 版本只能在特定 GPU 架构上运行

1. **二进制兼容性问题**

   - CUDA 版本需要匹配用户的 CUDA 版本（11.8, 12.1, 12.4...）
   - CUDA 版本需要匹配 PyTorch 的 CUDA 版本
   - CPU-only 无此限制

1. **主流实践**

   - **PyTorch**: 默认 CPU，CUDA 通过特殊索引安装
     ```bash
     pip install torch  # CPU
     pip install torch --index-url https://download.pytorch.org/whl/cu121  # CUDA 12.1
     ```
   - **TensorFlow**: 默认 CPU，GPU 版本是单独包
     ```bash
     pip install tensorflow  # CPU
     pip install tensorflow[and-cuda]  # GPU
     ```
   - **FAISS**: 提供多个包
     ```bash
     pip install faiss-cpu
     pip install faiss-gpu
     ```

1. **文件大小**

   - CPU-only: ~50-100MB
   - CUDA: ~200-500MB（包含 CUDA 库）

#### 推荐方案：提供两个安装选项

**方案 A：单一 CPU-only 包（推荐）**

```bash
# PyPI 只发布 CPU 版本
pip install isage-amms

# CUDA 用户从源码构建
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-libs
ENABLE_CUDA=1 pip install -e .
```

**优点**：

- ✅ 简单维护，只需发布一个包
- ✅ 兼容性最好
- ✅ 文件大小小
- ✅ CUDA 用户可轻松从源码构建

**方案 B：多个包（类似 FAISS）**

```bash
pip install isage-amms           # CPU-only
pip install isage-amms-gpu       # CUDA 12.1
pip install isage-amms-gpu-cu118 # CUDA 11.8
```

**缺点**：

- ❌ 需要维护多个包
- ❌ 需要为每个 CUDA 版本构建
- ❌ 容易混淆用户

## 最终推荐策略

### PyPI 发布：CPU-only + PAPI 禁用

```bash
# PyPI 构建命令
cd packages/sage-libs/src/sage/libs/amms

# 确保环境干净
rm -rf build dist *.egg-info

# 构建 CPU-only wheel（PAPI 默认禁用）
python setup.py bdist_wheel

# 上传到 PyPI
twine upload dist/isage_amms-*.whl
```

### 配置摘要

| 选项 | PyPI 默认值 | 智能检测              | 用户可覆盖                |
| ---- | ----------- | --------------------- | ------------------------- |
| CUDA | ❌ 禁用     | ❌                    | ✅ `ENABLE_CUDA=1`        |
| PAPI | ⚙️ 自动     | ✅ pkg-config/lib查找 | ✅ `ENABLE_AMMS_PAPI=1/0` |
| HDF5 | ✅ 启用     | ❌                    | ✅ `ENABLE_HDF5=0`        |

**PAPI 智能检测规则**：

- `ENABLE_AMMS_PAPI=auto`（默认）：自动检测系统是否有 libpapi-dev
- `ENABLE_AMMS_PAPI=1`：强制启用（构建失败如果没有 libpapi-dev）
- `ENABLE_AMMS_PAPI=0`：强制禁用

### 用户安装指南

#### 1. 标准用户（PyPI 预编译包）

```bash
# 最简单，适合 99% 用户
pip install isage-amms
```

**功能**：

- ✅ CPU-only AMM 算法
- ✅ 所有核心功能
- ✅ PAPI 自动检测（如果系统有 libpapi-dev）
- ❌ 无 CUDA 加速

#### 2. GPU 用户（从源码构建）

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-libs

# 构建 CUDA 版本
ENABLE_CUDA=1 pip install -e .
```

**功能**：

- ✅ CPU + CUDA AMM 算法
- ✅ GPU 加速
- ❌ 无 PAPI（除非额外启用）

#### 3. 性能分析用户（PAPI）

```bash
# 安装系统库
sudo apt-get install libpapi-dev

# 从源码构建并启用 PAPI
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-libs
ENABLE_AMMS_PAPI=1 pip install -e .
```

**功能**：

- ✅ CPU AMM 算法
- ✅ PAPI 硬件性能计数器
- ❌ 无 CUDA（除非额外启用）

#### 4. 完整功能（CUDA + PAPI）

```bash
# 安装系统库
sudo apt-get install libpapi-dev

# 从源码构建，全部启用
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-libs
ENABLE_CUDA=1 ENABLE_AMMS_PAPI=1 pip install -e .
```

## 更新 README 建议

在 `packages/sage-libs/src/sage/libs/amms/README.md` 添加：

````markdown
## Installation Options

### Quick Install (Recommended for Most Users)

```bash
pip install isage-amms
````

This installs the CPU-only version with all core AMM algorithms.

### GPU Support (Build from Source)

For CUDA acceleration:

```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-libs
ENABLE_CUDA=1 pip install -e .
```

### Hardware Performance Counters (Optional)

For PAPI hardware performance analysis:

```bash
# Install system library
sudo apt-get install libpapi-dev

# Build with PAPI
ENABLE_AMMS_PAPI=1 pip install isage-amms --no-binary :all:
```

### Full Features

```bash
sudo apt-get install libpapi-dev
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-libs
ENABLE_CUDA=1 ENABLE_AMMS_PAPI=1 pip install -e .
```

````

## CI/CD 构建配置

### GitHub Actions

```yaml
name: Build and Publish isage-amms

on:
  release:
    types: [published]

jobs:
  build-wheels:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install build twine
          pip install torch --index-url https://download.pytorch.org/whl/cpu

      - name: Build wheel (CPU-only, PAPI disabled)
        run: |
          cd packages/sage-libs/src/sage/libs/amms
          python -m build --wheel

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          twine upload packages/sage-libs/src/sage/libs/amms/dist/*.whl
````

## 总结

| 场景                       | 安装方式                             | CUDA | PAPI        |
| -------------------------- | ------------------------------------ | ---- | ----------- |
| **PyPI 发布**              | `pip install isage-amms`             | ❌   | ⚙️ 自动检测 |
| 标准用户（有 libpapi-dev） | PyPI                                 | ❌   | ✅ 自动启用 |
| 标准用户（无 libpapi-dev） | PyPI                                 | ❌   | ❌ 自动禁用 |
| GPU 用户                   | 源码 + `ENABLE_CUDA=1`               | ✅   | ⚙️ 自动检测 |
| 性能分析                   | 源码 + 安装 libpapi-dev              | ❌   | ✅ 自动启用 |
| 完整功能                   | 源码 + `ENABLE_CUDA=1` + libpapi-dev | ✅   | ✅ 自动启用 |

**关键原则**：

1. ✅ **智能检测优先**：PAPI 自动检测，无需用户干预
1. ✅ **优雅降级**：缺少 libpapi-dev 时自动禁用，不影响安装
1. ✅ **PyPI 默认值最大化兼容性**：CPU-only + PAPI 自动检测
1. ✅ **源码构建支持所有高级功能**：CUDA + PAPI 完全可控
1. ✅ **清晰文档说明每个选项**
1. ✅ **遵循 PyTorch/TensorFlow 最佳实践**
