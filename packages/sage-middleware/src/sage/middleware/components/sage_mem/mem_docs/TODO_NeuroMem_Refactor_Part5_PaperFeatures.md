# TODO Part 5: 论文特性支持

## 状态: ✅ 已完成 (2024-12)

## 背景

根据论文特性映射，NeuroMem 需要支持以下关键特性：

| 论文       | 核心特性          | NeuroMem 支持状态  |
| ---------- | ----------------- | ------------------ |
| TiM        | 三元组存储 + 蒸馏 | ✅ 已实现          |
| HippoRAG   | 知识图谱 + PPR    | ✅ 已实现 (Part 2) |
| A-Mem      | 链接演化          | ✅ 已实现          |
| MemoryBank | Ebbinghaus 遗忘   | ✅ 已实现          |
| MemoryOS   | Heat Score 迁移   | ✅ 已实现          |
| SCM        | Token Budget      | ✅ 已实现          |
| Mem0       | 冲突检测          | ✅ 已实现          |

## 实现概要

所有论文特性通过 **Mixin 模式** 实现，保持现有 Collection 接口不变：

### 文件结构

```
memory_collection/
├── paper_features.py       # 核心特性工具类 (新增)
├── enhanced_collections.py # 增强版 Collection (新增)
├── __init__.py            # 更新导出
└── ...
```

### 使用方式

**方式 1: 使用增强版 Collection（推荐）**

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    VDBMemoryCollectionWithFeatures,
    GraphMemoryCollectionWithFeatures,
)

# 创建增强版 VDB Collection - 包含所有论文特性
collection = VDBMemoryCollectionWithFeatures({"name": "my_collection"})

# 三元组存储 (TiM)
collection.insert_triple(query, passage, answer, vector)

# 冲突检测 (Mem0)
result = collection.insert_with_conflict_check(content, vector, index_name)

# Token 预算检索 (SCM)
results = collection.retrieve_with_budget(query_vector, index_name, token_budget=2000)

# 遗忘曲线 (MemoryBank)
collection.update_access(item_id)
forgotten_ids = collection.apply_forgetting()
```

**方式 2: 单独使用工具类**

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    EbbinghausForgetting,
    HeatScoreManager,
    TokenBudgetFilter,
    ConflictDetector,
)

# 遗忘曲线计算
forgetting = EbbinghausForgetting()
strength = forgetting.calculate_strength(last_access_time, access_count)

# 热度计算
heat_mgr = HeatScoreManager()
heat = heat_mgr.calculate_heat(access_count, last_access_time, creation_time)
action = heat_mgr.get_migration_action(heat)  # "promote", "demote", or None

# Token 预算过滤
budget_filter = TokenBudgetFilter()
filtered = budget_filter.filter_by_budget(items, budget=2000)

# 冲突检测
detector = ConflictDetector()
result = detector.detect(new_fact, existing_facts)
```

______________________________________________________________________

## 5.1 三元组存储（TiM）

**需求**：存储 (query, passage, answer) 三元组，支持按 query 检索

**实现位置**：`VDBMemoryCollection` 扩展

**方案**：

```python
class VDBMemoryCollection(BaseMemoryCollection):

    def insert_triple(
        self,
        query: str,
        passage: str,
        answer: str,
        vector: np.ndarray,
        metadata: dict | None = None
    ) -> str:
        """
        插入三元组

        存储结构：
        - text_storage: 存储完整三元组 JSON
        - metadata: 包含 query, passage, answer 的哈希
        - 向量索引: 基于 passage 的 embedding
        """
        triple_data = {
            "query": query,
            "passage": passage,
            "answer": answer
        }
        content = json.dumps(triple_data, ensure_ascii=False)

        extended_metadata = {
            **(metadata or {}),
            "type": "triple",
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
            "passage_hash": hashlib.md5(passage.encode()).hexdigest()[:8],
        }

        return self.insert(
            content=content,
            index_name="triple_index",
            vector=vector,
            metadata=extended_metadata
        )

    def retrieve_by_query(
        self,
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> list[dict]:
        """
        检索相似三元组

        Returns:
            [{"query": ..., "passage": ..., "answer": ..., "score": ...}, ...]
        """
        results = self.retrieve(
            query=query_vector,
            index_name="triple_index",
            top_k=top_k,
            with_metadata=True,
            metadata_filter=lambda m: m.get("type") == "triple"
        )

        # 解析三元组
        parsed = []
        for r in results:
            try:
                triple = json.loads(r["text"])
                triple["score"] = r.get("score", 0)
                parsed.append(triple)
            except json.JSONDecodeError:
                continue

        return parsed
```

