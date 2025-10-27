# Tools 目录脚本分类与迁移建议

**Date**: 2025-10-27  
**Author**: SAGE Team  
**Summary**: tools/ 目录下脚本的分类分析和迁移建议，用于指导 tools/ 到 sage-tools 的重构工作

## 📊 分析结果

### 脚本分类

根据功能和性质，`tools/` 下的脚本可以分为以下几类：

#### 1️⃣ **系统级安装脚本** - ⚠️ **必须保留**

```
tools/install/
├── install_system_deps.sh          # 系统依赖安装
├── examination_tools/              # 系统检查工具
├── fixes/                          # 系统级修复
└── installation_table/             # 安装流程脚本
    ├── core_installer.sh
    ├── dev_installer.sh
    ├── main_installer.sh
    ├── scientific_installer.sh
    └── vllm_installer.sh

tools/conda/
├── conda_utils.sh
├── install-sage-conda.sh
└── sage-conda.sh
```

**保留原因**:
- ✅ 需要在**安装 SAGE 之前**运行（鸡生蛋问题）
- ✅ 操作系统级依赖（apt、yum、conda）
- ✅ 环境准备，不依赖 Python 包

#### 2️⃣ **Git Hooks** - ⚠️ **必须保留**

```
tools/git-hooks/
├── install.sh
└── pre-commit
```

**保留原因**:
- ✅ Git 生态工具，不属于 Python 包
- ✅ 需要在项目根目录运行
- ✅ 开发者首次 clone 就需要

#### 3️⃣ **Shell 函数库** - ⚠️ **必须保留**

```
tools/lib/
├── common_utils.sh                 # 通用函数
├── config.sh                       # 配置变量
└── logging.sh                      # 日志函数
```

**保留原因**:
- ✅ 被其他 Shell 脚本依赖
- ✅ 不是独立工具，是函数库
- ✅ Shell 脚本生态，不适合 Python 化

#### 4️⃣ **开发辅助脚本** - ✅ **可以考虑迁移**

```
tools/dev.sh                        # 开发环境管理
tools/mypy-wrapper.sh              # Mypy 包装器
```

**迁移建议**:
- `dev.sh` → 可迁移到 `sage-dev` CLI
- `mypy-wrapper.sh` → 可集成到 `sage-dev lint` 或保留

#### 5️⃣ **维护脚本** - 🔄 **部分可迁移**

```
tools/maintenance/
├── check_docs.sh                   # 文档检查
├── fix-types-helper.sh            # 类型修复
├── sage-maintenance.sh            # 维护总控
├── setup_hooks.sh                 # Hooks 设置
└── helpers/
    ├── devnotes_organizer.py       # ✅ 可迁移
    ├── batch_fix_devnotes_metadata.py  # ✅ 可迁移
    ├── update_ruff_ignore.py       # ✅ 可迁移
    └── *.sh                        # ⚠️ 保留
```

**分析**:
- Python 脚本（`*.py`）→ **可迁移到 sage-tools**
- Shell 脚本（`*.sh`）→ **保留**（操作 Git、系统级操作）

## 🎯 迁移建议

### ✅ 推荐迁移到 sage-tools

| 当前位置 | 迁移目标 | CLI 命令 | 优先级 |
|---------|---------|---------|--------|
| `tools/dev.sh` 部分功能 | `packages/sage-tools/src/sage/tools/cli/commands/dev/` | `sage-dev ...` | 🔥 高 |
| `tools/maintenance/helpers/*.py` | `packages/sage-tools/src/sage/tools/dev/maintenance/` | `sage-dev maintenance ...` | 🔥 高 |
| `tools/mypy-wrapper.sh` 逻辑 | `packages/sage-tools/src/sage/tools/dev/tools/` | `sage-dev lint --mypy` | 🟡 中 |

### ⚠️ 必须保留（不能迁移）

| 路径 | 原因 | 说明 |
|------|------|------|
| `tools/install/` | 系统级安装 | SAGE 安装前需要运行 |
| `tools/conda/` | Conda 环境 | 独立于 Python 包 |
| `tools/git-hooks/` | Git 生态 | 必须在 .git/hooks |
| `tools/lib/` | Shell 函数库 | 被其他脚本依赖 |

### 🔄 可选保留（灵活处理）

| 路径 | Python 版本 | Shell 版本 | 建议 |
|------|------------|-----------|------|
| `tools/maintenance/check_docs.sh` | 迁移 | 保留为快捷入口 | 两者共存，Shell 调用 Python |
| `tools/maintenance/sage-maintenance.sh` | 迁移核心逻辑 | 保留总控 | Shell 作为统一入口 |

## 📋 具体迁移计划

### Phase 1: 迁移 Python 维护脚本 🔥

```bash
# 创建新模块
packages/sage-tools/src/sage/tools/dev/maintenance/
├── __init__.py
├── devnotes_organizer.py          # 从 tools/maintenance/helpers/
├── metadata_fixer.py              # 从 tools/maintenance/helpers/batch_fix_devnotes_metadata.py
└── ruff_ignore_updater.py         # 从 tools/maintenance/helpers/update_ruff_ignore.py

# 创建 CLI 命令
packages/sage-tools/src/sage/tools/cli/commands/dev/maintenance.py

# 新命令
sage-dev maintenance organize-devnotes
sage-dev maintenance fix-metadata
sage-dev maintenance update-ruff-ignore
```

### Phase 2: 集成 dev.sh 功能 🔥

