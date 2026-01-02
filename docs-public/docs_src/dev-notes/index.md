# 开发者笔记

经过提炼的技术总结和开发经验，帮助开发者更好地理解和贡献 SAGE。

## 📚 本章内容

开发者笔记提供了从开发者视角出发的技术总结和最佳实践，这些内容经过提炼和整理，具有长期参考价值。

### [包架构](package-architecture.md)

完整的包架构文档，包含：

- 📦 **10 个包的详细说明** - 每个包的职责、模块、测试状态
- 🔗 **依赖关系管理** - 允许和禁止的依赖模式
- 📋 **架构审查状态** - L1-L6 各层的审查成果
- 🔄 **重构历史** - 架构演进的重要里程碑
- 💡 **最佳实践** - 包开发的指导原则

**适合人群**：贡献者、架构师、想要深入了解代码组织的开发者

👉 [查看包架构文档](package-architecture.md)

______________________________________________________________________

## 📂 分层开发笔记

| 层级 | 目录                                     | 说明               |
| ---- | ---------------------------------------- | ------------------ |
| L1   | [l1-common](l1-common/README.md)         | 基础设施、共享组件 |
| L2   | [l2-platform](l2-platform/README.md)     | 平台服务、部署     |
| L3   | [l3-kernel](l3-kernel/README.md)         | 核心引擎           |
| L3   | [l3-libs](l3-libs/README.md)             | 算法库             |
| L4   | [l4-middleware](l4-middleware/README.md) | 中间件、C++ 扩展   |
| L5   | [l5-apps](l5-apps/README.md)             | 应用示例           |
| L5   | [l5-benchmark](l5-benchmark/README.md)   | 评测框架           |
| L6   | [l6-cli](l6-cli/README.md)               | 命令行工具         |
| L6   | [l6-gateway](l6-gateway/README.md)       | API 网关           |
| L6   | [l6-studio](l6-studio/README.md)         | 可视化工作室       |
| L6   | [l6-tools](l6-tools/README.md)           | 开发者工具         |

## 🔧 专题笔记

- [交叉层设计 (Cross-Layer)](cross-layer/README.md)
- [测试策略 (Testing)](testing/README.md)
- [研究工作 (Research)](research_work/README.md)
- [归档 (Archive)](archive/README.md)

______________________________________________________________________

## 🎯 与其他文档的关系

### 核心概念 vs 开发笔记

| 文档类型 | [核心概念](../concepts/index.md) | 开发笔记           |
| -------- | -------------------------------- | ------------------ |
| **视角** | 用户和架构师视角                 | 开发者和贡献者视角 |
| **内容** | 架构设计理念和原则               | 实现细节和开发经验 |
| **目标** | 理解为什么这样设计               | 理解如何开发和贡献 |
| **更新** | 稳定的架构文档                   | 随开发演进更新     |

### 推荐阅读路径

**如果你想...**

- **理解 SAGE 的设计理念** → 先读 [核心概念](../concepts/index.md)
- **开始贡献代码** → 先读 [包架构](package-architecture.md)
- **了解某个包的用法** → 查看 [用户指南](../guides/index.md)
- **查看 API 细节** → 查看 [API 参考](../api-reference/index.md)

______________________________________________________________________

## 💡 开发者最佳实践

### 添加新功能时

1. **确定合适的层级**

   - 基础工具 → sage-common (L1)
   - 平台服务 → sage-platform (L2)
   - 核心引擎/算法 → sage-kernel/sage-libs (L3)
   - 领域服务 → sage-middleware (L4)
   - 应用 → sage-apps (L5)
   - 工具/界面 → sage-cli/sage-studio/sage-tools (L6)

1. **检查依赖规则**

   - ✅ 只依赖更低层的包
   - ❌ 禁止向上依赖
   - ❌ 禁止跨层依赖（如 L1 → L3）

1. **保持代码质量**

   - 编写单元测试
   - 添加类型注解
   - 编写清晰的 docstrings
   - 更新相关文档

### 常见问题

**Q: 我应该在哪里添加新的算法？**

A: 如果是通用算法 → sage-libs (L3)；如果是领域特定的 → sage-middleware (L4)

**Q: 如何避免循环依赖？**

A: 遵循 L1-L6 单向依赖规则，参考 [包架构文档](package-architecture.md) 中的依赖关系图

**Q: 我的代码应该放在哪个模块？**

A: 参考 [包架构文档](package-architecture.md) 中每个包的模块组成部分

______________________________________________________________________

## � 相关资源

### 开发指南

- [贡献指南](../developers/commands.md) - 如何提交代码
- [开发环境设置](../developers/development-setup.md) - 环境配置
- [CI/CD](../developers/ci-cd.md) - 持续集成流程

### 架构文档

- [架构总览](../concepts/architecture/overview.md) - L1-L6 架构体系
- [包结构](../concepts/architecture/package-structure.md) - 包组织和依赖

### API 和指南

- [用户指南](../guides/index.md) - 按层级组织的使用指南
- [API 参考](../api-reference/index.md) - 完整的 API 文档

______________________________________________________________________

## 🔄 文档维护

### 更新原则

开发笔记应当：

- ✅ 提炼重要的技术见解
- ✅ 记录架构演进的关键决策
- ✅ 总结通用的开发模式
- ❌ 避免过于临时的实现细节
- ❌ 避免重复其他文档的内容

### 贡献开发笔记

如果你有有价值的技术总结想要分享：

1. 确保内容具有长期参考价值
1. 按照清晰的结构组织
1. 提供具体的示例和代码
1. 通过 PR 提交到 `docs-public/docs_src/dev-notes/`

______________________________________________________________________

## 📖 日常开发笔记

临时的开发笔记和工作记录请使用项目内的 `docs/dev-notes/` 目录，按以下结构组织：

```
docs/dev-notes/
├── l3-kernel/          # Kernel 开发笔记
├── l3-libs/            # Libs 开发笔记
├── l4-middleware/      # Middleware 开发笔记
├── l5-apps/            # Apps 开发笔记
├── l6-tools/           # Tools 开发笔记
├── cross-layer/        # 跨层主题
│   ├── architecture/   # 架构相关
│   ├── ci-cd/         # CI/CD 相关
│   └── performance/   # 性能相关
└── archive/           # 已归档的笔记
```

这些笔记用于日常开发过程中的记录和讨论，不会发布到公开文档网站。
