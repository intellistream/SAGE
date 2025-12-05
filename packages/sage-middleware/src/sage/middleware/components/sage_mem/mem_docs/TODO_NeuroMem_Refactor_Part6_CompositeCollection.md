# Part 6: 组合型 Collection 实现 ✅ 已完成

## 完成状态

**实现完成时间**：2024-12

**实现文件**：

- `memory_collection/hybrid_collection.py` - HybridCollection 主要实现
- `tests/test_hybrid_collection.py` - 单元测试
- `examples/memory_os_hybrid_example.py` - MemoryOS 使用示例

______________________________________________________________________

## 背景

**核心原则**：`Service : Collection = 1 : 1`

- **Service** 决定策略（如何插入、删除、检索）
- **Collection** 提供能力（数据存储 + 多索引）

______________________________________________________________________

## 关键理解

### Collection 的本质

```
Collection = 一份数据 + 多个索引
```

**VDBCollection** 可以在同一份数据上建多个 **向量索引**（不同维度/后端） **KVCollection** 可以在同一份数据上建多个 **文本索引**（BM25 等）
**GraphCollection** 可以在同一份数据上建多个 **图索引**

那么 **HybridCollection** 应该是：

> 在同一份数据上建立 **多种类型** 的索引（VDB + KV + Graph 混合）

### MemoryOS 案例分析

```
MemoryOS 的数据流：
1. 新记忆插入 → 进入 FIFO 队列（KV索引：按时间排序）
2. FIFO 满了 → Service 决定：
   - 从 FIFO 索引删除
   - 但数据保留，放入 Segment 索引（VDB索引：语义检索）
3. 检索时：
   - 最近记忆 → 查 FIFO 索引
   - 语义相关 → 查 Segment 索引
```

**关键点**：数据只有一份，索引有多个！

______________________________________________________________________

## 6.1 HybridCollection 实现 ✅

