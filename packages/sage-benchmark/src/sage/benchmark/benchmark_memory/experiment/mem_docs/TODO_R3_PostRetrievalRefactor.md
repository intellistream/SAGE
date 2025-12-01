# R3: PostRetrieval 职责边界修正

> **优先级**: P0 **预估工时**: 2 天 **依赖**: R1 (服务层重构: 继承 BaseService + 使用 NeuroMem) **状态**: ✅ 已完成
> (2025-12-01)

______________________________________________________________________

## 一、任务目标

修正 `post_retrieval.py` 的职责边界，确保：

1. 不再实现应属于记忆服务的功能（如 embedding 计算、去重）
1. 专注于检索结果的后处理和 prompt 格式化
1. 允许多次查询记忆服务以拼接 prompt
1. 不从 data 中读取多个记忆源（暗示多服务）

______________________________________________________________________

## 完成情况

### 已完成的修改

1. **移除 embedding 依赖**

   - 删除了 `EmbeddingGenerator` 导入和初始化
   - `_rerank_semantic` 现在只使用上游提供的 `query_embedding` 和 `metadata.embedding`
   - `_rerank_weighted` 的 `relevance` 因子只使用已有 score

1. **移除 filter.dedup**

   - 删除了 `_filter_dedup()` 方法
   - 删除了 `_execute_filter()` 中的 dedup 分支
   - 删除了 dedup 相关配置（`dedup_threshold`, `dedup_strategy`）

1. **重构 merge 逻辑**

   - 删除了从 data 读取多源的旧方法：`_merge_concat`, `_merge_interleave`, `_merge_weighted`, `_merge_rrf`
   - 删除了 `merge_sources`, `rrf_k`, `merge_weights` 配置
   - 新增 `_merge_by_link_expand()`: 通过调用服务获取关联记忆
   - 新增 `_merge_by_multi_query()`: 多次查询服务获取补充信息
   - 新增配置：`expand_top_n`, `max_depth`, `secondary_queries`

1. **代码统计**

   - 重构前：1428 行
   - 重构后：1238 行
   - 减少约 190 行

______________________________________________________________________

## 二、当前问题详解（历史记录）

### 2.1 实现了应属于服务的功能

```python
# ❌ embedding 计算应由服务完成
def _filter_dedup(self, items, data):
    # 自己调用 embedding_generator 计算相似度
    embeddings = self._embedding_generator.embed_batch([i.text for i in items])
    # 自己实现余弦相似度计算
    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        # ...

# ❌ 应该让服务返回已去重的结果，而非算子自己去重
```

### 2.2 从 data 读取多个记忆源

```python
# ❌ merge 暗示多服务设计
def _merge_concat(self, items, data):
    for src in self.merge_sources:  # ["memory_data", "context_data", ...]
        src_items = data.get(src)  # 从 data 中获取多个来源
        # ...

# 问题：这暗示 pipeline 中有多个记忆服务分别存储了 memory_data 和 context_data
```

### 2.3 职责边界模糊

```python
# 当前 PostRetrieval 的职责过于广泛：
# - rerank: OK，属于后处理
# - filter: 部分OK（top_k, threshold），部分越界（dedup 应由服务做）
# - merge: 越界，应由服务内部合并
# - augment: OK，属于后处理（拼接额外信息）
# - compress: OK，属于后处理（压缩 prompt）
# - format: OK，属于后处理（格式化输出）
```

______________________________________________________________________

## 三、重构方案

### 3.1 PostRetrieval 正确职责

```
PostRetrieval 职责边界：
├── 检索结果后处理
│   ├── rerank: 重新排序（使用已有 score，不计算新的 embedding）
│   ├── filter: 简单过滤（top_k, threshold, token_budget）
│   ├── augment: 增强结果（添加上下文、时间、元数据）
│   ├── compress: 压缩内容（LLMLingua, 抽取, 生成）
│   └── format: 格式化输出（template, structured, chat, xml）
│
├── 多次查询记忆服务（允许）
│   └── 例：先获取主记忆，再查询关联记忆，拼接成完整 prompt
│
└── Prompt 构建
    └── 将处理后的记忆拼接成 history_text

不应该做的事：
├── ❌ 自己计算 embedding
├── ❌ 自己实现去重算法
├── ❌ 从 data 读取多个记忆源（应只有一个 memory_data）
└── ❌ 实现记忆合并逻辑（应由服务内部完成）
```

### 3.2 merge 的正确实现

