# SAGE GitHub Actions 工作流文档

本目录包含 SAGE 项目的所有 GitHub Actions 工作流配置。这些工作流负责持续集成、构建发布、代码质量检查和分支管理。

## 📋 工作流概览

| 工作流名称 | 文件名 | 触发条件 | 主要功能 | 状态 |
|-----------|--------|----------|----------|------|
| **SAGE CI/CD** | `ci.yml` | `main-dev`, `refactor/*`, PR to `main` | 测试和验证 | ✅ 活跃 |
| **Build and Release** | `build-release.yml` | `main`, `main-dev`, `v*` tags | 构建和发布 | ✅ 活跃 |
| **Branch Protection** | `only-main-dev.yml` | PR to `main` | 分支保护 | ✅ 活跃 |
| **TODO to Issue** | `todo-to-issue-pr.yml` | PR 事件 | 自动化管理 | ✅ 活跃 |

## 🔄 工作流详细说明

### 1. SAGE CI/CD (`ci.yml`)

**目的：** 验证代码质量和功能完整性

**触发条件：**
- 推送到 `main-dev` 分支
- 推送到 `refactor/*` 分支
- 创建到 `main` 分支的 Pull Request
- 手动触发

**主要任务：**
- **测试任务 (`test`)**: 
  - 使用开发模式安装 SAGE (`pip install -e`)
  - 运行 pytest 测试套件
  - 测试各种 AI 服务集成
  - 超时时间：60分钟

- **Docker 集成测试提醒 (`docker-integration-reminder`)**:
  - 运行在 self-hosted runner
  - 提醒进行 C++ 扩展的 Docker 测试
  - 检查 `sage_db`, `sage_queue` 等组件

- **代码质量检查 (`lint`)**:
  - 运行在 self-hosted runner
  - 代码风格和类型检查
  - 超时时间：15分钟

**特点：**
- 专注于**开发环境验证**
- 不构建生产环境包
- 包含完整的测试覆盖

### 2. Build and Release (`build-release.yml`)

**目的：** 构建生产环境包并发布

**触发条件：**
- 推送到 `main` 分支（稳定版）
- 推送到 `main-dev` 分支（开发版）
- 推送 `v*` 标签（正式发布）
- 发布 GitHub Release

**构建流程：**

#### 阶段 1: 子包构建 (`build-subpackages`)
- **并行构建 4 个子包：**
  - `sage-common` → `isage-common-*.whl`
  - `sage-kernel` → `isage-kernel-*.whl`
  - `sage-middleware` → `isage-middleware-*.whl`
  - `sage-libs` → `isage-libs-*.whl`
- **策略：** Matrix 并行执行
- **输出：** 各子包的 wheel 文件

#### 阶段 2: Meta 包构建 (`build-metapackage`)
- **依赖：** 等待所有子包构建完成
- **特殊处理：** 发布时替换本地依赖为 PyPI 包名
  ```bash
  # 开发时: "isage-common @ file:./packages/sage-common"
  # 发布时: "isage-common"
  ```
- **输出：** 主包 `isage-*.whl`

#### 阶段 3: 基本测试 (`test`)
- **多版本测试：** Python 3.10, 3.11, 3.12
- **验证内容：** wheel 包安装和基本导入
- **策略：** 快速验证，不运行完整测试套件

#### 阶段 4: 发布 (`release`)
- **条件：** 仅在 `v*` 标签时执行
- **GitHub Release：** 自动创建 release 并上传所有 wheel 文件
- **PyPI 发布：** 如果配置了 `PYPI_API_TOKEN`

#### 阶段 5: 清理 (`cleanup`)
- **执行：** 无论其他任务成功失败都执行
- **功能：** 删除超过 30 天的 artifacts

**依赖关系流程：**
```
build-subpackages (并行执行)
        ↓
build-metapackage (等待所有子包)
        ↓
     test (验证)
        ↓
    release (仅标签)
        ↓
    cleanup (总是执行)
```

**特点：**
- 专注于**生产环境打包**
- 支持多包依赖管理
- 自动化发布流程

### 3. Branch Protection (`only-main-dev.yml`)

**目的：** 维护分支管理规范

**触发条件：**
- 创建到 `main` 分支的 Pull Request

**功能：**
- 检查 PR 源分支必须是 `main-dev`
- 阻止其他分支直接合并到 `main`
- 确保代码审查流程

**分支策略：**
```
feature/* → main-dev → main
   ↓           ↓        ↓
  开发      集成测试   稳定版
```

### 4. TODO to Issue (`todo-to-issue-pr.yml`)

**目的：** 自动化项目管理

**触发条件：**
- Pull Request 事件 (opened, synchronize, reopened)
- 手动触发

**功能：**
- 扫描代码中的 TODO 注释
- 自动创建 GitHub Issues
- 在代码中插入 Issue URL
- 提交更改回 PR 分支

## 🔧 工作流配置说明

### 环境变量和密钥

**CI/CD 相关：**
- `HF_TOKEN`: HuggingFace API Token
- `SILICONCLOUD_API_KEY`: 硅云 API 密钥
- `OPENAI_API_KEY`: OpenAI API 密钥
- `JINA_API_KEY`: Jina AI API 密钥
- `ALIBABA_API_KEY`: 阿里云 API 密钥
- `VLLM_API_KEY`: vLLM API 密钥