```python
class HybridCollection(BaseMemoryCollection):
    """
    混合索引 Collection

    在同一份数据上支持创建多种类型的索引：
    - VDB 索引（向量检索）
    - KV 索引（文本检索、FIFO 队列、时间排序）
    - Graph 索引（关系图）

    数据只存一份，索引可以有多个。
    """

    def __init__(self, config: dict[str, Any]):
        """
        Args:
            config:
                - name: Collection 名称
        """
        super().__init__(config)

        # 数据存储（只有一份）
        self.text_storage = TextStorage()
        self.metadata_storage = MetadataStorage()

        # 多种类型的索引
        self.vdb_indexes: dict[str, BaseVDBIndex] = {}      # 向量索引
        self.kv_indexes: dict[str, BaseKVIndex] = {}        # 文本索引
        self.graph_indexes: dict[str, BaseGraphIndex] = {}  # 图索引

        # 索引元信息
        self.index_meta: dict[str, dict] = {}  # name -> {type, config, ...}

    # ========== 索引管理 ==========

    def create_index(self, config: dict[str, Any]) -> bool:
        """
        创建索引（支持多种类型）

        Args:
            config:
                - name: 索引名称
                - type: "vdb" | "kv" | "graph"
                - 其他参数根据类型不同

                VDB 类型：
                    - dim: 向量维度
                    - backend_type: "FAISS" | "LSH" | ...

                KV 类型：
                    - index_type: "bm25s" | "fifo" | "sorted"
                    - sort_field: 排序字段（sorted 类型）
                    - capacity: 容量限制（fifo 类型）

                Graph 类型：
                    - graph_type: "simple" | "weighted"
        """
        index_name = config.get("name")
        index_type = config.get("type", "vdb").lower()

        if not index_name:
            self.logger.warning("Index name is required")
            return False

        if index_name in self.index_meta:
            self.logger.warning(f"Index '{index_name}' already exists")
            return False

        try:
            if index_type == "vdb":
                dim = config.get("dim")
                backend_type = config.get("backend_type", "FAISS")

                index = IndexFactory.create_vdb_index({
                    "name": index_name,
                    "dim": dim,
                    "backend_type": backend_type,
                    "config": config.get("index_parameter")
                })
                self.vdb_indexes[index_name] = index

            elif index_type == "kv":
                kv_type = config.get("index_type", "bm25s")

                index = IndexFactory.create_kv_index({
                    "name": index_name,
                    "index_type": kv_type,
                    "capacity": config.get("capacity"),
                    "sort_field": config.get("sort_field"),
                })
                self.kv_indexes[index_name] = index

            elif index_type == "graph":
                graph_type = config.get("graph_type", "simple")

                index = IndexFactory.create_graph_index({
                    "name": index_name,
                    "index_type": graph_type,
                })
                self.graph_indexes[index_name] = index

            else:
                self.logger.warning(f"Unknown index type: {index_type}")
                return False

            self.index_meta[index_name] = {
                "type": index_type,
                "config": config,
                "created_time": time.time()
            }

            self.logger.info(f"Created {index_type} index: {index_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create index: {e}")
            return False

    def delete_index(self, index_name: str) -> bool:
        """删除索引"""
        if index_name not in self.index_meta:
            return False

        index_type = self.index_meta[index_name]["type"]

        if index_type == "vdb":
            del self.vdb_indexes[index_name]
        elif index_type == "kv":
            del self.kv_indexes[index_name]
        elif index_type == "graph":
            del self.graph_indexes[index_name]

        del self.index_meta[index_name]
        return True

    def list_indexes(self) -> list[dict]:
        """列出所有索引"""
        return [
            {"name": name, **meta}
            for name, meta in self.index_meta.items()
        ]

    def get_index_type(self, index_name: str) -> str | None:
        """获取索引类型"""
        meta = self.index_meta.get(index_name)
        return meta["type"] if meta else None

    # ========== 数据操作 ==========

    def insert(
        self,
        content: str,
        index_name: str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
        **kwargs
    ) -> str:
        """
        插入数据

        Args:
            content: 文本内容
            index_name: 目标索引名（可选，不指定则只存数据）
            vector: 向量（VDB 索引需要）
            metadata: 元数据

        kwargs:
            - index_names: [name1, name2] 同时插入多个索引
            - vectors: {index_name: vector} 不同索引使用不同向量
            - node_id: 图索引的节点 ID
            - edges: [(target_id, weight)] 图索引的边

        Returns:
            stable_id
        """
        # 1. 存储数据
        stable_id = self._get_stable_id(content)
        self.text_storage.store(stable_id, content)

        if metadata:
            for field in metadata:
                if not self.metadata_storage.has_field(field):
                    self.metadata_storage.add_field(field)
            self.metadata_storage.store(stable_id, metadata)

        # 2. 更新索引
        index_names = kwargs.get("index_names", [index_name] if index_name else [])
        vectors = kwargs.get("vectors", {})

        for idx_name in index_names:
            if idx_name not in self.index_meta:
                self.logger.warning(f"Index '{idx_name}' not found, skipping")
                continue

            idx_type = self.index_meta[idx_name]["type"]

            if idx_type == "vdb":
                vec = vectors.get(idx_name, vector)
                if vec is not None:
                    self.vdb_indexes[idx_name].insert(vec, stable_id)

            elif idx_type == "kv":
                self.kv_indexes[idx_name].insert(content, stable_id)

            elif idx_type == "graph":
                node_id = kwargs.get("node_id", stable_id)
                self.graph_indexes[idx_name].add_node(node_id, content)

                # 处理边
                edges = kwargs.get("edges", [])
                for target_id, weight in edges:
                    self.graph_indexes[idx_name].add_edge(node_id, target_id, weight)

        return stable_id

    def insert_to_index(
        self,
        item_id: str,
        index_name: str,
        vector: np.ndarray | None = None,
        **kwargs
    ) -> bool:
        """
        将已存在的数据添加到指定索引

        用于：数据已经存在，只需要加到新索引中
        """
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found")
            return False

        if index_name not in self.index_meta:
            self.logger.warning(f"Index '{index_name}' not found")
            return False

        content = self.text_storage.get(item_id)
        idx_type = self.index_meta[index_name]["type"]

        if idx_type == "vdb":
            if vector is None:
                self.logger.warning("Vector required for VDB index")
                return False
            self.vdb_indexes[index_name].insert(vector, item_id)

        elif idx_type == "kv":
            self.kv_indexes[index_name].insert(content, item_id)

        elif idx_type == "graph":
            node_id = kwargs.get("node_id", item_id)
            self.graph_indexes[index_name].add_node(node_id, content)

        return True

    def remove_from_index(self, item_id: str, index_name: str) -> bool:
        """
        从指定索引中移除（数据保留）

        用于 MemoryOS 场景：从 FIFO 删除，但保留在 Segment 索引中
        """
        if index_name not in self.index_meta:
            return False

        idx_type = self.index_meta[index_name]["type"]

        try:
            if idx_type == "vdb":
                self.vdb_indexes[index_name].delete(item_id)
            elif idx_type == "kv":
                self.kv_indexes[index_name].delete(item_id)
            elif idx_type == "graph":
                self.graph_indexes[index_name].remove_node(item_id)
            return True
        except Exception:
            return False

    def delete(self, item_id: str) -> bool:
        """
        完全删除数据（从所有索引中移除）
        """
        if not self.text_storage.has(item_id):
            return False

        # 从所有索引删除
        for idx_name in self.vdb_indexes:
            try:
                self.vdb_indexes[idx_name].delete(item_id)
            except Exception:
                pass

        for idx_name in self.kv_indexes:
            try:
                self.kv_indexes[idx_name].delete(item_id)
            except Exception:
                pass

        for idx_name in self.graph_indexes:
            try:
                self.graph_indexes[idx_name].remove_node(item_id)
            except Exception:
                pass

        # 删除数据
        self.text_storage.delete(item_id)
        self.metadata_storage.delete(item_id)

        return True

    def retrieve(
        self,
        query: str | np.ndarray | None = None,
        index_name: str | None = None,
        top_k: int = 10,
        with_metadata: bool = False,
        **kwargs
    ) -> list[dict]:
        """
        检索

        Args:
            query: 查询（文本或向量）
            index_name: 使用的索引
            top_k: 返回数量

        kwargs:
            - threshold: 相似度阈值
            - start_node: 图遍历起点
            - max_depth: 图遍历深度
        """
        if index_name is None or index_name not in self.index_meta:
            self.logger.warning(f"Index '{index_name}' not found")
            return []

        idx_type = self.index_meta[index_name]["type"]
        result_ids = []
        scores = []

        if idx_type == "vdb":
            if not isinstance(query, np.ndarray):
                self.logger.warning("VDB index requires vector query")
                return []

            threshold = kwargs.get("threshold")
            result_ids, scores = self.vdb_indexes[index_name].search(
                query, topk=top_k, threshold=threshold
            )

        elif idx_type == "kv":
            if not isinstance(query, str):
                self.logger.warning("KV index requires text query")
                return []

            result_ids = self.kv_indexes[index_name].search(query, topk=top_k)
            scores = [1.0] * len(result_ids)  # KV 索引可能没有分数

        elif idx_type == "graph":
            start_node = kwargs.get("start_node")
            max_depth = kwargs.get("max_depth", 2)

            if start_node:
                result_ids = self.graph_indexes[index_name].traverse_bfs(
                    start_node, max_depth=max_depth, max_nodes=top_k
                )
            else:
                # 如果没有起点，返回空
                result_ids = []
            scores = [1.0] * len(result_ids)

        # 组装结果
        results = []
        for i, item_id in enumerate(result_ids):
            item = {
                "id": item_id,
                "text": self.text_storage.get(item_id),
                "score": scores[i] if i < len(scores) else 0.0,
            }
            if with_metadata:
                item["metadata"] = self.metadata_storage.get(item_id)
            results.append(item)

        return results

    def retrieve_multi(
        self,
        queries: dict[str, Any],
        top_k: int = 10,
        fusion_strategy: str = "rrf",
        **kwargs
    ) -> list[dict]:
        """
        多索引检索 + 融合

        Args:
            queries: {index_name: query} 每个索引的查询
            top_k: 最终返回数量
            fusion_strategy: "rrf" | "weighted" | "union"
        """
        all_results: dict[str, list[dict]] = {}

        for index_name, query in queries.items():
            results = self.retrieve(
                query=query,
                index_name=index_name,
                top_k=top_k * 2,  # 多取一些用于融合
                with_metadata=True
            )
            all_results[index_name] = results

        # 融合
        if fusion_strategy == "rrf":
            return self._rrf_fusion(all_results, top_k, kwargs.get("rrf_k", 60))
        elif fusion_strategy == "weighted":
            weights = kwargs.get("weights", {})
            return self._weighted_fusion(all_results, top_k, weights)
        else:  # union
            return self._union_fusion(all_results, top_k)

    def _rrf_fusion(self, results_by_index, top_k, rrf_k=60):
        """RRF 融合"""
        from collections import defaultdict

        scores = defaultdict(float)
        item_map = {}

        for results in results_by_index.values():
            for rank, item in enumerate(results):
                item_id = item["id"]
                scores[item_id] += 1.0 / (rrf_k + rank + 1)
                item_map[item_id] = item

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            {**item_map[id_], "fused_score": scores[id_]}
            for id_ in sorted_ids[:top_k]
        ]

    # ========== 索引特有操作 ==========

    def get_fifo_items(self, index_name: str, count: int) -> list[str]:
        """
        获取 FIFO 队列中最旧的 N 个元素

        用于 MemoryOS：获取要淘汰的元素
        """
        if index_name not in self.kv_indexes:
            return []

        # 假设 KV 索引支持按插入顺序获取
        # 需要在 BaseKVIndex 中添加此方法
        index = self.kv_indexes[index_name]
        if hasattr(index, "get_oldest"):
            return index.get_oldest(count)
        return []

    def get_index_count(self, index_name: str) -> int:
        """获取索引中的元素数量"""
        if index_name not in self.index_meta:
            return 0

        idx_type = self.index_meta[index_name]["type"]

        if idx_type == "vdb" and index_name in self.vdb_indexes:
            return self.vdb_indexes[index_name].count() if hasattr(
                self.vdb_indexes[index_name], "count"
            ) else 0
        elif idx_type == "kv" and index_name in self.kv_indexes:
            return self.kv_indexes[index_name].count() if hasattr(
                self.kv_indexes[index_name], "count"
            ) else 0
        elif idx_type == "graph" and index_name in self.graph_indexes:
            return self.graph_indexes[index_name].node_count() if hasattr(
                self.graph_indexes[index_name], "node_count"
            ) else 0

        return 0
```

