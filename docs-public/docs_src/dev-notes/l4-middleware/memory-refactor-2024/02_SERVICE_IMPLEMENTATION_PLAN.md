# MemoryService 层实现方案

> **目标**: 基于 UnifiedCollection 重新实现 13 个 MemoryService
>
> **原则**: Service 只负责业务逻辑，不关心底层 Collection 实现

______________________________________________________________________

## 🎯 设计原则

### Service 的职责

```python
MemoryService = Collection + 业务逻辑

Business Logic:
    - Summarization (特征提取)
    - Filtering (检索过滤)
    - Ranking (结果排序)
    - Combination (多索引融合)

Collection Provides:
    - Data Storage (原始数据)
    - Indexes (FAISS, Graph, FIFO, etc.)
    - Query APIs (query_by_index)
```

**关键区别**:

- ❌ 旧设计：Service 继承特定 Collection（强耦合）
- ✅ 新设计：Service 组合 UnifiedCollection（松耦合）

______________________________________________________________________

## 📐 Service 基类设计

```python
# packages/sage-middleware/src/sage/middleware/components/sage_mem/services/

class BaseMemoryService(ABC):
    """MemoryService 基类 - 所有 13 个 Service 的父类

    设计要点：
    1. 持有 UnifiedCollection 引用（不继承）
    2. 定义统一的业务接口
    3. 提供公共工具方法
    """

    def __init__(self, collection: UnifiedCollection, config: Dict[str, Any]):
        """初始化 Service

        Args:
            collection: UnifiedCollection 实例（由 Manager 提供）
            config: Service 配置（如 top_k, threshold 等）
        """
        self.collection = collection
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Service 特定初始化（子类实现）
        self._setup_indexes()

    # ========== 抽象方法（子类必须实现）==========
    @abstractmethod
    def _setup_indexes(self):
        """配置所需索引（在 __init__ 中调用）

        Example:
            self.collection.add_index("vector", "faiss", {"dim": 768})
            self.collection.add_index("queue", "fifo", {"max_size": 10})
        """

    @abstractmethod
    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        """插入数据（Service 特定逻辑）"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """检索数据（Service 特定逻辑）"""

    # ========== 公共方法（所有 Service 共享）==========
    def delete(self, data_id: str) -> bool:
        """删除数据（通用实现）"""
        return self.collection.delete(data_id)

    def get(self, data_id: str) -> Optional[Dict]:
        """获取原始数据（通用实现）"""
        return self.collection.get(data_id)

    def list_indexes(self) -> List[Dict]:
        """列出当前 Service 使用的索引"""
        return self.collection.list_indexes()

    # ========== 工具方法 ==========
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取 Embedding（公共工具）"""
        embedder = self.config.get("embedder")
        if not embedder:
            raise ValueError("Embedder not configured")
        return embedder.embed(texts)

    def _summarize(self, texts: List[str]) -> str:
        """总结文本（公共工具）"""
        summarizer = self.config.get("summarizer")
        if not summarizer:
            return " ".join(texts[:100])  # fallback
        return summarizer.summarize(texts)

    def _filter_by_metadata(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """元数据过滤（公共工具）"""
        if not filters:
            return results

        filtered = []
        for item in results:
            metadata = item.get("metadata", {})
            if all(metadata.get(k) == v for k, v in filters.items()):
                filtered.append(item)
        return filtered
```

______________________________________________________________________

## 📦 13 个 Service 实现

### 分类 1: Partitional Services (简单分区)

#### 1. FIFOQueueService

**索引**: FIFO 队列\
**特点**: 固定大小，先进先出

```python
class FIFOQueueService(BaseMemoryService):
    """FIFO 队列 - 保留最近 N 条数据

    使用场景：对话历史、实时日志
    """

    def _setup_indexes(self):
        max_size = self.config.get("max_size", 10)
        self.collection.add_index(
            "fifo_queue",
            "fifo",
            {"max_size": max_size}
        )

    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        """插入数据（自动淘汰最老的）"""
        data_id = self.collection.insert(text, metadata, index_names=["fifo_queue"])

        # FIFO 索引自动处理淘汰
        return data_id

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """检索最近的 top_k 条"""
        # FIFO 队列按时间顺序返回
        data_ids = self.collection.query_by_index("fifo_queue", query=None, top_k=top_k)
        return [self.collection.get(id) for id in data_ids]
```

#### 2. LSHHashService

**索引**: LSH (Locality-Sensitive Hashing)\
**特点**: 快速近似相似度搜索

