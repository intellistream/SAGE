# Dependency Management and Packaging Optimization

This document outlines the strategies used in SAGE to optimize dependency management and packaging,
aiming to improve user installation experience, compatibility, and maintainability.

## 1. Dependency Versioning Strategy

To enhance compatibility with other packages in the user's environment, we have adopted a flexible
versioning strategy for our dependencies.

### Problem

Previously, many dependencies in `pyproject.toml` were pinned to exact versions (e.g.,
`torch==2.7.1`). This approach, while ensuring deterministic builds, could lead to conflicts when
users had other packages requiring different versions of the same dependency.

### Solution

We have relaxed the version constraints to allow for a range of compatible versions. The new
strategy is as follows:

- **Use ranged versions**: Instead of pinning to an exact version, we now specify a compatible
  range. For example, `torch>=2.7.0,<3.0.0`. This allows `pip` to select a version that satisfies
  the requirements of SAGE and other installed packages.
- **Major version cap**: We cap the upper bound to the next major version (e.g., `<3.0.0`) to avoid
  pulling in potentially breaking changes from new major releases.
- **Flexible patch versions**: For most libraries, we allow patch and minor version updates, which
  are generally backward-compatible.

**Example (`packages/sage-kernel/pyproject.toml`):**

```toml
# Before
torch==2.7.1

# After
torch>=2.7.0,<3.0.0
```

This change significantly reduces the likelihood of dependency conflicts during installation.

## 2. Optional Dependencies and `extras`

SAGE is a modular framework, and not all users require all of its features. To cater to different
use cases, we have structured our dependencies into `extras`.

### Problem

A monolithic dependency list forces users to install packages they may not need (e.g., GPU-specific
libraries on a CPU-only machine), leading to bloated environments and longer installation times.

### Solution

We have defined several `extras` that allow users to install only the components they need.

**Key `extras` in `isage-kernel`:**

- `[gpu]`: Installs dependencies required for GPU acceleration. This is the default for `torch`.
- `[cpu]`: Ensures that CPU-only versions of libraries are used where applicable.
- `[web]`: Installs packages for web-based functionalities (e.g., `fastapi`, `uvicorn`).
- `[monitoring]`: Adds support for monitoring tools.

**Installation Examples:**

- **Minimal CPU installation:**

  ```bash
  pip install isage-kernel[cpu]
  ```

- **GPU installation with web support:**

  ```bash
  pip install isage-kernel[gpu,web]
  ```

This approach provides a more tailored and efficient installation experience.

## 3. Pre-compiled Wheels for C++ Extensions

Some SAGE components, like `sage-middleware`, include C++ extensions for performance-critical
operations. Compiling these extensions on the user's machine can be slow and error-prone, especially
if build tools (like a C++ compiler and CMake) are not pre-installed.

### Problem

- **Slow installation**: Source distributions (`sdist`) require local compilation, which can take
  several minutes.
- **Compilation errors**: Users may lack the necessary build toolchain, leading to installation
  failures.
- **Inconsistent environments**: Differences in local build environments can lead to subtle bugs.

### Solution

We pre-compile binary wheels for our C++ extensions for a variety of common platforms (Linux, macOS,
Windows) and Python versions (3.10, 3.11, 3.12).

We use `cibuildwheel` in our GitHub Actions workflow (`.github/workflows/build-wheels.yml`) to
automate this process. When a new version of SAGE is released, this workflow builds the wheels and
uploads them to PyPI alongside the source distribution.

**Benefits:**

- **Faster installation**: `pip` will automatically download and install the appropriate
  pre-compiled wheel, skipping the local compilation step entirely. This reduces installation time
  from minutes to seconds.
- **Improved reliability**: Since no local compilation is needed, the risk of installation failure
  due to missing build tools is eliminated.
- **Consistency**: All users get the same compiled binary, ensuring consistent behavior across
  different machines.

When a user runs `pip install isage-middleware`, `pip` intelligently selects the compatible wheel
for their system. If a pre-compiled wheel is not available for their specific platform (e.g., a less
common Linux distribution), `pip` falls back to downloading the source distribution (`sdist`) and
compiling it locally, ensuring that the package can still be installed.

## 4. Torch & vLLM Compatibility Guide

Torch 和 vLLM 的版本必须保持同步，否则会出现 `torch._inductor.config` 缺失或 CUDA 运算符注册失败等问题。SAGE 已经在
`packages/sage-common/pyproject.toml` 中通过 extras 为可选的 vLLM 功能声明了如下约束：

```toml
[project.optional-dependencies]
vllm = [
  "vllm>=0.10.1",
  "torch>=2.4.0",
  "torchaudio>=2.4.0",
  "torchvision>=0.17.0",
]
```

### 快速自检

1. 运行 `python tools/install/verify_dependencies.py --verbose`，脚本会自动检查 torch/vLLM 组合是否满足上述范围。
1. CI 失败时可参考 `.github/workflows/code-quality.yml` 中的 "Verify Dependency Compatibility" 步骤输出。
1. 如果看到 `AttributeError: module 'torch._inductor' has no attribute 'config'`，说明当前 torch 版本 \<
   2.4，需要升级。

### 推荐修复步骤

```bash
# 1. 卸载旧版本
pip uninstall -y torch torchaudio torchvision vllm

# 2. 安装兼容组合（默认会拉取 >=2.4 的 torch）
pip install vllm==0.10.1.1

# 3. 重新验证
python tools/install/verify_dependencies.py
```

在企业或自定义镜像环境中，可以使用 `tools/install/fix_vllm_torch.sh --non-interactive` 自动完成上述流程。

### 诊断 checklist

- `python -c "import torch, vllm; print(torch.__version__, vllm.__version__)"` 输出的 torch 主版本应 ≥ 2.4。
- `python -c "import torch._inductor.config"` 成功返回表示启用了 inductor。
- `python tools/install/verify_dependencies.py` 返回 0。
- 需要 GPU 支持时，确保 `nvidia-smi` 和 `torch.cuda.is_available()` 正常。

额外说明：`packages/sage-middleware/pyproject.toml` 中的 `vllm` extras 也会引用同样的约束，保持分层一致性即可。