```python
# 将 dev.sh 的功能集成到现有 sage-dev 命令

tools/dev.sh setup       → sage-dev project setup
tools/dev.sh format      → sage-dev format (已存在)
tools/dev.sh lint        → sage-dev lint (已存在)
tools/dev.sh test        → sage-dev project test (已存在)
tools/dev.sh clean       → sage-dev project clean (新增)
tools/dev.sh docs        → sage-dev docs build (新增)
```

### Phase 3: Mypy 集成 🟡

```python
# 将 mypy-wrapper.sh 的逻辑集成到 lint 命令

# 当前: tools/mypy-wrapper.sh
# 新命令: sage-dev lint --mypy --warn-only
```

## 🎨 迁移后的结构

### tools/ (精简后)

```
tools/
├── __init__.py                     # Python 包标识
├── lib/                            # Shell 函数库 ✅ 保留
├── install/                        # 安装脚本 ✅ 保留
├── conda/                          # Conda 管理 ✅ 保留
├── git-hooks/                      # Git hooks ✅ 保留
├── maintenance/                    # 维护脚本总控 ✅ 保留
│   ├── sage-maintenance.sh         # 统一入口（调用 sage-dev）
│   └── helpers/*.sh                # Shell 辅助脚本
├── pre-commit-config.yaml         # Pre-commit 配置 ✅ 保留
└── templates/                      # 模板 ✅ 保留
```

### packages/sage-tools/ (增强后)

```
packages/sage-tools/src/sage/tools/
├── cli/commands/dev/
│   ├── maintenance.py              # ✨ 新增：维护命令
│   ├── docs.py                     # ✨ 新增：文档命令
│   └── ...
├── dev/
│   ├── maintenance/                # ✨ 新增：维护工具
│   │   ├── devnotes_organizer.py
│   │   ├── metadata_fixer.py
│   │   └── ruff_ignore_updater.py
│   └── tools/
│       └── mypy_checker.py         # ✨ 新增：Mypy 集成
└── ...
```

## 💡 最佳实践建议

### 1. 双轨制过渡

```bash
# Shell 脚本调用 Python CLI
# tools/maintenance/sage-maintenance.sh

# 调用新的 Python CLI
sage-dev maintenance organize-devnotes "$@"

# 提示用户
echo "提示: 可直接使用 sage-dev maintenance organize-devnotes"
```

### 2. 保留必要的 Shell 入口

- ✅ `tools/dev.sh` → 保留为快捷方式，内部调用 `sage-dev`
- ✅ `quickstart.sh` → 保留（根目录快速启动）
- ✅ `manage.sh` → 保留（项目管理总入口）

### 3. 文档和废弃提示

```bash
# tools/dev.sh (更新版)
#!/bin/bash
echo "⚠️  tools/dev.sh 已整合到 sage-dev CLI"
echo "建议使用: sage-dev <command>"
echo ""
echo "继续使用旧命令..."

# 然后调用对应的 sage-dev 命令
```

## ⚖️ 应该迁移吗？

### 优点 ✅

1. **统一接口**: 所有开发工具通过 `sage-dev` 访问
2. **更好的可维护性**: Python 代码比 Shell 脚本更容易维护
3. **跨平台**: Python 比 Shell 更容易跨平台
4. **更好的测试**: Python 代码更容易写单元测试
5. **一致的用户体验**: Rich UI、错误处理、帮助信息

### 缺点 ❌

1. **需要 Python 环境**: Shell 脚本可以在没有 Python 的情况下运行
2. **迁移成本**: 需要时间重写和测试
3. **向后兼容**: 需要保持旧脚本或提供迁移路径
4. **系统级操作**: 某些操作（如 apt install）仍需 Shell

## 🎯 我的建议

### ✅ 已完成 (2025-10-27)

1. **✅ 迁移 Python 维护脚本** (`tools/maintenance/helpers/*.py`)
   - ✅ devnotes_organizer.py → sage.tools.dev.maintenance.devnotes_organizer
   - ✅ batch_fix_devnotes_metadata.py → sage.tools.dev.maintenance.metadata_fixer
   - ✅ update_ruff_ignore.py → sage.tools.dev.maintenance.ruff_updater
   - ✅ CLI 命令: sage-dev maintenance {organize-devnotes, fix-metadata, update-ruff-ignore}

2. **✅ 增强 sage-dev CLI - 文档管理**
   - ✅ 添加 `sage-dev docs build` - 构建文档
   - ✅ 添加 `sage-dev docs serve` - 启动文档服务器
   - ✅ 添加 `sage-dev docs check` - 检查文档
   - ✅ 已集成: `sage-dev project clean` - 清理项目

3. **✅ dev.sh 迁移提示**
   - ✅ 添加迁移警告到 clean, docs, serve-docs 命令
   - ✅ 保留 dev.sh 作为兼容层
   - ✅ 引导用户使用新命令

### 中期规划 🟡

3. **dev.sh 功能集成**
   - 逐步将功能迁移到 `sage-dev`
   - 保留 `dev.sh` 作为兼容层
   - 添加废弃提示

### 永久保留 ✅

4. **保留必要的 Shell 脚本**
   - `tools/install/` - 系统级安装
   - `tools/conda/` - Conda 管理
   - `tools/git-hooks/` - Git 集成
   - `tools/lib/` - Shell 函数库

## 🚀 下一步行动

如果你同意，我可以：

1. ✅ **立即开始**: 迁移 `tools/maintenance/helpers/*.py`
2. ✅ **创建 CLI**: 添加 `sage-dev maintenance` 命令组
3. ✅ **增强功能**: 添加 `clean`、`docs` 等命令
4. 📝 **更新文档**: 说明迁移和新命令使用

是否开始执行？