**发布相关：**
- `PYPI_API_TOKEN`: PyPI 发布令牌 (可选)
- `GITHUB_TOKEN`: GitHub API 访问令牌 (自动提供)

### Runner 配置

- **ubuntu-latest**: 用于大部分构建和测试任务
- **self-hosted**: 用于需要特殊环境的任务
  - Docker 集成测试
  - 代码质量检查

## 🚀 使用指南

### 开发工作流

1. **功能开发：**
   ```bash
   git checkout -b feature/new-feature
   # 开发代码...
   git push origin feature/new-feature
   # 创建 PR 到 main-dev
   ```

2. **集成测试：**
   ```bash
   git checkout main-dev
   git merge feature/new-feature
   git push origin main-dev
   # 触发 CI/CD 和 Build workflows
   ```

3. **稳定发布：**
   ```bash
   git checkout main
   git merge main-dev
   git tag v1.2.3
   git push origin main --tags
   # 触发正式发布流程
   ```

### 发布流程

**开发版本发布：**
- 推送到 `main-dev` → 自动构建开发版本
- 可在 Actions Artifacts 中下载

**正式版本发布：**
1. 创建并推送版本标签
2. 自动触发完整构建流程
3. 创建 GitHub Release
4. 发布到 PyPI (如果配置)

## 📊 工作流状态监控

### 检查工作流状态
```bash
# 查看最近的运行状态
gh run list --limit 10

# 查看特定工作流
gh run list --workflow="SAGE CI/CD"
gh run list --workflow="Build and Release"

# 查看运行详情
gh run view <run-id>
```

### 常见问题排查

**1. 子包构建失败：**
- 检查 `packages/*/pyproject.toml` 配置
- 确认依赖关系正确
- 检查 Python 版本兼容性

**2. Meta 包构建被阻塞：**
- 检查所有子包是否构建成功
- `build-metapackage` 依赖 `build-subpackages` 完成

**3. PyPI 发布失败：**
- 确认 `PYPI_API_TOKEN` 配置正确
- 检查包名是否冲突
- 验证版本号格式

**4. 测试超时：**
- CI 测试超时限制：60分钟
- 考虑拆分大型测试或优化测试速度

## 🔄 工作流优化建议

### 当前重复问题
- `ci.yml` 和 `build-release.yml` 在 `main-dev` 分支都会触发
- 可以考虑：
  - CI 专注于 `main-dev` 和 PR
  - Build 专注于 `main` 和 tags

### 性能优化
- 使用 Docker layer caching
- 优化依赖安装速度
- 并行化更多任务

### 安全性
- 定期轮换 API tokens
- 使用最小权限原则
- 启用依赖安全扫描

---

*最后更新：2025年9月2日*
*维护者：SAGE Team*

**触发条件**:
- Pull Request 事件 (opened, synchronize, reopened)
- 手动触发

**功能**:
- 扫描代码中的 TODO 注释
- 自动创建对应的 GitHub Issues
- 在代码中插入 Issue URL 链接
- 提交更改回 PR 分支

## ⚠️ 重要注意事项

### 工作流重复问题
当推送到 `main-dev` 分支时，会同时触发：
- ✅ `ci.yml` (测试验证)
- ✅ `build-release.yml` (构建包)

这是**有意设计**的：
- `ci.yml` 专注测试，快速反馈
- `build-release.yml` 专注构建，准备发布

### Meta 包构建延迟
`build-metapackage` 任务必须等待所有子包构建完成，所以：
- 如果任何一个子包构建失败/较慢，meta 包会被阻塞
- 这是正常的设计，确保 meta 包依赖完整

### 发布条件
- **开发构建**: 推送到 `main-dev` → 构建但不发布
- **正式发布**: 推送 `v*` 标签 → 构建并发布到 PyPI/GitHub

## 🚀 使用建议

### 开发流程
1. 在 `refactor/feature-name` 分支开发
2. 合并到 `main-dev` → 触发 CI + 构建
3. 创建 PR `main-dev → main` → 触发分支保护 + CI
4. 合并到 `main` → 准备发布
5. 打标签 `v1.0.0` → 自动发布

### 故障排查
- **CI 失败**: 检查 `ci.yml` 的测试任务
- **构建失败**: 检查 `build-release.yml` 的构建任务
- **Meta 包未构建**: 确认所有子包都构建成功
- **发布失败**: 检查 PyPI API Token 配置

## 📝 配置要求

### 必需的 Secrets
- `GITHUB_TOKEN`: GitHub API 访问 (自动提供)
- `PYPI_API_TOKEN`: PyPI 发布 (可选，发布时需要)
- 各种 AI 服务 API Keys (测试用):
  - `HF_TOKEN`, `OPENAI_API_KEY`, `JINA_API_KEY` 等

### 运行器要求
- `ubuntu-latest`: 大部分任务
- `self-hosted`: Docker 集成测试和代码质量检查

---

*最后更新: 2025-09-02*
