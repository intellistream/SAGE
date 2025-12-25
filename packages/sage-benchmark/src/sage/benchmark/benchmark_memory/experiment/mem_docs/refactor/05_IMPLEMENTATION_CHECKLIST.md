# 实施检查清单

> **目标**: 提供可执行的、按时间排序的实施任务清单
>
> **面向**: 程序员（逐项完成，逐项测试）

______________________________________________________________________

## 📅 时间线总览

| 阶段                       | 耗时      | 核心任务                                |
| -------------------------- | --------- | --------------------------------------- |
| **Phase 1: neuromem 重构** | 4 天      | UnifiedCollection + IndexFactory + 测试 |
| **Phase 2: Service 实现**  | 6 天      | 13 个 MemoryService + 测试              |
| **Phase 3: 配置迁移**      | 2.5 天    | 配置迁移 + 验证脚本 + 文档              |
| **Phase 4: 测试验收**      | 2.5 天    | 集成测试 + E2E + 性能测试               |
| **总计**                   | **15 天** | 预留 3 天 buffer → **18 天**            |

______________________________________________________________________

## 🚀 Phase 1: neuromem 层重构 (4 天)

### Day 1: UnifiedCollection 基础实现

**目标**: 实现数据管理 + 索引容器

#### Task 1.1: 创建文件结构 (0.5h)

```bash
# 创建新文件
cd packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem

# 创建目录
mkdir -p memory_collection/indexes

# 创建文件
touch memory_collection/unified_collection.py
touch memory_collection/indexes/__init__.py
touch memory_collection/indexes/base_index.py
touch memory_collection/indexes/index_factory.py
```

**验收**: 文件结构创建完成

______________________________________________________________________

#### Task 1.2: 实现 UnifiedCollection 数据管理 (2h)

**文件**: `memory_collection/unified_collection.py`

```python
# ✅ Checklist:
- [ ] 实现 __init__(name, config)
- [ ] 实现 insert(text, metadata, index_names) -> str
- [ ] 实现 get(data_id) -> Optional[Dict]
- [ ] 实现 delete(data_id) -> bool
- [ ] 实现 _generate_id(text, metadata) -> str (使用 UUID)
- [ ] 添加 logger
- [ ] 添加类型注解
```

**测试**: `tests/unit/neuromem/test_unified_collection_basic.py`

```python
def test_insert_and_get():
    coll = UnifiedCollection("test", {})
    data_id = coll.insert("Hello", {"source": "test"})
    data = coll.get(data_id)
    assert data["text"] == "Hello"

def test_delete():
    coll = UnifiedCollection("test", {})
    data_id = coll.insert("Hello")
    assert coll.delete(data_id) is True
    assert coll.get(data_id) is None
```

**验收**: 运行 `pytest tests/unit/neuromem/test_unified_collection_basic.py -v`

______________________________________________________________________

#### Task 1.3: 实现 UnifiedCollection 索引管理 (2h)

**文件**: `memory_collection/unified_collection.py`

```python
# ✅ Checklist:
- [ ] 实现 add_index(name, type, config) -> bool
- [ ] 实现 remove_index(name) -> bool
- [ ] 实现 list_indexes() -> List[Dict]
- [ ] 实现 insert_to_index(data_id, index_name) -> bool
- [ ] 实现 remove_from_index(data_id, index_name) -> bool
- [ ] 添加索引存在性检查
- [ ] 添加错误日志
```

**测试**: `tests/unit/neuromem/test_unified_collection_indexes.py`

```python
def test_add_index():
    coll = UnifiedCollection("test", {})
    assert coll.add_index("idx1", "faiss", {"dim": 768})
    assert "idx1" in coll.indexes

def test_remove_index():
    coll = UnifiedCollection("test", {})
    coll.add_index("idx1", "faiss", {"dim": 768})
    assert coll.remove_index("idx1")
    assert "idx1" not in coll.indexes
```

**验收**: 运行 `pytest tests/unit/neuromem/test_unified_collection_indexes.py -v`

______________________________________________________________________

#### Task 1.4: 实现 UnifiedCollection 查询 (1h)

**文件**: `memory_collection/unified_collection.py`

```python
# ✅ Checklist:
- [ ] 实现 query_by_index(index_name, query, **params) -> List[str]
- [ ] 实现 retrieve(index_name, query, **params) -> List[Dict]
- [ ] 添加索引不存在错误处理
- [ ] 添加空结果处理
```