______________________________________________________________________

## 6.2 MemoryOS 使用示例

```python
class MemoryOSService(BaseService):
    """MemoryOS 风格的记忆服务"""

    def __init__(self, stm_capacity=10, mtm_capacity=100):
        super().__init__()

        # 只持有一个 HybridCollection
        self.collection = HybridCollection({"name": "memory_os"})

        # 创建索引
        # STM: FIFO 队列
        self.collection.create_index({
            "name": "stm_fifo",
            "type": "kv",
            "index_type": "fifo",
            "capacity": stm_capacity
        })

        # MTM: 向量检索（按 segment 分组）
        self.collection.create_index({
            "name": "mtm_segment",
            "type": "vdb",
            "dim": 768,
            "backend_type": "FAISS"
        })

        # LTM: 向量检索（长期存储）
        self.collection.create_index({
            "name": "ltm_archive",
            "type": "vdb",
            "dim": 768,
            "backend_type": "FAISS"
        })

        self.stm_capacity = stm_capacity

    def insert(self, entry, vector, metadata=None, **kwargs):
        """插入记忆"""

        # 1. 存数据 + 插入 STM FIFO
        item_id = self.collection.insert(
            content=entry,
            index_name="stm_fifo",
            metadata={
                **(metadata or {}),
                "insert_time": time.time(),
                "tier": "stm"
            }
        )

        # 2. 检查 FIFO 是否溢出
        fifo_count = self.collection.get_index_count("stm_fifo")

        if fifo_count > self.stm_capacity:
            # 获取最旧的元素
            old_ids = self.collection.get_fifo_items("stm_fifo", count=1)

            for old_id in old_ids:
                # Service 决定：迁移到 MTM
                self._migrate_to_mtm(old_id, vector)

        return item_id

    def _migrate_to_mtm(self, item_id, vector):
        """从 STM 迁移到 MTM"""

        # 从 FIFO 索引移除（数据保留）
        self.collection.remove_from_index(item_id, "stm_fifo")

        # 添加到 MTM 向量索引
        self.collection.insert_to_index(item_id, "mtm_segment", vector=vector)

        # 更新 metadata
        meta = self.collection.metadata_storage.get(item_id)
        meta["tier"] = "mtm"
        meta["migrate_time"] = time.time()
        self.collection.metadata_storage.store(item_id, meta)

    def retrieve(self, query, vector, top_k=10, **kwargs):
        """检索记忆"""

        # 策略：先查 STM，不够再查 MTM
        results = []

        # 1. 从 STM 获取最近记忆
        stm_results = self.collection.retrieve(
            query=query,
            index_name="stm_fifo",
            top_k=top_k
        )
        results.extend(stm_results)

        # 2. 如果不够，从 MTM 语义检索
        if len(results) < top_k and vector is not None:
            mtm_results = self.collection.retrieve(
                query=vector,
                index_name="mtm_segment",
                top_k=top_k - len(results)
            )
            results.extend(mtm_results)

        return results[:top_k]
```

