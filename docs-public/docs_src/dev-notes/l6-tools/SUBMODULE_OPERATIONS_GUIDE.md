# Submodule 运维与 CI 对齐指南

**Date**: 2025-11-25 \
**Author**: SAGE Development Team \
**Summary**: 合并记录近期针对 submodule 初始化、分支切换以及 VS Code 显示异常的所有改动，涵盖 quickstart、manage.sh 与 CI 的一致性方案。

______________________________________________________________________

## 1. 为什么需要新的流程？

- **开发体验**：`./quickstart.sh --dev --yes` 现在一条命令即可完成依赖安装、子模块同步和 Git hooks 安装，避免再手动执行 `manage.sh`。
- **分支一致性**：过去浅克隆导致子模块停在远程默认分支（通常是 `main`），从而引发导入错误或 CI 只拉取旧代码。
- **工具一致性**：VS Code 在浅克隆后会把缺少上游追踪的分支标记为 "Publish Branch"，虽然远程分支真实存在。

______________________________________________________________________

## 2. Quick Start vs. 高级安装

| 场景         | 推荐命令                                                                  | 子模块行为                         | 适用人群                 |
| ------------ | ------------------------------------------------------------------------- | ---------------------------------- | ------------------------ |
| 日常开发     | `./quickstart.sh --dev --yes`                                             | 自动 init + branch switch + hooks  | 绝大多数贡献者           |
| 精细控制     | `./manage.sh` → `./quickstart.sh --core/standard`                         | 先手动执行 `manage.sh submodule *` | 需要自定义依赖的高级用户 |
| CI / Offline | `./quickstart.sh --dev --yes --no-sync-submodules` → 自己调用 `manage.sh` | 完全由脚本控制                     | 离线或缓存环境           |

Quick Start 文档在 README 的 Advanced Installation 部分也包含了流程图、场景表和疑难排解：

- **第一次安装**：`./quickstart.sh --dev --yes`
- **更新已有安装**：`git pull && ./manage.sh submodule switch && ./manage.sh submodule update`
- **修复空目录 / detached HEAD**：`./manage.sh submodule status` + `./manage.sh submodule switch`

______________________________________________________________________

## 3. manage.sh / helpers 的核心改动

### 3.1 统一的分支切换

`tools/maintenance/sage-maintenance.sh` 默认调用：

```bash
git submodule sync --recursive
git submodule update --init --recursive --remote --jobs 4 --depth 1
```

- `--remote` 会尊重 `.gitmodules` 中声明的 `branch = main-dev`。
- 按子模块并行处理，仍保持浅克隆以缩短时间。

### 3.2 分支状态修复

`tools/maintenance/helpers/manage_submodule_branches.sh` 新增 `setup_upstream_tracking()`：

```bash
if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
  git config --add remote.origin.fetch \
    "+refs/heads/$branch:refs/remotes/origin/$branch"
  git fetch origin "$branch"
  git branch -u "origin/$branch" "$branch"
fi
```

- 自动补齐浅克隆缺失的 fetch refspec。
- 统一设置上游追踪，VS Code 不再显示 "Publish Branch"。

### 3.3 CI/CD 中的显式切换

`.github/workflows/pip-installation-test.yml` 在 `actions/checkout` 之后加入：

```yaml
- name: Switch Submodules to main-dev Branch
  run: |
    git submodule foreach --recursive '
      if git show-ref --verify --quiet refs/remotes/origin/main-dev; then
        git checkout main-dev
        git pull origin main-dev || true
      else
        echo "⚠️  $name 没有 main-dev 分支"
      fi
    '
```

- 适用于 `test-local-build` 与 `test-dependency-resolution` job，避免 CI 安装 `sage.data` 的旧版本。

______________________________________________________________________

## 4. VS Code "Publish Branch" 误报

### 4.1 触发原因

1. 浅克隆 (`--depth 1`) 没有抓取 `refs/remotes/origin/main-dev`。
1. 子模块切换到 `main-dev` 后缺少上游追踪。
1. VS Code 检测不到 `[origin/main-dev]`，误判为需要发布的新分支。

### 4.2 现阶段的自动修复

- 新版 `manage.sh submodule switch` 已自动设置 fetch refspec + upstream。
- 运行 `./manage.sh submodule status` 可以快速检查是否还有 detached HEAD 或缺失追踪的情况。

### 4.3 手动修复命令（无需自建脚本，仅供排查）

```bash
cd packages/sage-benchmark/src/sage/data

git config --add remote.origin.fetch '+refs/heads/main-dev:refs/remotes/origin/main-dev'
git fetch origin main-dev
git branch -u origin/main-dev main-dev
```

执行后，`git branch -vv` 应显示 `* main-dev <sha> [origin/main-dev] ...`，VS Code 会恢复正常。

______________________________________________________________________

## 5. 常见故障排查

| 现象                          | 排查命令                                   | 修复建议                                                            |
| ----------------------------- | ------------------------------------------ | ------------------------------------------------------------------- |
| 子模块目录为空                | `git submodule status`                     | `./manage.sh submodule update --remote`                             |
| HEAD Detached                 | `git status` within submodule              | `./manage.sh submodule switch`                                      |
| CI 仍报错找不到 `sage.data`   | 检查 workflow 日志中是否执行了 switch step | 确认 step 未被条件跳过；必要时手动复制脚本                          |
| VS Code 再次出现 Publish 提示 | `git branch -vv`                           | 重新运行 `./manage.sh submodule switch`; 若是新子模块，执行手动脚本 |

______________________________________________________________________

## 6. 下一步

- 将 `manage.sh submodule bootstrap` 的输出嵌入 quickstart，以便在安装完成后提示用户执行 `git submodule status`。
- 为离线环境提供 `submodules.tar.zst` 缓存包，进一步减少 `--remote` 拉取时间。
- 在 `sage-dev maintain submodule status` 中展示 fetch refspec 与 upstream，方便直接通过 CLI 发现异常。
