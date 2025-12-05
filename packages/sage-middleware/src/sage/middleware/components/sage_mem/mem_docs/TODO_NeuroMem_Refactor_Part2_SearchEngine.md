# TODO Part 2: 索引层 (Search Engine) 重构

## ✅ 完成状态

**Part 2 已完成** - 2024-12

所有任务均已实现并测试通过：

- ✅ 2.1 GraphIndex 独立模块
- ✅ 2.2 KVIndex 功能补全
- ✅ 2.3 IndexFactory 统一工厂
- ✅ 2.4 PPR 算法支持

______________________________________________________________________

## 背景

NeuroMem 的索引层设计：

```
search_engine/
├── vdb_index/          # 向量索引 (FAISS, etc.)
│   ├── base_vdb_index.py
│   └── faiss_index.py
├── kv_index/           # 文本索引 (BM25, etc.)
│   ├── base_kv_index.py
│   └── bm25s_index.py
├── graph_index/        # 图索引 ✅ 已独立
│   ├── base_graph_index.py
│   └── simple_graph_index.py
├── hybrid_index/       # 混合索引（待实现）
└── index_factory.py    # 统一工厂 ✅ 新增
```

**核心设计**：

- 每种索引类型有一个 Base 抽象类
- 具体实现（FAISS, BM25S, SimpleGraph）继承 Base
- Collection 持有多个索引实例
- 统一的 IndexFactory 提供创建入口

______________________________________________________________________

## 任务概述

本任务负责补全和统一索引层的实现。

**涉及文件**：

- `search_engine/vdb_index/` （已完成，作为参考）
- `search_engine/kv_index/` （✅ 已补全）
- `search_engine/graph_index/` （✅ 已从 GraphCollection 中抽出）
- `search_engine/index_factory.py` （✅ 新增统一工厂）

______________________________________________________________________

## 2.1 抽出 GraphIndex 独立模块 ✅

**完成情况**：

- ✅ `SimpleGraphIndex` 从 `graph_collection.py` 移出
- ✅ 实现 `BaseGraphIndex` 抽象类（完整接口）
- ✅ `SimpleGraphIndex` 支持 relation、direction、update_edge_weight
- ✅ `GraphMemoryCollection` 使用 `search_engine/graph_index` 模块
- ✅ 向后兼容：`memory_collection` 仍导出 `SimpleGraphIndex`

**文件结构**：

```
search_engine/graph_index/
├── __init__.py              # 导出 + GraphIndexFactory
├── base_graph_index.py      # 抽象基类
└── simple_graph_index.py    # 完整实现
```

**BaseGraphIndex 接口设计**：

```python
class BaseGraphIndex(ABC):
    """图索引基类"""

    def __init__(self, name: str, config: dict | None = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def add_node(self, node_id: str, data: Any = None) -> bool:
        """添加节点"""
        ...

    @abstractmethod
    def add_edge(
        self,
        from_node: str,
        to_node: str,
        weight: float = 1.0,
        relation: str | None = None  # 边的类型/关系名
    ) -> bool:
        """添加边"""
        ...

    @abstractmethod
    def remove_node(self, node_id: str) -> bool:
        """删除节点（及其所有边）"""
        ...

    @abstractmethod
    def remove_edge(self, from_node: str, to_node: str) -> bool:
        """删除边"""
        ...

    @abstractmethod
    def get_neighbors(
        self,
        node_id: str,
        k: int = 10,
        direction: Literal["outgoing", "incoming", "both"] = "outgoing"
    ) -> list[tuple[str, float]]:
        """获取邻居节点，返回 [(node_id, weight), ...]"""
        ...

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在"""
        ...

    @abstractmethod
    def has_edge(self, from_node: str, to_node: str) -> bool:
        """检查边是否存在"""
        ...

    @abstractmethod
    def get_node_data(self, node_id: str) -> Any:
        """获取节点数据"""
        ...

    @abstractmethod
    def update_edge_weight(
        self,
        from_node: str,
        to_node: str,
        new_weight: float
    ) -> bool:
        """更新边权重"""
        ...

    @abstractmethod
    def traverse_bfs(
        self,
        start_node: str,
        max_depth: int = 2,
        max_nodes: int = 100
    ) -> list[str]:
        """BFS 遍历，返回节点 ID 列表"""
        ...

    # 持久化接口
    @abstractmethod
    def store(self, dir_path: str) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def load(cls, name: str, dir_path: str) -> "BaseGraphIndex": ...

    # 统计接口
    def node_count(self) -> int: ...
    def edge_count(self) -> int: ...
```

**验收标准**：

