# R5: PostRetrieval 算子重构

> 任务编号: R-POST-RETRIEVAL\
> 优先级: 中\
> 依赖: R1（服务接口统一后可开始）\
> 预计工时: 3-4 小时

## 一、任务目标

1. 只保留大类操作方法（action 级别），小类方法内联
1. 允许多次查询记忆服务以拼接完整 prompt
1. 确保不自己计算 embedding（由服务完成）

## 二、涉及文件

```
packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_retrieval.py
```

## 三、当前问题分析

### 3.1 小类方法过多

当前 PostRetrieval 有大量小类方法：

```python
# rerank 类下的小类方法（应内联）
def _rerank_semantic(...)
def _rerank_time_weighted(...)
def _rerank_ppr_placeholder(...)
def _rerank_weighted(...)
def _rerank_cross_encoder_placeholder(...)

# filter 类下的小类方法（应内联）
def _filter_token_budget(...)
def _filter_threshold(...)
def _filter_top_k(...)
def _filter_llm_placeholder(...)

# merge 类下的小类方法（应内联）
def _merge_by_link_expand(...)
def _merge_by_multi_query(...)

# augment 类下的小类方法（应内联）
def _augment_reflection_placeholder(...)
def _augment_context(...)
```

### 3.2 架构约束

PostRetrieval 的职责边界：

- ✅ 允许多次查询记忆服务
- ❌ 不自己计算 embedding
- ❌ 不从 data 读取多个记忆源

## 四、重构方案

### 4.1 只保留大类方法

重构后的类结构：

```python
class PostRetrieval(MapFunction):
    """记忆检索后的后处理算子

    职责：
    - 检索结果后处理
    - 允许多次查询记忆服务
    - 构建最终 history_text
    """

    # ==================== 公共方法 ====================
    def __init__(self, config): ...
    def execute(self, data: dict[str, Any]) -> dict[str, Any]: ...

    # ==================== 大类操作方法 ====================
    def _execute_none(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def _execute_rerank(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def _execute_filter(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def _execute_merge(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def _execute_augment(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def _execute_compress(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def _execute_format(self, data: dict[str, Any]) -> dict[str, Any]: ...

    # ==================== 通用辅助方法 ====================
    def _convert_to_memory_items(self, memory_data: list[dict]) -> list[MemoryItem]: ...
    def _convert_from_memory_items(self, items: list[MemoryItem]) -> list[dict]: ...
    def _format_dialog_history(self, data: dict[str, Any]) -> dict[str, Any]: ...
```

### 4.2 execute 方法重构

```python
def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    """执行后处理

    Args:
        data: 由 MemoryRetrieval 输出的数据，包含 memory_data

    Returns:
        处理后的数据，包含 history_text
    """
    action_handlers = {
        "none": self._execute_none,
        "rerank": self._execute_rerank,
        "filter": self._execute_filter,
        "merge": self._execute_merge,
        "augment": self._execute_augment,
        "compress": self._execute_compress,
        "format": self._execute_format,
    }

    handler = action_handlers.get(self.action)
    if handler:
        data = handler(data)
    else:
        print(f"[WARNING] Unknown action: {self.action}, using default format")
        data = self._execute_none(data)

    # 最终格式化（如果还没有 history_text）
    if "history_text" not in data:
        data = self._format_dialog_history(data)

    return data
```

### 4.3 rerank action 内联示例

