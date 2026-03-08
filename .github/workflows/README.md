# GitHub Actions Workflows

## Workflow Overview

| Workflow | 用途 | 触发条件 | 必须通过 |
|----------|------|----------|---------|
| `ci-build-test.yml` | 构建、测试、覆盖率 | PR, push | ✅ |
| `ci-sagellm-test.yml` | SageLLM mock/CUDA 测试 | PR, push | ✅ (mock) |
| `ci-code-quality.yml` | 代码质量检查 | PR, push | ✅ |
| `cd-publish-pypi.yml` | 发布到 PyPI | main/main-dev push | - |
| `util-branch-protection.yml` | PR 分支保护 | PR to main | ✅ |

---

## SageLLM Test Workflow

**文件**: `ci-sagellm-test.yml`

专门测试 SageLLM 推理引擎的 mock 和 CUDA 后端。

### Job 1: SageLLM Mock Backend (必须通过)

所有 PR 必须通过此测试，验证：
- SageLLM mock backend 正常工作
- `SageLLMGenerator` 与 mock backend 集成
- Agentic operators (Planning, Timing, ToolSelection) 与 mock backend 兼容

```yaml
# 测试命令
pytest -v -k "sagellm or mock or SageLLM or Mock" packages/
```

### Job 2: SageLLM CUDA Backend (可选)

GPU 测试，仅在以下情况运行：
- 手动触发 workflow 并选择 `run_cuda_tests: true`
- Push 到 `main` 分支

**要求**: Self-hosted runner with `[self-hosted, gpu, cuda]` labels

### 手动触发 CUDA 测试

```bash
# 使用 GitHub CLI
gh workflow run ci-sagellm-test.yml \
  -f run_cuda_tests=true

# 或在 GitHub UI:
# Actions → SageLLM Mock & CUDA Tests → Run workflow → ✅ Run CUDA tests
```

### Branch Protection 要求

在 Repository Settings → Branches → Branch protection rules 中，添加：

- **Required status checks**: `SageLLM Mock Backend`
- 这确保所有 PR 必须通过 sagellm mock 测试

---

## Publish to PyPI Workflow

自动构建和发布 SAGE 包到 PyPI 或 TestPyPI。

### 🤖 自动触发

Workflow 会在以下情况**自动运行**：

#### 📝 Push 到 `main-dev` 分支

- **版本**: 自动 `patch + 1` (例如: 0.1.6.2 → 0.1.6.3)
- **目标**: TestPyPI
- **用途**: 开发测试版本

#### 🚀 Push 到 `main` 分支

- **版本**: 自动 `micro + 1` (例如: 0.1.6.2 → 0.1.7.0)
- **目标**: PyPI (生产环境)
- **附加**: 自动创建 GitHub Release

**注意**:

- 提交信息包含 `[version bump]` 标记时不会触发（防止版本升级后的循环触发）
- 只修改文档 (`.md`、`docs/`、`examples/`) 时不会触发
- 版本升级的提交会触发其他 CI workflows (如 Build & Test)，以更新 README badges

### 🛠️ 手动触发（可选）

如需手动控制，可以通过以下方式触发：

1. **GitHub UI**:

   - 进入 Actions 标签页
   - 选择 "Publish to PyPI" workflow
   - 点击 "Run workflow"
   - 选择参数:
     - **repository**: `testpypi` 或 `pypi`
     - **version_bump**: `auto`/`patch`/`micro`/`minor`/`major`/`none`

1. **GitHub CLI**:

   ```bash
   # 手动测试发布
   gh workflow run publish-pypi.yml \
     -f repository=testpypi \
     -f version_bump=patch

   # 手动生产发布（不推荐，建议通过 PR 到 main）
   gh workflow run publish-pypi.yml \
     -f repository=pypi \
     -f version_bump=micro
   ```

### 配置要求

#### Secrets 设置

在 GitHub 仓库设置中添加以下 secrets:

1. **TEST_PYPI_API_TOKEN**: TestPyPI API token

   - 访问 https://test.pypi.org/manage/account/token/
   - 创建新 token
   - 权限: "Upload packages"
   - 将 token 添加到 GitHub Secrets

1. **PYPI_API_TOKEN**: PyPI API token

   - 访问 https://pypi.org/manage/account/token/
   - 创建新 token
   - 权限: "Upload packages"
   - 将 token 添加到 GitHub Secrets

#### Environment 设置（可选）

为生产发布添加保护:

1. 在 Settings → Environments 创建 `pypi-publishing` environment
1. 添加保护规则:
   - Required reviewers: 需要人工审批
   - Wait timer: 延迟发布时间
   - Deployment branches: 限制可发布的分支

### Workflow 流程

1. **检出代码**: 获取最新代码
1. **设置 Python 环境**: Python 3.11
1. **安装依赖**: twine, build, sage-tools
1. **升级版本** (如果选择了 version_bump):
   - 计算新版本号
   - 更新所有包的版本
   - 提交版本更改
1. **构建和发布**:
   - 按依赖顺序编译所有 11 个包
   - 生成 wheel 文件
   - 上传到指定仓库
1. **创建 GitHub Release** (仅生产发布):
   - 创建 git tag
   - 生成 release notes
   - 包含安装说明

### 发布的包

所有核心包都会按依赖顺序发布:

1. `isage-common` - 公共基础库 (L1)
1. `isage-kernel` - 核心运行时 (L2)
1. `isage-cli` - 命令行工具 (L3)
1. `isage` - 元包（安装所有子包）

