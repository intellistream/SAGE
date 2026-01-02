# vLLM 和 Torch 版本冲突问题分析与修复

## 🐛 问题描述

在运行 `sage-dev` 命令时出现以下错误：

```python
AttributeError: module 'torch._inductor' has no attribute 'config'
```

## 🔍 根本原因分析

### 1. 版本不匹配

**当前安装的版本**:

- torch: 2.2.0+cpu
- vllm: 0.10.1.1

**vllm 0.10.1.1 的实际要求**:

```
Requires-Dist: torch==2.7.1
Requires-Dist: torchaudio==2.7.1
Requires-Dist: torchvision==0.22.1
```

### 2. 为什么会出现这个问题？

1. **pip 的依赖解析问题**:

   - vllm 0.10.1.1 在 `METADATA` 中明确要求 `torch==2.7.1`
   - 但由于某种原因（可能是安装时使用了 `--no-deps` 或先安装了旧版 torch），pip 没有自动升级 torch

1. **torch.\_inductor.config 的引入时间**:

   - `torch._inductor.config` 是在 torch 2.4.0+ 版本中引入的
   - torch 2.2.0 没有这个属性，导致 vllm 无法导入

1. **项目依赖配置不够严格**:

   - `packages/sage-common/pyproject.toml` 中只指定了 `vllm>=0.9.2`
   - 没有明确指定 torch 的版本要求

## 🔧 解决方案

### 方案 1: 升级 torch 到兼容版本（推荐）

```bash
# 1. 卸载当前的 torch 和 vllm
pip uninstall -y torch torchaudio torchvision vllm xformers

# 2. 重新安装 vllm（会自动安装正确版本的 torch）
pip install vllm==0.10.1.1

# 或者直接安装最新版本
pip install vllm
```

### 方案 2: 降级 vllm 到兼容 torch 2.2.0 的版本

```bash
# 查找兼容 torch 2.2.0 的 vllm 版本
# vllm 0.3.x - 0.4.x 系列支持 torch 2.2.0

pip uninstall -y vllm
pip install vllm==0.4.3
```

### 方案 3: 使用 CPU-only 版本的 torch（如果不需要 GPU）

```bash
# 卸载当前版本
pip uninstall -y torch torchaudio torchvision

# 安装 CPU 版本的 torch 2.7.1
pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu torchvision==0.22.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# 重新安装 vllm
pip install vllm==0.10.1.1
```

## 📝 项目依赖配置改进

### 1. 更新 pyproject.toml

为了防止类似问题再次发生，应该在 `packages/sage-common/pyproject.toml` 中明确指定 torch 版本：

```toml
[project.optional-dependencies]
vllm = [
    "vllm>=0.10.1",
    "torch>=2.4.0",  # 添加明确的 torch 版本要求
]

# 或者更精确的版本锁定
vllm = [
    "vllm==0.10.1.1",
    "torch==2.7.1",
    "torchaudio==2.7.1",
    "torchvision==0.22.1",
]
```

### 2. 创建 requirements-vllm.txt

创建一个专门的 vllm 依赖文件，确保版本一致性：

```txt
# requirements-vllm.txt
# vLLM and its dependencies with pinned versions

vllm==0.10.1.1
torch==2.7.1
torchaudio==2.7.1
torchvision==0.22.1
xformers==0.0.31; platform_system == "Linux" and platform_machine == "x86_64"
```

### 3. 更新安装文档

在 `tools/install/VLLM_INSTALLATION_GUIDE.md` 中添加版本兼容性说明。

## 🛡️ 防止未来出现类似问题

### 1. 添加依赖验证脚本

创建 `tools/install/verify_dependencies.py`:

```python
#!/usr/bin/env python3
"""验证关键依赖的版本兼容性"""

import sys
from packaging import version

def verify_torch_vllm_compatibility():
    """验证 torch 和 vllm 的版本兼容性"""
    try:
        import torch
        import vllm

        torch_version = version.parse(torch.__version__.split('+')[0])
        vllm_version = version.parse(vllm.__version__)

        # vllm 0.10.x 需要 torch >= 2.4.0
        if vllm_version >= version.parse("0.10.0"):
            if torch_version < version.parse("2.4.0"):
                print(f"❌ 版本冲突: vllm {vllm.__version__} 需要 torch >= 2.4.0")
                print(f"   当前 torch 版本: {torch.__version__}")
                return False

        print(f"✅ 版本兼容: torch {torch.__version__} + vllm {vllm.__version__}")
        return True

    except ImportError as e:
        print(f"⚠️  无法导入依赖: {e}")
        return True  # 可选依赖，不报错
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    if not verify_torch_vllm_compatibility():
        sys.exit(1)
```

### 2. 在 pre-commit 中添加依赖检查

在 `.pre-commit-config.yaml` 中添加：

```yaml
- repo: local
  hooks:
  - id: verify-dependencies
    name: verify dependency versions
    entry: python tools/install/verify_dependencies.py
    language: system
    pass_filenames: false
    always_run: true
```

### 3. 在 CI/CD 中添加检查

在 GitHub Actions 中添加依赖验证步骤：

```yaml
- name: Verify dependency compatibility
  run: |
    python tools/install/verify_dependencies.py
```

## 📊 vLLM 版本兼容性表

| vLLM 版本 | 所需 Torch 版本 | Python 版本 | 备注                         |
| --------- | --------------- | ----------- | ---------------------------- |
| 0.11.x    | >= 2.5.0        | >= 3.9      | 最新版                       |
| 0.10.x    | >= 2.4.0        | >= 3.9      | 需要 torch.\_inductor.config |
| 0.9.x     | >= 2.3.0        | >= 3.8      |                              |
| 0.8.x     | >= 2.2.0        | >= 3.8      |                              |
| 0.4.x     | >= 2.2.0        | >= 3.8      | 稳定版，兼容旧 torch         |

## 🚀 立即修复步骤

```bash
# 1. 进入 SAGE 目录
cd /home/shuhao/SAGE

# 2. 激活环境
conda activate sage

# 3. 卸载冲突的包
pip uninstall -y torch torchaudio torchvision vllm xformers

# 4. 重新安装兼容版本
pip install vllm==0.10.1.1

# 5. 验证安装
python -c "import torch; print(f'Torch: {torch.__version__}')"
python -c "import vllm; print(f'vLLM: {vllm.__version__}')"
python -c "import torch._inductor.config; print('✅ torch._inductor.config 可用')"

# 6. 测试 sage-dev
sage-dev --help
```

## 📚 相关资源

- [vLLM 官方文档](https://docs.vllm.ai/)
- [vLLM GitHub Releases](https://github.com/vllm-project/vllm/releases)
- [PyTorch 版本历史](https://pytorch.org/get-started/previous-versions/)
- [SAGE vLLM 安装指南](../../../../tools/install/VLLM_INSTALLATION_GUIDE.md)

## ✅ 验证清单

- [ ] torch 版本 >= 2.4.0（对于 vllm 0.10.x）
- [ ] vllm 成功导入
- [ ] `torch._inductor.config` 可访问
- [ ] sage-dev 命令正常工作
- [ ] 更新了 pyproject.toml 中的版本约束
- [ ] 添加了依赖验证脚本
- [ ] 更新了安装文档
