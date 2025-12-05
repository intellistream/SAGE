# SAGE Memory Pipeline 开发档案（D1–D5 & R1–R5）

> 本档案汇总 `mem_docs` 目录下所有 TODO 任务（D1–D5、R1–R5 及配置剥离），并对照当前 `feature/memory-service-refactor`
> 分支上的实际代码，形成一份完整的开发与架构说明文档。原分散的 TODO\_\* 文档已被此档案取代。

______________________________________________________________________

## 一、整体架构概览

### 1.1 分层结构

SAGE 记忆系统分为三层：

```text
Pipeline 算子层 (libs)
    ├── PreInsert        (libs/pre_insert.py)
    ├── MemoryInsert     (libs/memory_insert.py)
    ├── PostInsert       (libs/post_insert.py)
    ├── PreRetrieval     (libs/pre_retrieval.py)
    ├── MemoryRetrieval  (libs/memory_retrieval.py)
    └── PostRetrieval    (libs/post_retrieval.py)

MemoryService 服务层 (sage_mem/services)
    ├── GraphMemoryService
    ├── HierarchicalMemoryService
    ├── HybridMemoryService
    ├── KeyValueMemoryService
    ├── ShortTermMemoryService
    ├── VectorHashMemoryService
    └── NeuroMemVDB / ParallelVDB 等

NeuroMem 引擎层 (sage_mem/neuromem)
    ├── MemoryManager
    └── MemoryCollection 家族
         ├── VDBMemoryCollection
         ├── GraphMemoryCollection
         └── KVMemoryCollection
```

### 1.2 操作与数据结构

```text
记忆体 = 记忆操作 + 记忆数据结构

记忆操作（4 阶段）
├── PreInsert       : 写入前预处理，只能检索
├── PostInsert      : 写入后优化，只允许一次 检索→删除→插入
├── PreRetrieval    : 检索前预处理，不访问存储
└── PostRetrieval   : 检索后处理，可多次检索并拼接 prompt

记忆数据结构
├── 存储结构：向量库 / 图 / KV / 分层 / 混合
└── 统一接口：insert / retrieve / delete / optimize
```

### 1.3 关键约束

- 每个 pipeline 只能配置一个记忆服务：`services.register_memory_service`
- Pipeline 算子层不直接操作底层数据结构，只通过 `call_service` 访问 MemoryService
- MemoryService 统一继承 `sage.platform.service.BaseService`，使用 NeuroMem 作为后端

______________________________________________________________________

## 二、D1：MemoryService（存储后端）

> 代码主位置：`sage-middleware/src/sage/middleware/components/sage_mem/services/`

### 2.1 统一接口与实现基线

所有 MemoryService 现在都：

- 继承 `BaseService`：`from sage.platform.service import BaseService`
- 在 `__init__` 中通过 `MemoryManager` 获取/创建 `MemoryCollection`
- 暴露统一接口（示意）：

```python
class XxxMemoryService(BaseService):
    def __init__(self, collection_name: str, ...):
        super().__init__()
        self.manager = MemoryManager(self._get_default_data_dir())
        self.collection = self.manager.create_collection({...})

    def insert(self, entry, vector=None, metadata=None, *, insert_mode="passive", insert_params=None):
        ...

    def retrieve(self, query=None, vector=None, metadata=None, top_k=10, hints=None):
        ...

    def delete(self, entry_id: str) -> bool:
        ...

    def optimize(self, params: dict) -> dict:
        ...
```

自定义的 `BaseMemoryService` 及其数据结构（nodes/edges/deque/dict 等）已在重构中删除，所有存储与索引逻辑下沉到 NeuroMem。

### 2.2 具体服务类型

- `GraphMemoryService`

  - 后端：`GraphMemoryCollection`
  - 功能：知识图谱 / 链接图存储，支持 link_evolution、synonym_edge 等

- `HierarchicalMemoryService`

  - 后端：多个 `VDBMemoryCollection`（如 STM/MTM/LTM）
  - 功能：分层存储与迁移，支持基于热度/时间/容量的迁移与遗忘

