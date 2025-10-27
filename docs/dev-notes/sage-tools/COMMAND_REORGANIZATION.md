# sage-dev 命令重组方案

## 📋 当前状态分析

### sage-dev 现有命令（15个）

按功能分类：

**质量检查工具** (6个)
- `quality` - 代码质量检查和修复（pre-commit + 架构检查）
- `architecture` - 显示架构信息
- `check-architecture` - 架构合规性检查
- `check-devnotes` - dev-notes 文档规范检查
- `check-readme` - 包 README 质量检查
- `check-all` - 运行所有质量检查

**开发辅助工具** (4个)
- `analyze` - 代码分析（依赖、复杂度等）
- `clean` - 清理构建产物和缓存
- `status` - 显示项目状态
- `test` - 运行项目测试
- `home` - 显示项目主页

**管理工具** (4个)
- `issues` - GitHub Issues 管理（11个子命令）
- `pypi` - PyPI 包管理（5个子命令）
- `version` - 版本管理（4个子命令）
- `models` - 模型缓存管理（4个子命令）

### tools/ 目录脚本（未集成）

**维护工具** (tools/maintenance/)
- `sage-maintenance.sh` - 项目维护主脚本
  - submodule 管理（init, status, switch, update, fix-conflict, cleanup）
  - 项目维护（doctor, status, clean, clean-deep, security-check, setup-hooks）

**开发辅助** (tools/)
- `dev.sh` - 开发辅助脚本
  - setup, install, test, lint, format, check, pre-commit, clean, docs, validate

**安装工具** (tools/install/)
- 系统依赖检查和安装
- 环境诊断和修复

## 🎯 重组方案

### 建议的二级命令组织

```
sage-dev
├── quality/          # 质量检查组
│   ├── check        # 运行所有检查（原 check-all）
│   ├── architecture # 架构检查
│   ├── devnotes     # 文档规范检查
│   ├── readme       # README 检查
│   ├── format       # 代码格式化（原 quality --format）
│   ├── lint         # 代码检查（原 quality --lint）
│   └── fix          # 自动修复（原 quality --fix）
│
├── project/          # 项目管理组
│   ├── status       # 项目状态
│   ├── analyze      # 代码分析
│   ├── clean        # 清理构建产物
│   ├── test         # 运行测试
│   └── architecture # 显示架构信息
│
├── maintain/         # 维护工具组（集成 sage-maintenance.sh）
│   ├── doctor       # 健康检查
│   ├── submodule    # Submodule 管理
│   │   ├── init
│   │   ├── status
│   │   ├── switch
│   │   ├── update
│   │   ├── fix-conflict
│   │   └── cleanup
│   ├── hooks        # Git hooks 管理
│   └── security     # 安全检查
│
├── package/          # 包管理组
│   ├── pypi         # PyPI 发布管理
│   │   ├── validate
│   │   ├── check
│   │   ├── build
│   │   ├── clean
│   │   └── publish
│   ├── version      # 版本管理
│   │   ├── list
│   │   ├── set
│   │   ├── bump
│   │   └── sync
│   └── install      # 安装管理
│       ├── dev      # 开发模式安装
│       └── deps     # 依赖安装
│
├── resource/         # 资源管理组
│   ├── models       # 模型缓存管理
│   │   ├── configure
│   │   ├── cache
│   │   ├── check
│   │   └── clear
│   └── data         # 数据管理（未来扩展）
│
└── github/           # GitHub 管理组
    └── issues       # Issues 管理
        ├── status
        ├── download
        ├── stats
        ├── team
        ├── create
        ├── project
        ├── config
        ├── ai
        ├── sync
        ├── organize
        └── test
```

## 📊 命令层级对比

### 现状（最深4级）
```
sage-dev issues create         # 3级 ✅
sage-dev pypi validate          # 3级 ✅
sage-dev quality --hook black   # 3级（选项）✅
```

### 重组后（最深4级）
```
sage-dev quality check          # 3级 ✅
sage-dev maintain submodule init # 4级 ✅
sage-dev package version bump   # 4级 ✅
sage-dev github issues create   # 4级 ✅
```

## ✨ 优势

### 1. 清晰的功能分组
- `quality/` - 所有质量相关的检查和修复
- `project/` - 项目级别的操作（状态、分析、测试）
- `maintain/` - 维护相关工具（submodule、hooks、doctor）
- `package/` - 包管理（发布、版本、安装）
- `resource/` - 资源管理（模型、数据）
- `github/` - GitHub 集成（issues、PR等）