**独立仓库发布** (不在 SAGE 核心仓库):
- `isagellm` - LLM 推理引擎 (sageLLM 仓库)
- `isage-benchmark` - 基准测试 (sage-benchmark 仓库)
- `isage-studio` - 可视化工具 (L4，sage-studio 仓库)
- `isage-edge` - 边缘聚合器 (sage-edge 仓库)

### 版本策略

版本号格式: `MAJOR.MINOR.MICRO.PATCH`

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 新增向后兼容的功能
- **MICRO**: Bug 修复和小改进
- **PATCH**: 紧急修复 (自动增量)

### 推荐工作流程

#### 开发和测试

```bash
# 1. 在 main-dev 分支开发
git checkout main-dev
# ... 开发工作 ...
git add .
git commit -m "feat: 新功能"
git push origin main-dev

# ✅ 自动触发：
#    - 版本: 0.1.6.2 → 0.1.6.3
#    - 发布到 TestPyPI
#    - 可以测试安装验证
```

#### 测试安装

```bash
# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  isage

# 验证功能
python -c "import sage; print(sage.__version__)"
```

#### 发布到生产

```bash
# 2. 确认测试通过后，合并到 main
git checkout main
git merge main-dev
git push origin main

# ✅ 自动触发：
#    - 版本: 0.1.6.3 → 0.1.7.0
#    - 发布到 PyPI
#    - 创建 GitHub Release v0.1.7.0
```

### 版本策略

版本号格式: `MAJOR.MINOR.MICRO.PATCH`

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 新增向后兼容的功能
- **MICRO**: Bug 修复和小改进
- **PATCH**: 紧急修复 (在 main-dev 自动增量)

**自动规则**:

- `main-dev` push → `PATCH + 1` (例如: 0.1.6.2 → 0.1.6.3)
- `main` push → `MICRO + 1, PATCH = 0` (例如: 0.1.6.2 → 0.1.7.0)

### 故障排除

**401 Unauthorized**:

- 检查 API token 是否正确配置
- 验证 token 权限是否包含 "Upload packages"

**400 Bad Request**:

- 版本号已存在，需要 bump version
- 检查 pyproject.toml 配置是否有误

**403 Forbidden**:

- 检查包名是否已被其他用户占用
- 验证账户是否有上传权限

**网络错误 (SSL/Timeout)**:

- GitHub Actions 网络问题，重新运行 workflow
- 可能是 PyPI 服务临时不可用

### 手动发布

如需手动发布（不推荐）:

```bash
# 升级版本
sage-dev package version set 0.1.6.3

# 发布到 TestPyPI
sage-dev package pypi publish-sage --no-dry-run -r testpypi

# 发布到 PyPI
sage-dev package pypi publish-sage --no-dry-run -r pypi
```

## Sync main to main-dev Workflow

自动将 main 分支的更改同步回 main-dev 分支，确保开发分支始终包含生产环境的最新更改。

### 🔄 工作原理

当代码合并到 `main` 分支时：

1. **main-dev → main** (通过 PR)

   - 开发版本: 0.1.7.8
   - 合并后 main 版本: 0.1.7.8

1. **main 自动 bump version**

   - Publish workflow 自动运行
   - 版本升级: 0.1.7.8 → 0.1.8.0
   - 提交到 main: `chore: bump version to 0.1.8.0 [version bump]`

1. **自动同步 main → main-dev**

   - Sync workflow 自动运行
   - 将 main 的版本更新合并回 main-dev
   - main-dev 版本同步到: 0.1.8.0

### ✅ 好处

- 🔄 **自动化**: 无需手动同步分支
- 📊 **版本一致**: main-dev 始终包含 main 的版本号
- 🚀 **减少冲突**: 及时同步减少后续合并冲突
- 🔧 **透明化**: 同步操作在 GitHub Actions 中可见

### ⚙️ 触发条件

- **自动触发**: 任何推送到 `main` 分支
- **跳过条件**: 从 main-dev 合并到 main 的 PR（避免循环）

### 🔍 查看同步状态

在 GitHub Actions 中查看 "Sync main to main-dev" workflow 的运行状态。

### ⚠️ 冲突处理

如果自动合并失败（罕见情况），workflow 会提示手动解决：

```bash
git checkout main-dev
git pull origin main
# 解决冲突（如果有）
git push origin main-dev
```

### 💡 最佳实践

1. **日常开发**: 在 `main-dev` 分支进行
1. **稳定发布**: 定期通过 PR 将 `main-dev` 合并到 `main`
1. **自动同步**: 让 workflow 自动处理版本同步
1. **冲突最小化**: 频繁小批量合并，而不是大批量积累

### 📋 完整工作流程

```bash
# 1. 在 main-dev 开发
git checkout main-dev
git pull
# ... 开发工作 ...
git commit -m "feat: new feature"
git push origin main-dev
# ✅ 自动发布到 TestPyPI (0.1.8.0 → 0.1.8.1)

# 2. 创建 PR 到 main
gh pr create --base main --head main-dev

# 3. 合并 PR
# ✅ main 接收更改 (版本 0.1.8.1)
# ✅ 自动 bump version (0.1.8.1 → 0.1.9.0)
# ✅ 自动同步回 main-dev (main-dev 也变成 0.1.9.0)

# 4. 继续在 main-dev 开发
# main-dev 现在是 0.1.9.0，与 main 同步
```