- `HybridMemoryService`

  - 后端：`VDBMemoryCollection` + `KVMemoryCollection`
  - 功能：多索引融合（语义向量 + 关键词/BM25），支持多维检索结果加权

- `KeyValueMemoryService`

  - 后端：`KVMemoryCollection`
  - 功能：精确/模糊/语义键值检索，适配实体/配置等场景

- `ShortTermMemoryService`

  - 后端：`VDBMemoryCollection` + 简单顺序索引
  - 功能：会话短期记忆，支持 FIFO、会话内快速检索

- `VectorHashMemoryService`

  - 后端：`VDBMemoryCollection`（LSH/FAISS 索引）
  - 功能：哈希桶式近似最近邻检索

- `NeuroMemVDBService` / `ParallelVDBService`

  - 后端：`MemoryManager` 管理的多 VDB 集合
  - 功能：通用向量数据库服务、多集合并行检索

______________________________________________________________________

## 三、D2：PreInsert（写入前预处理）

> 代码位置：`libs/pre_insert.py`\
> 配置前缀：`operators.pre_insert.*`

PreInsert 已实现以下 action，用于将原始输入规范化为 `memory_entries`：

- `none`：透传
- `tri_embed`：三元组抽取 + 向量化
- `transform`：分块/分段/事实抽取/摘要/压缩
- `extract`：关键词/实体/名词/Persona 抽取
- `score`：重要性/情绪等评分
- `multi_embed`：多路 embedding 生成
- `validate`：输入合法性与安全检查

配置与实现细节已在 `libs/pre_insert.py` 中落地，参数（如 `transform_type`、`extract_type`、`score_type` 等）均通过 YAML
配置驱动，不再依赖硬编码默认值。

______________________________________________________________________

## 四、D3：PostInsert（写入后巩固）

> 代码位置：`libs/post_insert.py`\
> 配置前缀：`operators.post_insert.*`

### 4.1 职责与动作

PostInsert 负责记忆写入后的巩固过程，当前实现的 action：

- 算子级（在算子内部完成）：

  - `none`：透传
  - `log`：记录日志
  - `stats`：统计插入数据
  - `distillation`：基于一次 检索→删除→插入 的记忆蒸馏

- 服务级（委托给 MemoryService）：

  - `reflection`：高阶反思生成
  - `link_evolution`：链接演化（同义边、强化、激活、自动链接）
  - `forgetting`：时间衰减/LRU/LFU/艾宾浩斯/混合遗忘
  - `summarize`：单层/分层/增量摘要
  - `migrate`：层间迁移（STM/MTM/LTM）

### 4.2 单服务与 optimize 接口

`PostInsert` 现在只保留一个服务名：

```python
self.service_name = config.get("services.register_memory_service", "short_term_memory")
```

所有服务级 action 通过统一入口触发：

```python
def _trigger_service_optimize(self, data):
    entries = data.get("memory_entries", [])
    optimize_params = {
        "trigger": self.action,
        "entries": entries,
        "config": getattr(self, "_action_config", {}),
    }
    result = self.call_service(
        self.service_name,
        method="optimize",
        params=optimize_params,
        timeout=30.0,
    )
    if result:
        data["optimize_result"] = result
```

各 MemoryService 在自身实现中解析 `trigger` 和 `config`，完成反思、链接、遗忘、迁移等逻辑，算子层不再维护状态机或数据结构。

______________________________________________________________________

## 五、D4：PreRetrieval（检索前预处理）

> 代码位置：`libs/pre_retrieval.py`\
> 配置前缀：`operators.pre_retrieval.*`

PreRetrieval 在不访问存储的前提下，对查询进行增强：

- `none`：透传
- `embedding`：基础向量化
- `optimize`：关键词提取、查询扩展、Query2Doc、指令增强
- `multi_embed`：多路查询 embedding（与 D2.multi_embed 配置对齐）
- `decompose`：复杂查询分解（LLM / 规则 / 混合）
- `route`：检索策略路由（输出 hints，而非服务路由）
- `validate`：查询长度/语言/安全检查

### 5.1 route 的 hints 输出

路由逻辑不再输出“服务列表”，而是输出检索提示：

