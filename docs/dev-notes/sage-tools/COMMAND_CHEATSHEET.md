# sage-dev 命令速查表

## 📋 新命令结构概览

```
sage-dev
├── quality/      🔍 质量检查
├── project/      📊 项目管理  
├── maintain/     🔧 维护工具
├── package/      📦 包管理
├── resource/     💾 资源管理
└── github/       🐙 GitHub 管理
```

## 🔍 quality - 质量检查

| 命令 | 说明 | 示例 |
|------|------|------|
| `sage-dev quality check` | 运行所有质量检查 | `sage-dev quality check` |
| `sage-dev quality architecture` | 架构合规性检查 | `sage-dev quality architecture --changed-only` |
| `sage-dev quality devnotes` | dev-notes 文档规范检查 | `sage-dev quality devnotes` |
| `sage-dev quality readme` | README 质量检查 | `sage-dev quality readme` |
| `sage-dev quality format` | 代码格式化 | `sage-dev quality format --all-files` |
| `sage-dev quality lint` | 代码检查 | `sage-dev quality lint` |
| `sage-dev quality fix` | 自动修复问题 | `sage-dev quality fix` |

## 📊 project - 项目管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `sage-dev project status` | 查看项目状态 | `sage-dev project status -p sage-libs` |
| `sage-dev project analyze` | 代码分析 | `sage-dev project analyze -t dependencies` |
| `sage-dev project clean` | 清理构建产物 | `sage-dev project clean --deep` |
| `sage-dev project test` | 运行测试 | `sage-dev project test --test-type unit` |
| `sage-dev project architecture` | 显示架构信息 | `sage-dev project architecture -f json` |
| `sage-dev project home` | 项目主页 | `sage-dev project home` |

## 🔧 maintain - 维护工具

| 命令 | 说明 | 示例 |
|------|------|------|
| `sage-dev maintain doctor` | 健康检查 | `sage-dev maintain doctor` |
| `sage-dev maintain submodule init` | 初始化 submodules | `sage-dev maintain submodule init` |
| `sage-dev maintain submodule status` | 查看 submodule 状态 | `sage-dev maintain submodule status` |
| `sage-dev maintain submodule switch` | 切换 submodule 分支 | `sage-dev maintain submodule switch` |
| `sage-dev maintain submodule update` | 更新 submodules | `sage-dev maintain submodule update` |
| `sage-dev maintain submodule fix-conflict` | 解决 submodule 冲突 | `sage-dev maintain submodule fix-conflict` |
| `sage-dev maintain submodule cleanup` | 清理 submodule 配置 | `sage-dev maintain submodule cleanup` |
| `sage-dev maintain submodule bootstrap` | 快速初始化 | `sage-dev maintain submodule bootstrap` |
| `sage-dev maintain hooks` | 安装 Git hooks | `sage-dev maintain hooks --force` |
| `sage-dev maintain security` | 安全检查 | `sage-dev maintain security` |
| `sage-dev maintain clean` | 清理项目 | `sage-dev maintain clean --deep` |

## 📦 package - 包管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `sage-dev package install` | 安装包 | `sage-dev package install -p sage-libs` |
| `sage-dev package pypi validate` | 验证包配置 | `sage-dev package pypi validate` |
| `sage-dev package pypi build` | 构建包 | `sage-dev package pypi build` |
| `sage-dev package pypi publish` | 发布到 PyPI | `sage-dev package pypi publish` |
| `sage-dev package version list` | 列出版本 | `sage-dev package version list` |
| `sage-dev package version bump` | 升级版本 | `sage-dev package version bump major` |
| `sage-dev package version sync` | 同步版本 | `sage-dev package version sync` |

## 💾 resource - 资源管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `sage-dev resource models configure` | 配置模型环境 | `sage-dev resource models configure` |
| `sage-dev resource models cache` | 缓存模型 | `sage-dev resource models cache` |
| `sage-dev resource models check` | 检查模型 | `sage-dev resource models check` |
| `sage-dev resource models clear` | 清理缓存 | `sage-dev resource models clear` |

## 🐙 github - GitHub 管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `sage-dev github issues status` | 查看 issues 状态 | `sage-dev github issues status` |
| `sage-dev github issues download` | 下载 issues | `sage-dev github issues download` |
| `sage-dev github issues stats` | Issues 统计 | `sage-dev github issues stats` |

注：github issues 功能正在迁移中，当前可能需要使用旧命令。

## 🔄 向后兼容别名

旧命令仍然可用，但会显示弃用警告：

| 旧命令 | 新命令 | 状态 |
|--------|--------|------|
| `sage-dev test` | `sage-dev project test` | ⚠️ 已弃用 |
| `sage-dev status` | `sage-dev project status` | ⚠️ 已弃用 |
| `sage-dev analyze` | `sage-dev project analyze` | ⚠️ 已弃用 |
| `sage-dev clean` | `sage-dev project clean` | ⚠️ 已弃用 |
| `sage-dev architecture` | `sage-dev project architecture` | ⚠️ 已弃用 |
| `sage-dev check-all` | `sage-dev quality check` | ⚠️ 已弃用 |
| `sage-dev check-architecture` | `sage-dev quality architecture` | ⚠️ 已弃用 |
| `sage-dev check-devnotes` | `sage-dev quality devnotes` | ⚠️ 已弃用 |
| `sage-dev check-readme` | `sage-dev quality readme` | ⚠️ 已弃用 |

## 💡 常用工作流

### 开发前检查
```bash
# 1. 健康检查
sage-dev maintain doctor

# 2. 初始化 submodules（首次）
sage-dev maintain submodule init

# 3. 查看项目状态
sage-dev project status
```

### 日常开发
```bash
# 1. 运行质量检查
sage-dev quality check

# 2. 格式化代码
sage-dev quality format

# 3. 运行测试
sage-dev project test --test-type unit
```

### 发布前准备
```bash
# 1. 完整质量检查
sage-dev quality check --readme

# 2. 运行所有测试
sage-dev project test

# 3. 升级版本
sage-dev package version bump patch

# 4. 构建包
sage-dev package pypi build

# 5. 发布
sage-dev package pypi publish
```

### 维护操作
```bash
# 1. 清理项目
sage-dev project clean --deep

# 2. Submodule 管理
sage-dev maintain submodule switch
sage-dev maintain submodule update

# 3. 安装 hooks
sage-dev maintain hooks --force

# 4. 安全检查
sage-dev maintain security
```

## 📝 命令层级规则

- **2级**: `sage-dev <group>`
- **3级**: `sage-dev <group> <command>`
- **4级**: `sage-dev <group> <subgroup> <command>`（最深）

示例：
```bash
sage-dev quality check                    # 3级 ✅
sage-dev maintain submodule init          # 4级 ✅
sage-dev package pypi validate            # 4级 ✅
```

## 🆘 获取帮助

```bash
# 查看所有命令组
sage-dev --help

# 查看特定组的命令
sage-dev quality --help
sage-dev project --help
sage-dev maintain --help

# 查看特定命令的详细说明
sage-dev quality check --help
sage-dev maintain submodule init --help
```

## 📚 相关文档

- [COMMAND_REORGANIZATION.md](./COMMAND_REORGANIZATION.md) - 重组方案详细说明
- [COMMAND_REORGANIZATION_PLAN.md](./COMMAND_REORGANIZATION_PLAN.md) - 实施计划
- [sage-tools README](../../../packages/sage-tools/README.md) - sage-tools 包文档
