# SAGE 包文档位置审计与整理

**日期**: 2026-01-02\
**问题**: packages 下发现多个违规 Markdown 文件\
**原因**: Pre-commit hook 的正则表达式过于宽泛

______________________________________________________________________

## 🔍 问题发现

### 违规文件清单

发现 **4 个违规文件**，分布在 **2 个包**中：

#### 1. packages/sage-libs/ (3 个)

- ❌ `AMMS_PYPI_PUBLISH_GUIDE.md` - PyPI 发布指南
- ❌ `LIBAMM_INSTALLATION.md` - LibAMM 安装文档
- ❌ `README_LIBAMM.md` - LibAMM 专用 README

#### 2. packages/sage-middleware/ (1 个)

- ❌ `MIGRATION_SCIKIT_BUILD.md` - scikit-build-core 迁移记录

### 其他包检查结果 ✅

所有其他包都符合规范：

- ✅ sage-apps, sage-benchmark, sage-cli
- ✅ sage-common, sage-edge, sage-kernel
- ✅ sage-llm-core, sage-llm-gateway
- ✅ sage-platform, sage-studio, sage-tools
- ✅ sage (meta-package)

______________________________________________________________________

## 🛠️ 修复措施

### 1. 修复 Pre-commit Hook

**文件**: `tools/hooks/check_docs_location.sh`

**修改前** (第 40-51 行，过于宽泛):

```bash
allowed_patterns=(
    ...
    "^packages/.*/README\.md$"      # 允许任何位置的 README
    "^packages/.*README.*\.md$"     # 允许任何 README 变体
    "^packages/.*\.md$"             # ❌ 允许任何 MD 文件！
    ...
)
```

**修改后** (严格限制):

```bash
allowed_patterns=(
    ...
    "^packages/[^/]+/README\.md$"              # 只允许顶层 README
    "^packages/[^/]+/CHANGELOG\.md$"           # 只允许顶层 CHANGELOG
    "^packages/[^/]+/(docs|documentation)/"    # 包 docs 目录
    "^packages/[^/]+/src/.*/docs/"             # 子模块 docs 目录
    ...
)
```

### 2. 文档整理方案

创建自动化脚本: `tools/scripts/reorganize_package_docs.sh`

#### sage-libs 文档整理

```bash
# 包级文档 (与包紧密相关)
git mv packages/sage-libs/LIBAMM_INSTALLATION.md packages/sage-libs/docs/
git mv packages/sage-libs/README_LIBAMM.md packages/sage-libs/docs/LIBAMM.md

# 项目级开发者文档 (跨包关注)
git mv packages/sage-libs/AMMS_PYPI_PUBLISH_GUIDE.md \
       docs-public/docs_src/dev-notes/l3-libs/pypi-publish-guide.md
```

#### sage-middleware 文档整理

```bash
# 创建 docs 目录并移动迁移记录
mkdir -p packages/sage-middleware/docs
git mv packages/sage-middleware/MIGRATION_SCIKIT_BUILD.md \
       packages/sage-middleware/docs/
```

______________________________________________________________________

## 📐 文档位置策略

### ✅ 包根目录 (packages/<package>/)

**只允许**:

- `README.md` - 包简介和快速开始
- `CHANGELOG.md` - 版本历史

### ✅ 包文档目录 (packages/<package>/docs/)

**适用于**:

- 包特定的安装/配置指南
- 包特定的 API 文档
- 包特定的架构设计文档
- 包特定的迁移/变更记录

### ✅ 子模块文档 (packages/<package>/src/.../submodule/docs/)

**适用于**:

- 子模块（sageLLM, sageFlow, sageDB 等）的独立文档
- 保持子模块的独立性

### ✅ 项目级文档 (docs-public/docs_src/dev-notes/)

**适用于**:

- 跨包的开发者指南
- 项目级的发布流程（如 PyPI 发布）
- 项目级的架构决策
- 跨包的最佳实践

______________________________________________________________________

## 🎯 整理后的目录结构