```python
def _route_query(self, data):
    question = data.get("question", "")

    if self.route_strategy == "keyword":
        strategies = self._route_by_keyword(question)
    elif self.route_strategy == "classifier":
        strategies = self._route_by_classifier(question)
    elif self.route_strategy == "llm":
        strategies = self._route_by_llm(question)
    else:
        strategies = []

    data["retrieval_hints"] = {
        "strategies": strategies,
        "route_strategy": self.route_strategy,
    }
    return data
```

MemoryRetrieval 和服务层读取 `retrieval_hints`，在单一服务内部选择检索策略（如深度搜索/时间过滤/Persona 优先等），不再由 PreRetrieval
指定服务。

______________________________________________________________________

## 六、D5：PostRetrieval（检索后结果整合）

> 代码位置：`libs/post_retrieval.py`\
> 配置前缀：`operators.post_retrieval.*`

PostRetrieval 负责把检索结果加工为最终 prompt：

- `none`：基础对话格式化（`conversation_format_prompt`）
- `rerank`：重排序（PPR、时间加权、多因子 weighted、cross-encoder 等）
- `filter`：基于 token_budget / threshold / top_k / LLM 的结果筛选
- `merge`：在单服务场景下，通过多次查询或链接扩展合并结果
- `augment`：补充上下文（persona、最近事件等）
- `compress`：压缩/摘要（如 LLMLingua）
- `format`：按下游 LLM 需要的格式生成 `history_text`

### 6.1 职责边界修正

PostRetrieval 现在遵守以下边界：

- 不再计算新的 embedding（已移除 `EmbeddingGenerator` 依赖）
- 不再在算子内部实现去重算法，去重由服务负责或通过 filter 规则近似实现
- 不从 `data` 中读取多个独立记忆源（不再有 `merge_sources` 概念）
- 可以多次调用单一记忆服务，以补充关联记忆或其他上下文

示例：通过多次检索和链接扩展来 merge：

```python
def _merge_by_link_expand(self, items):
    result = list(items)
    for item in items[:5]:
        related = self.call_service(
            self.service_name,
            method="retrieve",
            query=item.text,
            metadata={"expand_links": True, "max_depth": 1},
        )
        ...  # 将关联记忆追加到 result
    return result
```

______________________________________________________________________

## 七、R1–R5：架构级重构总结

### 7.1 R1：MemoryService 接口统一（BaseService + NeuroMem）

- 删除自定义 `BaseMemoryService` 文件及其引用
- 所有服务现统一继承 `BaseService` 并使用 `MemoryManager` + 各类 `MemoryCollection`
- `services/__init__.py` 仅导出新的服务实现，并标注“所有服务使用 NeuroMem 后端”

### 7.2 R2：PostInsert 单服务重构

- `libs/post_insert.py` 从多服务引用与自维护状态机，收敛为只引用 `services.register_memory_service`
- 复杂逻辑（反思、链接、遗忘、迁移、摘要）全部委托给 `service.optimize()`
- Distillation 保留在算子层，但严格遵守“一次 检索→删除→插入”的约束

### 7.3 R3：PostRetrieval 职责边界修正

- 删除算子内部 embedding 计算与 dedup 实现
- merge 逻辑改为通过多次调用同一服务完成，不再从 `data` 合并多个源
- PostRetrieval 聚焦于结果 rerank / filter / augment / compress / format

### 7.4 R4：MemoryInsert 插入模式扩展

- `libs/memory_insert.py` 支持 `insert_mode`（`active`/`passive`）与 `insert_params`
- PreInsert 可在 `memory_entries[*]` 中写入：

```python
{
    "refactor": "processed text",
    "embedding": [...],
    "metadata": {...},
    "insert_mode": "active",
    "insert_params": {"target_tier": "ltm", "priority": 10},
}
```

- 所有服务的 `insert()` 接口统一增加 `insert_mode` 与 `insert_params`，据此执行主动/被动插入逻辑

### 7.5 R5：PreRetrieval 路由逻辑修正

- `PreRetrieval.route` 的输出从 `retrieval_routes` 调整为 `retrieval_hints`
- 配置中 keyword/classifier/llm 路由规则不再对应“服务名”，而是对应“策略标签”与“检索参数”
- MemoryRetrieval 将 hints 透传给单一记忆服务，由服务内部解释和执行

