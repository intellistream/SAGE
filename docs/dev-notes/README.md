# Development Notes

开发笔记和技术文档，记录 SAGE 项目的实现细节、架构设计和开发指南。

## 📁 目录结构

```
dev-notes/
├── README.md                              # 本文件
├── TEMPLATE.md                            # 新文档模板
│
├── 🚀 快速开始
│   ├── QUICK_START.md                     # 快速开始指南
│   ├── DEV_COMMANDS.md                    # 开发命令参考
│   └── DEV_INFRASTRUCTURE_SETUP.md        # 基础设施配置
│
├── 🎯 Embedding 系统
│   ├── EMBEDDING_README.md                # Embedding 总览（含导航）
│   ├── EMBEDDING_QUICK_REFERENCE.md       # 快速参考手册
│   ├── EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md  # 完整总结
│   └── embedding/                         # 详细文档目录
│       ├── README.md                      # 子目录索引
│       ├── EMBEDDING_OPTIMIZATION_PLAN.md
│       ├── EMBEDDING_OPTIMIZATION_PHASE*.md (3个phase报告)
│       ├── EMBEDDING_CHANGELOG.md
│       └── PIPELINE_BUILDER_EMBEDDING_INTEGRATION.md
│
├── 📚 架构文档
│   ├── SAGE_CHAT_ARCHITECTURE.md          # Chat 命令架构
│   └── SAGE_LIBS_OPERATORS.md             # Operators 文档
│
└── 📂 专题目录
    ├── autostop/                          # Autostop 服务
    ├── security/                          # 安全配置
    └── ci-cd/                             # CI/CD 文档
```

## 📖 核心文档

### 🎯 快速入门
- **[QUICK_START.md](./QUICK_START.md)** - 开发环境搭建和基础操作
- **[DEV_COMMANDS.md](./DEV_COMMANDS.md)** - 常用开发命令参考
- **[DEV_INFRASTRUCTURE_SETUP.md](./DEV_INFRASTRUCTURE_SETUP.md)** - 基础设施和依赖配置

### 🔧 Embedding 系统
- **[EMBEDDING_README.md](./EMBEDDING_README.md)** - Embedding 系统总览和导航
- **[EMBEDDING_QUICK_REFERENCE.md](./EMBEDDING_QUICK_REFERENCE.md)** - API 快速查询
- **[embedding/](./embedding/)** - 详细实现文档（phase 报告、优化计划等）

### 🏗️ 架构设计
- **[SAGE_CHAT_ARCHITECTURE.md](./SAGE_CHAT_ARCHITECTURE.md)** - `sage chat` 命令架构
- **[SAGE_LIBS_OPERATORS.md](./SAGE_LIBS_OPERATORS.md)** - Pipeline Operators 文档

## 📝 创建新文档

使用模板创建新文档：

```bash
# 1. 复制模板
cp TEMPLATE.md your_feature_name.md

# 2. 编辑内容
# - 标题：简洁描述（如 "Embedding 优化 Phase 1"）
# - 状态：进行中/已完成/已归档
# - 日期：创建日期和更新日期
# - 内容：问题、解决方案、测试、总结

# 3. 选择合适的位置
# - 通用文档：放在 dev-notes/ 根目录
# - 专题文档：放在对应子目录（embedding/, autostop/, 等）
```

## 🎯 文档原则

1. **简洁明了** - 直接说明问题和解决方案
2. **结构清晰** - 使用标题、列表、代码块
3. **及时更新** - 保持状态和内容最新
4. **避免重复** - 相关内容合并到一个文档
5. **定期清理** - 删除过时的临时文档

## � 专题目录

### 🔄 [autostop/](./autostop/)
Autostop 服务实现和配置文档

### 🔒 [security/](./security/)
安全配置、API Key 管理、最佳实践

### 🔧 [ci-cd/](./ci-cd/)
CI/CD 配置、构建问题和部署文档

---

💡 **提示**: 优先查看 `QUICK_START.md` 和 `EMBEDDING_README.md`
