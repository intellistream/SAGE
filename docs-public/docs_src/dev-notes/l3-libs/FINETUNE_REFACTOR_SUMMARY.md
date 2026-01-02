# SAGE Finetune 重构总结

**Date**: 2024-10-12\
**Author**: SAGE Team\
**Summary**: Finetune 模块重构总结

______________________________________________________________________

> **✅ 当前文档**: 本文档描述了微调功能的模块化重构。完整 API 文档和使用指南见
> `packages/sage-tools/src/sage/tools/finetune/README.md`。

## 🎯 重构目标

将微调功能从单一脚本重构为模块化、可扩展的组件，为未来作为独立子模块做准备。

## 📦 新的目录结构

```
SAGE/
├── packages/
│   └── sage-tools/
│       └── src/sage/tools/
│           ├── cli/commands/
│           │   └── finetune.py  # CLI 接口层
│           └── finetune/  # ⭐ 核心微调模块
│               ├── __init__.py      # 模块导出
│               ├── README.md        # 完整文档
│               ├── config.py        # 配置管理
│               ├── data.py          # 数据处理
│               └── trainer.py       # 训练器实现
```

## ✨ 主要改进

### 1. 模块化设计

**Before (单一脚本)**:

```
scripts/simple_finetune.py  (~200行，所有功能耦合)
```

**After (模块化)**:

```
sage/tools/finetune/
├── __init__.py     # 导出接口
├── config.py       # 配置管理 (~230行)
├── data.py         # 数据处理 (~200行)
└── trainer.py      # 训练器 (~250行)
```

### 2. 可扩展性

#### 作为 Python 包使用

```python
# 简单使用
from sage.tools.finetune import LoRATrainer, PresetConfigs

config = PresetConfigs.rtx_3060()
trainer = LoRATrainer(config)
trainer.train()
```

#### 二次开发

```python
# 继承扩展
from sage.tools.finetune import LoRATrainer

class MyCustomTrainer(LoRATrainer):
    def prepare_data(self):
        # 自定义数据处理
        pass
```

### 3. 预设配置

提供针对不同硬件的优化配置：

```python
from sage.tools.finetune import PresetConfigs

# RTX 3060 (12GB)
config = PresetConfigs.rtx_3060()

# RTX 4090 (24GB)
config = PresetConfigs.rtx_4090()

# A100 (40GB/80GB)
config = PresetConfigs.a100()

# 最小配置 (<8GB)
config = PresetConfigs.minimal()
```

### 4. 数据格式支持

自动检测和处理多种数据格式：

- Alpaca 格式
- QA 格式
- 对话格式
- 纯文本格式

### 5. 完整的 API

#### Config API

- `TrainingConfig` - 训练配置
- `LoRAConfig` - LoRA 配置
- `PresetConfigs` - 预设配置集合

#### Trainer API

- `LoRATrainer` - 主训练器
- `train_from_meta()` - 从元信息训练（兼容旧接口）

#### Data API

- `load_training_data()` - 加载数据
- `prepare_dataset()` - 准备数据集
- `format_*_sample()` - 格式化样本

## 🔄 使用方式

### CLI 命令

```bash
# 快速开始
sage finetune quickstart code

# 运行训练
sage finetune run finetune_output/code

# 合并权重
sage finetune merge code

# 测试模型
sage finetune chat code
```

### Python 模块使用

```python
# 方式 1: 使用配置类
from sage.tools.finetune import LoRATrainer, TrainingConfig

config = TrainingConfig(
    model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
    data_path="./data.json",
    output_dir="./output",
)
trainer = LoRATrainer(config)
trainer.train()

# 方式 2: 使用预设配置
from sage.tools.finetune import PresetConfigs

config = PresetConfigs.rtx_3060()
config.data_path = "./data.json"
trainer = LoRATrainer(config)
trainer.train()

# 方式 3: 从元信息文件训练
from sage.tools.finetune.trainer import train_from_meta
train_from_meta("finetune_output/code")
```

## � 迁移指南（如果有旧代码）