**验收标准**：

- [ ] `insert_triple()` 方法实现
- [ ] `retrieve_by_query()` 方法实现
- [ ] 单元测试通过

______________________________________________________________________

## 5.2 链接演化（A-Mem）

**需求**：根据相似度动态更新节点间的链接权重

**实现位置**：`GraphMemoryCollection` + `SimpleGraphIndex`

**方案**：

```python
class GraphMemoryCollection(BaseMemoryCollection):

    def evolve_links(
        self,
        node_id: str,
        similarity_threshold: float = 0.7,
        decay_factor: float = 0.95,
        index_name: str = "default"
    ) -> int:
        """
        链接演化：
        1. 衰减现有链接权重
        2. 基于相似度添加/加强新链接

        Returns:
            更新的边数量
        """
        if index_name not in self.indexes:
            return 0

        graph_index = self.indexes[index_name]
        updated_count = 0

        # 1. 获取节点向量
        node_vector = self._get_node_vector(node_id)
        if node_vector is None:
            return 0

        # 2. 找相似节点
        similar_nodes = self._find_similar_nodes(node_vector, top_k=20)

        # 3. 衰减现有边
        current_neighbors = graph_index.get_neighbors(node_id, k=100)
        for neighbor_id, weight in current_neighbors:
            new_weight = weight * decay_factor
            if new_weight < 0.1:
                graph_index.remove_edge(node_id, neighbor_id)
            else:
                graph_index.update_edge_weight(node_id, neighbor_id, new_weight)
            updated_count += 1

        # 4. 添加/加强新边
        for neighbor_id, similarity in similar_nodes:
            if neighbor_id == node_id:
                continue
            if similarity < similarity_threshold:
                continue

            if graph_index.has_edge(node_id, neighbor_id):
                # 加强现有边
                current_weight = self._get_edge_weight(node_id, neighbor_id)
                new_weight = min(current_weight + similarity * 0.2, 2.0)
                graph_index.update_edge_weight(node_id, neighbor_id, new_weight)
            else:
                # 添加新边
                graph_index.add_edge(node_id, neighbor_id, similarity)

            updated_count += 1

        return updated_count

    def batch_evolve(
        self,
        decay_factor: float = 0.95,
        similarity_threshold: float = 0.7
    ) -> int:
        """批量演化所有节点"""
        total_updated = 0
        for node_id in self.text_storage.get_all_ids():
            total_updated += self.evolve_links(
                node_id,
                similarity_threshold,
                decay_factor
            )
        return total_updated
```

**验收标准**：

- [ ] `evolve_links()` 方法实现
- [ ] 边权重正确衰减和加强
- [ ] 批量演化正常工作

______________________________________________________________________

## 5.3 Ebbinghaus 遗忘曲线（MemoryBank）

**需求**：基于访问时间和次数计算记忆强度，低于阈值的记忆被遗忘

**实现位置**：作为 Collection 的可选 Mixin 或工具类

**方案**：

```python
class EbbinghausForgetting:
    """遗忘曲线计算器"""

    def __init__(
        self,
        strength_threshold: float = 0.3,
        base_decay: float = 0.8,
        reinforcement_factor: float = 0.2
    ):
        self.strength_threshold = strength_threshold
        self.base_decay = base_decay
        self.reinforcement_factor = reinforcement_factor

    def calculate_strength(
        self,
        last_access_time: float,
        access_count: int,
        current_time: float | None = None
    ) -> float:
        """
        计算记忆强度

        公式: S = S0 * e^(-λt) + reinforcement * access_count
        """
        import math

        current_time = current_time or time.time()
        elapsed_hours = (current_time - last_access_time) / 3600

        # 基础衰减
        base_strength = self.base_decay * math.exp(-0.1 * elapsed_hours)

        # 访问加成
        reinforcement = self.reinforcement_factor * math.log(access_count + 1)

        return min(base_strength + reinforcement, 1.0)

    def should_forget(self, metadata: dict) -> bool:
        """判断是否应该遗忘"""
        last_access = metadata.get("last_access_time", 0)
        access_count = metadata.get("access_count", 0)

        strength = self.calculate_strength(last_access, access_count)
        return strength < self.strength_threshold


class VDBMemoryCollection(BaseMemoryCollection):

    def apply_forgetting(
        self,
        forgetting: EbbinghausForgetting,
        index_name: str
    ) -> list[str]:
        """
        应用遗忘曲线，删除低强度记忆

        Returns:
            被删除的 ID 列表
        """
        forgotten_ids = []

        for item_id in self.get_all_ids():
            metadata = self.metadata_storage.get(item_id)
            if forgetting.should_forget(metadata):
                self.delete(item_id)
                forgotten_ids.append(item_id)

        return forgotten_ids

    def update_access(self, item_id: str):
        """更新访问时间和次数"""
        metadata = self.metadata_storage.get(item_id)
        metadata["last_access_time"] = time.time()
        metadata["access_count"] = metadata.get("access_count", 0) + 1
        self.metadata_storage.store(item_id, metadata)
```