```python
class LSHHashService(BaseMemoryService):
    """LSH 哈希 - 快速相似度搜索

    使用场景：大规模去重、快速检索
    """

    def _setup_indexes(self):
        dim = self.config.get("embedding_dim", 768)
        num_tables = self.config.get("num_tables", 10)

        self.collection.add_index(
            "lsh_index",
            "lsh",
            {"dim": dim, "num_tables": num_tables}
        )

    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        # 计算 Embedding
        embedding = self._get_embeddings([text])[0]

        # 插入数据 + LSH 索引
        data_id = self.collection.insert(
            text,
            metadata={**(metadata or {}), "embedding": embedding},
            index_names=["lsh_index"]
        )
        return data_id

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        # 计算 query embedding
        query_emb = self._get_embeddings([query])[0]

        # LSH 检索
        data_ids = self.collection.query_by_index(
            "lsh_index",
            query=query_emb,
            top_k=top_k
        )
        return self.collection.retrieve("lsh_index", query_emb, top_k=top_k)
```

#### 3. SegmentService

**索引**: Segment (时间/主题分段)\
**特点**: 自动分段，段内检索

```python
class SegmentService(BaseMemoryService):
    """分段索引 - 按时间或主题分组

    使用场景：长文档分段、会话分段
    """

    def _setup_indexes(self):
        segment_strategy = self.config.get("strategy", "time")  # time/topic
        segment_size = self.config.get("segment_size", 50)

        self.collection.add_index(
            "segment_index",
            "segment",
            {"strategy": segment_strategy, "size": segment_size}
        )

    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        # Segment 索引自动分组
        return self.collection.insert(text, metadata, index_names=["segment_index"])

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """检索相关段"""
        segment_id = kwargs.get("segment_id")  # 可选：指定段

        data_ids = self.collection.query_by_index(
            "segment_index",
            query=query,
            segment_id=segment_id,
            top_k=top_k
        )
        return [self.collection.get(id) for id in data_ids]
```

______________________________________________________________________

### 分类 2: Combination Services (组合型)

#### 4. FeatureSummaryVectorstoreCombinationService

**索引**: Feature Map + Summary + VectorStore\
**特点**: 三级检索（特征→总结→向量）

```python
class FeatureSummaryVectorstoreCombinationService(BaseMemoryService):
    """特征+总结+向量组合

    检索流程：
    1. 提取 query 特征 → 匹配 Feature Map
    2. 命中特征 → 查总结
    3. 总结不够详细 → 查原文 VectorStore
    """

    def _setup_indexes(self):
        # 1. Feature Map (关键词索引)
        self.collection.add_index("feature_map", "bm25", {})

        # 2. Summary Store (总结向量)
        self.collection.add_index(
            "summary_vector",
            "faiss",
            {"dim": self.config["embedding_dim"]}
        )

        # 3. Full Text VectorStore
        self.collection.add_index(
            "full_text_vector",
            "faiss",
            {"dim": self.config["embedding_dim"]}
        )

    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        # 1. 提取特征（关键词）
        features = self._extract_features(text)

        # 2. 生成总结
        summary = self._summarize([text])

        # 3. 计算 Embeddings
        summary_emb = self._get_embeddings([summary])[0]
        full_text_emb = self._get_embeddings([text])[0]

        # 插入数据
        data_id = self.collection.insert(
            text,
            metadata={
                **(metadata or {}),
                "features": features,
                "summary": summary,
                "summary_embedding": summary_emb,
                "full_text_embedding": full_text_emb
            },
            index_names=["feature_map", "summary_vector", "full_text_vector"]
        )
        return data_id

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        """三级检索"""
        # Level 1: Feature Map
        feature_matches = self.collection.query_by_index(
            "feature_map",
            query=query,
            top_k=top_k * 2
        )

        if len(feature_matches) >= top_k:
            # Level 2: Summary Vector (精炼结果)
            query_emb = self._get_embeddings([query])[0]
            summary_matches = self.collection.query_by_index(
                "summary_vector",
                query=query_emb,
                top_k=top_k,
                candidates=feature_matches  # 在 feature 结果中检索
            )

            # Level 3: Full Text Vector (需要更多细节时)
            if kwargs.get("detailed", False):
                full_matches = self.collection.query_by_index(
                    "full_text_vector",
                    query=query_emb,
                    top_k=top_k
                )
                return self._merge_results(summary_matches, full_matches)

            return [self.collection.get(id) for id in summary_matches]

        # Fallback: 直接用 Full Text Vector
        query_emb = self._get_embeddings([query])[0]
        full_matches = self.collection.query_by_index(
            "full_text_vector",
            query=query_emb,
            top_k=top_k
        )
        return [self.collection.get(id) for id in full_matches]

    def _extract_features(self, text: str) -> List[str]:
        """提取特征（关键词）"""
        # TODO: 实现特征提取（TF-IDF, KeyBERT, etc.）
        return text.split()[:10]  # 简化版

    def _merge_results(self, list1, list2) -> List[Dict]:
        """合并去重"""
        seen = set()
        merged = []
        for item in list1 + list2:
            if item["id"] not in seen:
                merged.append(item)
                seen.add(item["id"])
        return merged
```