______________________________________________________________________

## 八、配置剥离与“一切皆配置”

> 对应原 `TODO_ConfigRefactor.md` 中的任务，现在以实际实现为主简要归档。

### 8.1 目标

- 所有 Prompt 模板和默认参数移出代码，统一放入 YAML 配置
- 运行时严禁依赖硬编码默认值，缺失配置应快速失败
- 配置本身即文档：各 operators 下的配置树完整描述行为

### 8.2 实际落实要点

- `libs/pre_insert.py`、`libs/post_insert.py`、`libs/pre_retrieval.py`、`libs/post_retrieval.py` 中：

  - 各 action 的 Prompt（如 `TOPIC_SEGMENT_PROMPT`、`DEFAULT_REFLECTION_PROMPT` 等）已重构为从配置读取
  - 绝大多数参数通过 `config.get("operators.xxx.yyy")` 方式注入
  - 在关键路径统一使用 `get_required_config` 对必需配置进行校验

- benchmark 配置中提供完整模板（如 `config/template_full.yaml`），涵盖：

  - runtime（LLM/Embedding 服务）
  - services（注册的记忆服务名）
  - operators.pre_insert / post_insert / pre_retrieval / post_retrieval 的全部参数与 prompts

______________________________________________________________________

## 九、测试与基准

- 服务层：为插入模式扩展、NeuroMem 集成、层间迁移等新增/更新了单元测试（如 `test_insert_mode_extension.py` 等）
- 算子层：覆盖各 action 的参数分支、异常路径与与服务交互协议
- 集成层：通过 SAGE benchmark 的对话/记忆场景，验证 end-to-end 行为正确性

测试文件与具体用例请参考 `packages/sage-middleware` 与 `packages/sage-benchmark` 下的 `tests` 目录。

______________________________________________________________________

## 十、后续建议

- 若新增 MemoryService：

  - 必须继承 `BaseService`，并使用 `MemoryManager` + 适当的 `MemoryCollection`
  - 对外仅暴露 insert/retrieve/delete/optimize 等有限接口
  - 不在服务外泄露内部数据结构

- 若新增 Pipeline 算子或新 action：

  - 遵循本档案的职责边界与访问约束
  - 所有行为通过配置驱动，避免硬编码
  - 与单一记忆服务通过 `call_service` 交互，避免多服务耦合

本档案后续如有架构/实现变更，应同步更新，以保持文档与代码的一致性。

______________________________________________________________________

## 十一、论文特性映射矩阵（Memory.md 对照）

> 本节将 `Memory.md` 中各论文的记忆体设计，映射到 SAGE 的五个维度：记忆数据结构 + 插入前/后操作 +
> 检索前/后操作，并标出对应的大类/小类与主要代码位置，方便新同学直接对号入座。

### 11.1 维度说明

- **数据结构**：对应 MemoryService + NeuroMem Collection（graph / hierarchical / hybrid / kv / stm / vhash /
  vdb 等）。
- **插入前操作**：`PreInsert` 下的大类/小类（transform / extract / score / multi_embed / validate ...）。
- **插入后操作**：`PostInsert` 下的大类/小类（reflection / link_evolution / forgetting / summarize / migrate
  ...）。
- **检索前操作**：`PreRetrieval` 下的大类/小类（optimize / multi_embed / decompose / route / validate ...）。
- **检索后操作**：`PostRetrieval` 下的大类/小类（rerank / filter / merge / augment / compress / format ...）。

下面每个小表都是“论文 → SAGE 对照”，不是逐句复刻算法，而是“能力/位置”映射。

### 11.2 TiM: Think-in-Memory