```python
# 当前错误实现：
def _merge_concat(self, items, data):
    for src in self.merge_sources:  # ❌ 读取多个来源
        src_items = data.get(src)
        result.extend(src_items)

# 正确实现方案 A：服务内部合并
# 让 hierarchical_memory_service 在 retrieve() 时自动合并多层结果
# PostRetrieval 只处理单一的 memory_data

# 正确实现方案 B：PostRetrieval 多次查询
def _execute_merge(self, items, data):
    """多次查询服务并合并（符合规范）"""
    result = list(items)  # 第一次查询的结果

    # 允许多次查询
    if self.need_secondary_retrieval:
        # 例：获取关联记忆
        secondary_query = self._build_secondary_query(items)
        secondary_results = self.call_service(
            self.service_name,
            method="retrieve",
            query=secondary_query,
        )
        result.extend(secondary_results)

    return result
```

### 3.3 filter 的修正

```python
# 保留的 filter 类型（不需要 embedding）：
# - top_k: 简单截取
# - threshold: 基于已有 score 过滤
# - token_budget: 基于 token 数过滤
# - llm: 基于 LLM 判断过滤

# 移除的 filter 类型（需要 embedding，应由服务做）：
# - dedup: 移除，改为要求服务返回去重结果
```

______________________________________________________________________

## 四、具体修改清单

### 4.1 删除的代码

| 方法                                | 原因                           |
| ----------------------------------- | ------------------------------ |
| `_filter_dedup()`                   | embedding 计算应由服务完成     |
| `_merge_concat()` 中的多源读取      | 不应从 data 读取多个来源       |
| `_merge_interleave()`               | 同上                           |
| `_merge_weighted()`                 | 同上                           |
| `_merge_rrf()`                      | 同上（RRF 应在服务内做）       |
| `_merge_link_expand_placeholder()`  | 应由图服务在 retrieve 时完成   |
| `_merge_multi_aspect_placeholder()` | 应由混合服务在 retrieve 时完成 |

### 4.2 修改的代码

| 方法                | 修改内容                                |
| ------------------- | --------------------------------------- |
| `_execute_filter()` | 移除 dedup 分支                         |
| `_execute_merge()`  | 改为多次查询服务方式                    |
| `__init__()`        | 移除 `_embedding_generator`（不再需要） |

### 4.3 保留的代码

| 方法                       | 原因                                    |
| -------------------------- | --------------------------------------- |
| `_execute_rerank()`        | 使用已有 score 排序，不计算新 embedding |
| `_filter_top_k()`          | 简单截取，不需要 embedding              |
| `_filter_threshold()`      | 基于已有 score 过滤                     |
| `_filter_token_budget()`   | 基于 token 数过滤                       |
| `_filter_llm()`            | 基于 LLM 判断过滤                       |
| `_execute_augment()`       | 添加上下文信息                          |
| `_execute_compress()`      | 压缩内容                                |
| `_execute_format_action()` | 格式化输出                              |
| `_format_dialog_history()` | 构建 history_text                       |

______________________________________________________________________

## 五、重构后代码结构