#### 5. InvertedVectorstoreCombinationService

**索引**: Inverted Index + VectorStore\
**特点**: 关键词召回 + 向量精排

```python
class InvertedVectorstoreCombinationService(BaseMemoryService):
    """倒排索引 + 向量组合

    检索流程：
    1. 倒排索引快速召回
    2. 向量相似度精排
    """

    def _setup_indexes(self):
        self.collection.add_index("inverted_index", "bm25", {})
        self.collection.add_index(
            "vector_index",
            "faiss",
            {"dim": self.config["embedding_dim"]}
        )

    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        embedding = self._get_embeddings([text])[0]

        return self.collection.insert(
            text,
            metadata={**(metadata or {}), "embedding": embedding},
            index_names=["inverted_index", "vector_index"]
        )

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        recall_k = kwargs.get("recall_k", top_k * 10)

        # Stage 1: BM25 召回
        candidates = self.collection.query_by_index(
            "inverted_index",
            query=query,
            top_k=recall_k
        )

        # Stage 2: Vector 精排
        query_emb = self._get_embeddings([query])[0]
        ranked_ids = self.collection.query_by_index(
            "vector_index",
            query=query_emb,
            top_k=top_k,
            candidates=candidates
        )

        return [self.collection.get(id) for id in ranked_ids]
```

______________________________________________________________________

### 分类 3: Hierarchical Services (层级型)

#### 6. SemanticInvertedKnowledgeGraphService

**索引**: Graph + Inverted + VectorStore\
**特点**: 语义图 + 关键词 + 向量三合一

```python
class SemanticInvertedKnowledgeGraphService(BaseMemoryService):
    """语义倒排知识图谱

    检索流程：
    1. Graph 找实体关系
    2. Inverted 找相关文档
    3. Vector 排序
    """

    def _setup_indexes(self):
        self.collection.add_index("knowledge_graph", "graph", {})
        self.collection.add_index("inverted_index", "bm25", {})
        self.collection.add_index(
            "vector_index",
            "faiss",
            {"dim": self.config["embedding_dim"]}
        )

    def insert(self, text: str, metadata: Optional[Dict] = None) -> str:
        # 提取实体和关系
        entities = self._extract_entities(text)
        relations = self._extract_relations(text, entities)

        # 计算 embedding
        embedding = self._get_embeddings([text])[0]

        data_id = self.collection.insert(
            text,
            metadata={
                **(metadata or {}),
                "entities": entities,
                "relations": relations,
                "embedding": embedding
            },
            index_names=["knowledge_graph", "inverted_index", "vector_index"]
        )

        # 更新 Graph
        self._update_graph(data_id, entities, relations)

        return data_id

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Dict]:
        # 1. Graph: 找相关实体
        query_entities = self._extract_entities(query)
        graph_results = self.collection.query_by_index(
            "knowledge_graph",
            query=query_entities,
            top_k=top_k * 3
        )

        # 2. Inverted: 找相关文档
        inverted_results = self.collection.query_by_index(
            "inverted_index",
            query=query,
            top_k=top_k * 3
        )

        # 3. 合并候选
        candidates = list(set(graph_results + inverted_results))

        # 4. Vector: 精排
        query_emb = self._get_embeddings([query])[0]
        ranked_ids = self.collection.query_by_index(
            "vector_index",
            query=query_emb,
            top_k=top_k,
            candidates=candidates
        )

        return [self.collection.get(id) for id in ranked_ids]

    def _extract_entities(self, text: str) -> List[str]:
        """实体提取（NER）"""
        # TODO: 使用 NER 模型
        return []

    def _extract_relations(self, text: str, entities: List[str]) -> List[Tuple]:
        """关系提取"""
        # TODO: 使用 RE 模型
        return []

    def _update_graph(self, data_id: str, entities: List[str], relations: List[Tuple]):
        """更新知识图谱"""
        graph_index = self.collection.indexes["knowledge_graph"]
        for entity in entities:
            graph_index.add_node(entity, {"source": data_id})
        for head, rel, tail in relations:
            graph_index.add_edge(head, tail, {"type": rel, "source": data_id})
```