**测试**: `tests/unit/neuromem/test_unified_collection_query.py`

**验收**: 运行所有 UnifiedCollection 测试通过

______________________________________________________________________

### Day 2: IndexFactory + 基础索引实现

#### Task 1.5: 实现 BaseIndex (1h)

**文件**: `memory_collection/indexes/base_index.py`

```python
# ✅ Checklist:
- [ ] 定义 BaseIndex 抽象类
- [ ] 定义 add(data_id, text, metadata) 抽象方法
- [ ] 定义 remove(data_id) 抽象方法
- [ ] 定义 query(query, **params) 抽象方法
- [ ] 定义 contains(data_id) 抽象方法
- [ ] 定义 save(path) 抽象方法
- [ ] 定义 load(path) 抽象方法
```

**验收**: 代码通过 Mypy 类型检查

______________________________________________________________________

#### Task 1.6: 实现 IndexFactory (0.5h)

**文件**: `memory_collection/indexes/index_factory.py`

```python
# ✅ Checklist:
- [ ] 实现 _registry: Dict[str, Type[BaseIndex]]
- [ ] 实现 create(index_type, config) -> BaseIndex
- [ ] 实现 register(index_type, index_class)
- [ ] 添加未知类型错误处理
```

**验收**: 可以注册和创建索引

______________________________________________________________________

#### Task 1.7: 实现 FIFOQueueIndex (2h)

**文件**: `memory_collection/indexes/fifo_queue_index.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseIndex
- [ ] 使用 collections.deque 实现队列
- [ ] 实现 add(data_id, text, metadata) - 超过 max_size 自动淘汰
- [ ] 实现 remove(data_id)
- [ ] 实现 query(query, top_k) - 返回最近 top_k 条
- [ ] 实现 contains(data_id)
- [ ] 实现 save/load (pickle)
- [ ] 注册到 IndexFactory
```

**测试**: `tests/unit/neuromem/indexes/test_fifo_queue_index.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 1.8: 实现 BM25Index (2h)

**文件**: `memory_collection/indexes/bm25_index.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseIndex
- [ ] 使用 rank_bm25 库
- [ ] 实现 add(data_id, text, metadata) - 更新倒排索引
- [ ] 实现 remove(data_id)
- [ ] 实现 query(query, top_k) - BM25 打分
- [ ] 实现 contains(data_id)
- [ ] 实现 save/load
- [ ] 注册到 IndexFactory
```

**测试**: `tests/unit/neuromem/indexes/test_bm25_index.py`

**验收**: 运行测试通过

______________________________________________________________________

### Day 3: 更多索引实现

#### Task 1.9: 实现 FAISSIndex (3h)

**文件**: `memory_collection/indexes/faiss_index.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseIndex
- [ ] 使用 faiss 库
- [ ] 实现 add(data_id, text, metadata) - 需要 embedding
- [ ] 实现 remove(data_id) - 标记删除
- [ ] 实现 query(query_vector, top_k) - 向量相似度
- [ ] 实现 contains(data_id)
- [ ] 实现 save/load (faiss.write_index)
- [ ] 支持 metric (cosine, l2, ip)
- [ ] 注册到 IndexFactory
```

**测试**: `tests/unit/neuromem/indexes/test_faiss_index.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 1.10: 实现 LSHIndex (2h)

**文件**: `memory_collection/indexes/lsh_index.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseIndex
- [ ] 使用 datasketch.MinHashLSH 或自实现
- [ ] 实现 add(data_id, text, metadata)
- [ ] 实现 remove(data_id)
- [ ] 实现 query(query_vector, top_k)
- [ ] 实现 contains(data_id)
- [ ] 实现 save/load
- [ ] 注册到 IndexFactory
```