- [x] `SimpleGraphIndex` 从 `graph_collection.py` 移出
- [x] 实现 `BaseGraphIndex` 抽象类
- [x] `GraphMemoryCollection` 使用 `graph_index/` 模块
- [x] 现有图相关测试通过

______________________________________________________________________

## 2.2 补全 KVIndex 功能 ✅

**完成情况**：

- ✅ `BaseKVIndex` 新增 `search_with_scores`、`search_with_sort`、`search_range` 方法
- ✅ `BM25sIndex` 实现所有新方法
- ✅ 新增 `count()` 和 `get_all_ids()` 统计方法
- ✅ 单元测试验证通过

**新增方法**：

1. **search_with_scores** - 返回带分数的检索结果
1. **search_with_sort** - 支持按 metadata 字段排序
1. **search_range** - 支持 metadata 字段范围查询
1. **count** - 返回索引中的条目数量
1. **get_all_ids** - 返回所有 ID 列表

**验收标准**：

- [x] BM25sIndex 支持排序参数
- [x] 添加 Range 查询方法
- [x] 新增方法有单元测试

______________________________________________________________________

## 2.3 实现 IndexFactory 统一工厂 ✅

**完成情况**：

- ✅ 创建 `search_engine/index_factory.py`
- ✅ 统一的 `IndexFactory` 类，整合 VDB/KV/Graph 索引创建
- ✅ 支持注册自定义索引类型
- ✅ 模块级便捷函数 `create_vdb_index`, `create_kv_index`, `create_graph_index`

**使用示例**：

```python
from neuromem.search_engine import IndexFactory

# 创建各类索引
vdb_index = IndexFactory.create_vdb_index({"name": "my_vdb", "dim": 768})
kv_index = IndexFactory.create_kv_index({"name": "my_kv", "index_type": "bm25s"})
graph_index = IndexFactory.create_graph_index({"name": "my_graph"})

# 查看支持的类型
print(IndexFactory.get_supported_kv_types())    # ['bm25', 'bm25s']
print(IndexFactory.get_supported_graph_types()) # ['simple', 'adjacency']
```

**验收标准**：

- [x] 统一的 `IndexFactory` 类
- [x] 支持注册自定义索引
- [x] 现有代码迁移到使用统一工厂

______________________________________________________________________

## 2.4 添加 PPR（Personalized PageRank）支持 ✅

**完成情况**：

- ✅ `BaseGraphIndex` 定义 `ppr()` 抽象方法
- ✅ `SimpleGraphIndex` 实现 PPR 算法（power iteration）
- ✅ 支持加权边的 PPR 计算
- ✅ 测试验证 PPR 结果正确

**实现的 PPR 算法**：

- 使用 power iteration 方法
- 支持多个种子节点
- 考虑边权重的归一化
- 支持收敛检测

**验收标准**：

- [x] PPR 方法实现并通过测试
- [x] 与 HippoRAG 论文描述一致

______________________________________________________________________

## 依赖关系

- ✅ 依赖 Part 1（Collection 层）完成
- ✅ Part 2 已完成，Part 3 (Service 层) 可以开始

______________________________________________________________________

## 实际工时

| 子任务                  | 预估时间 | 实际时间          |
| ----------------------- | -------- | ----------------- |
| 2.1 GraphIndex 独立模块 | 4h       | ~2h               |
| 2.2 KVIndex 补全        | 2h       | ~1h               |
| 2.3 IndexFactory 统一   | 2h       | ~1h               |
| 2.4 PPR 实现            | 3h       | (已在 2.1 中完成) |
| 测试 & 验证             | 2h       | ~1h               |
| **总计**                | **13h**  | **~5h**           |

______________________________________________________________________

## 新增文件清单

```
search_engine/
├── graph_index/
│   ├── __init__.py          # 更新：导出 + GraphIndexFactory
│   ├── base_graph_index.py  # 重写：完整抽象接口
│   └── simple_graph_index.py # 新增：独立实现
├── kv_index/
│   ├── base_kv_index.py     # 更新：新增方法
│   └── bm25s_index.py       # 更新：实现新方法
├── index_factory.py         # 新增：统一工厂
└── __init__.py              # 更新：导出统一工厂

memory_collection/
├── __init__.py              # 更新：从 search_engine 导入 SimpleGraphIndex
└── graph_collection.py      # 更新：使用独立的 SimpleGraphIndex

tests/
└── test_search_engine_part2.py  # 新增：Part 2 单元测试
```

______________________________________________________________________

## 参考资料

- VDB Index 作为参考实现
- HippoRAG 论文中的 PPR 描述
- NetworkX 的 PPR 实现作为对照