______________________________________________________________________

## 🔧 Service 注册和工厂

```python
# services/registry.py

class MemoryServiceRegistry:
    """Service 注册表 - 管理所有 13 个 Service"""

    _services = {}

    @classmethod
    def register(cls, name: str, service_class: Type[BaseMemoryService]):
        """注册 Service

        Args:
            name: Service 名称（如 "partitional.fifo_queue"）
            service_class: Service 类
        """
        cls._services[name] = service_class

    @classmethod
    def create(cls, name: str, collection: UnifiedCollection,
               config: Dict) -> BaseMemoryService:
        """创建 Service 实例"""
        if name not in cls._services:
            raise ValueError(f"Unknown service: {name}")

        service_class = cls._services[name]
        return service_class(collection, config)

    @classmethod
    def list_services(cls) -> List[str]:
        """列出所有已注册 Service"""
        return list(cls._services.keys())


# 注册所有 Service
MemoryServiceRegistry.register("partitional.fifo_queue", FIFOQueueService)
MemoryServiceRegistry.register("partitional.lsh_hash", LSHHashService)
MemoryServiceRegistry.register("partitional.segment", SegmentService)
MemoryServiceRegistry.register(
    "partitional.feature_summary_vectorstore_combination",
    FeatureSummaryVectorstoreCombinationService
)
MemoryServiceRegistry.register(
    "partitional.inverted_vectorstore_combination",
    InvertedVectorstoreCombinationService
)
MemoryServiceRegistry.register(
    "hierarchical.semantic_inverted_knowledge_graph",
    SemanticInvertedKnowledgeGraphService
)
# ... 其余 7 个
```

______________________________________________________________________

## 📝 实施任务清单

### Task 2.1: 实现 BaseMemoryService (0.5天)

- [ ] 定义抽象接口（\_setup_indexes, insert, retrieve）
- [ ] 实现公共方法（delete, get, list_indexes）
- [ ] 实现工具方法（\_get_embeddings, \_summarize, \_filter_by_metadata）

### Task 2.2: 实现 9 个 Partitional Services (3天)

- [ ] FIFOQueueService
- [ ] LSHHashService
- [ ] SegmentService
- [ ] FeatureSummaryVectorstoreCombinationService
- [ ] FeatureQueueSegmentCombinationService
- [ ] FeatureQueueSummaryCombinationService
- [ ] FeatureQueueVectorstoreCombinationService
- [ ] InvertedVectorstoreCombinationService

### Task 2.3: 实现 3 个 Hierarchical Services (2天)

- [ ] SemanticInvertedKnowledgeGraphService
- [ ] LinknoteGraphService
- [ ] PropertyGraphService

### Task 2.4: 实现 Registry 和测试 (1天)

- [ ] 实现 MemoryServiceRegistry
- [ ] 单元测试（每个 Service）
- [ ] 集成测试（Service + Collection）

______________________________________________________________________

## 🧪 测试用例模板

```python
def test_service_basic_flow(service_class):
    """测试 Service 基础流程（模板）"""
    # 1. 创建 Collection
    collection = UnifiedCollection("test", {})

    # 2. 创建 Service
    config = {"embedding_dim": 768, "max_size": 10}
    service = service_class(collection, config)

    # 3. 插入数据
    id1 = service.insert("Hello World", {"source": "test"})
    assert id1 is not None

    # 4. 检索数据
    results = service.retrieve("Hello", top_k=5)
    assert len(results) > 0

    # 5. 删除数据
    assert service.delete(id1)

    # 6. 验证删除
    results = service.retrieve("Hello", top_k=5)
    assert len(results) == 0


def test_fifo_queue_service():
    """测试 FIFO Queue Service"""
    collection = UnifiedCollection("test", {})
    service = FIFOQueueService(collection, {"max_size": 3})

    # 插入 4 条（超过 max_size）
    service.insert("Text1")
    service.insert("Text2")
    service.insert("Text3")
    service.insert("Text4")  # 会淘汰 Text1

    # 检索
    results = service.retrieve("", top_k=10)
    assert len(results) == 3  # 只保留最近 3 条
    assert all(r["text"] != "Text1" for r in results)  # Text1 被淘汰
```

______________________________________________________________________

**下一步**: 阅读 `03_CONFIGURATION_MIGRATION.md` 了解配置文件迁移
