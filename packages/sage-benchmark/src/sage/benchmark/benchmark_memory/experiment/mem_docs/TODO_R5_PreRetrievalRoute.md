# R5: PreRetrieval 路由逻辑修正

> **优先级**: P1 **预估工时**: 1 天 **依赖**: R1, R3

______________________________________________________________________

## 一、任务目标

审查并修正 `pre_retrieval.py` 中的路由逻辑，确保：

1. 不访问记忆数据结构（严格遵守规范）
1. route action 不暗示多服务设计
1. 职责限于查询预处理

______________________________________________________________________

## 二、当前实现分析

### 2.1 PreRetrieval 当前职责

```python
class PreRetrieval(MapFunction):
    """支持的 action:
    - none: 透传
    - embedding: 基础向量化
    - optimize: 查询优化（关键词提取、扩展、改写、指令增强）
    - multi_embed: 多维向量生成
    - decompose: 复杂查询分解
    - route: 检索路由  # ⚠️ 需要审查
    - validate: 查询验证
    """
```

### 2.2 route action 审查结果

经过代码审查，route action 的当前实现：

```python
def _route_query(self, data):
    """检索路由

    根据查询内容决定查询哪些记忆源
    参考 MemoryOS（并行查询所有源）和 MemGPT（函数调用决定）
    """
    question = data.get("question", "")

    # 路由策略
    if self.route_strategy == "keyword":
        routes = self._route_by_keyword(question)
    elif self.route_strategy == "classifier":
        routes = self._route_by_classifier(question)
    elif self.route_strategy == "llm":
        routes = self._route_by_llm(question)

    data["retrieval_routes"] = routes  # ⚠️ 输出路由列表
    return data
```

**问题识别**：

- `retrieval_routes` 暗示可能路由到多个服务
- 配置中 `keyword_rules` 可能映射到不同服务名

______________________________________________________________________

## 三、规范要求

### 3.1 PreRetrieval 约束

```
检索前操作 (PreRetrieval):
├── 职责：预处理提问
├── 约束：不允许访问记忆数据结构
└── 输出：预处理后的查询（供 MemoryRetrieval 使用）

允许的操作：
├── 查询文本处理（改写、扩展、压缩）
├── 关键词提取
├── 向量化（不调用服务，只是计算）
├── 意图识别
└── 查询分解

不允许的操作：
├── ❌ 调用记忆服务检索
├── ❌ 读取记忆数据
└── ❌ 路由到不同服务
```

### 3.2 route 的正确理解

```
route 应该是：
├── ✅ 确定查询类型（用于告知服务如何检索）
├── ✅ 设置检索参数（如 top_k, threshold）
└── ✅ 输出路由元数据（服务根据元数据选择检索策略）

route 不应该是：
├── ❌ 选择不同的服务
├── ❌ 直接调用服务
└── ❌ 访问记忆数据
```

______________________________________________________________________

## 四、审查结论

### 4.1 ✅ 当前实现基本合规

1. **不访问记忆数据结构**：route action 只处理 query 文本，未调用服务
1. **不直接检索**：只输出 `retrieval_routes` 元数据，由 MemoryRetrieval 使用
1. **纯查询处理**：使用关键词匹配、分类器、LLM 判断查询意图

### 4.2 ⚠️ 需要修正的问题

1. **语义歧义**：`retrieval_routes` 暗示多服务，应改为 `retrieval_hints`
1. **配置歧义**：`keyword_rules[].route` 可能被理解为服务名，应改为 `strategy`
1. **文档不清晰**：需明确 route 输出的是检索策略提示，而非服务选择

______________________________________________________________________

## 五、修改方案

### 5.1 重命名输出字段

```python
# 修改前
data["retrieval_routes"] = routes

# 修改后
data["retrieval_hints"] = {
    "strategies": routes,  # 检索策略列表
    "route_strategy": self.route_strategy,
}
```

### 5.2 重命名配置项