**测试**: `tests/unit/neuromem/indexes/test_lsh_index.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 1.11: 实现 SegmentIndex (2h)

**文件**: `memory_collection/indexes/segment_index.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseIndex
- [ ] 支持 strategy: time / topic / size
- [ ] 实现 add(data_id, text, metadata) - 自动分段
- [ ] 实现 remove(data_id)
- [ ] 实现 query(query, segment_id, top_k)
- [ ] 实现 contains(data_id)
- [ ] 实现 save/load
- [ ] 注册到 IndexFactory
```

**测试**: `tests/unit/neuromem/indexes/test_segment_index.py`

**验收**: 运行测试通过

______________________________________________________________________

### Day 4: MemoryManager + 持久化

#### Task 1.12: 简化 MemoryManager (2h)

**文件**: `neuromem/memory_manager.py`

```python
# ✅ Checklist:
- [ ] 实现 __init__(data_dir)
- [ ] 实现 create_collection(name, config) -> UnifiedCollection
- [ ] 实现 get_collection(name) -> Optional[UnifiedCollection]
- [ ] 实现 remove_collection(name) -> bool
- [ ] 移除旧的 backend_type 注册逻辑
- [ ] 添加懒加载支持
```

**测试**: `tests/unit/neuromem/test_memory_manager.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 1.13: 实现持久化 (2h)

**文件**: `neuromem/memory_manager.py`

```python
# ✅ Checklist:
- [ ] 实现 persist(name) -> bool
  - [ ] 保存 raw_data.json
  - [ ] 保存 index_metadata.json
  - [ ] 调用各索引的 save()
- [ ] 实现 load_collection(name) -> Optional[UnifiedCollection]
  - [ ] 加载 raw_data.json
  - [ ] 加载 index_metadata.json
  - [ ] 重建索引（调用 IndexFactory + load）
- [ ] 实现 has_on_disk(name) -> bool
```

**测试**: `tests/unit/neuromem/test_memory_manager_persistence.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 1.14: Phase 1 集成测试 (1h)

**文件**: `tests/integration/neuromem/test_collection_manager_integration.py`

```python
# ✅ Checklist:
- [ ] 测试 Manager 创建 Collection
- [ ] 测试 Collection 添加多种索引
- [ ] 测试插入数据到多索引
- [ ] 测试查询多索引
- [ ] 测试持久化 + 重启加载
```

**验收**: 运行 `pytest tests/integration/neuromem/ -v`

______________________________________________________________________

## 🛠️ Phase 2: MemoryService 实现 (6 天)

### Day 5: BaseMemoryService + FIFO

#### Task 2.1: 实现 BaseMemoryService (2h)

**文件**: `services/base_service.py`

```python
# ✅ Checklist:
- [ ] 实现 __init__(collection, config)
- [ ] 定义 _setup_indexes() 抽象方法
- [ ] 定义 insert(text, metadata) 抽象方法
- [ ] 定义 retrieve(query, top_k, **kwargs) 抽象方法
- [ ] 实现 delete(data_id) 通用方法
- [ ] 实现 get(data_id) 通用方法
- [ ] 实现 list_indexes() 通用方法
- [ ] 实现 _get_embeddings(texts) 工具方法
- [ ] 实现 _summarize(texts) 工具方法
- [ ] 实现 _filter_by_metadata(results, filters) 工具方法
```

**验收**: 代码通过 Mypy 检查

______________________________________________________________________

#### Task 2.2: 实现 FIFOQueueService (1h)

**文件**: `services/partitional/fifo_queue_service.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] 实现 _setup_indexes() - 添加 FIFO 索引
- [ ] 实现 insert(text, metadata)
- [ ] 实现 retrieve(query, top_k)
- [ ] 添加 docstring
```

**测试**: `tests/unit/services/test_fifo_queue_service.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 2.3: 实现 MemoryServiceRegistry (1h)

**文件**: `services/registry.py`

```python
# ✅ Checklist:
- [ ] 实现 _services: Dict[str, Type[BaseMemoryService]]
- [ ] 实现 register(name, service_class)
- [ ] 实现 create(name, collection, config) -> BaseMemoryService
- [ ] 实现 list_services() -> List[str]
- [ ] 添加错误处理
```

**验收**: 可以注册和创建 Service

______________________________________________________________________

#### Task 2.4: 注册 FIFOQueueService (0.5h)

**文件**: `services/__init__.py`

```python
# ✅ Checklist:
- [ ] 导入 FIFOQueueService
- [ ] 调用 MemoryServiceRegistry.register("partitional.fifo_queue", FIFOQueueService)
```

**验收**: 可以通过 Registry 创建 FIFOQueueService

______________________________________________________________________

### Day 6-7: Partitional Services (简单)

#### Task 2.5: 实现 LSHHashService (2h)

**文件**: `services/partitional/lsh_hash_service.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] _setup_indexes() - 添加 LSH 索引
- [ ] insert() - 计算 embedding
- [ ] retrieve() - LSH 查询
- [ ] 注册到 Registry
```

