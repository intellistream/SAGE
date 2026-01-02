# Memory Service Refactor (2024-12) — Summary

> 目标：将 `sage-middleware` 的记忆服务从“多Collection继承体系”重构为“统一Collection + 动态索引 + 业务Service组合”的架构。
>
> 本文档为 **memory-refactor-2024** 目录的“去开发化”汇总版：只保留架构设计、命名体系、配置结构、迁移原则与测试结论；移除任务拆解、排期、分工、实现细节与代码片段。

______________________________________________________________________

## 1. 重构动机与结论

### 1.1 旧架构的主要痛点

- **Collection 过度多态**：VDB/Graph/KV/Hybrid 等多个 Collection 类型各自实现 insert/retrieve/delete，导致重复与耦合。
- **扩展成本高**：新增索引类型往往意味着修改/新增 Collection 子类。
- **职责边界模糊**：Collection 同时承担“数据容器 + 索引能力定义 + 部分业务逻辑”。
- **命名与配置碎片化**：旧命名（如 short_term_memory、hierarchical_memory）无法体现结构本质，也不利于与论文/实验一一对应。

### 1.2 新架构的核心思想

- **一个 Collection 足够**：数据只存一份，索引能力通过“动态索引组合”获得。
- **Service 只做业务逻辑**：Service 通过组合 Collection 的索引能力实现记忆策略，不关心底层存储形态。
- **命名体系语义化**：使用 `partitional.*` / `hierarchical.*` 等类别前缀，服务名反映“存储/索引结构 + 关键策略”。

______________________________________________________________________

## 2. 分层与组件边界（推荐心智模型）

### 2.1 分层概览

- **L2: neuromem（Data & Index Layer）**

  - `UnifiedCollection`：统一数据容器（raw data + 多索引容器）。
  - `Index`：独立的索引实现（FAISS/LSH/BM25/FIFO/Segment/Graph…）。
  - `MemoryManager`：Collection 生命周期管理（创建、加载、持久化、删除）。

- **L5: MemoryService（Business Logic Layer）**

  - 每个 Service = “使用哪些索引 + 插入/检索时的业务策略”。
  - 典型策略：特征提取、摘要、过滤、排序、多索引融合、路由等。

> 关键边界：
>
> - Collection 管“数据与索引容器”；
> - Index 管“索引结构与检索算法”；
> - Service 管“记忆策略（业务逻辑）”。

______________________________________________________________________

## 3. neuromem 新模型：UnifiedCollection + 动态索引

### 3.1 UnifiedCollection 的职责

- 保存原始数据：`text + metadata + created_at`（数据只存一份）。
- 管理多个索引：索引可按需创建/删除、按需写入。
- 提供统一的索引查询入口：按索引名称检索，返回 data_id，再由 Collection 取回完整数据。

### 3.2 动态索引的设计要点

- **索引彼此独立**：每个索引实现只关心 add/remove/query。
- **组合优先于继承**：新索引类型只需实现 Index 接口并注册到工厂，无需改 Collection。
- **按需写入**：insert 时可指定写入哪些索引（支持“同一数据，多索引落地”）。

### 3.3 Index 类型（文档中涉及的常见种类）

- Dense：FAISS（向量检索）
- Sparse：BM25（倒排/关键词检索）
- Approx：LSH（近似相似检索）
- Temporal：FIFO（窗口/队列淘汰）
- Structural：Graph（图遍历/关联/扩散）
- Organizational：Segment（分段/分组检索）

______________________________________________________________________

## 4. Service 分类与命名体系（最重要的对外接口）

### 4.1 命名规则

- 总体形式：`类别.修饰前缀_索引结构`
- 其中：
  - **类别**：`partitional` / `hierarchical`（目前文档主覆盖这两类）
  - **索引结构**：queue / hash / inverted / graph / segment / knowledge_graph / combination…
  - **修饰前缀**：fifo / lsh / semantic_inverted / feature_queue_segment …（用于表达关键实现差异）

### 4.2 13 个 Locomo 配置 → 新服务命名映射（讨论后确认）

| Locomo 配置                            | 新服务名称                                            |
| -------------------------------------- | ----------------------------------------------------- |
| locomo_short_term_memory_pipeline.yaml | `partitional.fifo_queue`                              |
| locomo_scm_pipeline.yaml               | `partitional.fifo_queue`                              |
| locomo_tim_pipeline.yaml               | `partitional.lsh_hash`                                |
| locomo_hipporag_pipeline.yaml          | `hierarchical.semantic_inverted_knowledge_graph`      |
| locomo_hipporag2_pipeline.yaml         | `hierarchical.semantic_inverted_knowledge_graph`      |
| locomo_amem_pipeline.yaml              | `hierarchical.linknote_graph`                         |
| locomo_memorybank_pipeline.yaml        | `partitional.feature_summary_vectorstore_combination` |
| locomo_memoryos_pipeline.yaml          | `partitional.feature_queue_segment_combination`       |
| locomo_ldagent_pipeline.yaml           | `partitional.feature_queue_summary_combination`       |
| locomo_secom_pipeline.yaml             | `partitional.segment`                                 |
| locomo_memgpt_pipeline.yaml            | `partitional.feature_queue_vectorstore_combination`   |
| locomo_mem0_pipeline.yaml              | `partitional.inverted_vectorstore_combination`        |
| locomo_mem0g_pipeline.yaml             | `hierarchical.property_graph`                         |

