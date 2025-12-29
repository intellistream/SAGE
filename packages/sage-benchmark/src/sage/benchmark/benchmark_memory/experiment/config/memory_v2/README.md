# Memory Service V2 配置文件

> **版本**: v2.0\
> **创建日期**: 2025-12-26\
> **状态**: 新格式（基于 neuromem + UnifiedCollection）

## 📋 概述

本目录包含13个 Memory Service 配置文件，采用新的统一配置格式。

### 设计原则

1. **类型明确**：使用 `partitional.*` 和 `hierarchical.*` 前缀区分服务类型
1. **配置统一**：Collection 和 Indexes 配置集中管理
1. **业务独立**：Service 业务逻辑配置分离
1. **向后兼容**：支持旧格式自动迁移

## 📦 配置文件清单

### Partitional Services（5个）

| 配置文件                                                   | Service Type                                          | 用途            | 使用场景                     |
| ---------------------------------------------------------- | ----------------------------------------------------- | --------------- | ---------------------------- |
| `partitional_fifo_queue.yaml`                              | `partitional.fifo_queue`                              | 短期记忆（STM） | 最近对话历史、滑动窗口缓存   |
| `partitional_lsh_hash.yaml`                                | `partitional.lsh_hash`                                | LSH去重检索     | 文本去重、近似相似搜索       |
| `partitional_segment.yaml`                                 | `partitional.segment`                                 | 分段存储        | 会话管理、时间序列、主题分组 |
| `partitional_feature_summary_vectorstore_combination.yaml` | `partitional.feature_summary_vectorstore_combination` | 多索引组合      | 复杂查询、多维度检索         |
| `partitional_inverted_vectorstore_combination.yaml`        | `partitional.inverted_vectorstore_combination`        | 混合检索        | 关键词 + 语义检索            |

### Hierarchical Services（8个）

| 配置文件                                              | Service Type                                     | 用途         | 使用场景               |
| ----------------------------------------------------- | ------------------------------------------------ | ------------ | ---------------------- |
| `hierarchical_semantic_inverted_knowledge_graph.yaml` | `hierarchical.semantic_inverted_knowledge_graph` | 三层架构     | 复杂知识管理、多跳推理 |
| `hierarchical_linknote_graph.yaml`                    | `hierarchical.linknote_graph`                    | 双向链接笔记 | 知识图谱、笔记关联     |
| `hierarchical_property_graph.yaml`                    | `hierarchical.property_graph`                    | 属性图存储   | 复杂关系查询、图数据库 |
| `hierarchical_temporal_graph.yaml`                    | `hierarchical.temporal_graph`                    | 时序图数据库 | 时间线分析、事件溯源   |
| `hierarchical_multi_modal_memory.yaml`                | `hierarchical.multi_modal_memory`                | 多模态记忆   | 多模态检索、跨模态匹配 |
| `hierarchical_episodic_memory.yaml`                   | `hierarchical.episodic_memory`                   | 情景记忆     | 对话历史、个性化推荐   |
| `hierarchical_semantic_memory.yaml`                   | `hierarchical.semantic_memory`                   | 语义记忆     | 知识库、概念图谱       |
| `hierarchical_working_memory.yaml`                    | `hierarchical.working_memory`                    | 工作记忆     | 多任务管理、上下文切换 |

## 🔧 配置结构

所有配置文件遵循统一结构：

```yaml
service:
  # ========== Service 类型 ==========
  type: "partitional.xxx" 或 "hierarchical.xxx"

  # ========== Collection 配置 ==========
  collection:
    name: "collection_name"
    data_dir: null  # 默认临时目录

  # ========== 索引配置 ==========
  indexes:
    - name: "index_name"
      type: "fifo|lsh|segment|faiss|bm25"
      config:
        # 索引特定配置

  # ========== 业务逻辑配置 ==========
  service_config:
    default_index: "index_name"
    # Service特定配置
```

## 📖 使用方法

### 基础用法

```python
from sage.middleware.components.sage_mem import create_memory_service_from_config
import yaml

# 加载配置
with open("memory_v2/partitional_fifo_queue.yaml", "r") as f:
    config = yaml.safe_load(f)

# 创建服务
service = create_memory_service_from_config(config)

# 使用服务
service.add(text="Hello, world.", metadata={"user_id": "123"})
results = service.retrieve(query="Hello", top_k=5)
```

### 自定义配置

可以直接修改配置文件，或在代码中覆盖配置：

```python
config = yaml.safe_load(open("memory_v2/partitional_fifo_queue.yaml"))

# 自定义配置
config["service"]["indexes"][0]["config"]["max_size"] = 200
config["service"]["collection"]["data_dir"] = "/path/to/data"

service = create_memory_service_from_config(config)
```

## 🔄 从旧格式迁移

如果有旧格式配置文件，可以使用迁移脚本：

