

# SAGE 贡献指南

> 本指南帮助你高效、规范地向 SAGE 贡献代码。提交 Pull Request 前，请先阅读此文档。

## 📚 开发者资源 / Developer Resources

开始贡献前，请查看以下资源：

- **[DEVELOPER.md](DEVELOPER.md)** - 完整开发指南，包含设置、工作流、测试等
  - 📦 **[Dependency Management](DEVELOPER.md#dependency-management)** - 核心依赖架构、分层依赖、和功能模块选项
- **[CHANGELOG.md](CHANGELOG.md)** - 项目变更日志（遵循 Keep a Changelog 格式）
- **`sage-dev` CLI** - 开发助手命令，提供质量检查、测试、维护等常用功能
- **[.pre-commit-config.yaml](.pre-commit-config.yaml)** - Pre-commit 钩子配置（链接到
  `tools/pre-commit-config.yaml`）
- **[docs/images/architecture.svg](docs/images/architecture.svg)** - 系统架构图
- **[docs-public/docs_src/dev-notes/](docs-public/docs_src/dev-notes/)** - 开发笔记和修复总结

**快速命令**:

```bash
sage-dev quality fix .              # 自动修复代码质量
sage-dev project test --coverage    # 运行测试
```

## 目录

- [新人贡献快速流程](#%E6%96%B0%E4%BA%BA%E8%B4%A1%E7%8C%AE%E5%BF%AB%E9%80%9F%E6%B5%81%E7%A8%8B)
- [分支与工作流](#%E5%88%86%E6%94%AF%E4%B8%8E%E5%B7%A5%E4%BD%9C%E6%B5%81)
- [提交信息规范](#%E6%8F%90%E4%BA%A4%E4%BF%A1%E6%81%AF%E8%A7%84%E8%8C%83)
- [测试与验证](#%E6%B5%8B%E8%AF%95%E4%B8%8E%E9%AA%8C%E8%AF%81)
- [常见问题排查](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98%E6%8E%92%E6%9F%A5)

## 快速贡献流程

1. **设置** - Clone + 安装

   ```bash
   git clone https://github.com/intellistream/SAGE.git && cd SAGE
   git checkout main-dev
   ./quickstart.sh --dev --yes
   ```

1. **分支** - 遵循命名规范

   ```bash
   git checkout -b <type>/<short-topic>
   # Examples: fix/ci-permissions, feat/streaming-support, docs/readme-update
   ```

1. **开发** - 编写代码

   ```bash
   # 保持同步
   git fetch origin && git rebase origin/main-dev
   ```

1. **测试** - 验证修改

   ```bash
   sage-dev project test --coverage    # 运行测试
   sage-dev quality fix .              # 修复代码质量
   ```

1. **提交** - 遵循规范化提交

   ```bash
   git commit -m "type(scope): summary"
   # Example: "fix(ci): avoid apt cache permission issue"
   ```

1. **推送和PR** - 创建Pull Request

   ```bash
   git push -u origin <branch>
   # 在 GitHub 上创建 PR，链接相关 Issue

   ```

## 提交信息规范

```
<type>(scope): summary

Examples:
  fix(ci): avoid apt cache permission issue
  feat(sage-kernel): add streaming operators
  docs(readme): update installation guide
```

**Type**: feat | fix | refactor | docs | test | ci | chore | security | ... **Scope** (optional):
Affected package/module

## 测试与验证

Run these before submitting a PR:

```bash
sage-dev project test --coverage       # Run core tests
sage-dev quality fix .                 # Fix code quality
```

## 常见问题排查

### 1. 分支落后于主分支

```bash
git fetch origin
git checkout <your-branch>
git rebase origin/main-dev
```

### 2. 提交信息写错了

```bash
# 修改最后一次（未推送）
git commit --amend

# 已推送慎用（需与协作者同步）
git push --force-with-lease
```

### 3. 想要撤销某些修改

```bash
# 撤销工作区修改
git restore <file>

# 撤销暂存区修改
git restore --staged <file>

# 回滚最近一次提交但保留修改
git reset --soft HEAD~1
```

### 4. 测试失败怎么办

```bash
pytest -vv --maxfail=1
tail -n 200 logs/install.log 2>/dev/null || true
bash -x quickstart.sh --core --yes  # 安装相关问题
```

### 5. CI构建失败

- 查看GitHub Actions日志
- 本地复现CI环境测试
- 检查文件权限问题
- 验证依赖是否正确安装
- 确认未使用过期脚本引用

### 6. 测试失败

查看失败案例：

```bash
sage-dev project test --coverage | tee /tmp/test.log
grep -i FAIL /tmp/test.log || true
```

### 7. 安装脚本卡住或没有输出

```
bash -x ./quickstart.sh --dev --yes
```

## GitHub Secrets 配置（维护者/贡献者）

______________________________________________________________________

感谢你的贡献！