> 备注：文档中提到“13 configs / 11 services”，原因是部分配置在概念上共享同一个 Service（通过参数区分具体行为）。

______________________________________________________________________

## 5. 配置体系（v2 方向）与迁移原则

### 5.1 配置 v2 的目标

- Service 类型与命名体系对齐：`service.type: partitional.fifo_queue`。
- Collection 配置统一：collection name、persist、data_dir 等集中定义。
- Index 配置集中：在同一处声明要创建的索引清单及参数。
- 业务配置与索引解耦：例如 top_k、threshold、缓存、embedder/summarizer 等。

### 5.2 v2 配置结构（概念级）

- `service.type`：选择服务类型（即 registry key）。
- `service.config.collection`：Collection 的持久化与命名。
- `service.config.indexes[]`：索引列表（name/type/config）。
- `service.config.embedder / summarizer`：可选的模型/摘要能力。
- `service.config.top_k / threshold`：服务层默认检索参数。

### 5.3 迁移原则（从 v1 → v2）

- **保持向后兼容**：旧配置仍可运行，新配置逐步替换。
- **消除 backend_type 绑定**：不再让“Collection 类型”决定索引能力；改为“Collection + indexes”。
- **把“索引声明”集中化**：避免散落在不同 service 私有字段/初始化代码中。

______________________________________________________________________

## 6. Registry / Factory 的对外体验（配置驱动实例化）

文档强调将记忆服务的实例化方式朝“Registry 模式”统一：

- 外部只需要通过 `service.type`（或等价字段）选择服务。
- Registry 负责 `name → ServiceClass` 映射。
- Service 负责结合 config 创建/绑定 collection，并配置所需 indexes。

> 目标效果：像 PreInsert/PostInsert 等算子一样，通过配置选择实现，避免多余的中间薄层。

______________________________________________________________________

## 7. 测试与质量保证（结论级）

测试策略遵循“单元 → 集成 → 端到端 → 性能”的金字塔：

- **单元测试**：覆盖 UnifiedCollection / 各 Index / 各 Service 的核心行为。
- **集成测试**：验证 Service + Collection + Index 的协同，以及 Manager 的持久化/加载。
- **E2E 测试**：覆盖“配置加载 → 创建服务 → 插入/检索/删除”的完整路径。
- **性能测试**：关注插入/检索速度、内存占用、并发能力（以基线±波动阈值评估）。

______________________________________________________________________

## 8. 对使用者的落地建议（非开发视角）

### 8.1 如何选服务

- **只要最近 N 条（对话历史）**：`partitional.fifo_queue`
- **需要快速近似相似检索（大规模去重/近邻）**：`partitional.lsh_hash`
- **长对话/长文按段组织**：`partitional.segment`
- **稀疏+稠密混合检索**：`partitional.inverted_vectorstore_combination`
- **知识图谱/多层路由/图推理**：`hierarchical.semantic_inverted_knowledge_graph` / `hierarchical.linknote_graph`
  / `hierarchical.property_graph`

### 8.2 配置上的共识

- 让“索引列表”成为配置第一公民：明确写出你要哪些索引，以及每个索引的参数。
- 把“业务策略参数”与“索引参数”分开：便于调参、也便于迁移。

______________________________________________________________________

## 9. 代码与文档入口（快速定位）

- 代码：`packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/`
  - `memory_collection.py` / `memory_manager.py` / `indexes/` / `services/`
- 文档：本目录 `memory-refactor-2024/`
  - 命名与映射：`MEMORY_SERVICE_NAMING_DISCUSSION.md`
  - 配置迁移：`03_CONFIGURATION_MIGRATION.md`
  - 测试策略：`04_TESTING_STRATEGY.md`

______________________________________________________________________

## 10. 术语表

- **Collection**：统一数据容器，保存 raw data，并持有多个 index。
- **Index**：可独立扩展的索引结构，实现 add/remove/query。
- **Service**：业务记忆策略实现，决定如何写索引、如何融合检索结果。
- **Partitional**：数据/索引呈分区或桶化组织，通常无显式中心层级。
- **Hierarchical**：显式层级或多层结构（或图结构的层/路由）。

______________________________________________________________________

## 变更记录（面向读者的简版）

- 架构从“多Collection继承” → “UnifiedCollection + 动态索引 + Service组合”。
- 命名从旧的功能名 → 新的结构语义名（partitional/hierarchical）。
- 配置从“backend_type/散落索引” → “collection + indexes + business config（集中声明）”。
