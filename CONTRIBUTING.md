

> 本地代码质量/测试请使用 `sage-dev quality` 或 `sage-dev test`，CI/CD 由 GitHub Workflows 自动完成。

# SAGE 贡献指南

> 本文档帮助你高效、规范地向 SAGE 贡献代码与文档。请在提交 Pull Request 前完整阅读。若英文协作者需要，可参考文末的 English Quick Guide。

## 📚 开发者资源 / Developer Resources

开始贡献前，请查看以下资源：

- **[DEVELOPER.md](DEVELOPER.md)** - 完整开发指南，包含设置、工作流、测试等
- **[CHANGELOG.md](CHANGELOG.md)** - 项目变更日志（遵循 Keep a Changelog 格式）
- **[tools/dev.sh](tools/dev.sh)** - 开发助手脚本，提供常用命令
- **[tools/pre-commit-config.yaml](tools/pre-commit-config.yaml)** - Pre-commit 钩子配置
- **[docs/images/architecture.svg](docs/images/architecture.svg)** - 系统架构图
- **[docs/dev-notes/](docs/dev-notes/)** - 开发笔记和修复总结

**快速开始开发**:

```bash
# 一键设置开发环境
./tools/dev.sh setup

# 格式化代码
./tools/dev.sh format

# 运行所有检查
./tools/dev.sh validate
```

## 目录

