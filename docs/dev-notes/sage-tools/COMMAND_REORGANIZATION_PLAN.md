# SAGE Dev 命令重组实施计划

## 📅 创建时间
2025-10-26

## 🎯 目标
将 `sage dev` 下的15个顶层命令重新组织为6个二级命令组，使命令结构更清晰、更易于理解和扩展。

## 📊 重组映射表

### 1. quality/ - 质量检查组

| 原命令 | 新命令 | 说明 |
|--------|--------|------|
| `check-all` | `quality check` | 运行所有质量检查 |
| `check-architecture` | `quality architecture` | 架构合规性检查 |
| `check-devnotes` | `quality devnotes` | dev-notes 文档规范检查 |
| `check-readme` | `quality readme` | README 质量检查 |
| `quality` | `quality format` | 代码格式化（拆分功能） |
| - | `quality lint` | 代码检查（拆分功能） |
| - | `quality fix` | 自动修复（拆分功能） |

**待实现**:
- [ ] 创建 `packages/sage-tools/src/sage/tools/cli/commands/dev/quality/__init__.py`
- [ ] 迁移 `check-all` 命令
- [ ] 迁移 `check-architecture` 命令
- [ ] 迁移 `check-devnotes` 命令
- [ ] 迁移 `check-readme` 命令
- [ ] 拆分 `quality` 命令为 format, lint, fix 子命令

### 2. project/ - 项目管理组

| 原命令 | 新命令 | 说明 |
|--------|--------|------|
| `status` | `project status` | 项目状态 |
| `analyze` | `project analyze` | 代码分析 |
| `clean` | `project clean` | 清理构建产物 |
| `test` | `project test` | 运行测试 |
| `architecture` | `project architecture` | 显示架构信息 |
| `home` | `project home` | 项目主页 |

**待实现**:
- [ ] 创建 `packages/sage-tools/src/sage/tools/cli/commands/dev/project/__init__.py`
- [ ] 迁移 `status` 命令
- [ ] 迁移 `analyze` 命令
- [ ] 迁移 `clean` 命令
- [ ] 迁移 `test` 命令
- [ ] 迁移 `architecture` 命令
- [ ] 迁移 `home` 命令

### 3. maintain/ - 维护工具组

| 原脚本/功能 | 新命令 | 说明 |
|------------|--------|------|
| `tools/maintenance/sage-maintenance.sh doctor` | `maintain doctor` | 健康检查 |
| `tools/maintenance/sage-maintenance.sh submodule *` | `maintain submodule` | Submodule 管理 |
| `tools/maintenance/sage-maintenance.sh setup-hooks` | `maintain hooks` | Git hooks 管理 |
| `tools/maintenance/sage-maintenance.sh security-check` | `maintain security` | 安全检查 |

**子命令: maintain submodule**
- `init` - 初始化 submodules
- `status` - 查看状态
- `switch` - 切换分支
- `update` - 更新
- `fix-conflict` - 解决冲突
- `cleanup` - 清理

**待实现**:
- [ ] 创建 `packages/sage-tools/src/sage/tools/cli/commands/dev/maintain/__init__.py`
- [ ] 集成 `sage-maintenance.sh` 的 doctor 功能
- [ ] 集成 submodule 管理功能
- [ ] 集成 hooks 管理功能
- [ ] 集成 security 检查功能

### 4. package/ - 包管理组

| 原命令 | 新命令 | 说明 |
|--------|--------|------|
| `pypi` | `package pypi` | PyPI 包管理 |
| `version` | `package version` | 版本管理 |
| - | `package install` | 安装管理（新增） |

**子命令: package pypi**
- `validate` - 验证包配置
- `check` - 检查包
- `build` - 构建包
- `clean` - 清理构建产物
- `publish` - 发布到 PyPI

**子命令: package version**
- `list` - 列出版本
- `set` - 设置版本
- `bump` - 升级版本
- `sync` - 同步版本

**待实现**:
- [ ] 创建 `packages/sage-tools/src/sage/tools/cli/commands/dev/package/__init__.py`
- [ ] 迁移 `pypi` 命令（已存在于 packages/sage-tools/src/sage/tools/cli/commands/pypi.py）
- [ ] 迁移 `version` 命令（已存在于 packages/sage-tools/src/sage/tools/cli/commands/dev/version.py）
- [ ] 添加 `install` 子命令

### 5. resource/ - 资源管理组

| 原命令 | 新命令 | 说明 |
|--------|--------|------|
| `models` | `resource models` | 模型缓存管理 |

**子命令: resource models**
- `configure` - 配置环境变量
- `cache` - 缓存模型
- `check` - 检查模型
- `clear` - 清理缓存

**待实现**:
- [ ] 创建 `packages/sage-tools/src/sage/tools/cli/commands/dev/resource/__init__.py`
- [ ] 迁移 `models` 命令（已存在于 packages/sage-tools/src/sage/tools/cli/commands/dev/models.py）

