**Date**: 2025-10-26  
**Author**: SAGE Development Team  
**Summary**: sage-cli 独立包创建计划 - 将 CLI 命令从 sage-tools 迁移到专门的包中

---

# SAGE CLI Package 创建计划

> **文档版本**: 1.0  
> **创建日期**: 2025-10-26  
> **状态**: 规划中  

## 📋 概述

本文档描述了创建独立 `sage-cli` 包的完整计划，将所有 CLI 命令从 `sage-tools` 迁移到专门的 CLI 包中。

## 🎯 目标

1. **职责分离**: CLI 命令与开发工具分离
2. **架构清晰**: sage-tools 回归纯开发工具库定位
3. **易于维护**: CLI 代码集中管理，便于升级和扩展
4. **符合架构**: sage-cli 作为 L6 层用户接口

## 🏗️ 包结构设计

### 当前实现（2025-02）

目前仓库已存在 `packages/sage-cli`，并完成以下内容：

```
packages/sage-cli/
├── pyproject.toml
├── src/sage/cli/
│   ├── main.py
│   ├── commands/
│   │   ├── platform/
│   │   │   ├── env.py            # ``sage env`` 交互式 .env 管理
│   │   │   └── llm_config.py     # ``sage llm-config auto`` 写入 generator 配置
│   │   └── apps/
│   │       ├── pipeline.py       # LLM 驱动的 pipeline builder
│   │       ├── pipeline_domain.py / pipeline_knowledge.py
│   │       ├── llm.py / chat.py / embedding.py / studio.py
│   │       └── pipeline_embedding.py
│   └── utils/
│       ├── env.py                # .env 检测 & 加载工具
│       └── llm_detection.py      # 本地 LLM 服务探测
└── tests/ (待补充)
```

- `sage env` 与 `sage llm-config auto` 仍归属 `sage` 主命令（platform 组），暂未迁入 `sage-dev project`。
- `sage-dev *` 命令仍由 `packages/sage-tools` 提供，CLI 包暂不包含 `dev` 子目录。

### 目标结构（规划）

```
packages/sage-cli/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── sage/
│       └── cli/
│           ├── __init__.py
│           ├── main.py                    # 主入口点
│           │
│           ├── commands/                  # 所有命令模块
│           │   ├── __init__.py
│           │   │
│           │   ├── platform/              # 平台层命令
│           │   │   ├── __init__.py
│           │   │   ├── cluster.py         # sage cluster
│           │   │   ├── head.py            # sage head
│           │   │   ├── worker.py          # sage worker
│           │   │   ├── job.py             # sage job
│           │   │   ├── jobmanager.py      # sage jobmanager
│           │   │   ├── config.py          # sage config
│           │   │   ├── doctor.py          # sage doctor
│           │   │   ├── version.py         # sage version
│           │   │   └── extensions.py      # sage extensions
│           │   │
│           │   ├── apps/                  # 应用层命令
│           │   │   ├── __init__.py
│           │   │   ├── llm.py             # sage llm
│           │   │   ├── chat.py            # sage chat
│           │   │   ├── embedding.py       # sage embedding
│           │   │   ├── pipeline.py        # sage pipeline
│           │   │   ├── pipeline_domain.py # 内部模块
│           │   │   ├── pipeline_embedding.py
│           │   │   ├── pipeline_knowledge.py
│           │   │   └── studio.py          # sage studio
│           │   │
│           │   └── dev/                   # 开发工具命令
│           │       ├── __init__.py
│           │       ├── quality/           # sage-dev quality
│           │       ├── project/           # sage-dev project
│           │       │   ├── __init__.py
│           │       │   ├── env.py         # 从 commands/env.py 移入
│           │       │   └── llm_config.py  # 从 commands/llm_config.py 移入
│           │       ├── maintain/          # sage-dev maintain
│           │       ├── package/           # sage-dev package
│           │       ├── resource/          # sage-dev resource
│           │       └── github/            # sage-dev github
│           │
│           ├── utils/                     # CLI 工具函数
│           │   ├── __init__.py
│           │   ├── output.py              # 从 sage-tools 移入
│           │   ├── llm_detection.py       # 从 sage-tools 移入
│           │   └── env.py                 # 从 sage-tools 移入
│           │
│           └── management/                # 管理工具
│               ├── __init__.py
│               ├── config_manager.py      # 从 sage-tools 移入
│               └── deployment_manager.py  # 从 sage-tools 移入
│
└── tests/
    ├── __init__.py
    ├── commands/
    │   ├── test_platform_commands.py
    │   ├── test_app_commands.py
    │   └── test_dev_commands.py
    └── utils/
        └── test_utils.py
```

### sage-devtools 清理后结构