```yaml
# 修改前（有歧义）
operators:
  pre_retrieval:
    action: route
    keyword_rules:
      - keywords: ["remember", "recall"]
        route: "long_term"  # ❌ 看起来像服务名

# 修改后（语义清晰）
operators:
  pre_retrieval:
    action: route
    keyword_rules:
      - keywords: ["remember", "recall"]
        strategy: "long_term"  # ✅ 检索策略标签
        params:  # 传递给服务的检索参数
          tier_preference: "ltm"
          expand_links: true
```

### 5.3 更新服务端使用方式

```python
# MemoryRetrieval 使用 hints
class MemoryRetrieval(MapFunction):
    def execute(self, data):
        query = data["question"]
        vector = data.get("query_embedding")

        # 读取 route hints（可选）
        hints = data.get("retrieval_hints", {})
        strategies = hints.get("strategies", [])

        # 传递给服务，让服务决定如何使用
        result = self.call_service(
            self.service_name,
            query=query,
            vector=vector,
            retrieval_hints=hints,  # 服务自行解释
            method="retrieve",
        )

        data["memory_data"] = result
        return data
```

______________________________________________________________________

## 六、具体修改清单

### 6.1 pre_retrieval.py 修改

| 位置                     | 修改内容                                             |
| ------------------------ | ---------------------------------------------------- |
| `_route_query()`         | 输出字段从 `retrieval_routes` 改为 `retrieval_hints` |
| `_route_by_keyword()`    | 返回值结构调整                                       |
| `_route_by_classifier()` | 返回值结构调整                                       |
| `_route_by_llm()`        | 返回值结构调整                                       |

### 6.2 配置结构修改

```yaml
# 新配置结构
operators:
  pre_retrieval:
    action: route
    route_strategy: keyword  # keyword | classifier | llm

    # keyword 策略
    keyword_rules:
      - keywords: ["remember", "recall", "what did"]
        strategy: "deep_search"
        params:
          search_depth: 3
          expand_links: true

      - keywords: ["yesterday", "recent", "just now"]
        strategy: "temporal_search"
        params:
          time_range: "recent"

      - keywords: ["personality", "traits", "character"]
        strategy: "persona_search"
        params:
          include_persona: true

    default_strategy: "semantic_search"
```

### 6.3 memory_retrieval.py 适配

```python
def execute(self, data):
    query = data["question"]
    vector = data.get("query_embedding")

    # 提取 hints（如有）
    hints = data.get("retrieval_hints", {})

    result = self.call_service(
        self.service_name,
        query=query,
        vector=vector,
        hints=hints,
        method="retrieve",
    )

    data["memory_data"] = result
    return data
```

______________________________________________________________________

## 七、开发步骤

### Step 1: 重命名和重构 (0.5天)

- [ ] 将 `retrieval_routes` 改为 `retrieval_hints`
- [ ] 重构 `_route_query()` 返回结构
- [ ] 更新配置解析

### Step 2: 更新下游使用 (0.5天)

- [ ] 更新 `memory_retrieval.py` 读取 hints
- [ ] 更新服务接口接收 hints
- [ ] 更新测试用例

______________________________________________________________________

## 八、验收标准

1. **语义清晰**：输出字段名明确表示是"提示"而非"路由目标"
1. **配置清晰**：配置项名称不暗示多服务
1. **向后兼容**：旧配置仍可工作（通过兼容层）
1. **测试通过**：现有测试用例通过

______________________________________________________________________

## 九、附加说明

### 9.1 为什么保留 route action

虽然 route 看起来有多服务嫌疑，但它的实际作用是：

- 分析查询意图
- 输出检索策略建议
- 让单一服务根据建议调整检索行为

这与"分层服务内部根据查询选择检索哪一层"是一致的。

### 9.2 服务如何使用 hints

```python
# HierarchicalMemoryService 示例
def retrieve(self, query, vector, hints=None):
    strategies = (hints or {}).get("strategies", [])

    if "deep_search" in strategies:
        # 搜索所有层级
        return self._search_all_tiers(query, vector)
    elif "temporal_search" in strategies:
        # 只搜索 STM
        return self._search_stm_only(query, vector)
    else:
        # 默认策略
        return self._default_search(query, vector)
```

______________________________________________________________________

*文档创建时间: 2025-12-01*