```python
class PostRetrieval(MapFunction):
    """记忆检索后的后处理算子

    职责：
    - 检索结果后处理（rerank, filter, augment, compress, format）
    - 允许多次查询记忆服务以拼接完整 prompt
    - 构建最终 history_text

    约束：
    - 不自己计算 embedding
    - 不从 data 读取多个记忆源
    - 只与单一记忆服务交互
    """

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.action = get_required_config(self.config, "operators.post_retrieval.action")

        # ✅ 只引用单一服务（用于多次查询）
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 基础格式化 Prompt
        self.conversation_format_prompt = config.get(
            "operators.post_retrieval.conversation_format_prompt",
            "Below is a conversation between two people..."
        )

        # ❌ 删除 embedding_generator
        # self._embedding_generator = ...  # 不再需要

        self._init_for_action()

    def execute(self, data):
        """执行后处理"""
        if not data:
            return data

        action = self.action or "none"

        if action == "none":
            processed = data
        elif action == "rerank":
            processed = self._execute_rerank(data)
        elif action == "filter":
            processed = self._execute_filter_action(data)
        elif action == "merge":
            processed = self._execute_merge_action(data)  # 重构后
        elif action == "augment":
            processed = self._execute_augment_action(data)
        elif action == "compress":
            processed = self._execute_compress_action(data)
        elif action == "format":
            return self._execute_format_action(data)
        else:
            processed = data

        return self._format_dialog_history(processed)

    def _execute_merge_action(self, data):
        """merge action 重构版：多次查询服务

        允许多次查询记忆服务以获取更完整的上下文。
        例如：
        - 获取关联记忆（通过链接）
        - 获取补充上下文
        - 获取相关 persona
        """
        memory_data = data.get("memory_data", []) or []
        items = self._convert_to_memory_items(memory_data)

        # 根据 merge_type 决定如何多次查询
        if self.merge_type == "link_expand":
            merged_items = self._merge_by_link_expand(items)
        elif self.merge_type == "multi_query":
            merged_items = self._merge_by_multi_query(items, data)
        else:
            # 默认：不合并，直接使用
            merged_items = items

        data["memory_data"] = self._convert_from_memory_items(merged_items)
        return self._format_dialog_history(data)

    def _merge_by_link_expand(self, items):
        """通过链接扩展获取关联记忆

        调用服务的 retrieve 方法获取关联记忆。
        """
        result = list(items)

        for item in items[:5]:  # 只扩展 top 5
            # 查询关联记忆（服务负责实现扩展逻辑）
            related = self.call_service(
                self.service_name,
                method="retrieve",
                query=item.text,
                metadata={"expand_links": True, "max_depth": 1},
            )
            if related:
                for r in related:
                    if r["text"] not in [i.text for i in result]:
                        result.append(MemoryItem(
                            text=r["text"],
                            score=r.get("score"),
                            metadata=r.get("metadata", {}),
                            original_index=-1,
                        ))

        return result

    def _merge_by_multi_query(self, items, data):
        """多次查询获取补充信息"""
        result = list(items)

        # 构造补充查询
        if self.secondary_queries:
            for query_config in self.secondary_queries:
                secondary_result = self.call_service(
                    self.service_name,
                    method="retrieve",
                    query=query_config.get("query") or data.get("question"),
                    metadata=query_config.get("metadata"),
                )
                if secondary_result:
                    for r in secondary_result:
                        result.append(MemoryItem(
                            text=r["text"],
                            score=r.get("score"),
                            metadata=r.get("metadata", {}),
                            original_index=-1,
                        ))

        return result
```

______________________________________________________________________

## 六、配置变更

### 6.1 filter 配置

```yaml
operators:
  post_retrieval:
    action: filter

    # 保留的 filter_type
    filter_type: "top_k"  # top_k | threshold | token_budget | llm

    # ❌ 删除 dedup 相关配置（改为要求服务返回去重结果）
    # dedup_threshold: 0.9
    # dedup_strategy: "keep_first"
```

### 6.2 merge 配置

```yaml
operators:
  post_retrieval:
    action: merge

    # 新的 merge_type（基于多次查询）
    merge_type: "link_expand"  # link_expand | multi_query

    # link_expand 专用
    expand_top_n: 5
    max_depth: 1

    # multi_query 专用
    secondary_queries:
      - query_template: "persona of {user}"
        metadata: {type: "persona"}
      - query_template: "recent events"
        metadata: {type: "event"}

    # ❌ 删除多源配置
    # merge_sources: ["memory_data", "context_data"]  # 不再支持
```

______________________________________________________________________

## 七、开发步骤

### Step 1: 移除 embedding 依赖 (0.5天)

- [ ] 删除 `_embedding_generator` 初始化
- [ ] 删除 `_filter_dedup()` 方法
- [ ] 修改 `_execute_filter()` 移除 dedup 分支

### Step 2: 重构 merge 逻辑 (1天)

- [ ] 删除旧的多源 merge 方法
- [ ] 实现 `_merge_by_link_expand()`
- [ ] 实现 `_merge_by_multi_query()`
- [ ] 更新配置解析

### Step 3: 清理和测试 (0.5天)

- [ ] 删除不再需要的代码
- [ ] 更新文档注释
- [ ] 运行测试验证

______________________________________________________________________

## 八、验收标准

1. **无 embedding 依赖**：不再初始化或使用 `EmbeddingGenerator`
1. **单源数据**：只从 `data["memory_data"]` 读取，不读取多个来源
1. **多次查询**：merge 通过调用服务实现，而非从 data 读取
1. **测试通过**：现有测试用例通过
1. **配置兼容**：filter 配置（除 dedup）仍可工作

______________________________________________________________________

## 九、重构前后对比

### 行数对比

| 项目        | 重构前 | 重构后 |
| ----------- | ------ | ------ |
| 总行数      | 1428   | ~1000  |
| merge 相关  | 300行  | 100行  |
| filter 相关 | 200行  | 100行  |

### 依赖对比

| 依赖               | 重构前       | 重构后                          |
| ------------------ | ------------ | ------------------------------- |
| EmbeddingGenerator | ✅ 使用      | ❌ 移除                         |
| LLMGenerator       | ✅ 使用      | ✅ 保留（compress, llm_filter） |
| 多服务             | 隐式（多源） | 显式（单服务多次查询）          |

______________________________________________________________________

*文档创建时间: 2025-12-01*
