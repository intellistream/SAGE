# GitHub Actions Workflows

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

- 提交信息包含 `[skip ci]` 时不会触发
- 只修改文档 (`.md`、`docs/`、`examples/`) 时不会触发

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

所有包都会按依赖顺序发布:

1. `isage-common` - 公共基础库
1. `isage-kernel` - 核心引擎
1. `isage-libs` - 工具库
1. `isage-middleware` - 中间件组件
1. `isage-platform` - 平台服务
1. `isage-cli` - 命令行工具
1. `isage-apps` - 应用示例
1. `isage-benchmark` - 基准测试
1. `isage-studio` - 可视化工具
1. `isage-tools` - 开发工具
1. `isage` - 元包（安装所有子包）

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

# GitHub Actions Workflows

## Publish to PyPI Workflow

自动构建和发布 SAGE 包到 PyPI 或 TestPyPI。

### 🤖 自动触发

Workflow 会在以下情况**自动运行**：

#### 📝 Push 到 `main-dev` 分支

- **版本**: 自动 `patch + 1` (例如: 0.1.6.2 → 0.1.6.3)
- **目标**: TestPyPI
- **用途**: 开发测试版本

#### 🚀 Push 到 `main` 分支

- **版本**: 自动 `minor + 1` (例如: 0.1.6.2 → 0.1.7.0)
- **目标**: PyPI (生产环境)
- **附加**: 自动创建 GitHub Release

**注意**:

- 提交信息包含 `[skip ci]` 时不会触发
- 只修改文档 (`.md`、`docs/`、`examples/`) 时不会触发

### 🛠️ 手动触发（可选）

如需手动控制，可以通过以下方式触发：

1. **GitHub UI**:

   - 进入 Actions 标签页
   - 选择 "Publish to PyPI" workflow
   - 点击 "Run workflow"
   - 选择参数:
     - **repository**: `testpypi` 或 `pypi`
     - **version_bump**: `auto`/`patch`/`minor`/`major`/`none`

1. **GitHub CLI**:

   ```bash
   # 手动测试发布
   gh workflow run publish-pypi.yml \
     -f repository=testpypi \
     -f version_bump=patch

   # 手动生产发布（不推荐，建议通过 PR 到 main）
   gh workflow run publish-pypi.yml \
     -f repository=pypi \
     -f version_bump=minor
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

所有包都会按依赖顺序发布:

1. `isage-common` - 公共基础库
1. `isage-kernel` - 核心引擎
1. `isage-libs` - 工具库
1. `isage-middleware` - 中间件组件
1. `isage-platform` - 平台服务
1. `isage-cli` - 命令行工具
1. `isage-apps` - 应用示例
1. `isage-benchmark` - 基准测试
1. `isage-studio` - 可视化工具
1. `isage-tools` - 开发工具
1. `isage` - 元包（安装所有子包）

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

- `main-dev` push → `PATCH + 1`
- `main` push → `MINOR + 1, PATCH = 0`

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
