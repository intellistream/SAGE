# Package README 编写指南

**Date**: 2024-10-24  
**Author**: GitHub Copilot  
**Summary**: Package README 编写指南和质量检查工具使用说明

---

## 一、概述

本文档定义了 SAGE 项目中各包 README 的标准格式和质量要求。

## 二、README 模板

标准模板位于：`packages/sage-tools/src/sage/tools/templates/PACKAGE_README_TEMPLATE.md`

### 2.1 必需章节（Required Sections）

所有包的 README 必须包含以下章节：

1. **Title** (`# Package Name`)
   - 包名称（使用完整名称，如 "SAGE Kernel"）
   - 简短描述（一句话说明包的用途）

2. **Overview** (`## 📋 Overview`)
   - 包的详细介绍
   - 主要用途和应用场景
   - 与其他包的关系

3. **Installation** (`## 🚀 Installation`)
   - 基础安装方法
   - 开发安装方法
   - 可选依赖说明

4. **Quick Start** (`## 📖 Quick Start`)
   - 基础使用示例（代码块）
   - 常见用例
   - 最简配置

5. **License** (`## 📄 License`)
   - 许可证说明
   - 指向项目根目录的 LICENSE 文件

### 2.2 推荐章节（Recommended Sections）

建议包含以下章节以提高文档质量：

6. **Features** (`## ✨ Key Features`)
   - 核心功能列表
   - 每个功能的简短说明

7. **Package Structure** (`## 📦 Package Structure`)
   - 目录结构图
   - 主要模块说明

8. **Configuration** (`## 🔧 Configuration`)
   - 配置方法（环境变量、配置文件等）
   - 配置示例
   - 常用配置项说明

9. **Documentation** (`## 📚 Documentation`)
   - 用户指南链接
   - API 文档链接
   - 示例代码链接

10. **Testing** (`## 🧪 Testing`)
    - 如何运行测试
    - 测试覆盖率
    - 测试命令示例

11. **Contributing** (`## 🤝 Contributing`)
    - 指向 CONTRIBUTING.md
    - 简要贡献指南

### 2.3 可选章节（Optional Sections）

根据包的特点，可以添加：

- **Related Packages**: 相关包列表
- **Support**: 支持渠道（Issues, Discussions 等）
- **Architecture**: 架构说明（如果复杂）
- **Performance**: 性能说明（如果相关）
- **Migration Guide**: 迁移指南（主要版本升级时）

## 三、编写规范

### 3.1 标题规范

- **H1 标题** (`#`): 仅用于包名称，每个文件只有一个
- **H2 标题** (`##`): 用于主要章节
- **H3 标题** (`###`): 用于子章节
- **使用 emoji**: 推荐在 H2 标题前使用 emoji 图标，增强可读性

### 3.2 代码示例规范

```python
# ✅ 好的示例：完整、可运行
from sage.kernel import Function

@Function
def my_function(x: int) -> int:
    return x * 2

result = my_function(5)
print(result)  # 输出: 10
```

```python
# ❌ 不好的示例：不完整、不可运行
obj = SomeClass()  # 没有 import 语句
result = obj.process()  # 没有参数说明
```

### 3.3 链接规范

- **相对链接**: 使用相对路径链接项目内文件
  ```markdown
  [CONTRIBUTING.md](../../CONTRIBUTING.md)
  [LICENSE](../../LICENSE)
  ```

- **文档链接**: 使用完整 URL 链接到 docs-public
  ```markdown
  [User Guide](https://intellistream.github.io/SAGE-Pub/guides/packages/sage-kernel/)
  ```

### 3.4 徽章（Badges）规范

推荐添加以下徽章：

```markdown
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)
```

可选徽章：
- PyPI 版本（发布后）
- 测试状态
- 代码覆盖率
- 文档状态

## 四、质量检查工具

### 4.1 自动检查工具

位置：`sage-dev check-readme`

#### 使用方法

```bash
# 检查所有包
sage-dev check-readme --all

# 检查特定包
sage-dev check-readme --package sage-kernel

# 生成详细报告
sage-dev check-readme --all --report --output report.md
```

#### 评分标准

- **100-80 分** ✅: 优秀 - 包含所有必需和推荐章节
- **79-60 分** ⚠️: 良好 - 包含所有必需章节，缺少部分推荐章节
- **59-0 分** ❌: 需改进 - 缺少必需章节

评分计算：
- 必需章节：70% 权重
- 推荐章节：30% 权重

### 4.2 检查项目

工具会检查：