| 维度         | 论文中的设计                                                       | SAGE 中对应实现/位置                                              |
| ------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| 数据结构     | LSH 哈希桶 + thoughts（自然语言三元组）                            | `VectorHashMemoryService` + `VDBMemoryCollection`（LSH 索引）     |
| 插入前操作   | 对当前 Q-R 做 post-thinking，生成 inductive thoughts，可查询旧记忆 | `PreInsert.tri_embed` / `extract`，必要时 `call_service.retrieve` |
| 插入（接口） | 对 thought 做 LSH → 插入桶中                                       | MemoryInsert + VectorHash 服务的 `insert(entry, vector, ...)`     |
| 插入后操作   | 在桶内一次性 Forget / Merge：检索桶 → LLM 处理 → 清桶再插          | `PostInsert.distillation` + 服务 \`optimize(trigger="summarize"   |
| 检索前操作   | 对 query 嵌入化                                                    | `PreRetrieval.embedding` / `multi_embed`                          |
| 检索（接口） | LSH 定位桶 + 桶内相似度 top-k，外部不可干预                        | VectorHash 服务 `retrieve(query, vector, top_k)`                  |
| 检索后操作   | 将 thoughts 拼接为 prompt，可多次查询                              | `PostRetrieval.merge`+`augment`+`format`                          |

### 11.3 MemoryBank

| 维度         | 论文中的设计                                                    | SAGE 中对应实现/位置                                                                |
| ------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 数据结构     | 原始对话 + daily / global summary + user portrait，多层长期记忆 | `HierarchicalMemoryService`（STM/MTM/LTM）+ PostInsert.summarize 的层级摘要         |
| 插入前操作   | 可检索已有 persona/summary 决定是否生成新摘要                   | `PreInsert.transform.summarize` / `score.importance` + 可选 `call_service.retrieve` |
| 插入（接口） | 追加原始对话 + 生成并插入 daily/global summary                  | MemoryInsert + Hierarchical 服务 `insert(..., insert_mode, insert_params)`          |
| 插入后操作   | 基于 Ebbinghaus/heat 的遗忘与淘汰                               | \`PostInsert.forgetting(decay_type="ebbinghaus"                                     |
| 检索前操作   | 直接用当前 utterance 作为 query                                 | `PreRetrieval.none` / 基础 `embedding`                                              |
| 检索（接口） | Dense retrieval + FAISS，固定策略                               | NeuroMem VDB 服务 `retrieve(query, vector, top_k)`                                  |
| 检索后操作   | 将检索到的片段 + 全局画像/summary 拼接成 prompt                 | `PostRetrieval.augment`（persona/global summary）+ `format`                         |

### 11.4 MemGPT

| 维度         | 论文中的设计                                                               | SAGE 中对应实现/位置                                                             |
| ------------ | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 数据结构     | Working Context（结构化长期事实）+ FIFO Message Queue（STM）+ Recall Store | `KeyValueMemoryService` / `HierarchicalMemoryService` + `ShortTermMemoryService` |
| 插入前操作   | 提取事实、决定是否 replace（只能检索 Working Context，不写）               | `PreInsert.extract`+`score.importance`，必要时 `call_service.retrieve`           |
| 插入（接口） | append（FIFO）、写入 Working Context/Recall Storage，支持主动/被动插入     | MemoryInsert `insert_mode` + 各服务 insert 中的主动/被动分支                     |
| 插入后操作   | replace(old,new)：检索旧事实→删除→插入新事实                               | `PostInsert.distillation` / 服务 \`optimize(trigger="migrate"                    |
| 检索前操作   | 解析 query，提取关键词/意图，不访问记忆                                    | `PreRetrieval.optimize.keyword_extract` / `decompose`                            |
| 检索（接口） | 调用 Recall/Working Context 的固定检索接口                                 | 对应 MemoryService `retrieve(query, vector, hints)`                              |
| 检索后操作   | 多次访问 Working/Recall，拼接上下文                                        | `PostRetrieval.merge`（multi_query）+`augment`+`format`                          |

### 11.5 A-Mem

| 维度         | 论文中的设计                                                                | SAGE 中对应实现/位置                                                          |
| ------------ | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 数据结构     | note = {content, timestamp, keywords, tags, context, embedding, links} 图式 | `GraphMemoryService` / `HybridMemoryService` + Graph/VDB/KV Collections       |
| 插入前操作   | 用 LLM 从交互生成 Ki/Gi/Xi（关键词/标签/上下文），不访问记忆                | `PreInsert.extract`（keyword/entity/persona）+`transform.fact_extract`        |
| 插入（接口） | 被动插入：计算 embedding → 写入集合 M                                       | MemoryInsert + Graph/Hybrid 服务 `insert(entry, vector, metadata, ...)`       |
| 插入后操作   | Link Generation + Memory Evolution：一次检索邻居→建立链接→必要时 replace    | `PostInsert.link_evolution` + Graph 服务 `optimize(trigger="link_evolution")` |
| 检索前操作   | 对 query 编码为 eq                                                          | `PreRetrieval.embedding` / `multi_embed`                                      |
| 检索（接口） | 余弦相似度 top-k 检索                                                       | Graph/Hybrid/VDB 服务 `retrieve(query, vector, top_k)`                        |
| 检索后操作   | 对检索结果可再取链接记忆 L_i，多跳扩展后拼 prompt                           | `PostRetrieval.merge(link_expand)` + `augment`                                |

### 11.6 MemoryOS

| 维度         | 论文中的设计                                                       | SAGE 中对应实现/位置                                                         |
| ------------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 数据结构     | STM（FIFO）+ MTM（segment/page + heat）+ LPM（persona/KB/traits）  | `HierarchicalMemoryService`（stm/mtm/ltm tiers）+ KV/Graph 视需要组成 hybrid |
| 插入前操作   | 计算 Fscore/heat 决定 STM→MTM、MTM→LPM，允许对 heat 等进行检索     | `PreInsert.score` + 可选 `call_service.retrieve`（查看 heat/usage）          |
| 插入（接口） | STM append、MTM 归入 segment/LPM 更新 persona/traits，均为被动策略 | MemoryInsert.passive + Hierarchical 服务内部路由                             |
| 插入后操作   | 基于 heat 的迁移与淘汰（delete/evict）                             | `PostInsert.migrate`+`forgetting` + Hierarchical.optimize                    |
| 检索前操作   | 对 query 做 embedding/关键词提取，不访问记忆                       | `PreRetrieval.embedding`+`optimize.keyword_extract`                          |
| 检索（接口） | STM 全部 + MTM 两阶段检索 + LPM top-10 persona/traits              | Hierarchical 服务 `retrieve(..., hints)` 内部实现多层检索                    |
| 检索后操作   | 拼接 STM + MTM + LPM 结果成 prompt，多次查询记忆结构               | `PostRetrieval.merge`（multi_query）+`augment`+`format`                      |

### 11.7 HippoRAG / HippoRAG2

| 维度         | 论文中的设计                                                        | SAGE 中对应实现/位置                                                          |
| ------------ | ------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 数据结构     | Open KG：Phrase/Passage nodes + Relation/Synonym/Contains edges     | `GraphMemoryService` + `GraphMemoryCollection` + link_evolution.syndonym_edge |
| 插入前操作   | 使用 LLM 做 NER + OpenIE 提取 triples                               | `PreInsert.tri_embed` / `extract.entity`                                      |
| 插入（接口） | 被动插入：根据 triples 创建/扩展图、建立同义词边                    | Graph 服务 `insert(entry, metadata)` + optimize(trigger="link_evolution")     |
| 插入后操作   | 原文中基本缺失（无显式 once 检索-删除-插入），但可映射为图清理/压缩 | 可由 Graph 服务 \`optimize(trigger="summarize"                                |
| 检索前操作   | 对 query 做 NER / Query-to-Triple（部分实现等价于检索内部第一步）   | `PreRetrieval.optimize.keyword_extract` / `optimize.instruction`              |
| 检索（接口） | PPR 图检索 + Passage 排序                                           | Graph 服务 `retrieve(..., hints)` 内部实现 PPR，PostRetrieval.rerank.ppr      |
| 检索后操作   | 简单拼接 top-k 段落，未充分利用多次检索能力                         | 对应 SAGE 的 `PostRetrieval.none`/`format`；可扩展用 merge/link_expand        |

### 11.8 LD-Agent

| 维度         | 论文中的设计                                                      | SAGE 中对应实现/位置                                                  |
| ------------ | ----------------------------------------------------------------- | --------------------------------------------------------------------- |
| 数据结构     | STM 对话缓存 + LTM 事件摘要库                                     | `ShortTermMemoryService` + `HierarchicalMemoryService`                |
| 插入前操作   | 判断对话是否构成“事件”，可能检索已有摘要避免重复                  | `PreInsert.transform.summarize`+`score.importance` + 可选检索         |
| 插入（接口） | 短时缓存超时 → 触发摘要，写入 LTM（被动）；也支持主动插入事件摘要 | MemoryInsert + Hierarchical/NeuroMemVDB insert（active/passive）      |
| 插入后操作   | Replace/更新旧摘要（理论能力），一次检索-删除-插入                | PostInsert.distillation/forgetting + 服务 optimize(trigger="migrate") |
| 检索前操作   | 提取关键词集合 V_q 用于话题重叠                                   | `PreRetrieval.optimize.keyword_extract`                               |
| 检索（接口） | 综合语义相似度 + 话题重叠 + 时间衰减的打分检索                    | PostRetrieval.rerank.weighted + 服务检索返回基础分                    |
| 检索后操作   | 将记忆 m 与 STM、用户 persona、代理 persona 一起拼接              | `PostRetrieval.augment`（persona/traits）+`format`                    |

### 11.9 SCM（Self-Controlled Memory）

| 维度         | 论文中的设计                                                        | SAGE 中对应实现/位置                                             |
| ------------ | ------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 数据结构     | Memory Stream：{observation, response, summary, embedding} 追加序列 | `ShortTermMemoryService` + PreInsert.summarize + multi_embed     |
| 插入前操作   | 针对每轮交互生成 summary + embedding                                | `PreInsert.transform.summarize` + `multi_embed`                  |
| 插入（接口） | 将交互项 append 至 Memory Stream                                    | MemoryInsert.passive + ShortTermService.insert                   |
| 插入后操作   | 无（不做 replace/merge）                                            | 对应 SAGE 中不启用 PostInsert 的 reflection/forgetting 即可      |
| 检索前操作   | 判断是否需要激活记忆（yes/no），准备 query                          | `PreRetrieval.validate` + `optimize`                             |
| 检索（接口） | 根据 embedding + recency score 做 top-K 激活记忆检索                | VDB/ShortTerm 服务 retrieve + PostRetrieval.rerank.time_weighted |
| 检索后操作   | 若超 token budget，决定 truncate/summarize/drop，并拼成最终 prompt  | `PostRetrieval.filter.token_budget` + `compress` + `format`      |

### 11.10 Mem0 / Mem0ᵍ

| 维度         | 论文中的设计                                                         | SAGE 中对应实现/位置                                                               |
| ------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 数据结构     | 文本事实 + 全局摘要 S / 图记忆 G（实体+关系+时间戳+嵌入）            | 文本：`HierarchicalMemoryService` + PostInsert.summarize；图：`GraphMemoryService` |
| 插入前操作   | 读取摘要 S 和近期对话，提取候选记忆；Mem0ᵍ 生成实体和关系 triplets   | `PreInsert.transform` + `extract.entity` + 可选 `call_service.retrieve`            |
| 插入（接口） | Mem0：ADD/UPDATE/DELETE/NOOP；Mem0ᵍ：相似节点复用、新建节点、建边    | MemoryInsert + 各服务 insert；PostInsert/服务 optimize 决定 ADD/UPDATE/DELETE      |
| 插入后操作   | Mem0：检索相似记忆→UPDATE/DELETE；Mem0ᵍ：冲突关系逻辑删除+插入新关系 | `PostInsert.distillation`/`forgetting` + Graph/Hybrid 服务 optimize                |
| 检索前操作   | 直接用 query，不访问记忆或仅做 embedding                             | `PreRetrieval.embedding`                                                           |
| 检索（接口） | 文本向量检索 / 图中实体+关系双路径检索                               | VDB/Graph 服务 retrieve                                                            |
| 检索后操作   | Mem0：一次检索拼接；Mem0ᵍ：构建子图、多跳访问图后序列化为 prompt     | `PostRetrieval.merge`（link_expand/multi_query）+`format`                          |
