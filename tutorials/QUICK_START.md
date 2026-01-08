# 🚀 SAGE Tutorials - Quick Start

欢迎来到 SAGE Tutorials！本指南将帮助你在 **5 分钟内**开始使用 SAGE。

## ⚡ 超快入门（2 分钟）

### 1. 运行第一个示例

```bash
cd /path/to/SAGE/examples/tutorials
python hello_world.py
```

恭喜！你已经运行了第一个 SAGE 程序！

### 2. 理解架构

SAGE 采用 **6 层架构**，从底层到应用层：

```
L1: Common      → 基础工具 (配置、日志)
L2: Kernel      → 核心引擎 (流处理、批处理)
L3: Middleware  → 数据服务 (向量数据库、时序数据库)
L4: Libs        → 应用库 (RAG、Agents、LLM)
L5: Platform    → 平台服务 (调度、部署)
L6: Apps        → 完整应用 (端到端解决方案)
```

### 3. 选择学习路径

根据你的角色选择合适的路径：

| 角色          | 推荐路径           | 时间     |
| ------------- | ------------------ | -------- |
| 🔰 初学者     | L1 → L2 基础       | 1-2 小时 |
| 🚀 应用开发者 | L1 → L2 → L3 → L4  | 4-6 小时 |
| 🧠 平台开发者 | 全栈学习 L1-L5     | 1-2 天   |
| 🏗️ 架构师     | 全部 L1-L6 + tools | 2-3 天   |

______________________________________________________________________

## 📚 分层学习指南

### L1: Common - 基础层（15 分钟）

**目标**：理解 SAGE 的基础概念

```bash
cd L1-common
python hello_world.py        # 最基础的示例
```

**核心概念**：

- SAGE 环境配置
- 日志系统
- 基本术语

👉 **下一步**：进入 L2-kernel 学习核心 API

______________________________________________________________________

### L2: Kernel - 核心层（2-3 小时）

**目标**：掌握流处理和批处理

#### 2.1 批处理基础（30 分钟）

```bash
cd L2-kernel/batch
python hello_local_batch.py   # 本地批处理
python hello_remote_batch.py  # 远程批处理
```

#### 2.2 流处理基础（30 分钟）

```bash
cd L2-kernel/stream
python hello_streaming_world.py  # 基础流处理
python hello_onebyone_world.py   # 单条流处理
```

#### 2.3 操作符系统（1 小时）

```bash
cd L2-kernel/operators
python hello_comap_world.py    # CoMap 操作符
python hello_filter_world.py   # Filter 过滤
python hello_flatmap_world.py  # FlatMap 展开
python hello_join_world.py     # Join 连接
```

#### 2.4 高级特性（选修）

```bash
cd L2-kernel/advanced
python hello_future_world.py   # Future 异步
```

**核心概念**：

- DataStream API
- Operator 系统
- 批处理 vs 流处理
- Pipeline 构建

👉 **下一步**：进入 L3-middleware 学习数据服务

______________________________________________________________________

### L3: Middleware - 中间件层（1-2 小时）

**目标**：使用数据服务和中间件

#### 3.1 服务入门（15 分钟）

```bash
cd L3-middleware
python hello_service_world.py  # 理解服务模型
```

#### 3.2 Memory Service（30 分钟）

```bash
cd L3-middleware/memory_service
python rag_memory_service.py   # RAG 内存服务
```

#### 3.3 数据库服务（30 分钟）

```bash
cd L3-middleware/sage_db
python workflow_demo.py        # 向量数据库

cd L3-middleware/sage_tsdb
python basic_dag_example.py    # 时序数据库
```

**核心概念**：

- Service API
- 向量数据库
- 时序数据处理
- 内存管理

👉 **下一步**：进入 L4-libs 构建应用

______________________________________________________________________

### L4: Libs - 应用库层（2-4 小时）

**目标**：构建实际应用

#### 4.1 RAG 应用（1-2 小时）

```bash
cd L4-libs/rag
python simple_rag.py                # 简单 RAG
python usage_1_direct_library.py    # 直接使用库
python usage_4_complete_rag.py      # 完整 RAG 系统
```