**验收标准**：

- [ ] 遗忘曲线计算正确
- [ ] `apply_forgetting()` 正确删除记忆
- [ ] 访问更新正常工作

______________________________________________________________________

## 5.4 Heat Score 迁移（MemoryOS）

**需求**：基于热度分数在层级间迁移记忆

**实现位置**：`HierarchicalMemoryService` 扩展

**方案**：

```python
class HeatScoreManager:
    """热度分数管理器"""

    def __init__(
        self,
        cold_threshold: float = 0.3,
        hot_threshold: float = 0.8,
        decay_rate: float = 0.05
    ):
        self.cold_threshold = cold_threshold
        self.hot_threshold = hot_threshold
        self.decay_rate = decay_rate

    def calculate_heat(
        self,
        access_count: int,
        last_access_time: float,
        creation_time: float,
        current_time: float | None = None
    ) -> float:
        """
        计算热度分数

        考虑因素：
        - 访问频率
        - 最近访问时间
        - 存活时间
        """
        import math

        current_time = current_time or time.time()

        # 访问频率贡献
        age_hours = (current_time - creation_time) / 3600 + 1
        frequency = access_count / age_hours
        freq_score = min(frequency / 10, 0.5)  # 最多贡献 0.5

        # 时间衰减
        hours_since_access = (current_time - last_access_time) / 3600
        recency_score = 0.5 * math.exp(-self.decay_rate * hours_since_access)

        return freq_score + recency_score

    def get_migration_action(self, heat: float) -> str | None:
        """返回迁移动作"""
        if heat < self.cold_threshold:
            return "demote"  # 降级
        elif heat > self.hot_threshold:
            return "promote"  # 升级
        return None  # 保持


# 在 HierarchicalMemoryService 中使用
class HierarchicalMemoryService(BaseService):

    def apply_heat_migration(self) -> dict[str, int]:
        """
        根据热度执行迁移

        Returns:
            {"promoted": n, "demoted": n}
        """
        heat_manager = HeatScoreManager()
        promoted = 0
        demoted = 0

        for tier_idx, tier_name in enumerate(self.tier_names):
            collection = self.tier_collections[tier_name]

            for item_id in collection.get_all_ids():
                metadata = collection.metadata_storage.get(item_id)

                heat = heat_manager.calculate_heat(
                    access_count=metadata.get("access_count", 0),
                    last_access_time=metadata.get("last_access_time", 0),
                    creation_time=metadata.get("creation_time", 0)
                )

                action = heat_manager.get_migration_action(heat)

                if action == "promote" and tier_idx > 0:
                    # 升级到上一层
                    target_tier = self.tier_names[tier_idx - 1]
                    self._migrate(tier_name, target_tier, item_id)
                    promoted += 1

                elif action == "demote" and tier_idx < len(self.tier_names) - 1:
                    # 降级到下一层
                    target_tier = self.tier_names[tier_idx + 1]
                    self._migrate(tier_name, target_tier, item_id)
                    demoted += 1

        return {"promoted": promoted, "demoted": demoted}
```

**验收标准**：

- [ ] 热度计算正确
- [ ] 升降级逻辑正确
- [ ] 迁移不丢数据

______________________________________________________________________

## 5.5 Token Budget 压缩（SCM）

**需求**：控制返回的记忆在 token 预算内

**实现位置**：Collection `retrieve()` 的后处理

**方案**：