```
packages/sage-devtools/  (原 sage-tools)
├── pyproject.toml
├── README.md
├── src/
│   └── sage/
│       └── devtools/            # 重命名 from sage.tools
│           ├── __init__.py
│           ├── dev/
│           │   └── tools/       # 开发工具实现
│           │       ├── __init__.py
│           │       ├── architecture_checker.py
│           │       ├── devnotes_checker.py
│           │       ├── devnotes_organizer.py
│           │       ├── package_readme_checker.py
│           │       └── batch_fix_devnotes_metadata.py
│           │
│           └── utils/           # 开发工具公共库
│               ├── __init__.py
│               ├── file_utils.py
│               └── ...
│
└── tests/
    └── ...
```

## 📊 架构层级定义

### 更新后的 SAGE 架构

```
L1: sage-common          (基础设施、通用组件)
L2: sage-platform        (平台核心功能)
L3: sage-kernel          (计算引擎核心)
    sage-libs            (算法库)
L4: sage-middleware      (中间件、服务层)
L5: sage-apps            (应用业务逻辑)
    sage-benchmark       (性能测试)
L6: sage-cli             (命令行接口) ← 新增
    sage-devtools        (开发者工具，原 sage-tools)
    sage-studio          (可视化界面)
```

### 依赖关系

```python
LAYER_DEFINITION = {
    "L1": ["sage-common"],
    "L2": ["sage-platform"],
    "L3": ["sage-kernel", "sage-libs"],
    "L4": ["sage-middleware"],
    "L5": ["sage-apps", "sage-benchmark"],
    "L6": ["sage-cli", "sage-devtools", "sage-studio"],
}

ALLOWED_DEPENDENCIES = {
    "sage-cli": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
        "sage-apps",
        "sage-benchmark",
    },  # L6 CLI 可以依赖所有下层

    "sage-devtools": {  # 原 sage-tools
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
        "sage-studio",
    },

    "sage-studio": {
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
    },
}
```

## 🔄 迁移步骤

### Phase 1: 准备工作

1. **创建 sage-cli 包结构**
   ```bash
   mkdir -p packages/sage-cli/src/sage/cli/{commands/{platform,apps,dev},utils,management}
   mkdir -p packages/sage-cli/tests
   ```

2. **设置 pyproject.toml**
   - 包名: `sage-cli`
   - 版本: `0.1.0`
   - 依赖: typer, rich, pyyaml, 等

3. **创建基础文件**
   - `__init__.py` 文件
   - `main.py` 入口点
   - `README.md` 说明文档

### Phase 2: 迁移命令文件

#### 2.1 平台命令 (9个)

从 `sage-tools/cli/commands/` 移动到 `sage-cli/commands/platform/`:

- `cluster.py` → `platform/cluster.py`
- `head.py` → `platform/head.py`
- `worker.py` → `platform/worker.py`
- `job.py` → `platform/job.py`
- `jobmanager.py` → `platform/jobmanager.py`
- `config.py` → `platform/config.py`
- `doctor.py` → `platform/doctor.py`
- `version.py` → `platform/version.py`
- `extensions.py` → `platform/extensions.py`

#### 2.2 应用命令 (5个 + 3个内部模块)

从 `sage-tools/cli/commands/` 移动到 `sage-cli/commands/apps/`:

- `llm.py` → `apps/llm.py`
- `chat.py` → `apps/chat.py`
- `embedding.py` → `apps/embedding.py`
- `pipeline.py` → `apps/pipeline.py`
- `studio.py` → `apps/studio.py`
- `pipeline_domain.py` → `apps/pipeline_domain.py` (内部模块)
- `pipeline_embedding.py` → `apps/pipeline_embedding.py` (内部模块)
- `pipeline_knowledge.py` → `apps/pipeline_knowledge.py` (内部模块)

#### 2.3 开发命令

从 `sage-tools/cli/commands/dev/` 移动到 `sage-cli/commands/dev/`:

- `dev/quality/` → `dev/quality/`
- `dev/project/` → `dev/project/`
- `dev/maintain/` → `dev/maintain/`
- `dev/package/` → `dev/package/`
- `dev/resource/` → `dev/resource/`
- `dev/github/` → `dev/github/`

整合孤立命令:
- `commands/env.py` → `dev/project/env.py`
- `commands/llm_config.py` → `dev/project/llm_config.py`

#### 2.4 工具模块

从 `sage-tools/cli/` 移动到 `sage-cli/`:

- `utils/` → `utils/`
- `management/` → `management/`

### Phase 3: 更新导入路径

所有导入需要更新:

```python
# 旧导入
from sage.tools.cli.commands.cluster import app

# 新导入
from sage.cli.commands.platform.cluster import app
```

使用脚本批量更新:

```bash
# 查找所有导入
grep -r "from sage.tools.cli" packages/sage-cli/

# 批量替换
find packages/sage-cli -type f -name "*.py" -exec sed -i \
  's/from sage\.tools\.cli/from sage.cli/g' {} +
```

### Phase 4: 更新 main.py

在 `sage-cli/main.py` 中注册所有命令:

```python
#!/usr/bin/env python3
"""
SAGE CLI - Unified Command Line Interface
"""
import typer

app = typer.Typer(
    name="sage",
    help="🚀 SAGE - Streaming-Augmented Generative Execution",
    no_args_is_help=True,
)

# 注册平台命令
from sage.cli.commands.platform.cluster import app as cluster_app
from sage.cli.commands.platform.config import app as config_app
# ... 其他平台命令

# 注册应用命令
from sage.cli.commands.apps.llm import app as llm_app
from sage.cli.commands.apps.chat import app as chat_app
# ... 其他应用命令

# 注册开发命令
from sage.cli.commands.dev import app as dev_app

# 添加命令
app.add_typer(cluster_app, name="cluster", help="🌐 集群管理")
app.add_typer(config_app, name="config", help="⚙️ 配置管理")
# ... 其他命令
app.add_typer(dev_app, name="dev", help="🛠️ 开发工具")

if __name__ == "__main__":
    app()
```

### Phase 5: 更新 Entry Points

#### 修改 sage-cli/pyproject.toml

```toml
[project.scripts]
sage = "sage.cli.main:app"
```

#### 删除 sage-tools 中的 entry point

从 `sage-tools/pyproject.toml` 中移除:

```toml
[project.scripts]
# sage = "sage.tools.cli.main:app"  # 删除这行
```

### Phase 6: 清理 sage-tools

1. **删除 CLI 相关目录**
   ```bash
   rm -rf packages/sage-tools/src/sage/tools/cli/commands/
   rm -rf packages/sage-tools/src/sage/tools/cli/utils/
   rm -rf packages/sage-tools/src/sage/tools/management/
   rm packages/sage-tools/src/sage/tools/cli/main.py
   ```

2. **保留开发工具**
   ```
   packages/sage-tools/
   └── src/sage/tools/
       └── dev/tools/    # 保留所有开发工具实现
   ```

### Phase 7: 更新架构检查器

修改 `architecture_checker.py`:

```python
LAYER_DEFINITION = {
    "L1": ["sage-common"],
    "L2": ["sage-platform"],
    "L3": ["sage-kernel", "sage-libs"],
    "L4": ["sage-middleware"],
    "L5": ["sage-apps", "sage-benchmark"],
    "L6": ["sage-cli", "sage-tools", "sage-studio"],  # 添加 sage-cli
}

PACKAGE_PATHS = {
    # ... 现有包
    "sage-cli": "packages/sage-cli/src",  # 新增
}

ALLOWED_DEPENDENCIES = {
    # ... 现有依赖
    "sage-cli": {  # 新增
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
        "sage-apps",
        "sage-benchmark",
    },
}
```

### Phase 8: 测试

1. **安装 sage-cli 包**
   ```bash
   cd packages/sage-cli
   pip install -e .
   ```

2. **测试所有命令**
   ```bash
   sage --help
   sage cluster --help
   sage-dev --help
   sage llm --help
   ```

3. **运行测试套件**
   ```bash
   pytest packages/sage-cli/tests/
   ```

4. **架构检查**
   ```bash
   sage-dev quality architecture
   ```

## ⚠️ 风险与缓解

### 风险1: 大量导入路径需要更新

**影响**: 可能导致导入错误

**缓解措施**:
- 使用自动化脚本批量更新
- 分阶段测试
- 提供兼容性导入别名 (过渡期)

```python
# 在 sage-tools/cli/commands/ 添加 __init__.py
import warnings

def __getattr__(name):
    warnings.warn(
        f"Importing {name} from sage.tools.cli.commands is deprecated. "
        "Use sage.cli.commands instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # 重定向到新位置
    import importlib
    return importlib.import_module(f"sage.cli.commands.{name}")
```

### 风险2: 依赖关系可能不完整

**影响**: 运行时错误

**缓解措施**:
- 仔细检查 pyproject.toml 依赖
- 确保所有依赖都已声明
- 在虚拟环境中测试

### 风险3: 已有脚本和文档引用旧路径

**影响**: 文档过时，脚本失效

**缓解措施**:
- 更新所有文档
- 更新 CI/CD 脚本
- 提供迁移指南

## 📅 时间线

- **Week 1**: 创建 sage-cli 包结构，迁移命令文件
- **Week 2**: 更新导入路径，测试基本功能
- **Week 3**: 清理 sage-tools，更新文档
- **Week 4**: 全面测试，准备发布

## ✅ 验收标准

- [ ] sage-cli 包成功创建
- [ ] 所有命令从 sage-tools 迁移到 sage-cli
- [ ] 所有命令正常工作
- [ ] 所有测试通过
- [ ] 架构检查通过
- [ ] 文档已更新
- [ ] CI/CD 流程正常

## 📚 相关文档

- [命令重组总结](../l6-cli/COMMAND_REORGANIZATION_SUMMARY.md)
- [架构文档](./PACKAGE_ARCHITECTURE.md)

## 🔗 相关 Issue/PR

- Issue #1032: Package Restructuring
- PR #XXX: 创建 sage-cli 包 (待创建)