**测试**: `tests/unit/services/test_lsh_hash_service.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 2.6: 实现 SegmentService (2h)

**文件**: `services/partitional/segment_service.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] _setup_indexes() - 添加 Segment 索引
- [ ] insert()
- [ ] retrieve() - 支持 segment_id 参数
- [ ] 注册到 Registry
```

**测试**: `tests/unit/services/test_segment_service.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 2.7-2.10: 实现 4 个 Combination Services (2 天，每个 0.5 天)

**Services**:

1. `FeatureSummaryVectorstoreCombinationService` (3h)
1. `FeatureQueueSegmentCombinationService` (3h)
1. `FeatureQueueSummaryCombinationService` (3h)
1. `InvertedVectorstoreCombinationService` (3h)

**每个 Service 的 Checklist**:

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] _setup_indexes() - 添加多个索引
- [ ] insert() - 多级数据处理
- [ ] retrieve() - 多级检索逻辑
- [ ] 实现特定工具方法（如 _extract_features）
- [ ] 添加详细 docstring
- [ ] 编写单元测试
- [ ] 注册到 Registry
```

**验收**: 每个 Service 测试通过

______________________________________________________________________

### Day 8-9: Hierarchical Services

#### Task 2.11: 实现 GraphIndex (3h)

**文件**: `memory_collection/indexes/graph_index.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseIndex
- [ ] 使用 networkx (默认) 或 neo4j
- [ ] 实现 add(data_id, text, metadata) - 提取节点和边
- [ ] 实现 add_node(node, properties)
- [ ] 实现 add_edge(source, target, properties)
- [ ] 实现 remove(data_id)
- [ ] 实现 query(entities, hop) - 图遍历
- [ ] 实现 save/load (networkx: pickle, neo4j: 无需)
- [ ] 注册到 IndexFactory
```

**测试**: `tests/unit/neuromem/indexes/test_graph_index.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 2.12: 实现 SemanticInvertedKnowledgeGraphService (4h)

**文件**: `services/hierarchical/semantic_inverted_kg_service.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] _setup_indexes() - Graph + Inverted + Vector
- [ ] 实现 _extract_entities(text) (NER)
- [ ] 实现 _extract_relations(text, entities) (RE)
- [ ] 实现 _update_graph(data_id, entities, relations)
- [ ] insert() - 三重处理
- [ ] retrieve() - 三级检索
- [ ] 注册到 Registry
```