- [新人贡献快速流程](#%E6%96%B0%E4%BA%BA%E8%B4%A1%E7%8C%AE%E5%BF%AB%E9%80%9F%E6%B5%81%E7%A8%8B)
- [分支与工作流](#%E5%88%86%E6%94%AF%E4%B8%8E%E5%B7%A5%E4%BD%9C%E6%B5%81)
- [提交信息规范](#%E6%8F%90%E4%BA%A4%E4%BF%A1%E6%81%AF%E8%A7%84%E8%8C%83)
- [测试与验证](#%E6%B5%8B%E8%AF%95%E4%B8%8E%E9%AA%8C%E8%AF%81)
- [代码与文档质量](#%E4%BB%A3%E7%A0%81%E4%B8%8E%E6%96%87%E6%A1%A3%E8%B4%A8%E9%87%8F)
- [命令与脚本说明](#%E5%91%BD%E4%BB%A4%E4%B8%8E%E8%84%9A%E6%9C%AC%E8%AF%B4%E6%98%8E)
- [常见问题排查](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98%E6%8E%92%E6%9F%A5)
- [安全与披露](#%E5%AE%89%E5%85%A8%E4%B8%8E%E6%8A%AB%E9%9C%B2)
- [最佳实践建议](#%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5%E5%BB%BA%E8%AE%AE)
- [English Quick Guide](#english-quick-guide)

## 新人贡献快速流程

### 第一步：获取代码与环境

```bash
# 克隆仓库（若已 fork，请替换为你的 fork 地址）
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 切换主开发分支并更新
git fetch origin
git checkout main-dev
git pull --ff-only origin main-dev

# 初始化 submodules（会自动切换到正确的分支）
./tools/maintenance/sage-maintenance.sh submodule init

# 安装开发环境 (默认 dev 模式 + conda)
./quickstart.sh --dev --yes

# 或最小安装（仅核心包）
./quickstart.sh --minimal --yes

# 标准模式 + 安装 VLLM 支持
./quickstart.sh --standard --vllm --yes
```

**重要提示：**

- ✅ 使用 `./tools/maintenance/sage-maintenance.sh submodule init` 初始化 submodules
- ❌ 不要使用 `git submodule update --init`（会导致 detached HEAD）

### 第二步：创建功能分支（勿在 main-dev 直接开发）

```bash
# 基础格式
# <type>/<short-topic>
# 推荐类型(type): feat / fix / refactor / docs / test / style / perf / ci / chore / build / deps / revert / security

# 示例
git checkout -b fix/ci-cache-permissions
git checkout -b feat/vllm-integration
git checkout -b refactor/jobmanager-architecture
```

### 第三步：开发与同步主分支

```bash
# 查看修改
git status
git diff

# 开发过程中保持同步（避免大冲突）
git fetch origin
git rebase origin/main-dev   # 有冲突时解决后: git add <files> && git rebase --continue

# 或使用 merge（团队更偏好 REBASE 的话请遵守该策略）
# git merge origin/main-dev
```

### 第四步：本地测试与验证

```bash
# 运行核心安装验证（若修改安装逻辑）
./quickstart.sh --minimal --yes

# 运行示例/集成测试集合（当前推荐方式）
bash tools/tests/run_examples_tests.sh

# 运行全部 pytest （如需要更广覆盖）
pytest -vv

# 只运行与 issues manager 相关测试
pytest -k issues_manager -vv

# 语法与基础静态检查（建议）
python -m py_compile path/to/modified.py
bash -n path/to/script.sh

# 可选：若已安装 black / mypy（dev 模式会安装）
black --check .
mypy packages/sage-kernel || true
```

### 第五步：提交代码（使用规范化提交信息）

```bash
# 暂存
git add <files>

# 快速单行提交（首行必须 <type>(scope?): summary 英文，≤72 字符）
git commit -m "fix(ci): avoid apt cache permission issue in CI"

# 多段描述提交（推荐，使用多个 -m 或进入编辑器）
git commit -m "fix(ci): avoid apt cache permission issue" \
           -m "原因: GitHub Actions 缓存目录权限不足导致 post job 失败\n做法: 移除 /var/cache/apt 缓存依赖, 采用用户缓存目录, 减少 apt 输出\n影响: CI 更稳定, 安装时间略下降"

# 修改最后一次提交（尚未推送）
git commit --amend
```

### 第六步：推送分支

```bash
git push -u origin <branch-name>
```

### 第七步：创建 Pull Request

PR 描述建议模板：

```
### 变更类型
feat | fix | refactor | docs | test | perf | ci | chore | build | deps | security

### 问题背景
（关联的 Issue 链接 / 现象说明）

### 解决方案
（核心实现要点 / 设计取舍）

### 测试与验证
- [ ] quickstart 最小安装通过
- [ ] examples 测试脚本通过
- [ ] pytest 核心用例通过

### 影响范围
（受影响的包 / 模块 / 部署方式）

### 其它备注
（向 Reviewer 提示审阅重点）
```

> PR 必须通过 CI；建议至少 1 名维护者 Review 才可合并（团队策略可调整）。

## 分支与工作流

### 主要分支说明

- `main-dev`: 主开发分支（默认基线）
- `main`: 稳定发布（仅合并已验证发布）
- `feature/<epic-name>`: 大型特性聚合分支（需要时建立）

### 分支命名规范

```
feat/<topic>           新功能
fix/<issue-or-bug>     缺陷修复
refactor/<area>        重构
docs/<topic>           文档
test/<topic>           测试

perf/<area>            性能
ci/<area>              CI/CD
chore/<misc>           杂项维护
build/<target>         构建系统
security/<issue>       安全修复
revert/<hash-fragment> 回滚
```

> 不建议使用过长分支名；保持 3-5 个词以内。

### 避免子模块指针冲突

本仓库目前包含多个 Git submodule（如
`docs-public`、`packages/sage-middleware/src/sage/middleware/components/sage_db`、`packages/sage-middleware/src/sage/middleware/components/sage_flow`、`packages/sage-common/src/sage/common/components/sage_vllm/sageLLM`
等）。当多人并行修改这些子仓库时，请遵循以下通用流程，降低 submodule 指针冲突概率：

1. **先合并子仓库 PR**：针对某个子仓库的变更，务必先让它在对应的子仓库仓库内合并到 upstream，不要在主仓库引用未合并的 commit。
1. **同步主仓库指针**：在 SAGE 仓库根目录执行 `git submodule update --remote <submodule-path>`（或使用
   `./tools/maintenance/manage_submodule_branches.sh switch`）获取最新 commit，随后
   `git add <submodule-path>` 更新指针。
1. **提交主仓库 PR**：提交、推送包含最新子模块指针的 PR，并在描述中清楚标注对应子仓库的改动链接。

协作注意事项：

- 对同一子模块，尽量只保留一个主仓库分支负责更新指针，其他分支在需要时先 rebase/merge 最新的主仓库分支。
- 若多个分支已指向不同 commit，合并冲突时选择最新的子仓库 commit，执行 `git add <submodule-path> && git commit` 重新提交即可。
- Reviewer 审核时推荐顺序：**先合并子仓库 PR** → **再合并主仓库同步指针的 PR**。涉及多个子模块时，可逐个对子仓库执行以上流程。

## 提交信息规范

### 基本格式

```
<type>(scope): summary

<body 可选，多段换行>
<footer 可选，如 Closes #123 / BREAKING CHANGE>
```

### 类型说明

- feat / fix / refactor / docs / test / style / perf / ci / chore / build / deps / revert / security

### 范围说明

范围(scope) 建议与实际包/模块对应：

```
sage-common | sage-kernel | sage-libs | sage-middleware | sage-tools | quickstart | docs | tests | ci | infra
```

允许复合：`feat(sage-kernel,quickstart): ...`

### 提交信息示例

#### 修复问题

```
fix(ci): avoid apt permission error in GitHub Actions

Cause: post-job cache save failed due to /var/cache/apt permissions
Change: remove global apt cache reuse; use $HOME/.cache/pip and ephemeral /tmp/apt-cache
Impact: CI stable, slight speed improvement
Closes: #123
```

#### 新功能

```
feat(quickstart): add optional VLLM installation flag

Add --vllm flag to quickstart; auto-verifies vllm after install.
Docs updated.
```

#### 测试修复

```
fix(tests): stabilize example + issues integration tests

Replace legacy shell script with python-based IssuesTestSuite.
Reduce flakiness via timeout + category filtering.
```

## 测试与验证

### 必跑测试清单

1. **语法检查**

   ```bash
   bash -n path/to/script.sh
   python -m py_compile path/to/module.py
   ```

1. **功能测试**

   ```bash
   ./quickstart.sh --minimal --yes             # 安装/环境相关改动
   bash tools/tests/run_examples_tests.sh      # 示例 + 基础集成
   pytest -k issues_manager -vv                # Issues 管理相关
   ```

1. **集成测试**

   ```bash
   ./quickstart.sh --dev --yes
   python -c "import sage; print(sage.__version__)"
   ```

1. **可选强化**

   ```bash
   pytest -m quick_examples        # 标记的快速示例
   pytest --maxfail=1 --durations=10
   black --check . && isort --check-only . || true
   mypy packages/sage-kernel || true
   ```

## 代码与文档质量

### Shell脚本

- 使用`set -e`
- 添加必要的注释
- 使用函数封装逻辑
- 处理边界情况和错误
- 避免无提示的 `rm -rf`；必要时加交互/显式目录
- 可选：通过 `shellcheck` 静态分析

### Python代码

- 遵循PEP 8规范
- 添加类型注解
- 编写单元测试
- 添加适当的文档字符串
- 避免循环内重复 I/O；优先使用批量操作
- 日志使用 `logging` 而非 print（测试内部除外）

### 通用要求

- 代码可读性强
- 添加必要注释
- 处理异常情况
- 避免硬编码
- 新增/变更公共API需同步更新文档或示例

## 命令与脚本说明

| 目的           | 推荐命令                                           | 说明                       |
| -------------- | -------------------------------------------------- | -------------------------- |
| 安装（交互式） | `./quickstart.sh`                                  | 未传参进入菜单             |
| 最小安装       | `./quickstart.sh --minimal --yes`                  | 仅核心包                   |
| 开发者安装     | `./quickstart.sh --dev --yes`                      | 安装开发依赖（可编辑模式） |
| 启用 VLLM      | `./quickstart.sh --standard --vllm --yes`          | 额外安装 vllm              |
| 示例测试       | `bash tools/tests/run_examples_tests.sh`           | 运行示例/集成集            |
| 单个测试       | `pytest -k <keyword>`                              | 关键字过滤                 |
| Issues 测试    | `pytest -k issues_manager -vv`                     | Python 化测试              |
| 版本查看       | `python -c "import sage; print(sage.__version__)"` | 确认安装                   |

> 任何命令失败，请附上一行重现命令与终端输出前 50 行发至 Issue。

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
bash -x quickstart.sh --minimal --yes  # 安装相关问题
```

### 5. CI构建失败

- 查看GitHub Actions日志
- 本地复现CI环境测试
- 检查文件权限问题
- 验证依赖是否正确安装
- 确认未使用过期脚本引用

### 6. 示例测试脚本退出码 1

查看失败案例：

```
bash tools/tests/run_examples_tests.sh | tee /tmp/examples.log
grep -i FAIL /tmp/examples.log || true
```

### 7. 安装脚本卡住或没有输出

```
bash -x ./quickstart.sh --dev --yes
```

## GitHub Secrets 配置（维护者/贡献者）

### 🚀 为什么需要配置 Secrets？

为了让 CI/CD 正常工作，仓库需要配置以下 GitHub Secrets。如果你是：

- **仓库维护者**：需要在主仓库配置 Secrets
- **外部贡献者**：在你的 fork 中配置 Secrets 以运行 CI（可选）

### 最小必需配置

使用 GitHub CLI（推荐）：

```bash
gh secret set OPENAI_API_KEY -b "your-openai-or-dashscope-key"
gh secret set HF_TOKEN -b "your-huggingface-token"
```

### 完整配置（可选）

```bash
# LLM 服务
gh secret set OPENAI_API_KEY -b "sk-xxx..."
gh secret set ALIBABA_API_KEY -b "sk-xxx..."
gh secret set SILICONCLOUD_API_KEY -b "your-key"

# 其他服务
gh secret set JINA_API_KEY -b "your-key"
gh secret set WEB_SEARCH_API_KEY -b "your-key"

# vLLM 本地服务（如果不需要认证可以留空）
gh secret set VLLM_API_KEY -b "token-abc123"

# Hugging Face
gh secret set HF_TOKEN -b "hf_xxx..."
```

### 通过 Web 界面设置

1. 访问：`https://github.com/YOUR_USERNAME/SAGE/settings/secrets/actions`
1. 点击 `New repository secret`
1. 添加以下 secrets：

| Name                 | Value                                 | Required |
| -------------------- | ------------------------------------- | -------- |
| `OPENAI_API_KEY`     | 你的 OpenAI/DashScope API key         | ✅ 是    |
| `HF_TOKEN`           | 你的 Hugging Face token               | ✅ 是    |
| `ALIBABA_API_KEY`    | 阿里云 API key                        | ⭕ 可选  |
| `VLLM_API_KEY`       | vLLM 服务 token（默认: token-abc123） | ⭕ 可选  |
| `WEB_SEARCH_API_KEY` | Web 搜索服务 key                      | ⭕ 可选  |

### 验证配置

配置完成后，触发一次 CI 运行来验证：

```bash
git commit --allow-empty -m "test: trigger CI to verify secrets"
git push
```

查看 CI 日志，应该能看到：

```
✅ .env 文件创建完成
📋 验证 .env 文件内容（隐藏敏感信息）:
OPENAI_API_KEY=***
HF_TOKEN=***
...
```

### 外部贡献者注意事项

外部贡献者的 PR 默认无法访问主仓库的 Secrets（这是 GitHub 的安全特性）。你可以：

1. **在自己的 fork 中配置 Secrets**（推荐用于测试）
1. **使用 mock 模式测试**（大多数测试支持）：
   ```bash
   SAGE_TEST_MODE=true pytest
   ```
1. **等待维护者审核后触发 CI**（维护者可手动触发带 Secrets 的 CI）

### ⚠️ 安全注意事项

1. **不要**在 Pull Request 评论或 Issue 中粘贴真实的 API keys
1. 定期轮换 API keys（建议每 90 天一次）
1. 使用专用的 CI/CD API keys，与生产环境分离
1. 确认 Secret 名称区分大小写

## 安全与披露

若发现安全问题（例如：任意代码执行 / 信息泄露 / 供应链风险），请不要直接公开 Issue，可通过以下方式私下披露：

- 邮件：security@intellistream.cn （示例；若需调整请维护者更新）
- 标题建议：`[SECURITY] <简要描述>`

请包含：影响版本、复现步骤、预期 vs 实际、安全影响评估。我们将在确认后尽快回应并在修复后发布公告。

## 最佳实践建议

- 提交粒度：功能完成或逻辑自洽即可，不要把无关修改混在同一次提交。
- 避免大型 PR：>800 行差异建议拆分；文档、重构、逻辑变更最好分开。
- 使用英文提交首行：方便国际贡献者理解；正文可中英混合。
- 对复杂逻辑添加架构注释或在 PR 描述添加“设计要点”。
- 遇到不确定的实现路径：先建 Issue / Draft PR 讨论。

## English Quick Guide

```
1. Clone & install: ./quickstart.sh --dev --yes
2. Create branch: git checkout -b feat/<topic>
3. Keep updated: git fetch && git rebase origin/main-dev
4. Test: bash tools/tests/run_examples_tests.sh && pytest -vv
5. Commit: feat(sage-kernel): add xyz
6. Push & PR: include background / solution / tests / impact
```

Commit format: `<type>(scope): summary` with optional multi-line body. Supported types: feat, fix,
refactor, docs, test, style, perf, ci, chore, build, deps, revert, security.

______________________________________________________________________

记住：优秀的贡献不仅是“跑通”，还要让后来者易于维护与扩展。感谢你的贡献！🚀