1. **章节完整性**
   - 所有必需章节是否存在
   - 推荐章节是否存在

2. **内容质量**
   - 是否包含代码示例
   - 是否有占位符文本（如 `{PACKAGE_NAME}`）
   - 是否有状态徽章

3. **格式规范**
   - 标题格式是否正确
   - Markdown 语法是否规范

### 4.3 当前状态

根据最新检查（2024-10-24）：

| 包名 | 分数 | 状态 | 主要问题 |
|------|------|------|----------|
| sage-tools | 90.0 | ✅ | 缺少 Overview 章节 |
| sage-libs | 90.0 | ✅ | 缺少部分必需章节 |
| sage-studio | 90.0 | ✅ | 缺少部分必需章节 |
| sage-apps | 90.0 | ✅ | 缺少 Quick Start |
| sage-platform | 71.0 | ⚠️ | 缺少 Quick Start |
| sage-common | 71.0 | ⚠️ | 缺少多个必需章节 |
| sage-kernel | 71.0 | ⚠️ | 缺少多个必需章节 |
| sage-middleware | 71.0 | ⚠️ | 缺少多个必需章节 |
| sage-benchmark | 57.0 | ❌ | 缺少 Overview 和 Quick Start |

**平均分数**: 77.9/100

## 五、改进流程

### 5.1 对于新包

1. 复制模板：
   ```bash
   cp packages/sage-tools/src/sage/tools/templates/PACKAGE_README_TEMPLATE.md packages/your-package/README.md
   ```

2. 替换占位符：
   - `{PACKAGE_NAME}`: 包的完整名称
   - `{BRIEF_DESCRIPTION}`: 简短描述
   - `{module_name}`: Python 模块名
   - 其他 `{...}` 占位符

3. 填写内容：
   - 按模板结构填写每个章节
   - 确保代码示例可运行
   - 添加真实的配置示例

4. 运行检查：
   ```bash
   sage-dev check-readme --package your-package
   ```

### 5.2 对于现有包

1. 运行检查工具识别问题：
   ```bash
   sage-dev check-readme --package sage-kernel
   ```

2. 根据报告逐项修复：
   - 添加缺失的必需章节
   - 补充推荐章节
   - 改进代码示例
   - 添加徽章

3. 重新检查确认改进：
   ```bash
   sage-dev check-readme --package sage-kernel
   ```

### 5.3 持续改进

- **定期检查**: 每次重大更新后运行检查
- **版本同步**: 功能变更时更新 README
- **用户反馈**: 根据用户问题改进文档
- **示例更新**: 保持代码示例与最新 API 一致

## 六、集成到 CI/CD

### 6.1 Pre-commit Hook

可以将 README 检查添加到 pre-commit hook：

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-package-readme
      name: Check Package README Quality
      entry: sage-dev check-readme --all
      language: system
      pass_filenames: false
```

### 6.2 GitHub Actions

在 CI workflow 中添加检查：

```yaml
# .github/workflows/ci.yml
- name: Check Package README Quality
  run: |
    sage-dev check-readme --all --report
```

## 七、最佳实践

### 7.1 写作建议

1. **简洁明了**: 每个章节直奔主题
2. **用户视角**: 从使用者角度编写
3. **实例优先**: 用代码示例说明
4. **循序渐进**: 从简单到复杂

### 7.2 常见问题

**Q: 为什么我的包需要 Overview 章节？**
A: Overview 帮助用户快速了解包的用途和价值，是文档的入口。

**Q: Quick Start 和 Installation 有什么区别？**
A: Installation 说明如何安装，Quick Start 展示如何使用。

**Q: 必须使用 emoji 吗？**
A: 不是必需的，但推荐使用，可以提高可读性。

**Q: 代码示例必须完整吗？**
A: 是的，所有代码示例应该可以直接复制运行。

## 八、参考资源

- **模板文件**: `packages/sage-tools/src/sage/tools/templates/PACKAGE_README_TEMPLATE.md`
- **检查工具**: `sage-dev check-readme`
- **质量报告**: `docs/dev-notes/ci-cd/PACKAGE_README_QUALITY_REPORT.md`
- **示例 README**: 查看 `sage-tools` 或 `sage-apps` 的 README

## 九、更新记录

- **2024-10-24**: 初始版本，添加模板和检查工具
- 当前平均质量分数: 77.9/100
- 目标: 所有包达到 80+ 分

---

**维护者**: SAGE Team  
**最后更新**: 2024-10-24  
**下次审查**: 2024-11-24 （每月审查一次）
