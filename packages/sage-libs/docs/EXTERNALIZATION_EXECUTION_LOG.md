# 外迁执行记录（选项 A）

**开始时间**: 2026-01-10 20:10\
**执行人**: AI Assistant\
**策略**: 完整外迁（选项 A）

## 📋 执行清单

### ✅ 阶段 0: 准备工作（已完成）

- [x] sage-agentic 仓库创建并初始化
- [x] sage-rag 仓库创建并初始化
- [x] 接口层代码已复制到外部仓库
- [x] 完整实现代码已复制到外部仓库
- [x] 文档已准备（README, MIGRATION_GUIDE）
- [x] License 已更新（Apache 2.0）
- [x] .gitignore 已配置

### 🚧 阶段 1: 更新 sage-libs pyproject.toml

#### 1.1 添加 extras 依赖

需要在 `packages/sage-libs/pyproject.toml` 中添加：

```toml
[project.optional-dependencies]
# 外迁的包（作为可选依赖）
agentic = ["isage-agentic>=0.1.0"]
rag = ["isage-rag>=0.1.0"]
ann = ["isage-anns>=0.1.0"]  # 注：已重命名为 ann
amms = ["isage-amms>=0.1.0"]
finetune = ["isage-finetune>=0.1.0"]

# 全量安装（开发/CI 用）
all = [
    "isage-agentic>=0.1.0",
    "isage-rag>=0.1.0",
    "isage-anns>=0.1.0",
    "isage-amms>=0.1.0",
    "isage-finetune>=0.1.0",
]
```

#### 1.2 更新依赖版本

确保所有依赖版本与 `dependencies-spec.yaml` 一致

### 🚧 阶段 2: 删除或标记 sage-libs 中的目录

#### 2.1 处理 agentic/

选项：

- [ ] **选项 A**: 完全删除（推荐，干净）
- [ ] **选项 B**: 保留空的 `__init__.py` 作为重导出层

**决策**: 选项 A - 完全删除

```bash
rm -rf packages/sage-libs/src/sage/libs/agentic/
```

理由：

- agentic 已完全外迁到 isage-agentic
- 只有接口层，没有实现
- 通过 extras 依赖，用户安装 `sage-libs[agentic]` 即可

#### 2.2 处理 rag/

**决策**: 选项 A - 完全删除

```bash
rm -rf packages/sage-libs/src/sage/libs/rag/
```

理由：

- rag 已完全外迁到 isage-rag
- 包含完整实现（chunk.py, document_loaders.py, types.py）
- 通过 extras 依赖

#### 2.3 处理 sias/

**决策**: 完全删除

```bash
rm -rf packages/sage-libs/src/sage/libs/sias/
```

理由：

- SIAS 的定位已澄清（工具选择算法的训练组件）
- 应该整合到 isage-agentic 中
- 当前只有空的接口层，无实际代码

### 🚧 阶段 3: 更新 sage-tools 的导入

sage-tools 中使用了 SIAS 组件，需要更新导入路径：

**文件**: `packages/sage-tools/src/sage/tools/agent_training/sft_trainer.py`

```python
# 旧导入
from sage.libs.sias import CoresetSelector, OnlineContinualLearner

# 新导入（暂时保持，等 isage-agentic 实现后更新）
# from sage.libs.agentic.training import CoresetSelector, OnlineContinualLearner
```

**决策**: 暂时注释掉 SIAS 相关代码，等 isage-agentic 完整实现后再恢复

### 🚧 阶段 4: 更新文档

#### 4.1 更新 sage-libs/README.md

需要说明：

- 哪些模块已外迁
- 如何安装外迁的包
- extras 的使用方式

#### 4.2 更新 REORGANIZATION_PROPOSAL.md

标记为已完成，更新状态

#### 4.3 更新 .github/copilot-instructions.md

更新模块位置说明

### 🚧 阶段 5: 测试验证

#### 5.1 本地测试

```bash
# 安装 sage-libs（不含 extras）
pip uninstall -y sage-libs
pip install -e packages/sage-libs

# 测试核心功能
python -c "from sage.libs.foundation import *"
python -c "from sage.libs.dataops import *"

# 安装 extras
pip install -e packages/sage-libs[all]

# 测试外迁包导入（模拟）
# python -c "from sage.libs.agentic import *"
# python -c "from sage.libs.rag import *"
```

#### 5.2 运行测试套件

```bash
sage-dev project test packages/sage-libs/tests/
```

### 🚧 阶段 6: 发布外迁包

#### 6.1 发布到 TestPyPI

```bash
cd ~/sage-pypi-publisher
./publish.sh isage-agentic --test-pypi --version 0.1.0
./publish.sh isage-rag --test-pypi --version 0.1.0
```

#### 6.2 测试安装

```bash
pip install -i https://test.pypi.org/simple/ isage-agentic
pip install -i https://test.pypi.org/simple/ isage-rag
```

#### 6.3 发布到正式 PyPI

```bash
./publish.sh isage-agentic --version 0.1.0
./publish.sh isage-rag --version 0.1.0
```

## 📊 当前进度

- [x] 阶段 0: 准备工作（100%）
- [ ] 阶段 1: 更新 pyproject.toml（0%）
- [ ] 阶段 2: 删除/标记目录（0%）
- [ ] 阶段 3: 更新导入（0%）
- [ ] 阶段 4: 更新文档（0%）
- [ ] 阶段 5: 测试验证（0%）
- [ ] 阶段 6: 发布（0%）

**总进度**: 14% (1/7 阶段完成)

## 📝 注意事项

1. **SIAS 的完整实现** - 需要在 isage-agentic 中补全：

   - 训练组件：CoresetSelector, OnlineContinualLearner
   - 运行时选择器：SiasToolSelector

1. **向后兼容** - 删除目录后无向后兼容，需要：

   - 更新所有文档中的导入示例
   - 在 CHANGELOG 中明确说明破坏性变更

1. **CI/CD 更新** - 需要更新所有 GitHub Actions workflow：

   - 安装命令改为：`pip install -e packages/sage-libs[all]`

1. **依赖版本** - 确保所有包的依赖版本一致：

   - 参考 `dependencies-spec.yaml`
   - 使用 `tools/scripts/check_dependency_consistency.py` 验证

## 🎯 下一步

立即开始：**阶段 1 - 更新 sage-libs pyproject.toml**