```python
def _execute_rerank(self, data: dict[str, Any]) -> dict[str, Any]:
    """执行结果重排序（rerank action）

    支持的 rerank_type:
    - semantic: 语义相似度重排
    - time_weighted: 时间衰减重排
    - ppr: Personalized PageRank
    - weighted: 多因子加权
    - cross_encoder: 交叉编码器重排
    """
    memory_data = data.get("memory_data", [])
    if not memory_data:
        return data

    items = self._convert_to_memory_items(memory_data)
    rerank_type = self.rerank_type

    # 根据 rerank_type 内联处理逻辑
    scored_items: list[tuple[MemoryItem, float]] = []

    if rerank_type == "semantic":
        # ---- semantic 重排内联 ----
        query = data.get("question", "")
        query_embedding = data.get("query_embedding")

        if query_embedding is None:
            # 注意：不自己计算 embedding，跳过语义重排
            scored_items = [(item, item.score or 0.5) for item in items]
        else:
            # 使用已有的 query_embedding 计算相似度
            for item in items:
                item_embedding = item.metadata.get("embedding")
                if item_embedding is not None:
                    # 余弦相似度
                    import numpy as np
                    q_vec = np.array(query_embedding)
                    i_vec = np.array(item_embedding)
                    score = float(np.dot(q_vec, i_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(i_vec) + 1e-8))
                else:
                    score = item.score or 0.5
                scored_items.append((item, score))

    elif rerank_type == "time_weighted":
        # ---- time_weighted 重排内联 ----
        now = datetime.now(UTC)
        decay_rate = self.time_decay_rate
        time_field = self.time_field

        for item in items:
            ts = item.get_timestamp(time_field)
            if ts:
                age_hours = (now - ts).total_seconds() / 3600
                time_score = math.exp(-decay_rate * age_hours)
            else:
                time_score = 0.5

            base_score = item.score or 0.5
            final_score = base_score * time_score
            scored_items.append((item, final_score))

    elif rerank_type == "ppr":
        # ---- ppr 重排内联（占位实现）----
        # PPR 需要图结构，这里使用简单近似
        scored_items = [(item, item.score or 0.5) for item in items]

    elif rerank_type == "weighted":
        # ---- weighted 重排内联 ----
        factors = self.weighted_factors

        for item in items:
            total_score = 0.0
            total_weight = 0.0

            for factor in factors:
                field = factor.get("field", "score")
                weight = factor.get("weight", 1.0)
                default = factor.get("default", 0.5)

                if field == "score":
                    value = item.score or default
                elif field == "recency":
                    ts = item.get_timestamp(self.time_field)
                    if ts:
                        age_hours = (datetime.now(UTC) - ts).total_seconds() / 3600
                        value = math.exp(-0.1 * age_hours)
                    else:
                        value = default
                else:
                    value = item.metadata.get(field, default)

                total_score += weight * value
                total_weight += weight

            final_score = total_score / total_weight if total_weight > 0 else 0.5
            scored_items.append((item, final_score))

    elif rerank_type == "cross_encoder":
        # ---- cross_encoder 重排内联（占位实现）----
        # 需要加载 cross-encoder 模型，这里使用原始分数
        scored_items = [(item, item.score or 0.5) for item in items]

    # 排序
    scored_items.sort(key=lambda x: x[1], reverse=True)

    # 应用 top_k
    if self.rerank_top_k:
        scored_items = scored_items[:self.rerank_top_k]

    # 更新分数并转换回字典格式
    result_items = []
    for item, score in scored_items:
        item.score = score
        item.metadata[self.rerank_score_field] = score
        result_items.append(item)

    data["memory_data"] = self._convert_from_memory_items(result_items)
    return data
```

### 4.4 merge action 内联示例