### Phase 1: 当前状态 ✅

- [x] 重构为模块化代码
- [x] 集成到 `sage-tools`
- [x] 保持 CLI 兼容性
- [x] 添加完整文档

### Phase 2: 拆分为子模块（推荐）

#### 2.1 创建独立仓库

```bash
# 1. 创建新仓库
cd /path/to/your/repos
git init sage-finetune
cd sage-finetune

# 2. 设置项目结构
mkdir -p src/sage_finetune
cp -r /path/to/SAGE/packages/sage-tools/src/sage/tools/finetune/* src/sage_finetune/

# 3. 创建 pyproject.toml
cat > pyproject.toml <<EOF
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-finetune"
version = "0.1.0"
description = "Lightweight LLM finetuning toolkit"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "transformers>=4.36.0",
    "peft>=0.7.0",
    "accelerate>=0.25.0",
    "bitsandbytes>=0.41.0",
    "datasets>=2.0.0",
]

[project.optional-dependencies]
tensorboard = ["tensorboard>=2.14.0"]
wandb = ["wandb>=0.16.0"]
full = ["sage-finetune[tensorboard,wandb]", "deepspeed>=0.12.0"]

[project.scripts]
sage-finetune = "sage_finetune.cli:main"
EOF

# 4. 初始化 Git
git add .
git commit -m "Initial commit: SAGE Finetune as standalone package"
git remote add origin https://github.com/intellistream/sage-finetune.git
git push -u origin main
```

#### 2.2 在 SAGE 中添加为子模块

```bash
cd /path/to/SAGE

# 删除现有的 finetune 目录
rm -rf packages/sage-tools/src/sage/tools/finetune

# 添加为 Git 子模块
git submodule add https://github.com/intellistream/sage-finetune.git packages/sage-finetune

# 在 sage-tools 中创建软链接（或在 pyproject.toml 中添加依赖）
ln -s ../../sage-finetune/src/sage_finetune packages/sage-tools/src/sage/tools/finetune

# 更新 .gitmodules
cat >> .gitmodules <<EOF
[submodule "packages/sage-finetune"]
    path = packages/sage-finetune
    url = https://github.com/intellistream/sage-finetune.git
EOF

# 提交更改
git add .
git commit -m "Add sage-finetune as submodule"
git push
```

#### 2.3 使用子模块

**克隆 SAGE（包含子模块）**:

```bash
git clone --recursive https://github.com/intellistream/SAGE.git

# 或已有仓库
git submodule init
git submodule update
```

**更新子模块**:

```bash
cd packages/sage-finetune
git pull origin main
cd ../..
git add packages/sage-finetune
git commit -m "Update sage-finetune submodule"
```

**独立开发子模块**:

```bash
# Fork sage-finetune 仓库
git clone https://github.com/YOUR_USERNAME/sage-finetune.git
cd sage-finetune

# 进行开发
# ...

# 提交 PR
git push origin my-feature
# 在 GitHub 上创建 PR
```

### Phase 3: 独立发布到 PyPI

```bash
# 构建包
cd packages/sage-finetune
python -m build

# 发布到 PyPI
python -m twine upload dist/*
```

**用户安装**:

```bash
# 作为独立包使用
pip install sage-finetune

# 或与 SAGE 一起使用
pip install isage-tools[finetune]
```

## 📚 文档结构

### 当前文档

1. **README.md** - 完整使用指南

   - 快速开始
   - 预设配置
   - API 文档
   - 故障排除

1. **代码文档** - 完整的文档字符串

   - 所有公共类和函数
   - 类型注解
   - 使用示例

### 未来文档（作为子模块后）