```python
class TokenBudgetFilter:
    """Token 预算过滤器"""

    def __init__(self, tokenizer=None):
        # 可以使用 tiktoken 或简单的词数估算
        self.tokenizer = tokenizer

    def count_tokens(self, text: str) -> int:
        """计算 token 数"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # 简单估算：每 4 个字符约 1 token
            return len(text) // 4

    def filter_by_budget(
        self,
        items: list[dict],
        budget: int,
        text_key: str = "text"
    ) -> list[dict]:
        """
        过滤结果使总 token 不超过预算

        假设 items 已按重要性排序
        """
        result = []
        used_tokens = 0

        for item in items:
            text = item.get(text_key, "")
            tokens = self.count_tokens(text)

            if used_tokens + tokens > budget:
                break

            result.append(item)
            used_tokens += tokens

        return result


class VDBMemoryCollection(BaseMemoryCollection):

    def retrieve_with_budget(
        self,
        query: np.ndarray,
        index_name: str,
        token_budget: int = 2000,
        max_candidates: int = 50
    ) -> list[dict]:
        """
        带 token 预算的检索
        """
        # 先取足够多的候选
        candidates = self.retrieve(
            query=query,
            index_name=index_name,
            top_k=max_candidates,
            with_metadata=True
        )

        # 按预算过滤
        filter_ = TokenBudgetFilter()
        return filter_.filter_by_budget(candidates, token_budget)
```

**验收标准**：

- [ ] Token 计算准确
- [ ] 不超过预算
- [ ] 按重要性优先

______________________________________________________________________

## 5.6 冲突检测（Mem0）

**需求**：检测新插入的事实是否与已有事实冲突

**实现位置**：Collection 的 `insert()` 扩展

**方案**：

```python
class ConflictDetector:
    """事实冲突检测器"""

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold

    def extract_entity_attribute(self, text: str) -> tuple[str, str] | None:
        """
        提取 (实体, 属性) 对

        简单实现：使用正则或 LLM 提取
        """
        # 简化实现：假设格式 "Entity's attribute is value"
        import re
        match = re.match(r"(.+?)'s\s+(.+?)\s+is\s+(.+)", text, re.IGNORECASE)
        if match:
            return (match.group(1).strip(), match.group(2).strip())
        return None

    def detect(
        self,
        new_fact: str,
        existing_facts: list[dict],
        similarity_func=None
    ) -> dict | None:
        """
        检测冲突

        Returns:
            冲突的已有事实，或 None
        """
        new_ea = self.extract_entity_attribute(new_fact)
        if not new_ea:
            return None

        for fact in existing_facts:
            existing_ea = self.extract_entity_attribute(fact["text"])
            if not existing_ea:
                continue

            # 相同实体+属性 = 潜在冲突
            if new_ea == existing_ea:
                return fact

            # 或者基于相似度判断
            if similarity_func:
                sim = similarity_func(new_fact, fact["text"])
                if sim > self.similarity_threshold:
                    return fact

        return None


class VDBMemoryCollection(BaseMemoryCollection):

    def insert_with_conflict_check(
        self,
        content: str,
        vector: np.ndarray,
        index_name: str,
        resolution: str = "skip",  # "skip" | "replace" | "append"
        metadata: dict | None = None
    ) -> dict:
        """
        带冲突检测的插入

        Returns:
            {
                "id": str | None,
                "action": "inserted" | "skipped" | "replaced",
                "conflict": dict | None
            }
        """
        detector = ConflictDetector()

        # 检索相似记忆
        similar = self.retrieve(
            query=vector,
            index_name=index_name,
            top_k=10,
            with_metadata=True
        )

        # 检测冲突
        conflict = detector.detect(content, similar)

        if conflict:
            if resolution == "skip":
                return {
                    "id": None,
                    "action": "skipped",
                    "conflict": conflict
                }
            elif resolution == "replace":
                # 删除旧的
                self.delete(conflict["id"])
                # 插入新的
                new_id = self.insert(
                    content=content,
                    index_name=index_name,
                    vector=vector,
                    metadata=metadata
                )
                return {
                    "id": new_id,
                    "action": "replaced",
                    "conflict": conflict
                }

        # 无冲突，正常插入
        new_id = self.insert(
            content=content,
            index_name=index_name,
            vector=vector,
            metadata=metadata
        )
        return {
            "id": new_id,
            "action": "inserted",
            "conflict": None
        }
```

**验收标准**：

- [ ] 实体属性提取正确
- [ ] 冲突检测正确
- [ ] 三种解决策略都工作

______________________________________________________________________

## 依赖关系

- 依赖 Part 1-4 全部完成
- 可以并行开发各特性

______________________________________________________________________

## 预估工时

| 子任务              | 预估时间 |
| ------------------- | -------- |
| 5.1 三元组存储      | 3h       |
| 5.2 链接演化        | 4h       |
| 5.3 Ebbinghaus 遗忘 | 3h       |
| 5.4 Heat Score 迁移 | 3h       |
| 5.5 Token Budget    | 2h       |
| 5.6 冲突检测        | 4h       |
| 测试 & 验证         | 3h       |
| **总计**            | **22h**  |

______________________________________________________________________

## 参考资料

- 各论文原文
- 开发档案中的论文特性映射矩阵
