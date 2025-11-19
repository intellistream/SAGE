# SAGE 安装一致性工具

本目录包含用于确保本地开发环境与 CI/CD 环境安装一致性的工具。

## 问题背景

在开发过程中，我们经常遇到 "CI/CD 通过但本地失败" 的问题。主要原因是本地和 CI/CD 使用不同的安装方式。

## 解决方案

所有环境（本地开发、CI/CD）都必须使用 `quickstart.sh` 进行安装。

## 工具列表

### 1. CI/CD 安装包装器

**文件**: `ci_install_wrapper.sh`

CI/CD 环境使用的安装脚本，确保与本地开发使用完全相同的安装方式。

```bash
# CI/CD 中使用
./tools/install/ci_install_wrapper.sh --dev --yes
```

**功能**:

- 包装 `quickstart.sh`
- 记录详细日志到 `.sage/logs/ci_install.log`
- 验证 CI 环境

### 2. 安装验证工具

**文件**: `validate_installation.sh`

开发者可以手动运行的验证工具，检查本地安装是否与 CI/CD 一致。

```bash
# 基本验证
./tools/install/validate_installation.sh

# 自动修复问题
./tools/install/validate_installation.sh --fix

# 严格模式（任何警告都失败）
./tools/install/validate_installation.sh --strict

# 详细对比 CI/CD 配置
./tools/install/validate_installation.sh --ci-compare
```

**检查项目**:

- ✅ 安装方法（是否使用 quickstart.sh）
- ✅ 包安装方式（可编辑 vs 标准）
- ✅ Python 版本（3.10-3.12）
- ✅ 系统依赖（gcc, cmake, git）
- ✅ Git 子模块状态
- ✅ Git Hooks 安装
- ✅ CI/CD 配置对比

### 3. Pre-commit Hook 检查

**文件**: `examination_tools/installation_consistency_check.sh`

集成到 Git pre-commit hooks 中，在提交代码时自动检查安装一致性。

**触发条件**: 修改以下文件时自动运行

- `quickstart.sh`
- `tools/install/**/*.sh`
- `packages/*/pyproject.toml`
- `packages/*/setup.py`
- `.github/workflows/*.yml`

## 使用指南

### 对于开发者

#### 首次安装

```bash
# 1. 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 使用 quickstart.sh 安装（推荐开发模式）
./quickstart.sh --dev --yes

# 3. 验证安装
./tools/install/validate_installation.sh

# 4. 安装 Git hooks（包含安装一致性检查）
sage-dev maintain hooks install
```

#### 日常开发

```bash
# 更新依赖后验证
./tools/install/validate_installation.sh

# 修复检测到的问题
./tools/install/validate_installation.sh --fix

# 严格模式验证（推荐在提交 PR 前运行）
./tools/install/validate_installation.sh --strict --ci-compare
```

### 对于 CI/CD

在 GitHub Actions workflow 中使用：

```yaml
- name: Install SAGE
  run: |
    chmod +x ./tools/install/ci_install_wrapper.sh
    ./tools/install/ci_install_wrapper.sh --dev --yes
```

## 最佳实践

### ✅ 应该做的

- 始终使用 `quickstart.sh` 安装
- 定期运行 `validate_installation.sh`
- 安装 Git hooks 进行自动检查
- 在虚拟环境或 conda 环境中工作
- 使用 Python 3.10-3.12（与 CI 一致）

### ❌ 不应该做的

- 不要手动运行 `pip install isage`
- 不要跳过 pre-commit 检查（`--no-verify`）
- 不要在 CI 配置中添加特殊安装步骤
- 不要混合使用不同的安装方式

## 验证清单

在提交 PR 或遇到问题时，请确保：

- [ ] 使用 `quickstart.sh` 安装
- [ ] 运行 `./tools/install/validate_installation.sh` 通过
- [ ] Git hooks 已安装
- [ ] 所有子模块已初始化
- [ ] 在虚拟环境中工作
- [ ] Python 版本在 3.10-3.12 之间

## 故障排除

### 问题：CI 通过但本地失败

**解决步骤**:

```bash
# 1. 运行验证工具
./tools/install/validate_installation.sh --ci-compare

# 2. 检查是否使用 quickstart.sh 安装
ls -la .sage/logs/install.log

# 3. 清理并重新安装
./quickstart.sh --clean
./quickstart.sh --dev --yes

# 4. 再次验证
./tools/install/validate_installation.sh
```

### 问题：手动安装了包怎么办

**解决步骤**:

```bash
# 1. 卸载现有安装
pip uninstall isage isage-common isage-kernel -y

# 2. 清理环境
./quickstart.sh --clean

# 3. 使用 quickstart.sh 重新安装
./quickstart.sh --dev --yes
```

### 问题：Pre-commit 检查失败

**解决步骤**:

```bash
# 1. 查看具体错误
git commit -v

# 2. 运行详细验证
./tools/install/validate_installation.sh --fix

# 3. 重新提交
git commit
```

## 详细文档

- **完整指南**:
  [docs/dev-notes/INSTALLATION_CONSISTENCY.md](../../docs/dev-notes/INSTALLATION_CONSISTENCY.md)
- **解决方案总结**: [docs/dev-notes/ISSUE_1121_SOLUTION.md](../../docs/dev-notes/ISSUE_1121_SOLUTION.md)
- **开发者指南**: [DEVELOPER.md](../../DEVELOPER.md)

## 相关 Issue

- Issue #1121: CI/CD 通过但本地安装出现 bug

## 反馈和改进

如果您遇到问题或有改进建议：

1. 运行验证工具并保存输出
1. 收集相关日志（`.sage/logs/install.log`）
1. 在 GitHub 创建 issue
1. 标记为 `installation` 和 `consistency` 标签

______________________________________________________________________

**最后更新**: 2025-11-19\
**版本**: 1.0