**测试**: `tests/unit/services/test_semantic_inverted_kg_service.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 2.13: 实现 LinknoteGraphService (3h)

**文件**: `services/hierarchical/linknote_graph_service.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] _setup_indexes() - Graph + Vector
- [ ] 实现 _extract_links(text) - 正则匹配 [[note_name]]
- [ ] insert() - 建立链接
- [ ] retrieve() - 图 + 向量
- [ ] 注册到 Registry
```

**测试**: `tests/unit/services/test_linknote_graph_service.py`

**验收**: 运行测试通过

______________________________________________________________________

#### Task 2.14: 实现 PropertyGraphService (3h)

**文件**: `services/hierarchical/property_graph_service.py`

```python
# ✅ Checklist:
- [ ] 继承 BaseMemoryService
- [ ] _setup_indexes() - Graph (Neo4j 优先) + Vector
- [ ] insert() - 添加节点和边属性
- [ ] retrieve() - 属性查询 + 向量
- [ ] 注册到 Registry
```

**测试**: `tests/unit/services/test_property_graph_service.py`

**验收**: 运行测试通过

______________________________________________________________________

### Day 10: Service 集成测试

#### Task 2.15: Service 集成测试 (3h)

**文件**: `tests/integration/services/test_all_services_integration.py`

```python
# ✅ Checklist:
- [ ] 参数化测试所有 13 个 Service
- [ ] 测试创建 Service
- [ ] 测试插入数据
- [ ] 测试检索数据
- [ ] 测试删除数据
- [ ] 测试持久化 + 重启
```

**验收**: 运行 `pytest tests/integration/services/ -v`

______________________________________________________________________

## 🔧 Phase 3: 配置迁移 (2.5 天)

### Day 11: 配置文件创建

#### Task 3.1: 创建 13 个新配置文件 (4h)

**目录**: `examples/tutorials/L5-apps/configs/memory_v2/`

**Checklist**:

```bash
# ✅ 创建以下配置文件:
- [ ] partitional_fifo_queue.yaml
- [ ] partitional_lsh_hash.yaml
- [ ] partitional_segment.yaml
- [ ] partitional_feature_summary_vectorstore_combination.yaml
- [ ] partitional_feature_queue_segment_combination.yaml
- [ ] partitional_feature_queue_summary_combination.yaml
- [ ] partitional_feature_queue_vectorstore_combination.yaml
- [ ] partitional_inverted_vectorstore_combination.yaml
- [ ] hierarchical_semantic_inverted_knowledge_graph.yaml
- [ ] hierarchical_linknote_graph.yaml
- [ ] hierarchical_property_graph.yaml
```

**验收**: 所有配置文件创建完成

______________________________________________________________________

#### Task 3.2: 配置文件验证 (2h)

**文件**: `tools/config_validator.py`

```python
# ✅ Checklist:
- [ ] 定义 Pydantic 模型
- [ ] 实现 validate_config_file()
- [ ] 实现 validate_all_configs()
- [ ] 验证所有 13 个配置文件
```

**验收**: 运行 `python tools/config_validator.py` 无错误

______________________________________________________________________

### Day 12: 迁移脚本

#### Task 3.3: 实现配置迁移脚本 (3h)

**文件**: `tools/config_migration.py`

```python
# ✅ Checklist:
- [ ] 定义 SERVICE_NAME_MAPPING
- [ ] 定义 BACKEND_TO_INDEXES
- [ ] 实现 migrate_config(old_config)
- [ ] 实现 migrate_config_file(input, output)
- [ ] 实现 migrate_all_configs(input_dir, output_dir)
- [ ] 添加 CLI 参数解析
```

**验收**: 运行 `python tools/config_migration.py` 成功迁移

______________________________________________________________________

#### Task 3.4: 测试迁移脚本 (1h)

**测试**: `tests/unit/tools/test_config_migration.py`

```python
# ✅ Checklist:
- [ ] 测试 migrate_config() 基础功能
- [ ] 测试 SERVICE_NAME_MAPPING 所有映射
- [ ] 测试 BACKEND_TO_INDEXES 所有映射
- [ ] 测试迁移后配置通过验证
```

**验收**: 运行测试通过

______________________________________________________________________

### Day 13: 文档更新

#### Task 3.5: 更新配置文档 (2h)

**文件**: `docs/config_guide.md`

```markdown
# ✅ Checklist:
- [ ] 添加新配置格式说明
- [ ] 添加 13 个 Service 配置示例
- [ ] 添加迁移指南
- [ ] 添加常见问题 FAQ
```

**验收**: 文档完整

______________________________________________________________________

#### Task 3.6: 更新示例代码 (1h)

**文件**: `examples/tutorials/L5-apps/memory_service_demo.py`

```python
# ✅ Checklist:
- [ ] 使用新配置格式
- [ ] 演示所有 13 个 Service
- [ ] 添加详细注释
```

**验收**: 示例可运行

______________________________________________________________________

## 🧪 Phase 4: 测试验收 (2.5 天)

### Day 14: E2E + 性能测试

#### Task 4.1: 端到端测试 (3h)

**文件**: `tests/e2e/test_complete_workflows.py`

```python
# ✅ Checklist:
- [ ] 测试 FIFO Queue 完整流程
- [ ] 测试 Combination Service 完整流程
- [ ] 测试 Hierarchical Service 完整流程
- [ ] 测试配置加载 → Service 创建流程
```

**验收**: 运行 `pytest tests/e2e/ -v`

______________________________________________________________________

#### Task 4.2: 性能基准测试 (2h)

**文件**: `tests/performance/test_benchmarks.py`

```python
# ✅ Checklist:
- [ ] 测试插入性能（10K 条）
- [ ] 测试检索性能（1K 查询）
- [ ] 测试大数据集性能（100K 条）
- [ ] 测试内存占用
- [ ] 对比旧实现性能
```

**验收**: 性能满足目标（±5%）

______________________________________________________________________

### Day 15: 文档 + CI

#### Task 4.3: 更新 README (1h)

**文件**: `packages/sage-middleware/README.md`

```markdown
# ✅ Checklist:
- [ ] 更新架构说明
- [ ] 更新使用示例
- [ ] 添加 13 个 Service 说明
- [ ] 添加迁移指南链接
```

**验收**: 文档完整

______________________________________________________________________

#### Task 4.4: 配置 CI (2h)

**文件**: `.github/workflows/test-memory-service.yml`

```yaml
# ✅ Checklist:
- [ ] 添加单元测试 job
- [ ] 添加集成测试 job
- [ ] 添加 E2E 测试 job
- [ ] 添加覆盖率上传
- [ ] 添加性能回归检测
```

**验收**: CI 通过

______________________________________________________________________

#### Task 4.5: 最终验收 (2h)

**Checklist**:

```bash
# ✅ 最终检查:
- [ ] 所有单元测试通过（覆盖率 >85%）
- [ ] 所有集成测试通过
- [ ] 所有 E2E 测试通过
- [ ] 性能测试满足目标
- [ ] CI 全绿
- [ ] 文档完整
- [ ] 示例可运行
- [ ] 代码通过 Mypy + Ruff 检查
```

**验收**: 所有检查通过 ✅

______________________________________________________________________

## 📋 快速启动指南

### 给程序员的快速开始

```bash
# 1. 克隆仓库
git clone <repo>
cd SAGE

