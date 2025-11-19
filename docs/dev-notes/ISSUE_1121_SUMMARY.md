# Issue #1121 解决方案 - 精简版

## 问题本质

**CI/CD 通过但本地失败** - 但这不是因为 CI 用了不同的安装方式！

## 真相

✅ **CI/CD 已经在用 `quickstart.sh`**  
❌ **问题在于开发者不知道也要用 `quickstart.sh`**

## 根本原因

1. **缺少明确指导** - 开发者可能手动 `pip install isage`
2. **环境配置差异** - Python 版本、系统依赖、子模块等
3. **缺少验证工具** - 无法快速检查本地环境是否与 CI 一致

## 解决方案（核心是教育+验证）

### 1. 强化文档 📚

在 `DEVELOPER.md` 顶部添加明确警告：

```markdown
## ⚠️ 重要：安装一致性
必须使用 quickstart.sh 安装！
详见：docs/dev-notes/INSTALLATION_CONSISTENCY.md
```

### 2. 验证工具 🔍

开发者可以自查环境：

```bash
# 检查 7 个方面的一致性
./tools/install/validate_installation.sh

# 自动修复问题
./tools/install/validate_installation.sh --fix

# 与 CI 详细对比
./tools/install/validate_installation.sh --ci-compare
```

### 3. Pre-commit Hook ⚡

修改安装相关文件时自动检查：

```bash
# 自动运行（已集成到 .pre-commit-config.yaml）
git commit
# → 触发安装一致性检查
```

### 4. CI 包装器（可选）📦

虽然 CI 已经用 `quickstart.sh`，但加了包装器提供额外保障：

```bash
# CI/CD 中使用（可选）
./tools/install/ci_install_wrapper.sh --dev --yes
# → 额外的日志和验证
```

## 新增的工具

| 工具 | 作用 | 使用场景 |
|------|------|----------|
| `validate_installation.sh` | 验证环境一致性 | 开发者手动运行 |
| `installation_consistency_check.sh` | 快速检查 | Pre-commit hook |
| `ci_install_wrapper.sh` | 增强日志和验证 | CI/CD（可选） |

## 开发者指南

### 正确的开发流程

```bash
# 1. 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 使用 quickstart.sh 安装（与 CI 一致）
./quickstart.sh --dev --yes

# 3. 验证环境
./tools/install/validate_installation.sh

# 4. 安装 Git hooks
sage-dev maintain hooks install
```

### ❌ 不要这样做

```bash
pip install isage           # 不是开发模式
pip install -e .            # 缺少依赖和检查
python setup.py install     # 过时方式
```

## CI/CD 说明

### build-test.yml（主要测试）

```yaml
# 已经正确，开发者应该参考这个
./quickstart.sh --dev --yes
```

### installation-test.yml（3 个 Jobs）

1. **Job 1**: ✅ 使用 `quickstart.sh` - **开发者参考这个**
2. **Job 2**: ⚠️ 从 wheel 安装 - 测试 PyPI 发布，不是开发流程
3. **Job 3**: ⚠️ 源码 pip install - 测试特殊场景，不是开发流程

## 检查清单

提交 PR 前：

- [ ] 使用 `./quickstart.sh --dev --yes` 安装
- [ ] 运行 `./tools/install/validate_installation.sh` 通过
- [ ] Git hooks 已安装
- [ ] Python 3.10-3.12
- [ ] 子模块已初始化

## 关键文档

- 📘 [完整指南](docs/dev-notes/INSTALLATION_CONSISTENCY.md)
- 🔍 [根因分析](docs/dev-notes/ISSUE_1121_ROOT_CAUSE_ANALYSIS.md)
- 🛠️ [工具说明](tools/install/README_CONSISTENCY.md)

## 一句话总结

**CI/CD 已经正确，问题是开发者不知道要用 `quickstart.sh`。解决方案：文档+验证工具+自动检查。**

---

**Issue**: #1121  
**日期**: 2025-11-19  
**核心洞察**: 问题不在 CI，在开发者教育
