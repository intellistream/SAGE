**Date**: 2025-11-12
**Author**: shuhao
**Summary**: Fix for CI/CD submodule branch issues to ensure proper branch handling and error reporting during installation.

# 修复 CI/CD 子模块分支问题

## 问题描述

CI/CD 在安装 `sage-benchmark` 时失败：

```
[ERROR] 安装 sage-benchmark 失败
❌ 安装 sage-benchmark 失败！
```

但没有显示具体错误信息。

## 根本原因

### 问题 1: 子模块分支不匹配

虽然 `.gitmodules` 中配置了所有子模块使用 `main-dev` 分支：

```gitmodules
[submodule "packages/sage-benchmark/src/sage/data"]
    path = packages/sage-benchmark/src/sage/data
    url = https://github.com/intellistream/sageData.git
    branch = main-dev
```

但是 **GitHub Actions 的 `actions/checkout@v4` 在 checkout 子模块时，默认使用的是远程仓库的 HEAD 引用（通常是 `main` 分支）**，而不是 `.gitmodules` 中指定的分支！

### 问题 2: 代码不同步

- **main 分支**：sage.data 子模块有旧的导入错误（绝对导入）
- **main-dev 分支**：sage.data 子模块已修复导入问题（相对导入）- commit `6c1cd52`

CI 使用 `main` 分支的代码，导致：
1. ✅ sage-benchmark 包能安装
2. ❌ 但 sage.data 子模块中的代码有 Python 导入错误
3. ❌ 安装过程中可能在构建或验证阶段失败

## 解决方案

### 在 Checkout 后显式切换子模块分支

在 `.github/workflows/pip-installation-test.yml` 中，在 checkout 步骤之后添加：

```yaml
- name: Switch Submodules to main-dev Branch
  run: |
    echo "🔀 切换所有子模块到 main-dev 分支..."
    git submodule foreach --recursive '
      if git show-ref --verify --quiet refs/remotes/origin/main-dev; then
        echo "切换 $name 到 main-dev..."
        git checkout main-dev
        git pull origin main-dev || true
      else
        echo "⚠️  $name 没有 main-dev 分支，保持当前状态"
      fi
    '
    echo "✅ 子模块分支切换完成"
```

### 应用位置

需要在两个 job 中添加：
1. ✅ `test-local-build` - 测试本地构建安装
2. ✅ `test-dependency-resolution` - 测试从本地 wheels 安装

## 技术细节

### 为什么 actions/checkout@v4 不自动切换分支？

GitHub Actions 的 checkout action 行为：

1. **主仓库**:
   - 使用 `ref` 参数指定的分支（默认是触发 workflow 的分支）
   - Pull Request: 自动 checkout PR 的分支

2. **子模块**:
   - 使用 `submodules: 'recursive'` 会初始化和更新子模块
   - 但只是简单地 checkout 子模块当前记录的 commit SHA
   - **不会**自动切换到 `.gitmodules` 中指定的 `branch`
   - 需要手动 `git submodule update --remote` 或 `git checkout <branch>`

### `.gitmodules` 中的 `branch` 字段作用

```gitmodules
branch = main-dev
```

这个字段主要用于：
- `git submodule update --remote`: 更新子模块到指定分支的最新 commit
- 提示开发者该子模块应该使用哪个分支
- **但不会**自动在 checkout 时切换分支

### 我们的修复方案

```bash
git submodule foreach --recursive '...'
```

- `foreach`: 对每个子模块执行命令
- `--recursive`: 递归处理嵌套子模块
- `git show-ref --verify`: 检查分支是否存在
- `git checkout main-dev`: 切换到 main-dev 分支
- `git pull origin main-dev || true`: 拉取最新代码（失败不中断）

## 验证

### 预期结果

1. ✅ 所有子模块都切换到 `main-dev` 分支
2. ✅ sage.data 子模块使用修复后的相对导入代码
3. ✅ sage-benchmark 安装成功
4. ✅ 所有导入测试通过

### 测试方法

本地模拟 CI 环境：

```bash
# 1. 清理并重新 checkout
git submodule deinit -f .
git submodule update --init --recursive

# 2. 检查子模块分支（应该是 detached HEAD）
cd packages/sage-benchmark/src/sage/data
git branch
# * (HEAD detached at <commit>)

# 3. 执行我们的修复脚本
cd /home/zrc/develop_item/SAGE
git submodule foreach --recursive '
  if git show-ref --verify --quiet refs/remotes/origin/main-dev; then
    echo "切换 $name 到 main-dev..."
    git checkout main-dev
  fi
'

# 4. 再次检查（应该是 main-dev）
cd packages/sage-benchmark/src/sage/data
git branch
# * main-dev

# 5. 验证代码
cat __init__.py | grep "from \."
# 应该看到相对导入
```

## 相关 Issues

### 为什么之前没发现这个问题？

1. **本地开发**: 我们手动管理子模块，总是在 `main-dev` 分支
2. **CI 之前可能一直失败**: 但我们没有注意到详细的错误信息
3. **最近的修复**: 相对导入修复是最近才提交到 `main-dev` 的

### 其他可能受影响的 Workflow

检查其他使用子模块的 workflow，确保它们也正确切换分支：

```bash
grep -r "submodules.*recursive" .github/workflows/
```

如果有其他 workflow 使用子模块，也需要添加相同的分支切换步骤。

## 最佳实践

### 推荐的子模块管理方式

1. **在 `.gitmodules` 中明确指定分支**:
   ```gitmodules
   branch = main-dev
   ```

2. **在 CI/CD 中显式切换分支**:
   ```yaml
   - name: Checkout with submodules
     uses: actions/checkout@v4
     with:
       submodules: 'recursive'

   - name: Switch submodules to correct branch
     run: git submodule foreach --recursive 'git checkout main-dev'
   ```

3. **本地开发提醒**:
   ```bash
   # 在 README 中提醒开发者
   git submodule update --init --recursive
   git submodule foreach --recursive 'git checkout main-dev'
   ```

4. **使用 Git hooks**:
   创建 `.git/hooks/post-checkout` 自动切换子模块分支

## 后续行动

- [x] 修复 CI/CD workflow
- [ ] 更新开发者文档，说明子模块管理
- [ ] 考虑添加 pre-commit hook 检查子模块分支
- [ ] 检查其他 workflows 是否有同样问题

## 文件修改

- `.github/workflows/pip-installation-test.yml`:
  - 在 `test-local-build` job 中添加子模块分支切换
  - 在 `test-dependency-resolution` job 中添加子模块分支切换

## Commit

```bash
git add .github/workflows/pip-installation-test.yml
git commit -m "fix(ci): 在 CI/CD 中显式切换子模块到 main-dev 分支

问题: sage-benchmark 安装失败，因为 sage.data 子模块使用的是 main 分支的旧代码

原因: actions/checkout@v4 不会自动切换到 .gitmodules 中指定的分支

解决: 在 checkout 后显式执行 git submodule foreach 切换分支

影响:
- test-local-build job
- test-dependency-resolution job"
```
