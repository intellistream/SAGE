# 安装一致性指南

## 问题背景 (Issue #1121)

在开发过程中，我们经常遇到一个问题：**CI/CD 测试通过，但本地安装时出现 bug 检测不到**。这种不一致性会导致：

- 开发者在本地无法复现 CI 通过的环境
- 隐藏的 bug 在生产环境中暴露
- 浪费大量调试时间
- 降低代码质量和可靠性

## 根本原因

经过详细分析，发现主要问题**不是** CI/CD 使用了不同的安装方式（CI/CD 已经在用 `quickstart.sh`），而是：

### 1. **开发者不知道应该用 quickstart.sh**

很多开发者可能会：
```bash
# ❌ 常见错误
pip install isage
pip install -e packages/sage
python setup.py install
```

而 CI/CD 实际使用：
```bash
# ✅ CI/CD 的正确方式
./quickstart.sh --dev --yes
```

### 2. **环境配置差异**

即使使用了 `quickstart.sh`，仍可能存在：
- Python 版本不同（本地 3.9 vs CI 3.10-3.12）
- 系统依赖缺失（gcc, cmake, git）
- 子模块未初始化
- Git hooks 未安装
- 虚拟环境配置不当

### 3. **缺少验证机制**

开发者无法：
- 快速检查本地环境是否与 CI 一致
- 诊断配置问题
- 获得修复建议

## 解决方案

为了确保本地环境与 CI/CD 完全一致，我们实施了以下措施：

### 1. 统一安装方法

**明确规范：所有环境（本地开发、CI/CD）都必须使用 `quickstart.sh` 进行安装**

```bash
# ✅ 正确的安装方式（CI/CD 已在使用）
./quickstart.sh --dev --yes

# ❌ 不要使用
pip install isage
pip install -e .
python setup.py install
```

> **注意**: CI/CD 已经在使用 `quickstart.sh`，这个规范主要是为了确保**本地开发者也使用相同方式**。

### 2. CI/CD 安装包装器（可选增强）

虽然 CI/CD 已经在使用 `quickstart.sh`，我们添加了一个可选的包装器 `tools/install/ci_install_wrapper.sh`，提供：

- 记录详细的安装日志（便于对比排查）
- 验证 CI 环境配置
- 统一的入口点（未来可扩展更多检查）

```yaml
# .github/workflows/build-test.yml
# 可选：使用包装器获得额外的日志和验证
- name: Install SAGE
  run: |
    ./tools/install/ci_install_wrapper.sh --dev --yes
```

**重要**: 这个包装器不改变安装方式，只是在 `quickstart.sh` 外加了一层验证和日志。

### 3. 自动化检查

#### 3.1 Pre-commit Hook

在提交代码时自动检查安装一致性：

```yaml
# .pre-commit-config.yaml
- id: installation-consistency-check
  name: installation consistency check (local vs CI/CD)
  entry: bash tools/install/examination_tools/installation_consistency_check.sh
  language: system
  pass_filenames: false
  files: ^(quickstart\.sh|tools/install/.*\.sh|packages/.*/pyproject\.toml|\.github/workflows/.*\.yml)$
```

当修改安装相关文件时，会自动运行检查，确保本地安装配置与 CI/CD 一致。

#### 3.2 手动验证工具

开发者可以随时运行验证脚本：

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

## 开发者最佳实践

### 安装 SAGE

```bash
# 1. 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 使用 quickstart.sh 安装（开发模式）
./quickstart.sh --dev --yes

# 3. 验证安装
./tools/install/validate_installation.sh
```

### 更新依赖

```bash
# ❌ 不要手动安装包
# pip install some-package

# ✅ 更新 pyproject.toml，然后重新运行
./quickstart.sh --dev --yes
```

### 清理并重新安装

```bash
# 清理环境
./quickstart.sh --clean

# 重新安装
./quickstart.sh --dev --yes

# 验证
./tools/install/validate_installation.sh
```

### 安装 Git Hooks

```bash
# 安装代码质量检查 hooks
sage-dev maintain hooks install

# 查看 hooks 状态
sage-dev maintain hooks status
```

## 验证清单

在提交 PR 或遇到问题时，请确保：

- [ ] 使用 `quickstart.sh` 安装
- [ ] 运行 `./tools/install/validate_installation.sh` 通过
- [ ] Git hooks 已安装
- [ ] 所有子模块已初始化
- [ ] 在虚拟环境或 conda 环境中工作
- [ ] Python 版本在 3.10-3.12 之间（与 CI 一致）

## 工具说明

### 1. `quickstart.sh`

主安装脚本，支持多种模式：

```bash
./quickstart.sh --help                    # 查看帮助
./quickstart.sh --dev --yes              # 开发模式，自动确认
./quickstart.sh --core --yes             # 核心模式
./quickstart.sh --standard --yes         # 标准模式
./quickstart.sh --full --yes             # 完整模式
./quickstart.sh --clean                  # 清理环境
```

### 2. `tools/install/ci_install_wrapper.sh`

CI/CD 安装包装器：

- 在 CI/CD 环境中使用
- 记录详细日志到 `.sage/logs/ci_install.log`
- 验证 CI 环境配置
- 确保与 `quickstart.sh` 完全一致

### 3. `tools/install/validate_installation.sh`

安装验证工具：

```bash
./tools/install/validate_installation.sh           # 基本验证
./tools/install/validate_installation.sh --fix     # 自动修复
./tools/install/validate_installation.sh --strict  # 严格模式
./tools/install/validate_installation.sh --ci-compare  # CI 对比
```

