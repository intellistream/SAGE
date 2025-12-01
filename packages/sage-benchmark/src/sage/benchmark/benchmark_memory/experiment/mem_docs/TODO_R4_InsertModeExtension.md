# R4: MemoryInsert 插入模式扩展

> **优先级**: P1 **预估工时**: 1 天 **依赖**: R1 (服务层重构: 继承 BaseService + 使用 NeuroMem) **状态**: ✅ 已完成
> (2025-12-01)

______________________________________________________________________

## 一、任务目标

扩展 `memory_insert.py`，使其支持：

1. **主动插入**: 外部（PreInsert）提供参数，指定记忆服务如何插入
1. **被动插入**: 由服务内部决定如何插入（当前默认行为）

______________________________________________________________________

## 二、当前实现分析

### 2.1 当前代码

```python
class MemoryInsert(MapFunction):
    def execute(self, data):
        for entry_dict in data.get("memory_entries", []):
            self._insert_single_entry(entry_dict)
        return data

    def _insert_single_entry(self, entry_dict: dict):
        entry = entry_dict.get("refactor", "")
        vector = entry_dict.get("embedding", None)
        metadata = entry_dict.get("metadata", None)

        # 当前只有一种调用方式（被动插入）
        self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            method="insert",
        )
```

### 2.2 问题

- 只支持被动插入
- PreInsert 无法指定插入方式
- 无法适配需要主动插入的场景（如指定插入到 LTM 层）

______________________________________________________________________

## 三、插入模式设计

### 3.1 被动插入（Passive Insert）

```
特点：
- 由记忆服务内部决定如何存储
- 例：FIFO 队列自动决定位置
- 例：分层服务自动决定存入哪一层
- 例：图服务自动决定节点类型

使用场景：
- 短期记忆 (STM)
- 日常对话存储
- 默认行为
```

### 3.2 主动插入（Active Insert）

```
特点：
- 外部（PreInsert）提供参数指定插入方式
- 通过 insert_params 传递参数
- 服务根据参数执行特定插入逻辑

使用场景：
- 强制存入长期记忆 (LTM)
- 指定节点类型（entity vs fact）
- 高优先级记忆
- 特定位置插入
```

______________________________________________________________________

## 四、实现方案

### 4.1 PreInsert 输出格式扩展

```python
# PreInsert 输出的 memory_entries 格式
{
    "memory_entries": [
        {
            "refactor": "processed text",
            "embedding": [...],
            "metadata": {...},

            # 新增：插入模式配置
            "insert_mode": "active",  # "active" | "passive"（默认）
            "insert_params": {
                # 分层服务参数
                "target_tier": "ltm",

                # 图服务参数
                "node_type": "entity",
                "create_edges": True,

                # 通用参数
                "priority": 10,
                "force": False,
            }
        }
    ]
}
```

### 4.2 MemoryInsert 重构

```python
class MemoryInsert(MapFunction):
    """将对话插入记忆服务

    支持两种插入模式：
    - passive: 被动插入，由服务内部决定如何存储（默认）
    - active: 主动插入，根据 insert_params 指定存储方式
    """

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # adapter 保持兼容
        self.adapter = config.get("services.memory_insert_adapter", "to_dialogs") if config else "to_dialogs"

        if self.adapter == "to_dialogs":
            self.dialogue_parser = DialogueParser()

    def execute(self, data):
        """执行记忆插入"""
        for entry_dict in data.get("memory_entries", []):
            self._insert_single_entry(entry_dict)
        return data

    def _insert_single_entry(self, entry_dict: dict):
        """插入单条记忆条目

        根据 insert_mode 决定调用方式：
        - passive: 简单调用，由服务决定如何存储
        - active: 传递 insert_params，服务按参数存储
        """
        # 提取基本信息
        if self.adapter == "to_dialogs":
            dialogs = entry_dict.get("dialogs", [])
            entry = self.dialogue_parser.format(dialogs)
        else:
            entry = entry_dict.get("refactor", "")

        if not entry:
            return

        vector = entry_dict.get("embedding")
        metadata = entry_dict.get("metadata")

        # 获取插入模式配置
        insert_mode = entry_dict.get("insert_mode", "passive")
        insert_params = entry_dict.get("insert_params")

        # 调用服务
        self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            insert_mode=insert_mode,
            insert_params=insert_params,
            method="insert",
            timeout=10.0,
        )
```

### 4.3 服务端适配

```python
# BaseMemoryService.insert() 签名
def insert(
    self,
    entry: str,
    vector: list[float] | None = None,
    metadata: dict | None = None,
    *,
    insert_mode: Literal["active", "passive"] = "passive",
    insert_params: dict | None = None,
) -> InsertResult:
    """插入记忆

    Args:
        insert_mode: 插入模式
            - "passive": 由服务自行决定存储方式
            - "active": 根据 insert_params 指定存储方式
        insert_params: 主动插入参数
            - target_tier: 目标层级 (分层服务)
            - node_type: 节点类型 (图服务)
            - priority: 优先级
            - force: 是否强制插入
    """
    if insert_mode == "passive":
        return self._passive_insert(entry, vector, metadata)
    else:
        return self._active_insert(entry, vector, metadata, insert_params)
```

______________________________________________________________________

## 五、使用示例

### 5.1 被动插入（默认）

```yaml
# PreInsert 配置
operators:
  pre_insert:
    action: none  # 简单透传

# 结果：memory_entries 中没有 insert_mode，默认为 passive
```

### 5.2 主动插入到 LTM

```yaml
# PreInsert 配置
operators:
  pre_insert:
    action: score
    score_type: importance

    # 高重要性记忆强制存入 LTM
    high_importance_insert:
      threshold: 8
      insert_mode: active
      insert_params:
        target_tier: ltm
        priority: 10
```