3. **docs/** - 详细文档

   - 架构设计
   - 开发指南
   - 贡献指南
   - API 参考

1. **examples/** - 示例代码

   - 基础示例
   - 高级用法
   - 自定义扩展

## 🎓 二次开发建议

### 对于想研究微调的同学

1. **Fork 独立仓库**（未来）

   ```bash
   git clone https://github.com/YOUR_USERNAME/sage-finetune.git
   ```

1. **本地开发**

   ```bash
   cd sage-finetune
   pip install -e ".[full]"
   ```

1. **修改和扩展**

   - 添加新的训练策略
   - 支持新的数据格式
   - 优化训练性能
   - 添加新的模型架构

1. **贡献回社区**

   - 提交 Issue
   - 创建 PR
   - 分享经验

### 当前开发方式

虽然还没有拆分为子模块，但代码已经模块化：

```python
# 1. 克隆 SAGE
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 定位到微调模块
cd packages/sage-tools/src/sage/tools/finetune

# 3. 进行修改
#    - 修改 trainer.py 添加新功能
#    - 修改 data.py 支持新格式
#    - 修改 config.py 添加新配置

# 4. 测试
python -m pytest tests/  # (需要添加测试)

# 5. 提交 PR 到 SAGE
```

## 🔄 迁移指南（如果有旧代码）

如果之前使用过 `scripts/simple_finetune.py`：

**旧方式**:

```bash
python scripts/simple_finetune.py finetune_output/code
```

**新方式**:

1. **使用 CLI（推荐）**:

```bash
sage finetune run finetune_output/code
```

2. **使用 Python 模块**:

```bash
python -m sage.tools.finetune.trainer finetune_output/code
```

3. **使用代码**:

```python
from sage.tools.finetune.trainer import train_from_meta
train_from_meta("finetune_output/code")
```

配置文件会自动从 `finetune_meta.json` 读取，完全兼容。

## 🚀 作为独立子模块的路线图

### 功能测试

```bash
# 1. 快速开始
sage finetune quickstart code

# 2. 运行训练
sage finetune run finetune_output/code

# 3. 其他命令
sage finetune list
sage finetune merge code
sage finetune chat code
```

### 模块导入测试

```python
# 测试导入
from sage.tools.finetune import (
    LoRATrainer,
    TrainingConfig,
    LoRAConfig,
    PresetConfigs,
    prepare_dataset,
    load_training_data,
)

# 测试配置
config = PresetConfigs.rtx_3060()
print(config.effective_batch_size)  # 应该输出 16

# 测试训练器创建
trainer = LoRATrainer(config)
```

## 📊 性能优化记录

### VS Code 崩溃修复

1. **8-bit 量化**: 减少 50% 显存占用
1. **Gradient Checkpointing**: 减少 30% 显存占用
1. **Batch size = 1**: 避免 OOM
1. **Max length = 1024**: 适配 RTX 3060

### 预设配置效果

| 配置     | 显卡  | Batch Size | Max Length | 显存占用 |
| -------- | ----- | ---------- | ---------- | -------- |
| minimal  | \<8GB | 1          | 512        | ~6GB     |
| rtx_3060 | 12GB  | 1          | 1024       | ~10GB    |
| rtx_4090 | 24GB  | 4          | 2048       | ~20GB    |
| a100     | 40GB+ | 8          | 4096       | ~35GB    |

## 🎯 总结

### 已完成 ✅

1. ✅ 模块化重构
1. ✅ 预设配置
1. ✅ 数据格式支持
1. ✅ 完整 API
1. ✅ 向后兼容
1. ✅ 完整文档
1. ✅ VS Code 崩溃修复

### 下一步 🚀

1. 📝 添加单元测试
1. 📝 添加更多示例
1. 📦 拆分为独立子模块
1. 🌐 发布到 PyPI
1. 📚 建立独立文档站

### 对研究者的建议

**现在**:

- 可以直接修改 `packages/sage-tools/src/sage/tools/finetune/` 中的代码
- 遵循模块化设计原则
- 提交 PR 到 SAGE 主仓库

**未来（子模块后）**:

- Fork `sage-finetune` 独立仓库
- 完全独立开发
- 更灵活的版本管理
- 更容易贡献和分享

______________________________________________________________________

**作者**: GitHub Copilot\
**日期**: 2025-10-07\
**版本**: v1.0