检查项目：
- 安装方法（是否使用 quickstart.sh）
- 包安装方式（可编辑 vs 标准）
- Python 版本兼容性
- 系统依赖（gcc, cmake, git）
- Git 子模块状态
- Git hooks 安装
- CI/CD 配置对比

### 4. `tools/install/examination_tools/installation_consistency_check.sh`

Pre-commit hook 检查脚本：

- 自动运行于修改安装相关文件时
- 检查本地安装与 CI/CD 的一致性
- 提供修复建议

## CI/CD 配置说明

### 主要工作流

1. **build-test.yml**: 构建和测试
   - 使用 `quickstart.sh --dev --yes`（或通过 ci_install_wrapper.sh）
   - 这是**标准的开发安装方式**
   - 与本地开发者应该使用的方式完全一致

2. **installation-test.yml**: 安装测试（多场景）
   - **Job 1: 依赖完整性检查** - 使用 `quickstart.sh` ✅
     - 这是标准流程，与本地开发一致
   - **Job 2: Wheel 安装测试** - 从 wheel 安装 ⚠️
     - 目的：测试 **PyPI 发布后**用户的安装体验
     - **不是**开发者的标准流程
   - **Job 3: 源码安装测试** - 直接 pip install ⚠️
     - 目的：测试特殊安装场景
     - **不是**开发者的标准流程

3. **code-quality.yml**: 代码质量
   - 使用 `quickstart.sh --dev --yes`
   - 运行 pre-commit hooks（包括安装一致性检查）

### 重要说明

**本地开发者应该参考的是 Job 1（使用 quickstart.sh），而不是 Job 2/Job 3**

Job 2 和 Job 3 是为了测试不同的用户安装场景（PyPI 用户、特殊安装等），不是给开发者参考的标准流程。

### 测试矩阵

- Python 版本: 3.10, 3.11, 3.12
- 安装模式: core, standard, full, dev
- 操作系统: Ubuntu Latest

## 常见问题

### Q1: 为什么不能直接使用 `pip install isage`？

**A**: `pip install isage` 会从 PyPI 下载预构建的包，可能：
- 版本不是最新的开发版本
- 缺少 C++ 扩展的源码编译
- 依赖版本与本地开发不一致
- 无法进行可编辑安装（开发模式）

### Q2: 我已经手动安装了，怎么办？

**A**: 卸载并重新使用 `quickstart.sh` 安装：

```bash
# 卸载现有安装
pip uninstall isage isage-common isage-kernel -y

# 清理
./quickstart.sh --clean

# 重新安装
./quickstart.sh --dev --yes
```

### Q3: CI 通过但本地失败怎么办？

**A**:
1. 运行验证工具：`./tools/install/validate_installation.sh --ci-compare`
2. 检查 Python 版本是否一致
3. 确保使用 `quickstart.sh` 安装
4. 检查子模块是否已初始化
5. 查看 `.sage/logs/install.log` 对比 CI 日志

### Q4: 如何确保我的修改不会破坏安装一致性？

**A**:
1. 安装 Git hooks: `sage-dev maintain hooks install`
2. 修改安装相关文件时会自动运行检查
3. 提交前运行: `./tools/install/validate_installation.sh --strict`
4. 等待 CI/CD 完成验证

## 贡献者指南

如果您需要修改安装流程：

1. **只修改 `quickstart.sh`**
   - 不要在 CI/CD 配置中添加额外的安装步骤
   - 所有安装逻辑都应该在 `quickstart.sh` 或其调用的脚本中

2. **测试修改**
   ```bash
   # 本地测试
   ./quickstart.sh --clean
   ./quickstart.sh --dev --yes
   ./tools/install/validate_installation.sh

   # 验证 CI 会使用相同的方式
   ./tools/install/ci_install_wrapper.sh --dev --yes
   ```

3. **更新文档**
   - 如果添加了新的安装选项，更新此文档
   - 更新 `quickstart.sh --help` 的帮助信息

4. **提交 PR**
   - Git hooks 会自动检查
   - CI/CD 会验证所有安装模式

## 总结

**核心原则：本地开发环境与 CI/CD 环境必须完全一致**

- ✅ 使用 `quickstart.sh` 安装
- ✅ 安装 Git hooks
- ✅ 定期运行验证工具
- ✅ 遵循最佳实践

- ❌ 不要手动 `pip install`
- ❌ 不要跳过 pre-commit 检查
- ❌ 不要在 CI 配置中添加特殊安装步骤

通过遵循这些准则，我们可以：
- 消除 "CI 通过但本地失败" 的问题
- 提高代码质量和可靠性
- 减少调试时间
- 改善开发体验

## 相关文档

- [DEVELOPER.md](../../DEVELOPER.md) - 开发者指南
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - 贡献指南
- [quickstart.sh](../../quickstart.sh) - 安装脚本
- [.pre-commit-config.yaml](../../.pre-commit-config.yaml) - Pre-commit 配置

## 问题反馈

如果您遇到安装一致性问题，请：

1. 运行 `./tools/install/validate_installation.sh --ci-compare`
2. 收集日志：`.sage/logs/install.log`, `.sage/logs/ci_install.log`
3. 在 GitHub 上创建 issue，并附上验证结果和日志
4. 标记为 `installation` 和 `consistency` 标签

---

**最后更新**: 2025-11-19  
**相关 Issue**: #1121  
**版本**: 1.0
