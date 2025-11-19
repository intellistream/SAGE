# Issue #1121 解决方案总结

## 问题描述

CI/CD 测试通过，但本地安装时出现 bug 检测不到。需要升级 hooks 来检查两边的安装是否保持一致，或者让 CI/CD 完全使用 quickstart.sh 来安装。

## 实施的解决方案

### 1. CI/CD 安装包装器
- **文件**: `tools/install/ci_install_wrapper.sh`
- **功能**:
  - 包装 `quickstart.sh`，确保 CI/CD 与本地使用完全相同的安装方式
  - 记录详细的安装日志到 `.sage/logs/ci_install.log`
  - 验证 CI 环境配置

### 2. Pre-commit Hook 检查
- **文件**: `tools/install/examination_tools/installation_consistency_check.sh`
- **集成**: 已添加到 `.pre-commit-config.yaml`
- **功能**:
  - 检查本地安装方法是否使用 `quickstart.sh`
  - 验证包安装方式（可编辑 vs 标准安装）
  - 检查 Python 版本兼容性
  - 验证系统依赖和 Git 子模块
  - 在修改安装相关文件时自动运行

### 3. 手动验证工具
- **文件**: `tools/install/validate_installation.sh`
- **功能**:
  - 全面检查本地安装与 CI/CD 的一致性
  - 支持自动修复 (`--fix`)
  - 严格模式 (`--strict`)
  - CI 配置对比 (`--ci-compare`)
  - 提供详细的报告和建议

### 4. CI/CD Workflow 更新
- **修改的文件**:
  - `.github/workflows/build-test.yml`
  - `.github/workflows/installation-test.yml`
- **变更**:
  - 统一使用 `ci_install_wrapper.sh` 调用 `quickstart.sh`
  - 添加注释说明 wheel 测试的目的（模拟 PyPI 发布）
  - 确保所有主要 CI job 都使用相同的安装方式

### 5. 文档更新
- **新增文档**: `docs/dev-notes/INSTALLATION_CONSISTENCY.md`
  - 详细说明问题背景和解决方案
  - 提供开发者最佳实践
  - 工具使用说明
  - 常见问题解答
- **更新文档**: `DEVELOPER.md`
  - 在顶部添加安装一致性警告
  - 链接到详细指南

## 使用方法

### 对于开发者

1. **安装 SAGE**
   ```bash
   ./quickstart.sh --dev --yes
   ```

2. **验证安装**
   ```bash
   ./tools/install/validate_installation.sh
   ```

3. **安装 Git Hooks**（自动检查）
   ```bash
   sage-dev maintain hooks install
   ```

4. **定期验证**
   ```bash
   ./tools/install/validate_installation.sh --ci-compare
   ```

### 对于 CI/CD

CI/CD 工作流自动使用 `ci_install_wrapper.sh`:

```yaml
- name: Install SAGE
  run: |
    ./tools/install/ci_install_wrapper.sh --dev --yes
```

### Pre-commit Hook

当修改以下文件时自动运行检查：
- `quickstart.sh`
- `tools/install/**/*.sh`
- `packages/*/pyproject.toml`
- `packages/*/setup.py`
- `.github/workflows/*.yml`

## 检查项目

验证工具会检查：

1. ✅ 安装方法（是否使用 quickstart.sh）
2. ✅ 包安装方式（可编辑 vs 标准）
3. ✅ Python 版本（3.10-3.12）
4. ✅ 系统依赖（gcc, cmake, git）
5. ✅ Git 子模块状态
6. ✅ Git Hooks 安装
7. ✅ CI/CD 配置一致性

## 效果

### 解决的问题
- ✅ 消除 "CI 通过但本地失败" 的不一致性
- ✅ 自动化检查，及早发现问题
- ✅ 提供清晰的修复指导
- ✅ 确保所有环境使用相同的安装方式

### 开发者体验改善
- 🎯 明确的安装指南
- 🔍 自动化检查，减少人工验证
- 🛠️ 自动修复工具
- 📚 详细的文档和最佳实践

### CI/CD 改进
- 🔐 更可靠的测试结果
- 📊 详细的安装日志
- 🔄 与本地开发完全一致
- ⚡ 更早发现环境问题

## 文件清单

### 新增文件
1. `tools/install/ci_install_wrapper.sh` - CI/CD 安装包装器
2. `tools/install/validate_installation.sh` - 手动验证工具
3. `tools/install/examination_tools/installation_consistency_check.sh` - Pre-commit hook 检查
4. `docs/dev-notes/INSTALLATION_CONSISTENCY.md` - 详细文档

### 修改文件
1. `.pre-commit-config.yaml` - 添加安装一致性检查 hook
2. `.github/workflows/build-test.yml` - 使用 ci_install_wrapper.sh
3. `.github/workflows/installation-test.yml` - 使用 ci_install_wrapper.sh，添加说明注释
4. `DEVELOPER.md` - 添加安装一致性警告和链接

## 测试建议

### 本地测试
```bash
# 1. 清理环境
./quickstart.sh --clean

# 2. 使用 quickstart.sh 安装
./quickstart.sh --dev --yes

# 3. 运行验证
./tools/install/validate_installation.sh

# 4. 测试 pre-commit hook
git add .
git commit -m "test: installation consistency check"
```

### CI/CD 测试
- 创建 PR 触发所有 CI 工作流
- 验证 `ci_install_wrapper.sh` 正常工作
- 检查安装日志是否完整

## 后续改进建议

1. **添加更多检查项**
   - 检查 conda/venv 环境变量
   - 验证 C++ 扩展构建配置
   - 检查依赖版本精确匹配

2. **增强自动修复**
   - 自动切换到推荐的 Python 版本
   - 自动安装缺失的系统依赖
   - 自动清理冲突的安装

3. **集成到 CI 报告**
   - 在 PR 中显示安装一致性检查结果
   - 失败时提供详细的修复建议
   - 追踪一致性指标

4. **监控和告警**
   - 定期检查开发者的安装配置
   - 当检测到不一致时发送通知
   - 统计常见的安装问题

## 总结

通过实施这套完整的解决方案，我们：

1. **统一了安装方式** - 所有环境都使用 `quickstart.sh`
2. **自动化了检查** - Pre-commit hook 和验证工具
3. **改进了 CI/CD** - 使用包装器确保一致性
4. **完善了文档** - 清晰的指南和最佳实践

这将显著减少 "CI 通过但本地失败" 的问题，提高开发效率和代码质量。

---

**相关 Issue**: #1121  
**实施日期**: 2025-11-19  
**版本**: 1.0