```
packages/
  sage-libs/
    README.md                    ✅ 包简介
    docs/
      LIBAMM.md                  ✅ LibAMM 详细文档
      LIBAMM_INSTALLATION.md     ✅ 安装指南
      LIBAMM_DATA_QUICKSTART.md  ✅ 已存在

  sage-middleware/
    README.md                    ✅ 包简介
    docs/
      MIGRATION_SCIKIT_BUILD.md  ✅ 迁移记录

docs-public/docs_src/dev-notes/
  l3-libs/
    pypi-publish-guide.md        ✅ PyPI 发布流程（项目级）
```

______________________________________________________________________

## 📋 执行步骤

### 1. 自动整理文档

```bash
./tools/scripts/reorganize_package_docs.sh
```

### 2. 检查并更新文档链接

```bash
# 搜索所有引用
grep -r 'AMMS_PYPI_PUBLISH_GUIDE' --include='*.md' --include='*.py' .
grep -r 'LIBAMM_INSTALLATION' --include='*.md' --include='*.py' .
grep -r 'README_LIBAMM' --include='*.md' --include='*.py' .
grep -r 'MIGRATION_SCIKIT_BUILD' --include='*.md' --include='*.py' .

# 更新 packages/sage-libs/README.md 中的相对链接
# 例如: ./LIBAMM_INSTALLATION.md → ./docs/LIBAMM_INSTALLATION.md
```

### 3. 验证 Pre-commit Hook

```bash
pre-commit run markdown-files-location-check --all-files
```

### 4. 提交变更

```bash
git status
git add -A

git commit -m 'docs: reorganize package documentation to follow location policy

- Move sage-libs docs to proper locations
  • LIBAMM_INSTALLATION.md → docs/
  • README_LIBAMM.md → docs/LIBAMM.md
  • AMMS_PYPI_PUBLISH_GUIDE.md → docs-public/docs_src/dev-notes/l3-libs/

- Move sage-middleware docs to proper location
  • MIGRATION_SCIKIT_BUILD.md → docs/

- Fix pre-commit hook patterns to be stricter
  • Only allow README.md and CHANGELOG.md in package root
  • Enforce docs/ directory for other documentation

- Update documentation location check script
  • Prevent future violations

Ref: Documentation Location Policy (.github/copilot-instructions.md)'
```

______________________________________________________________________

## 🔒 防止未来违规

### Pre-commit Hook 现在会阻止:

- ❌ 包根目录下除 `README.md` 和 `CHANGELOG.md` 外的任何 `.md` 文件
- ❌ 根 `docs/` 目录下的任何文件（必须使用 `docs-public/`）
- ❌ 不符合允许模式的任何文档

### 开发者需要知道:

1. 包特定文档 → `packages/<package>/docs/`
1. 项目级文档 → `docs-public/docs_src/`
1. 包简介 → `packages/<package>/README.md`
1. 子模块文档 → `packages/<package>/src/.../submodule/docs/`

______________________________________________________________________

## 📊 影响范围

- **修改的文件**: 5 (4 个文档 + 1 个 hook 脚本)
- **影响的包**: 2 (sage-libs, sage-middleware)
- **新增的文档目录**: 1 (packages/sage-middleware/docs/)
- **破坏性变更**: 文档路径变化，需要更新引用

______________________________________________________________________

## ✅ 验证清单

- [x] 识别所有违规文件 (4 个)
- [x] 修复 pre-commit hook 正则表达式
- [x] 创建自动化整理脚本
- [x] 生成完整的审计报告
- [ ] 执行文档整理脚本
- [ ] 更新文档内部链接
- [ ] 验证 pre-commit hook
- [ ] 提交变更

______________________________________________________________________

## 📚 相关文档

- **Documentation Policy**: `docs-public/docs_src/dev-notes/cross-layer/documentation-policy.md`
- **Copilot Instructions**: `.github/copilot-instructions.md` (Documentation Location Policy
  section)
- **Pre-commit Config**: `tools/pre-commit-config.yaml`
