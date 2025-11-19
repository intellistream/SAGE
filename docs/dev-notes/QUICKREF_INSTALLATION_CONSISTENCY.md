# Issue #1121: 安装一致性解决方案 - 快速参考

## 问题

CI/CD 通过，但本地安装出现 bug 检测不到。

## 真相

✅ **CI/CD 已经在用 `quickstart.sh`**\
❌ **问题：开发者不知道也要用 `quickstart.sh`**

## 解决方案（教育+验证）

### 核心：让开发者知道并验证正确的安装方式

**不是改 CI/CD（CI 已经正确），而是帮助开发者对齐环境**

## 核心原则

**所有环境都必须使用 `quickstart.sh` 安装**

```bash
# ✅ 正确
./quickstart.sh --dev --yes

# ❌ 错误
pip install isage
```

## 新增工具

### 1. CI/CD 安装包装器

```bash
./tools/install/ci_install_wrapper.sh --dev --yes
```

- CI/CD 专用
- 包装 quickstart.sh
- 记录详细日志

### 2. 安装验证工具

```bash
./tools/install/validate_installation.sh [--fix|--strict|--ci-compare]
```

- 开发者手动运行
- 全面检查 7 个项目
- 可自动修复问题

### 3. Pre-commit Hook

```bash
# 自动运行，修改安装文件时触发
```

- 集成到 .pre-commit-config.yaml
- 自动检查一致性
- 提供修复建议

## 快速开始

### 新开发者

```bash
# 1. 克隆并安装
git clone https://github.com/intellistream/SAGE.git
cd SAGE
./quickstart.sh --dev --yes

# 2. 验证安装
./tools/install/validate_installation.sh

# 3. 安装 hooks
sage-dev maintain hooks install
```

### 现有开发者

```bash
# 如果之前手动安装过
pip uninstall isage -y
./quickstart.sh --clean
./quickstart.sh --dev --yes

# 验证
./tools/install/validate_installation.sh
```

## 文件变更

### 新增文件（4个）

1. `tools/install/ci_install_wrapper.sh` - CI 包装器
1. `tools/install/validate_installation.sh` - 验证工具
1. `tools/install/examination_tools/installation_consistency_check.sh` - Hook 检查
1. `docs/dev-notes/INSTALLATION_CONSISTENCY.md` - 完整文档

### 修改文件（3个）

1. `.pre-commit-config.yaml` - 添加检查 hook
1. `.github/workflows/build-test.yml` - 使用包装器
1. `.github/workflows/installation-test.yml` - 使用包装器
1. `DEVELOPER.md` - 添加警告和链接

### 新增文档（3个）

1. `docs/dev-notes/INSTALLATION_CONSISTENCY.md` - 完整指南
1. `docs/dev-notes/ISSUE_1121_SOLUTION.md` - 解决方案总结
1. `tools/install/README_CONSISTENCY.md` - 工具说明

## 验证清单

提交 PR 前确保：

- [ ] 使用 `quickstart.sh` 安装
- [ ] `./tools/install/validate_installation.sh` 通过
- [ ] Git hooks 已安装
- [ ] Python 3.10-3.12
- [ ] 子模块已初始化

## 检查项目

验证工具检查 7 个方面：

1. 安装方法（quickstart.sh）
1. 包安装方式（可编辑安装）
1. Python 环境（3.10-3.12）
1. 系统依赖（gcc, cmake, git）
1. Git 子模块
1. Git Hooks
1. CI/CD 配置对比

## 详细文档

- 📘 **完整指南**:
  [docs/dev-notes/INSTALLATION_CONSISTENCY.md](docs/dev-notes/INSTALLATION_CONSISTENCY.md)
- 📋 **解决方案**: [docs/dev-notes/ISSUE_1121_SOLUTION.md](docs/dev-notes/ISSUE_1121_SOLUTION.md)
- 🛠️ **工具说明**: [tools/install/README_CONSISTENCY.md](tools/install/README_CONSISTENCY.md)
- 👨‍💻 **开发指南**: [DEVELOPER.md](DEVELOPER.md)

## 命令速查

```bash
# 验证安装
./tools/install/validate_installation.sh

# 自动修复
./tools/install/validate_installation.sh --fix

# 严格模式
./tools/install/validate_installation.sh --strict

# CI 对比
./tools/install/validate_installation.sh --ci-compare

# 清理重装
./quickstart.sh --clean
./quickstart.sh --dev --yes

# 安装 hooks
sage-dev maintain hooks install
```

## 问题排查

### CI 通过但本地失败？

```bash
./tools/install/validate_installation.sh --ci-compare
```

### 手动安装了包？

```bash
pip uninstall isage -y
./quickstart.sh --clean
./quickstart.sh --dev --yes
```

### Hook 检查失败？

```bash
./tools/install/validate_installation.sh --fix
git commit
```

## 效果

✅ 消除 "CI 通过但本地失败"\
✅ 自动化检查，及早发现问题\
✅ 清晰的修复指导\
✅ 统一的安装方式

______________________________________________________________________

**Issue**: #1121\
**日期**: 2025-11-19\
**作者**: GitHub Copilot