# 2. 安装依赖
./quickstart.sh --dev --yes

# 3. 查看任务清单
cat packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/refactor/05_IMPLEMENTATION_CHECKLIST.md

# 4. 开始实施（从 Phase 1 Day 1 开始）
cd packages/sage-middleware
mkdir -p src/sage/middleware/components/sage_mem/neuromem/memory_collection/indexes

# 5. 实现 → 测试 → 提交（循环）
# 实现一个任务
vim src/sage/middleware/components/sage_mem/neuromem/memory_collection/unified_collection.py

# 运行测试
pytest tests/unit/neuromem/test_unified_collection_basic.py -v

# 提交
git add .
git commit -m "feat(neuromem): implement UnifiedCollection data management"

# 6. 重复步骤 5，直到完成所有任务
```

______________________________________________________________________

## 🔍 调试指南

### 常见问题

#### 问题 1: 索引导入失败

```python
# ❌ 错误
from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import FAISSIndex

# ✅ 解决
from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes.faiss_index import FAISSIndex
```

#### 问题 2: Collection 未找到

```python
# 确保已持久化
manager.persist("my_collection")

# 确保数据目录正确
manager = MemoryManager(data_dir="/correct/path")
```

#### 问题 3: 测试失败（数据污染）

```python
# 每个测试前清理
def setup_method(self):
    self.collection = UnifiedCollection("test", {})

# 或使用 pytest fixture
@pytest.fixture
def clean_collection():
    return UnifiedCollection("test", {})
```

______________________________________________________________________

## 📊 进度追踪

### 每日检查点

| Day | 完成任务                   | 验收标准              | 状态 |
| --- | -------------------------- | --------------------- | ---- |
| 1   | UnifiedCollection 基础     | 数据管理测试通过      | ⏳   |
| 2   | IndexFactory + FIFO/BM25   | 索引测试通过          | ⏳   |
| 3   | FAISS/LSH/Segment 索引     | 所有索引测试通过      | ⏳   |
| 4   | MemoryManager + 持久化     | 集成测试通过          | ⏳   |
| 5   | BaseService + FIFO         | Service 测试通过      | ⏳   |
| 6-7 | 4 个 Combination Services  | 所有 Service 测试通过 | ⏳   |
| 8-9 | 3 个 Hierarchical Services | 所有 Service 测试通过 | ⏳   |
| 10  | Service 集成测试           | 集成测试通过          | ⏳   |
| 11  | 配置文件创建               | 13 个配置文件完成     | ⏳   |
| 12  | 迁移脚本                   | 迁移测试通过          | ⏳   |
| 13  | 文档更新                   | 文档完整              | ⏳   |
| 14  | E2E + 性能测试             | E2E 通过，性能达标    | ⏳   |
| 15  | 文档 + CI                  | CI 全绿               | ⏳   |

______________________________________________________________________

## 🎯 成功标准

### 最终验收标准

- ✅ **功能完整**: 13 个 MemoryService 全部实现并通过测试
- ✅ **测试覆盖**: neuromem >90%, MemoryService >85%
- ✅ **性能达标**: 插入/检索性能 ±5% 基准
- ✅ **文档完整**: README, 配置指南, 迁移指南
- ✅ **CI 通过**: 所有测试绿色
- ✅ **代码质量**: Mypy + Ruff 无错误

______________________________________________________________________

**恭喜！** 如果所有任务完成，重构成功 🎉
