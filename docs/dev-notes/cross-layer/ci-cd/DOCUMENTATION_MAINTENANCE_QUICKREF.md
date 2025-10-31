# 文档维护快速参考

**Date**: 2024-10-24  
**Author**: GitHub Copilot  
**Summary**: 文档维护快速参考 - 常用命令和工作流程

---

## 🚀 快速命令

### 检查文档质量

```bash
# 方式1: 使用 Makefile（推荐）
make docs-check          # 快速检查
make docs-report         # 详细报告

# 方式2: 直接使用工具
sage-dev check-devnotes --all
sage-dev check-readme --all

# 方式3: 使用维护脚本
bash tools/maintenance/check_docs.sh
```

### 生成质量报告

```bash
# 生成 dev-notes 检查报告
sage-dev check-devnotes --all --strict

# 生成 Package README 质量报告
sage-dev check-readme --all --report --output report.md

# 生成完整文档质量报告
make docs-report
```

### 检查特定包

```bash
# 检查单个包的 README
sage-dev check-readme --package sage-kernel

# 检查已修改的 dev-notes
sage-dev check-devnotes --changed-only
```

## 📝 文档编写工作流

### 1. 创建新的 dev-notes 文档

```bash
# 1. 复制模板
cp docs/dev-notes/TEMPLATE.md docs/dev-notes/<category>/<your-doc>.md

# 2. 填写元数据
# 编辑文件，确保包含：
#   **Date**: YYYY-MM-DD
#   **Author**: Your Name
#   **Summary**: Brief description

# 3. 选择正确的分类目录
# 允许的分类: architecture, kernel, middleware, libs, apps,
#             ci-cd, performance, security, testing, deployment,
#             migration, tools, archive

# 4. 检查格式
sage-dev check-devnotes --changed-only

# 5. 提交（pre-commit 会自动检查）
git add docs/dev-notes/<category>/<your-doc>.md
git commit -m "docs: Add <description>"
```

### 2. 创建新包的 README

```bash
# 1. 复制模板
cp packages/sage-tools/src/sage/tools/templates/PACKAGE_README_TEMPLATE.md packages/<your-package>/README.md

# 2. 替换占位符
# 在编辑器中替换所有 {PLACEHOLDER} 文本:
#   {PACKAGE_NAME} → 包的完整名称
#   {BRIEF_DESCRIPTION} → 简短描述
#   {module_name} → Python 模块名
#   {DOC_LINK} → 文档链接

# 3. 填写必需章节
#   - Overview
#   - Key Features
#   - Installation
#   - Quick Start
#   - License

# 4. 检查质量
sage-dev check-readme --package <your-package>

# 5. 提交
git add packages/<your-package>/README.md
git commit -m "docs: Add README for <your-package>"
```

### 3. 改进现有 README

```bash
# 1. 检查当前状态
sage-dev check-readme --package <package-name>

# 2. 查看缺少的章节
# 工具会列出所有缺失的必需和推荐章节

# 3. 参考模板添加缺失章节
# 参考: packages/sage-tools/src/sage/tools/templates/PACKAGE_README_TEMPLATE.md

# 4. 重新检查
sage-dev check-readme --package <package-name>

# 5. 确认改进
# 目标: 至少 80 分，最好 100 分
```

## 🎯 质量标准

### Dev-notes 文档

**必需**:
- ✅ 放在正确的分类目录下
- ✅ 包含元数据（Date, Author, Summary）
- ✅ 日期格式正确（YYYY-MM-DD）

**推荐**:
- 📝 使用清晰的标题结构
- 📝 包含代码示例
- 📝 添加相关链接（Related字段）

### Package README

**必需章节** (70%权重):
- ✅ Title (包名称)
- ✅ Overview (概述)
- ✅ Installation (安装)
- ✅ Quick Start (快速开始)
- ✅ License (许可证)

**推荐章节** (30%权重):
- 📝 Key Features
- 📝 Package Structure
- 📝 Configuration
- 📝 Documentation
- 📝 Testing
- 📝 Contributing

**评分标准**:
- 100-80分: ✅ 优秀
- 79-60分: ⚠️ 良好
- 59-0分: ❌ 需改进

## 🔧 常见问题

### Q1: Pre-commit 检查失败怎么办？