```bash
# 运行迁移脚本
python tools/config_migration.py \
  --input old_config.yaml \
  --output memory_v2/new_config.yaml
```

或使用批量迁移：

```bash
# 迁移整个目录
python tools/config_migration.py \
  --input-dir configs/memory/ \
  --output-dir configs/memory_v2/
```

## 🧪 验证配置

使用验证脚本检查配置文件格式：

```bash
# 验证单个文件
python tools/config_validator.py memory_v2/partitional_fifo_queue.yaml

# 验证整个目录
python tools/config_validator.py memory_v2/
```

## 📚 索引类型说明

### 可用索引类型

| 索引类型  | 描述     | 主要参数                          | 适用场景             |
| --------- | -------- | --------------------------------- | -------------------- |
| `fifo`    | FIFO队列 | `max_size`                        | 短期记忆、滑动窗口   |
| `lsh`     | LSH哈希  | `n_gram`, `num_perm`, `threshold` | 去重、相似搜索       |
| `segment` | 分段索引 | `strategy`, `segment_size`        | 时间序列、分组管理   |
| `faiss`   | 向量索引 | `dim`, `metric`, `index_type`     | 语义检索、相似度搜索 |
| `bm25`    | BM25倒排 | `backend`, `language`             | 关键词检索、全文搜索 |

### 索引组合策略

**Combination Services** 支持多个索引组合：

- `weighted`: 加权融合
- `voting`: 投票机制
- `cascade`: 级联查询
- `rrf`: Reciprocal Rank Fusion

## 🎯 最佳实践

### 1. 选择合适的 Service Type

- **简单场景**：使用 Partitional Services

  - 短期记忆 → `partitional.fifo_queue`
  - 文本去重 → `partitional.lsh_hash`
  - 时间分段 → `partitional.segment`

- **复杂场景**：使用 Hierarchical Services

  - 知识管理 → `hierarchical.semantic_inverted_knowledge_graph`
  - 对话历史 → `hierarchical.episodic_memory`
  - 多任务 → `hierarchical.working_memory`

### 2. 配置索引参数

**FIFO Queue:**

```yaml
config:
  max_size: 100  # 根据内存限制调整
```

**LSH Hash:**

```yaml
config:
  n_gram: 3        # 3-5 推荐
  num_perm: 128    # 越大越精确但越慢
  threshold: 0.5   # 0-1，相似度阈值
```

**Segment:**

```yaml
config:
  strategy: "time"       # time|keyword|custom
  segment_size: 100      # 每段数据量
  segment_duration: 3600 # 时间分段（秒）
```

**FAISS:**

```yaml
config:
  dim: 768              # 向量维度（与embedding模型匹配）
  metric: "cosine"      # cosine|l2|ip
  index_type: "Flat"    # Flat|IVF*|HNSW*
```

**BM25:**

```yaml
config:
  backend: "numba"      # numba（推荐）|python
  language: "auto"      # auto|zh|en
```

### 3. 数据目录管理

- **开发测试**：`data_dir: null`（使用临时目录）
- **生产环境**：`data_dir: "/path/to/persistent/storage"`

### 4. 性能优化

- **小数据量（\<1000）**：使用 `Flat` 索引
- **中等数据量（1000-100万）**：使用 `IVF` 索引
- **大数据量（>100万）**：使用 `HNSW` 索引

## 🔍 故障排查

### 常见问题

**1. 配置文件格式错误**

```bash
# 错误信息：Invalid config format
# 解决：运行验证工具
python tools/config_validator.py your_config.yaml
```

**2. 索引类型不存在**

```bash
# 错误信息：Unknown index type 'xxx'
# 解决：检查索引类型是否正确，参考上方"索引类型说明"
```

**3. 维度不匹配**

```bash
# 错误信息：Dimension mismatch
# 解决：确保 FAISS 的 dim 参数与 embedding 模型输出维度一致
```

## 📝 版本历史

- **v2.0** (2025-12-26)
  - 初始版本
  - 基于 neuromem + UnifiedCollection
  - 13个配置文件
  - 统一配置格式

## 🔗 相关文档

- [配置迁移指南](../../mem_docs/refactor/03_CONFIGURATION_MIGRATION.md)
- [测试策略](../../mem_docs/refactor/04_TESTING_STRATEGY.md)
- [任务分配方案](../../mem_docs/refactor/TASK_ASSIGNMENT.md)
- [neuromem API文档](../../../../sage-middleware/src/sage/middleware/components/sage_mem/neuromem/README.md)

## 🤝 贡献

如需添加新的配置文件或修改现有配置：

1. 复制最接近的配置文件作为模板
1. 修改 `service.type` 和相关配置
1. 运行验证工具确保格式正确
1. 更新本 README 的清单表格

## 📧 联系

如有问题，请参考项目文档或提交 Issue。