### 2. 语义化命令
```bash
# 更直观的命令路径
sage-dev quality check           # 运行质量检查
sage-dev quality architecture    # 架构检查
sage-dev maintain doctor         # 健康诊断
sage-dev maintain submodule init # Submodule 初始化
sage-dev package pypi publish    # 发布到 PyPI
sage-dev package version bump    # 版本升级
sage-dev github issues stats     # Issues 统计
```

### 3. 易于扩展
每个组都可以独立扩展新命令，不会让顶层命令过于拥挤。

### 4. 向后兼容
可以保留旧命令作为别名：
```bash
sage-dev check-all → sage-dev quality check
sage-dev test      → sage-dev project test
sage-dev pypi      → sage-dev package pypi
```

## 🚀 实施步骤

### Phase 1: 重组命令结构
1. 创建新的命令组目录结构
2. 将现有命令迁移到对应组
3. 添加命令别名支持

### Phase 2: 集成 tools/ 脚本
1. 集成 `sage-maintenance.sh` → `sage-dev maintain`
2. 集成 `dev.sh` 功能到各组
3. 集成安装工具到 `sage-dev package install`

### Phase 3: 文档和测试
1. 更新文档和帮助信息
2. 更新 CI/CD 工作流
3. 添加命令别名测试

### Phase 4: 废弃旧命令
1. 在旧命令上添加 deprecation 警告
2. 文档中说明迁移路径
3. 几个版本后移除旧命令

## 📝 向后兼容映射

```python
# 命令别名映射
COMMAND_ALIASES = {
    # 旧命令 → 新命令
    "check-all": "quality check",
    "check-architecture": "quality architecture",
    "check-devnotes": "quality devnotes",
    "check-readme": "quality readme",
    "test": "project test",
    "status": "project status",
    "analyze": "project analyze",
    "clean": "project clean",
    "architecture": "project architecture",
    # 保留的命令组（向后兼容）
    "issues": "github issues",
    "pypi": "package pypi",
    "version": "package version",
    "models": "resource models",
}
```

## 🎯 使用示例

### 质量检查
```bash
# 运行所有检查
sage-dev quality check

# 只检查架构
sage-dev quality architecture

# 格式化代码
sage-dev quality format

# 自动修复问题
sage-dev quality fix
```

### 项目管理
```bash
# 查看项目状态
sage-dev project status

# 运行测试
sage-dev project test

# 代码分析
sage-dev project analyze

# 清理构建产物
sage-dev project clean
```

### 维护工具
```bash
# 健康检查
sage-dev maintain doctor

# Submodule 管理
sage-dev maintain submodule init
sage-dev maintain submodule status
sage-dev maintain submodule switch

# Git hooks
sage-dev maintain hooks install
```

### 包管理
```bash
# PyPI 发布
sage-dev package pypi validate
sage-dev package pypi build
sage-dev package pypi publish

# 版本管理
sage-dev package version list
sage-dev package version bump major
```

### GitHub 管理
```bash
# Issues 管理
sage-dev github issues status
sage-dev github issues stats
sage-dev github issues create
```

## 💡 额外建议

### 1. 添加快捷命令
常用操作提供更短的别名：
```bash
sage-dev q         # quality check
sage-dev qa        # quality architecture
sage-dev t         # project test
sage-dev c         # project clean
```

### 2. 交互式模式
```bash
sage-dev           # 进入交互式菜单
# 显示：
# 1. Quality Checks
# 2. Project Management
# 3. Maintenance
# 4. Package Management
# 5. GitHub Integration
```

### 3. 组合命令
```bash
sage-dev full-check  # quality check + project test + maintain doctor
sage-dev pre-commit  # quality check + quality format
sage-dev release     # quality check + project test + package version bump + package pypi publish
```

## 📊 迁移影响评估

### CI/CD 影响
需要更新的工作流文件：
- `.github/workflows/code-quality.yml`
- `.github/workflows/deployment-check.yml`

### 文档影响
需要更新的文档：
- `DEVELOPER.md`
- `CONTRIBUTING.md`
- `packages/sage-tools/README.md`
- 所有 dev-notes

### 用户影响
- 通过别名保持向后兼容
- 添加 deprecation 警告
- 提供迁移指南

## 🎉 预期收益

1. **更清晰** - 命令按功能分组，一目了然
2. **更易学** - 语义化命令，容易记忆
3. **更易扩展** - 组内添加新命令不影响其他组
4. **更专业** - 类似 git、kubectl 等成熟 CLI 的组织方式
5. **集成完整** - 将所有开发工具统一到 sage-dev 下