```python
def _execute_merge(self, data: dict[str, Any]) -> dict[str, Any]:
    """执行结果合并（merge action）

    通过多次查询服务实现合并，而非从 data 读取多源

    支持的 merge_type:
    - link_expand: 基于链接扩展
    - multi_query: 多次查询合并
    """
    memory_data = data.get("memory_data", [])
    items = self._convert_to_memory_items(memory_data)
    merge_type = self.merge_type

    if merge_type == "link_expand":
        # ---- link_expand 内联 ----
        expand_top_n = self.expand_top_n
        max_depth = self.max_depth

        # 从初始结果中获取要扩展的条目
        entries_to_expand = items[:expand_top_n]
        expanded_ids = {item.metadata.get("entry_id") for item in items if item.metadata.get("entry_id")}

        for depth in range(max_depth):
            if not entries_to_expand:
                break

            new_entries = []
            for item in entries_to_expand:
                # 调用服务获取关联记忆
                entry_id = item.metadata.get("entry_id", "")
                if not entry_id:
                    continue

                related = self.call_service(
                    self.service_name,
                    query=entry_id,  # 使用 entry_id 作为查询
                    metadata={"method": "neighbors", "max_depth": 1},
                    top_k=5,
                    method="retrieve",
                    timeout=5.0,
                )

                if related:
                    for r in related:
                        r_id = r.get("entry_id", r.get("node_id", ""))
                        if r_id and r_id not in expanded_ids:
                            expanded_ids.add(r_id)
                            new_item = MemoryItem(
                                text=r.get("text", ""),
                                score=r.get("score", 0.3),
                                metadata=r.get("metadata", {}),
                                original_index=len(items) + len(new_entries),
                            )
                            new_entries.append(new_item)
                            items.append(new_item)

            entries_to_expand = new_entries

        data["memory_data"] = self._convert_from_memory_items(items)

    elif merge_type == "multi_query":
        # ---- multi_query 内联 ----
        secondary_queries = self.secondary_queries
        original_items = set(item.metadata.get("entry_id", id(item)) for item in items)

        for sq in secondary_queries:
            query_text = sq.get("query", "")
            if not query_text:
                continue

            # 替换模板变量
            original_question = data.get("question", "")
            query_text = query_text.replace("{question}", original_question)

            results = self.call_service(
                self.service_name,
                query=query_text,
                top_k=sq.get("top_k", 5),
                method="retrieve",
                timeout=5.0,
            )

            if results:
                for r in results:
                    r_id = r.get("entry_id", "")
                    if r_id not in original_items:
                        original_items.add(r_id)
                        new_item = MemoryItem(
                            text=r.get("text", ""),
                            score=r.get("score", 0.3),
                            metadata=r.get("metadata", {}),
                            original_index=len(items),
                        )
                        items.append(new_item)

        data["memory_data"] = self._convert_from_memory_items(items)

    return data
```

## 五、重构步骤

### 步骤 1：备份原文件

```bash
cp post_retrieval.py post_retrieval.py.bak
```

### 步骤 2：删除小类方法，内联到大类方法

1. 将 `_rerank_*` 逻辑内联到 `_execute_rerank`
1. 将 `_filter_*` 逻辑内联到 `_execute_filter`
1. 将 `_merge_by_*` 逻辑内联到 `_execute_merge`
1. 将 `_augment_*` 逻辑内联到 `_execute_augment`

### 步骤 3：确保遵循约束

- 检查没有自己计算 embedding
- 多次查询通过 `call_service` 实现

### 步骤 4：更新 execute 方法

使用字典映射替代 if-elif 链

### 步骤 5：测试验证

```bash
pytest packages/sage-benchmark/tests/ -v -k "post_retrieval"
```

## 六、架构约束检查清单

在重构过程中，确保以下约束：

- [ ] 不自己调用 EmbeddingGenerator（使用已有的 query_embedding）
- [ ] 多次查询通过 `call_service` 实现
- [ ] 最终输出 `history_text`

## 七、验收标准

1. ✅ PostRetrieval 只有大类方法（`_execute_*`）
1. ✅ 小类逻辑全部内联
1. ✅ 不自己计算 embedding
1. ✅ 多次查询通过服务调用
1. ✅ 现有测试用例通过

## 八、注意事项

1. **MemoryItem 保留**：`MemoryItem` dataclass 用于内部处理，可保留
1. **辅助方法保留**：`_convert_to_memory_items` 等转换方法可保留
1. **format 分离**：最终格式化逻辑可单独保留