### 6. github/ - GitHub 管理组

| 原命令 | 新命令 | 说明 |
|--------|--------|------|
| `issues` | `github issues` | Issues 管理 |

**子命令: github issues**
- `status` - 查看状态
- `download` - 下载 issues
- `stats` - 统计信息
- `team` - 团队信息
- `create` - 创建 issue
- `project` - 项目管理
- `config` - 配置
- `ai` - AI 辅助
- `sync` - 同步
- `organize` - 组织
- `test` - 测试

**待实现**:
- [ ] 创建 `packages/sage-tools/src/sage/tools/cli/commands/dev/github/__init__.py`
- [ ] 迁移 `issues` 命令（需要从独立模块移动）

## 🔄 向后兼容策略

### 命令别名
保留旧命令作为别名，显示 deprecation 警告：

```python
# 在 main.py 中添加
DEPRECATED_COMMANDS = {
    "check-all": "quality check",
    "check-architecture": "quality architecture",
    "check-devnotes": "quality devnotes",
    "check-readme": "quality readme",
    "test": "project test",
    "status": "project status",
    "analyze": "project analyze",
    "clean": "project clean",
    "architecture": "project architecture",
    "issues": "github issues",
    "pypi": "package pypi",
    "version": "package version",
    "models": "resource models",
}
```

### Deprecation 警告示例
```
⚠️  警告: 'sage dev test' 已弃用，请使用 'sage dev project test'
   旧命令将在 v1.0.0 版本后移除
```

## 📁 新目录结构

```
packages/sage-tools/src/sage/tools/cli/commands/dev/
├── __init__.py                 # 主命令注册
├── main.py                     # 保留用于向后兼容别名
├── quality/                    # 质量检查组
│   ├── __init__.py
│   ├── check.py               # check-all
│   ├── architecture.py        # check-architecture
│   ├── devnotes.py           # check-devnotes
│   ├── readme.py             # check-readme
│   ├── format.py             # 格式化
│   ├── lint.py               # 检查
│   └── fix.py                # 修复
├── project/                    # 项目管理组
│   ├── __init__.py
│   ├── status.py
│   ├── analyze.py
│   ├── clean.py
│   ├── test.py
│   ├── architecture.py
│   └── home.py
├── maintain/                   # 维护工具组
│   ├── __init__.py
│   ├── doctor.py
│   ├── submodule.py
│   ├── hooks.py
│   └── security.py
├── package/                    # 包管理组
│   ├── __init__.py
│   ├── pypi.py
│   ├── version.py
│   └── install.py
├── resource/                   # 资源管理组
│   ├── __init__.py
│   └── models.py
└── github/                     # GitHub 管理组
    ├── __init__.py
    └── issues.py
```

## 🚀 实施阶段

### Phase 1: 创建基础结构（当前）
- [x] 创建6个命令组目录
- [x] 创建重组方案文档
- [ ] 创建各组的 `__init__.py`
- [ ] 实现命令别名机制

### Phase 2: 迁移现有命令
- [ ] 迁移 quality 组命令
- [ ] 迁移 project 组命令
- [ ] 迁移 package 组命令
- [ ] 迁移 resource 组命令
- [ ] 迁移 github 组命令

### Phase 3: 集成 tools/ 脚本
- [ ] 集成 sage-maintenance.sh
- [ ] 集成 dev.sh 功能
- [ ] 添加缺失的命令

### Phase 4: 测试和文档
- [ ] 更新所有测试
- [ ] 更新 CI/CD 工作流
- [ ] 更新文档
- [ ] 添加迁移指南

### Phase 5: 发布
- [ ] 发布 beta 版本
- [ ] 收集用户反馈
- [ ] 正式发布
- [ ] 逐步废弃旧命令

## 📝 注意事项

1. **保持向后兼容**: 所有旧命令必须通过别名继续工作
2. **渐进式废弃**: 给用户足够时间迁移（至少2个版本）
3. **清晰的文档**: 提供详细的迁移指南
4. **CI/CD 更新**: 确保所有自动化工作流使用新命令
5. **测试覆盖**: 为所有命令添加测试，包括别名

## 🎯 预期收益

1. **命令发现性**: 从15个平铺命令 → 6个分组命令
2. **语义清晰**: `sage dev quality check` vs `sage dev check-all`
3. **易于扩展**: 每个组可以独立添加新命令
4. **专业性**: 类似 git、kubectl 的命令组织方式
5. **集成完整**: 所有开发工具统一入口

## 📊 进度跟踪

- **总进度**: 0/60 (0%)
  - Phase 1: 2/4 (50%)
  - Phase 2: 0/25 (0%)
  - Phase 3: 0/10 (0%)
  - Phase 4: 0/15 (0%)
  - Phase 5: 0/6 (0%)

**最后更新**: 2025-10-26
