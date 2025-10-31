# 🚀 SAGE Tutorials

欢迎来到 SAGE Tutorials！这里包含了按照 SAGE 架构分层组织的完整示例和文档。

> **从基础到应用：循序渐进地掌握 SAGE 框架**

## ⚡ 5 分钟快速开始

```bash
# 1. 运行第一个示例
python hello_world.py

# 2. 查看快速入门指南
cat QUICK_START.md
```

## 📐 SAGE 6 层架构概览

SAGE 采用 **6 层分层架构**，从底层基础设施到顶层应用：

```
┌─────────────────────────────────────────────┐
│ L6: Interface (接口层)                      │
│ sage-studio, sage-tools, sage-cli          │
│ Web UI + CLI 工具 + 命令行接口              │
├─────────────────────────────────────────────┤
│ L5: Apps (应用层)                           │
│ sage-apps, sage-benchmark                  │
│ 完整应用 + 性能测试                         │
├─────────────────────────────────────────────┤
│ L4: Middleware (中间件层)                   │
│ sage-middleware                            │
│ 领域算子 + 中间件组件                       │
├─────────────────────────────────────────────┤
│ L3: Core (核心层)                           │
│ sage-kernel + sage-libs                   │
│ 执行引擎 + 算法库                           │
├─────────────────────────────────────────────┤
│ L2: Platform (平台层)                       │
│ sage-platform                              │
│ 队列 + 存储 + 服务抽象                      │
├─────────────────────────────────────────────┤
│ L1: Foundation (基础层)                     │
│ sage-common                                │
│ 配置 + 日志 + 工具                          │
└─────────────────────────────────────────────┘
```

**核心原则**：

- ✅ **单向依赖**：只能向下依赖（L6→L5→L4→L3→L2→L1）
- ❌ **禁止反向**：禁止向上或循环依赖
- 📚 **详细说明**：[SAGE 包架构文档](../../docs-public/docs_src/dev-notes/package-architecture.md)

## 📚 Tutorial 目录结构

```
tutorials/
│
├── hello_world.py         # 最简入门（快速开始）
├── QUICK_START.md         # 5 分钟快速指南
├── README.md              # 本文档
│
├── L1-common/             # 基础层：配置、日志、工具
├── L2-platform/           # 平台层：队列、存储、调度
├── L3-kernel/             # 核心层：执行引擎、流处理
├── L3-libs/               # 核心层：RAG、Agents、算法库
├── L4-middleware/         # 中间件层：领域算子、数据服务
├── L5-apps/               # 应用层：完整应用
├── L6-interface/          # 接口层：CLI、Web UI
│
├── config/                # 配置文件示例
└── docs/                  # 文档（快速参考、故障排除）
```

## �� 学习路径

### 🔰 初学者路径（2-3 小时）

适合第一次接触 SAGE 的用户

```bash
# L1: 基础概念
cd L1-common && python hello_world.py

# L2: 平台服务
cd L2-platform/scheduler && python scheduler_comparison.py

# L3: 核心引擎
cd L3-kernel/batch && python hello_local_batch.py
cd L3-kernel/stream && python hello_streaming_world.py
cd L3-kernel/operators && python hello_comap_world.py
```

**学习目标**：理解 SAGE 基础概念、流处理模型、操作符系统

### 🚀 应用开发者路径（4-6 小时）

适合想要构建应用的开发者

```bash
# 完成初学者路径后

# L3: 算法库
cd L3-libs/rag && python simple_rag.py
cd L3-libs/agents && python basic_agent.py

# L4: 中间件服务
cd L4-middleware && python hello_service_world.py
cd L4-middleware/memory_service && python rag_memory_service.py

# L4: 数据服务
cd L4-middleware/sage_db && python workflow_demo.py
cd L4-middleware/sage_tsdb && python basic_dag_example.py
```

**学习目标**：掌握 RAG 系统、Agent 开发、数据服务使用

### 🧠 高级开发者路径（1-2 天）

适合平台开发者和架构师

```bash
# 完成应用开发者路径后

# L3: 高级特性
cd L3-kernel/advanced && python hello_future_world.py
cd L3-kernel/advanced/fault_tolerance && python fault_tolerance.py

# L3: 完整 RAG 系统
cd L3-libs/rag && python usage_4_complete_rag.py

# L5: 应用集成
# （待添加完整应用示例）
```

**学习目标**：深入理解容错机制、异步处理、生产级系统设计

## �� 各层级详细说明

### L1: Common - 基础层

**对应包**：`sage-common`

**内容**：

- `hello_world.py` - 最基础的 SAGE 程序
- 配置管理示例
- 日志系统示例

**Python 文件数**：1

[查看详细文档 →](L1-common/README.md)

______________________________________________________________________

### L2: Platform - 平台服务层

**对应包**：`sage-platform`

**内容**：

- `scheduler/` - 调度系统示例
- 队列抽象示例（待添加）
- 存储后端示例（待添加）

**Python 文件数**：2

[查看详细文档 →](L2-platform/README.md)

______________________________________________________________________

### L3: Kernel - 核心引擎层

**对应包**：`sage-kernel`

**内容**：

- `batch/` - 批处理示例（3 个）
- `stream/` - 流处理示例（3 个）
- `operators/` - 操作符示例（5 个）
- `functions/` - 函数示例（3 个）
- `advanced/` - 高级特性（容错、Future、Pipeline-as-Service 等，17 个）