```bash
# 查看具体错误
git commit -v

# 常见问题:
# 1. Dev-notes 缺少元数据
#    → 在文档开头添加 **Date**, **Author**, **Summary**

# 2. Dev-notes 在根目录
#    → 移动到正确的分类目录

# 3. 日期格式错误
#    → 使用 YYYY-MM-DD 格式

# 如果确实需要跳过检查（谨慎使用）:
git commit --no-verify -m "message"
```

### Q2: README 检查显示"缺少章节"但实际存在？

```bash
# 可能是格式问题，检查:
# 1. 标题必须是 ## 开头
# 2. 章节名称要匹配（可以带 emoji）
# 3. 示例:
#    ✅ ## 📋 Overview
#    ✅ ## Overview
#    ❌ # Overview (H1 不行)
#    ❌ ### Overview (H3 不行)
```

### Q3: 如何提高 README 分数？

```bash
# 1. 检查缺少什么
sage-dev check-readme --package <pkg> --report

# 2. 优先添加必需章节（70%权重）
#    - Overview, Installation, Quick Start, License

# 3. 再添加推荐章节（30%权重）
#    - Key Features, Package Structure, Configuration

# 4. 添加代码示例和徽章
#    - 每个章节最好有实际的代码示例
#    - 添加 Python version 和 License 徽章
```

### Q4: 如何批量检查文档？

```bash
# 检查所有包
make docs-check

# 生成完整报告
make docs-report

# 只检查已修改的文档
sage-dev check-devnotes --changed-only

# 检查与特定提交的差异
sage-dev check-devnotes --changed-only --diff HEAD~5
```

## 📊 当前状态 (2024-10-24)

### Package README 质量

| 分数段 | 数量 | 状态 |
|--------|------|------|
| 100分  | 6个  | ✅ 优秀 |
| 90分   | 3个  | ✅ 优秀 |
| 平均   | 98.9 | 🏆 卓越 |

**详细分数**:
- sage-platform: 100.0
- sage-common: 100.0
- sage-kernel: 100.0
- sage-middleware: 100.0
- sage-tools: 100.0
- sage-libs: 100.0
- sage-studio: 100.0
- sage-apps: 100.0
- sage-benchmark: 90.0

### Dev-notes 文档

- 总数: ~70+ 个文档
- 分类: 13 个允许的目录
- 元数据要求: Date, Author, Summary

## 🔗 相关资源

### 工具

- `sage-dev check-devnotes` - Dev-notes 规范检查
- `sage-dev check-readme` - README 质量检查
- `tools/devnotes_organizer.py` - 文档整理助手
- `tools/maintenance/check_docs.sh` - 完整检查脚本

### 模板

- `docs/dev-notes/TEMPLATE.md` - Dev-notes 模板
- `packages/sage-tools/src/sage/tools/templates/PACKAGE_README_TEMPLATE.md` - README 模板

### 文档

- `docs/dev-notes/ci-cd/PACKAGE_README_GUIDELINES.md` - README 编写指南
- `docs/dev-notes/ci-cd/DOCUMENTATION_CHECK_REPORT.md` - 文档检查报告
- `README.md` - 项目主 README

### CI/CD

- `.github/workflows/documentation-check.yml` - 文档质量检查 workflow
- `tools/git-hooks/pre-commit` - Pre-commit hook（含文档检查）

## 💡 最佳实践

1. **写文档时**:
   - 先查看模板
   - 参考现有优秀文档
   - 包含可运行的代码示例
   - 添加清晰的标题结构

2. **提交前**:
   - 运行 `make docs-check`
   - 修复所有错误
   - 确保 README 至少 80 分

3. **定期维护**:
   - 每月运行 `make docs-report`
   - 更新过时的文档
   - 改进低分 README
   - 清理 TODO 标记

4. **协作时**:
   - PR 中包含文档更新
   - 功能变更同步更新文档
   - Review 时检查文档质量

## 🎓 学习资源

### 优秀示例

- **Package README**:
  - `packages/sage-platform/README.md` (100分)
  - `packages/sage-common/README.md` (100分)
  - `packages/sage-benchmark/README.md` (90分)

- **Dev-notes**:
  - `docs/dev-notes/ci-cd/PACKAGE_README_GUIDELINES.md`
  - `docs/dev-notes/architecture/DATA_TYPES_ARCHITECTURE.md`

### 外部参考

- [Best README Template](https://github.com/othneildrew/Best-README-Template)
- [Markdown Guide](https://www.markdownguide.org/)
- [Documentation Best Practices](https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/)

---

**维护者**: SAGE Team  
**最后更新**: 2024-10-24  
**下次审查**: 每月第一周
