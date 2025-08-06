# SAGE 文档管理指南

本文档介绍 SAGE 项目的文档组织结构和管理流程。

## 📁 文档架构

SAGE 采用分层文档架构，对应项目的三层技术栈：

```
📁 文档架构
├── 🏗️ Kernel (核心层)
│   ├── DataStream API - 流处理核心API
│   ├── Environments API - 执行环境管理
│   ├── Functions API - 自定义函数接口
│   ├── Connected Streams API - 多流处理
│   ├── 架构设计 - 系统设计文档
│   ├── 最佳实践 - 性能优化指南
│   └── CLI 工具 - 命令行工具文档
├── 🔧 Middleware (中间件层)
│   ├── Service API - 中间件服务接口
│   ├── Memory Service - 内存服务
│   ├── KV Service - 键值存储服务
│   └── VDB Service - 向量数据库服务
└── 🚀 Applications (应用层)
    ├── RAG 应用 - 检索增强生成
    ├── Agents - 智能代理
    ├── Tools - 工具生态
    ├── IO 组件 - 输入输出接口
    └── Context 管理 - 上下文管理
```

## 📂 目录结构

### 内部文档 (开发文档)
```
packages/
├── sage-kernel/docs/          # Kernel层文档
├── sage-middleware/docs/      # Middleware层文档 (待创建)
└── sage-tools/docs/          # Tools层文档 (待创建)
```

### 公开文档 (用户文档)
```
docs-public/                   # SAGE-Pub submodule
└── docs_src/
    ├── kernel/               # Kernel文档 (同步自sage-kernel/docs)
    ├── middleware/           # Middleware文档 (同步自sage-middleware/docs)
    └── applications/         # Applications文档 (重组自原sage_lib)
```

## 🔄 文档同步流程

### 1. 自动同步

使用同步脚本自动将内部文档同步到公开文档：

```bash
# 执行文档同步
./tools/sync_docs.sh
```

脚本功能：
- 自动检测文档更改
- 同步内部文档到公开仓库
- 提供交互式提交和推送选项
- 生成自动化提交信息

### 2. 手动同步

如需手动同步特定文档：

```bash
# 同步 Kernel 文档
rsync -av packages/sage-kernel/docs/ docs-public/docs_src/kernel/

# 同步 Middleware 文档
rsync -av packages/sage-middleware/docs/ docs-public/docs_src/middleware/

# 提交更改
cd docs-public
git add -A
git commit -m "docs: 手动同步文档更新"
git push origin main
```

## ✏️ 文档编写规范

### Kernel 层文档
- **位置**: `packages/sage-kernel/docs/`
- **内容**: 核心API、架构设计、开发指南
- **风格**: 技术性强，面向开发者
- **语言**: 中英文并重，API文档以英文为主

### Middleware 层文档
- **位置**: `packages/sage-middleware/docs/`
- **内容**: 服务接口、配置指南、集成示例
- **风格**: 实用性强，面向系统集成
- **语言**: 中文为主，配置示例以代码为主

### Applications 层文档
- **位置**: 直接在 `docs-public/docs_src/applications/`
- **内容**: 应用场景、使用示例、最佳实践
- **风格**: 易懂性强，面向最终用户
- **语言**: 中文为主，突出实用性

### 文档格式规范

1. **Markdown 格式**: 所有文档使用 Markdown 格式
2. **标题层次**: 使用 `#` 到 `####` 的标题层次
3. **代码示例**: 使用代码块，并指定语言类型
4. **链接引用**: 使用相对路径，确保链接有效性
5. **图片资源**: 统一放在 `docs-public/docs_src/assets/` 目录

### 示例文档模板

```markdown
# 组件名称

简要描述组件的功能和用途。

## 🏗️ 架构概览

描述组件在整体架构中的位置和作用。

## 🚀 快速开始

### 基础用法

\`\`\`python
# 简单示例代码
from sage.component import Component

component = Component()
result = component.execute()
\`\`\`

### 高级用法

更复杂的使用场景和配置。

## 📚 API 参考

详细的API文档，包括：
- 类和方法签名
- 参数说明
- 返回值描述
- 异常处理

## 🔧 配置选项

支持的配置参数和默认值。

## 📖 最佳实践

使用建议和性能优化技巧。

## 🤔 常见问题

用户常遇到的问题和解决方案。
```

## 🚀 发布流程

### 1. 本地构建测试

```bash
cd docs-public
mkdocs serve  # 本地预览
mkdocs build  # 构建检查
```

### 2. 提交到公开仓库

```bash
# 使用同步脚本
./tools/sync_docs.sh

# 或手动提交
cd docs-public
git add -A
git commit -m "docs: 更新文档内容"
git push origin main
```

### 3. 自动部署

推送到 `main` 分支后，GitHub Actions 会自动：
- 构建 MkDocs 文档
- 部署到 GitHub Pages
- 更新 https://intellistream.github.io/SAGE-Pub/

## 🔗 相关链接

- [公开文档网站](https://intellistream.github.io/SAGE-Pub/)
- [文档源码仓库](https://github.com/intellistream/SAGE-Pub)
- [MkDocs 官方文档](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

## 🛠️ 维护指南

### 定期任务

1. **每周检查**: 检查文档链接有效性
2. **版本发布时**: 同步更新所有相关文档
3. **功能更新时**: 及时更新API文档和示例

### 故障排除

1. **构建失败**: 检查 MkDocs 配置和文件路径
2. **链接错误**: 使用相对路径并验证文件存在
3. **同步问题**: 检查 rsync 命令和权限设置

### 贡献指南

1. **内部开发者**: 在对应的 `packages/*/docs/` 目录编写文档
2. **外部贡献者**: 直接在 `docs-public` 仓库提交 PR
3. **文档审核**: 确保内容准确性和格式一致性

---

通过这套文档管理流程，我们能够：
- 保持内部开发文档和公开用户文档的同步
- 确保文档的组织结构清晰合理
- 提供高质量的用户体验
- 支持协作开发和社区贡献