______________________________________________________________________

## 6.3 HierarchicalCollection 简化

按照同样的思路，HierarchicalCollection 也可以简化：

```python
class HierarchicalCollection(HybridCollection):
    """
    分层记忆 Collection

    本质上是 HybridCollection 的特化版本，
    预定义了多个同类型的索引用于分层。
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)

        tier_mode = config.get("tier_mode", "three_tier")
        embedding_dim = config.get("embedding_dim", 768)

        # 确定层级
        if tier_mode == "two_tier":
            self.tier_names = ["stm", "ltm"]
        elif tier_mode == "three_tier":
            self.tier_names = ["stm", "mtm", "ltm"]
        else:
            self.tier_names = ["episodic", "semantic", "procedural"]

        # 为每层创建 VDB 索引
        for tier in self.tier_names:
            self.create_index({
                "name": f"{tier}_index",
                "type": "vdb",
                "dim": embedding_dim,
                "backend_type": "FAISS"
            })

        # 容量配置
        self.tier_capacities = config.get("tier_capacities", {
            "stm": 10, "mtm": 100, "ltm": -1
        })

    def insert_to_tier(self, content, vector, tier, metadata=None):
        """插入到指定层"""
        return self.insert(
            content=content,
            index_name=f"{tier}_index",
            vector=vector,
            metadata={**(metadata or {}), "tier": tier}
        )

    def migrate(self, item_id, from_tier, to_tier, vector):
        """层间迁移"""
        self.remove_from_index(item_id, f"{from_tier}_index")
        self.insert_to_index(item_id, f"{to_tier}_index", vector=vector)

        # 更新 metadata
        meta = self.metadata_storage.get(item_id)
        meta["tier"] = to_tier
        meta["migrated_from"] = from_tier
        self.metadata_storage.store(item_id, meta)
```

