# sageRefiner Submodule Migration Guide

## 概述

sage_refiner 已经被拆分为两部分：
1. **sageRefiner** (独立子模块) - 核心压缩算法库
2. **Python Adapter Layer** - SAGE框架集成层

## 目录结构

```
packages/sage-middleware/src/sage/middleware/components/sage_refiner/
├── __init__.py                          # SAGE集成入口
├── .gitignore
├── config_examples.yaml                 # SAGE示例配置
│
├── sageRefiner/                         # [Submodule] 独立算法库
│   ├── __init__.py                      # 暴露: LongRefiner, RefinerConfig, etc.
│   ├── README.md                        # 独立项目文档
│   ├── SUBMODULE.md                     # Submodule使用说明
│   ├── setup.py / pyproject.toml        # 独立安装配置
│   ├── algorithms/                      # 核心算法
│   │   ├── LongRefiner/                 # LongRefiner算法
│   │   └── reform/                      # Reform算法
│   ├── config.py                        # 配置管理
│   ├── examples/                        # 独立示例
│   └── tests/                           # 单元测试
│
├── python/                              # SAGE适配层
│   ├── adapter.py                       # RefinerAdapter (SAGE MapFunction)
│   ├── service.py                       # RefinerService (SAGE BaseService)
│   └── context_service.py               # ContextService
│
└── examples/                            # SAGE集成示例
    ├── basic_usage.py
    └── rag_integration.py
```

## 迁移细节

### 已迁移到 sageRefiner 子模块

- ✅ `python/algorithms/` → `sageRefiner/algorithms/`
- ✅ `python/config.py` → `sageRefiner/config.py`
- ✅ 新增独立文档和示例

### 保留在 SAGE (python/)

- ✅ `adapter.py` - 依赖 `sage.common.core.MapFunction`
- ✅ `service.py` - 依赖 `sage.platform.service.BaseService`
- ✅ `context_service.py` - SAGE上下文服务

## 导入路径变更

### 旧的导入方式 (已废弃)

```python
# ❌ 不再可用
from sage.middleware.components.sage_refiner.python.config import RefinerConfig
from sage.middleware.components.sage_refiner.python.algorithms.LongRefiner import LongRefiner
```

### 新的导入方式

#### 方式 1: SAGE 集成层 (推荐在 SAGE 管道中使用)

```python
from sage.middleware.components.sage_refiner import (
    RefinerService,      # SAGE服务层
    RefinerAdapter,      # SAGE MapFunction适配器
    RefinerConfig,       # 配置类
)

# 在SAGE管道中使用
env.from_batch(...)
   .map(ChromaRetriever, retriever_config)
   .map(RefinerAdapter, refiner_config)  # 添加压缩步骤
   .map(QAPromptor, promptor_config)
   .sink(...)
```

#### 方式 2: 直接使用 sageRefiner 子模块 (独立使用)

```python
from sage.middleware.components.sage_refiner.sageRefiner import (
    LongRefiner,
    RefinerConfig,
    RefinerAlgorithm,
)

# 独立使用
config = RefinerConfig(algorithm="long_refiner", budget=2048)
refiner = LongRefiner(config.to_dict())
refiner.initialize()
result = refiner.refine(query, documents, budget=2048)
```

#### 方式 3: 作为独立包安装 (未来支持)

```bash
# 从 GitHub 安装
pip install git+https://github.com/intellistream/sageRefiner.git

# 使用
from sageRefiner import LongRefiner, RefinerConfig
```

## Submodule 工作流程

### 修改 sageRefiner 算法代码

```bash
# 1. 进入子模块目录
cd packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner

# 2. 确保在正确的分支
git checkout main
git pull origin main

# 3. 进行修改
# ... 编辑算法代码 ...

# 4. 提交到子模块仓库
git add .
git commit -m "feat: improve compression algorithm"
git push origin main

# 5. 回到主仓库，更新子模块引用
cd ../../../../../../
git add packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner
git commit -m "chore: update sageRefiner submodule reference"
git push origin feature/refiner
```

### 修改 SAGE 适配层代码

```bash
# 直接在 SAGE 主仓库修改
cd /home/cyb/SAGE
# 编辑 python/adapter.py, python/service.py 等
git add packages/sage-middleware/src/sage/middleware/components/sage_refiner/python/
git commit -m "feat: improve SAGE adapter"
git push origin feature/refiner
```

## 依赖关系

### sageRefiner (独立包)

```python
dependencies = [
    "torch>=2.0.0",
    "transformers>=4.30.0",
    "numpy>=1.24.0",
    "pyyaml>=6.0",
]
```

### SAGE 适配层

```python
dependencies = [
    "sage-platform",           # RefinerService 依赖
    "sage-common",             # RefinerAdapter 依赖
    # sageRefiner 通过 submodule 自动包含
]
```

## 测试

### 测试 sageRefiner (独立)

```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner
pytest tests/
```

### 测试 SAGE 集成

```bash
cd /home/cyb/SAGE
sage-dev project test --quick
# 或
pytest packages/sage-middleware/tests/unit/components/test_sage_refiner.py
```

## 常见问题

### Q: 导入错误 "No module named 'sageRefiner'"

**A**: 确保子模块已初始化：
```bash
cd /home/cyb/SAGE
git submodule update --init --recursive
```

### Q: 子模块显示 "modified content"

**A**: 进入子模块检查状态：
```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner
git status
# 如果是未提交的修改，提交或重置
```

### Q: 如何单独发布 sageRefiner？

**A**: 
```bash
cd /tmp/sageRefiner  # 或克隆独立仓库
python -m build
twine upload dist/*
```

### Q: 如何回退到旧版本？

**A**: 旧的 `python/algorithms/` 和 `python/config.py` 已被移除。如需回退，请查看 Git 历史。

## 迁移检查清单

- [x] 算法代码迁移到 sageRefiner 子模块
- [x] 配置文件迁移到 sageRefiner
- [x] 更新所有导入路径
- [x] 删除重复的代码 (python/algorithms/, python/config.py)
- [x] 创建独立文档和示例
- [x] 添加 .gitmodules 配置
- [x] 生成 SUBMODULE.md
- [ ] 推送 sageRefiner 到 GitHub (待权限)
- [ ] 更新 CI/CD 配置
- [ ] 验证测试通过

## 相关文件

- `sageRefiner/README.md` - 独立项目文档
- `sageRefiner/SUBMODULE.md` - Submodule 使用说明
- `.gitmodules` - Submodule 配置
- `CONTRIBUTING.md` - SAGE 贡献指南 (包含 submodule 工作流)

---

**迁移完成日期**: 2025-11-28  
**迁移人**: GitHub Copilot  
**相关 PR**: (待创建)