#### 4.2 Agent 应用（30 分钟）

```bash
cd L4-libs/agents
python basic_agent.py          # 基础智能体
python workflow_demo.py        # 工作流
```

#### 4.3 Embedding 应用（30 分钟）

```bash
cd L4-libs/embeddings
python embedding_demo.py        # 嵌入演示
python cross_modal_search.py   # 跨模态搜索
```

#### 4.4 LLM 应用（30 分钟）

```bash
cd L4-libs/llm
python pipeline_builder_llm_demo.py  # LLM 管道
python templates_to_llm_demo.py      # 模板演示
```

**核心概念**：

- RAG 系统设计
- Agent 架构
- 向量嵌入
- LLM 集成

👉 **下一步**：进入 L5-platform 学习平台服务（高级）

______________________________________________________________________

### L5: Platform - 平台层（1-2 小时，高级）

**目标**：理解平台级服务

```bash
cd L5-platform/scheduler
python scheduler_comparison.py  # 调度器对比
python remote_env.py            # 远程环境
```

**核心概念**：

- 任务调度
- 分布式执行
- 资源管理

👉 **下一步**：探索 L6-apps 完整应用（即将推出）

______________________________________________________________________

## 🎯 常见学习路径

### 路径 1：RAG 开发者（最热门）

```
1. L1-common/hello_world.py              (5 分钟)
2. L2-kernel/batch/hello_local_batch.py  (15 分钟)
3. L3-middleware/memory_service/         (30 分钟)
4. L4-libs/rag/simple_rag.py             (30 分钟)
5. L4-libs/rag/usage_4_complete_rag.py   (1 小时)
```

**总时间**：约 2.5 小时

### 路径 2：Agent 开发者

```
1. L1-common/hello_world.py              (5 分钟)
2. L2-kernel/stream/                     (30 分钟)
3. L4-libs/agents/basic_agent.py         (30 分钟)
4. L4-libs/agents/workflow_demo.py       (1 小时)
```

**总时间**：约 2 小时

### 路径 3：平台工程师

```
1. 完整学习 L1-L2                        (3 小时)
2. L3-middleware/ 全部                   (2 小时)
3. L5-platform/ 全部                     (2 小时)
```

**总时间**：约 7 小时

______________________________________________________________________

## 📖 文档和帮助

### 快速查询

- **快速参考**：`docs/QUICK_REFERENCE.md`
- **故障排除**：`docs/TROUBLESHOOTING.md`
- **学习路径**：`docs/LEARNING_PATH.md`（即将推出）

### 层级文档

每个层级目录都有详细的 README：

- `L1-common/README.md`
- `L2-kernel/README.md`
- `L3-middleware/README.md`
- `L4-libs/README.md`
- `L5-platform/README.md`
- `L6-apps/README.md`

### 遇到问题？

1. 查看 `docs/TROUBLESHOOTING.md`
1. 检查每个示例的注释
1. 阅读对应层级的 README
1. 查看项目主 README

______________________________________________________________________

## 🎓 学习建议

### ✅ 推荐做法

1. **按顺序学习**：从 L1 开始，逐层深入
1. **动手实践**：运行每个示例，修改参数
1. **阅读注释**：示例中有详细的说明
1. **理解概念**：不要只运行，要理解原理

### ❌ 避免

1. **跳过基础**：L1-L2 是必须的
1. **只看不做**：一定要运行代码
1. **贪多嚼不烂**：一次专注一个主题

______________________________________________________________________

## 🚀 下一步行动

根据你的兴趣选择：

- **我想构建 RAG 系统** → 按"路径 1"学习
- **我想开发 Agent** → 按"路径 2"学习
- **我想深入理解架构** → 从 L1 开始系统学习
- **我只想快速尝试** → 运行 `hello_world.py` 和几个感兴趣的示例

______________________________________________________________________

## 💡 小贴士

- 每个示例都可以独立运行
- 示例之间有依赖关系，建议按推荐顺序学习
- 遇到错误先查看 `TROUBLESHOOTING.md`
- 配置文件在 `config/` 目录

______________________________________________________________________

**开始你的 SAGE 之旅吧！🎉**