**Python 文件数**：31

[查看详细文档 →](L3-kernel/README.md)

______________________________________________________________________

### L3: Libs - 算法库层

**对应包**：`sage-libs`

**内容**：

- `rag/` - RAG 应用示例（7 个）
- `agents/` - 智能体示例（5 个）
- `embeddings/` - 嵌入示例（4 个）
- `llm/` - LLM 集成示例（2 个）
- `unlearning/` - 机器遗忘示例（5 个）

**Python 文件数**：23

[查看详细文档 →](L3-libs/README.md)

______________________________________________________________________

### L4: Middleware - 中间件层

**对应包**：`sage-middleware`

**内容**：

- `hello_service_world.py` - 服务入门
- `memory_service/` - 内存管理（3 个）
- `sage_db/` - 向量数据库（4 个）
- `sage_flow/` - 流数据服务（3 个）
- `sage_tsdb/` - 时序数据库（3 个）

**Python 文件数**：13

[查看详细文档 →](L4-middleware/README.md)

______________________________________________________________________

### L5: Apps - 应用层

**对应包**：`sage-apps`, `sage-benchmark`

**内容**：

- `complete_solutions/` - 完整应用（待添加）

**Python 文件数**：0 (待添加)

[查看详细文档 →](L5-apps/README.md)

______________________________________________________________________

### L6: Interface - 接口层

**对应包**：`sage-studio` (Web UI), `sage-tools` (开发工具), `sage-cli` (命令行)

**内容**：

- CLI 工具示例（待添加）
- Web UI 示例（待添加）
- 命令行工具示例（待添加）

**Python 文件数**：0 (待添加)

**说明**：

- **sage-studio**：可视化 Web UI，提供管道编辑器
- **sage-tools**：开发工具集（测试、质量检查、包管理等）
- **sage-cli**：命令行接口，提供 `sage` 命令

[查看详细文档 →](L6-interface/README.md)

______________________________________________________________________

## 📊 示例统计

| 层级     | 对应包                            | Python 文件 | 主要内容     |
| -------- | --------------------------------- | ----------- | ------------ |
| L1       | sage-common                       | 1           | 基础工具     |
| L2       | sage-platform                     | 2           | 平台服务     |
| L3       | sage-kernel                       | 31          | 流处理引擎   |
| L3       | sage-libs                         | 23          | 算法库       |
| L4       | sage-middleware                   | 13          | 数据服务     |
| L5       | sage-apps, sage-benchmark         | 0           | 待添加       |
| L6       | sage-studio, sage-tools, sage-cli | 0           | 待添加       |
| **总计** | -                                 | **70**      | **6 层架构** |

## 📖 补充文档

- [**QUICK_START.md**](QUICK_START.md) - 5 分钟快速入门
- [**docs/QUICK_REFERENCE.md**](docs/QUICK_REFERENCE.md) - 快速参考卡
- [**docs/TROUBLESHOOTING.md**](docs/TROUBLESHOOTING.md) - 故障排除指南

## 🔍 如何选择示例

### 我想学习...

- **基础概念** → 从 `hello_world.py` 开始
- **流处理** → `L3-kernel/stream/`
- **批处理** → `L3-kernel/batch/`
- **RAG 系统** → `L3-libs/rag/`
- **智能体** → `L3-libs/agents/`
- **数据服务** → `L4-middleware/`
- **容错机制** → `L3-kernel/advanced/fault_tolerance/`

### 我想构建...

- **简单脚本** → `L3-libs/rag/usage_1_direct_library.py`
- **数据管道** → `L3-kernel/` 中的示例
- **RAG 应用** → `L3-libs/rag/usage_4_complete_rag.py`
- **Agent 系统** → `L3-libs/agents/workflow_demo.py`
- **完整应用** → 学习所有层级

## 🎓 学习建议

### ✅ 推荐做法

1. **按层级学习**：从 L1 开始，逐层深入
1. **理解依赖**：了解为什么上层可以用下层，反之不行
1. **动手实践**：运行每个示例，修改参数观察效果
1. **阅读代码**：示例中有详细注释
1. **参考文档**：遇到问题查看各层的 README

### ❌ 避免

1. **跳过基础**：L1-L3 是必须理解的
1. **只看不做**：一定要运行代码
1. **忽略架构**：理解架构有助于设计更好的系统
1. **违反依赖**：不要在低层导入高层代码

## 🆘 遇到问题？

1. 查看 [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
1. 检查示例的注释和 docstring
1. 阅读对应层级的 README
1. 查看 [SAGE 包架构文档](../../docs-public/docs_src/dev-notes/package-architecture.md)
1. 提交 Issue 到 GitHub

## 🤝 贡献

欢迎添加新示例或改进现有示例！请确保：

1. 示例放在正确的层级目录
1. 遵循依赖规则（只向下依赖）
1. 添加清晰的注释和文档
1. 更新对应的 README

## 📜 变更历史

- **2025-10-29**: 按照 SAGE 6 层架构重组目录（L1-L6）
  - 完整映射 9 个 SAGE 包到 6 个层级
  - 添加 sage-cli 到 L6 接口层说明
  - 迁移 service 目录内容到对应层级
  - 创建完整的学习路径和文档

______________________________________________________________________

**开始探索 SAGE 吧！🎉**

有任何问题或建议，欢迎提 Issue 或 PR！