```python
# PreInsert 输出
{
    "memory_entries": [
        {
            "refactor": "User's birthday is Feb 7",
            "embedding": [...],
            "metadata": {"importance_score": 9},
            "insert_mode": "active",
            "insert_params": {"target_tier": "ltm", "priority": 10}
        }
    ]
}
```

### 5.3 主动插入为实体节点

```yaml
# PreInsert 配置
operators:
  pre_insert:
    action: extract
    extract_type: entity

    # 提取的实体作为实体节点插入
    entity_insert:
      insert_mode: active
      insert_params:
        node_type: entity
        create_edges: true
```

______________________________________________________________________

## 六、开发步骤

### Step 1: 扩展 MemoryInsert (0.5天)

- [x] 修改 `_insert_single_entry()` 读取 insert_mode
- [x] 传递 insert_params 给服务
- [x] 添加文档注释

### Step 2: 更新服务接口 (0.5天)

- [x] 更新各服务的 `insert()` 签名添加 `insert_mode` 和 `insert_params` 参数
- [x] 各服务实现主动插入逻辑
- [x] 添加参数校验

______________________________________________________________________

## 七、验收标准

1. ✅ **向后兼容**：未指定 insert_mode 时默认 passive
1. ✅ **主动插入**：支持通过 insert_params 指定插入方式
1. ✅ **参数透传**：insert_params 正确传递给服务
1. ✅ **测试覆盖**：新增主动插入测试用例

______________________________________________________________________

## 八、影响范围

### 已修改的文件

| 文件                             | 修改内容                               | 状态      |
| -------------------------------- | -------------------------------------- | --------- |
| `libs/memory_insert.py`          | 支持 insert_mode 和 insert_params      | ✅ 已完成 |
| `hierarchical_memory_service.py` | 支持 target_tier, priority, force 参数 | ✅ 已完成 |
| `graph_memory_service.py`        | 支持 node_type, create_edges 参数      | ✅ 已完成 |
| `short_term_memory_service.py`   | 支持 force 跳过 FIFO 容量限制          | ✅ 已完成 |
| `vector_hash_memory_service.py`  | 支持 priority 参数                     | ✅ 已完成 |
| `hybrid_memory_service.py`       | 支持 target_indexes 参数               | ✅ 已完成 |
| `key_value_memory_service.py`    | 支持 priority 参数                     | ✅ 已完成 |

### 新增的文件

| 文件                            | 内容                 |
| ------------------------------- | -------------------- |
| `test_insert_mode_extension.py` | 插入模式扩展单元测试 |

### 不需要修改的文件

| 文件                       | 原因                     |
| -------------------------- | ------------------------ |
| `libs/pre_retrieval.py`    | 与插入无关               |
| `libs/memory_retrieval.py` | 与插入无关               |
| `libs/post_retrieval.py`   | 与插入无关               |
| `libs/post_insert.py`      | 插入已完成，不影响后处理 |

______________________________________________________________________

## 九、实现细节

### 9.1 MemoryInsert 重构结果

```python
def _insert_single_entry(self, entry_dict: dict[str, Any]) -> None:
    """插入单条记忆条目

    根据 insert_mode 决定调用方式：
    - passive: 简单调用，由服务决定如何存储（默认）
    - active: 传递 insert_params，服务按参数存储
    """
    # ... 提取 entry, vector, metadata ...

    # 获取插入模式配置
    insert_mode: Literal["active", "passive"] = entry_dict.get("insert_mode", "passive")
    insert_params: dict[str, Any] | None = entry_dict.get("insert_params", None)

    # 统一插入
    self.call_service(
        self.service_name,
        entry=entry,
        vector=vector,
        metadata=metadata,
        insert_mode=insert_mode,
        insert_params=insert_params,
        method="insert",
        timeout=10.0,
    )
```

### 9.2 服务接口签名

所有记忆服务的 `insert()` 方法现在统一支持以下签名：

```python
def insert(
    self,
    entry: str,
    vector: np.ndarray | list[float] | None = None,
    metadata: dict | None = None,
    *,
    insert_mode: Literal["active", "passive"] = "passive",
    insert_params: dict | None = None,
) -> str:
    """插入记忆

    Args:
        entry: 文本内容
        vector: embedding 向量
        metadata: 元数据
        insert_mode: 插入模式
            - "passive": 由服务自行决定存储方式（默认）
            - "active": 根据 insert_params 指定存储方式
        insert_params: 主动插入参数（各服务支持不同参数）

    Returns:
        str: 条目 ID
    """
```

### 9.3 各服务支持的 insert_params

| 服务                      | 参数             | 说明                           |
| ------------------------- | ---------------- | ------------------------------ |
| HierarchicalMemoryService | `target_tier`    | 目标层级 (stm/mtm/ltm)         |
|                           | `priority`       | 优先级                         |
|                           | `force`          | 跳过容量检查                   |
| GraphMemoryService        | `node_type`      | 节点类型 (entity/fact/passage) |
|                           | `create_edges`   | 是否创建边                     |
|                           | `priority`       | 优先级                         |
| ShortTermMemoryService    | `force`          | 跳过 FIFO 容量限制             |
|                           | `priority`       | 优先级                         |
| HybridMemoryService       | `target_indexes` | 目标索引列表                   |
|                           | `priority`       | 优先级                         |
| VectorHashMemoryService   | `priority`       | 优先级                         |
| KeyValueMemoryService     | `priority`       | 优先级                         |

______________________________________________________________________

*文档创建时间: 2025-12-01* *文档更新时间: 2025-12-01 (重构完成)*