______________________________________________________________________

## 关键变化总结

| 之前的设计                                 | 现在的设计                                    |
| ------------------------------------------ | --------------------------------------------- |
| HybridCollection 内部持有多个子 Collection | HybridCollection 在一份数据上建多种类型的索引 |
| 数据存多份（每个子 Collection 一份）       | 数据只存一份                                  |
| 需要同步多个 Collection                    | 只需管理索引的增删                            |

**核心方法**：

- `insert_to_index(item_id, index_name)` - 将已有数据加到索引
- `remove_from_index(item_id, index_name)` - 从索引移除（数据保留）
- `delete(item_id)` - 完全删除（数据 + 所有索引）

______________________________________________________________________

## 依赖关系

- 依赖 Part 1（Collection 基础接口）
- 依赖 Part 2（IndexFactory 统一创建各类索引）

______________________________________________________________________

## 预估工时

| 子任务                          | 预估时间 |
| ------------------------------- | -------- |
| 6.1 HybridCollection 实现       | 8h       |
| 6.2 MemoryOS 示例验证           | 2h       |
| 6.3 HierarchicalCollection 简化 | 3h       |
| Service 层适配                  | 3h       |
| 测试 & 验证                     | 2h       |
| **总计**                        | **18h**  |

______________________________________________________________________

## 参考资料

- 当前 HierarchicalMemoryService（已重构）
- 当前 HybridMemoryService（已重构）
- MemoryOS 论文中的 FIFO + Segment 设计
