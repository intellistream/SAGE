# neuromem 层重构方案

> **目标**: 简化 neuromem 架构，从多态 Collection 转向统一数据容器 + 动态索引管理
>
> **原则**: 一个 Collection 足够，索引能力通过组合而非继承获得

______________________________________________________________________

## 🎯 重构目标

### 当前问题

```python
# 现状：多种 Collection 类型（过度设计）
VDBMemoryCollection      # 只能建 VDB 索引
GraphMemoryCollection    # 只能建 Graph 索引
KVMemoryCollection       # 只能建 KV 索引
HybridCollection         # 可以建多种索引（最接近理想）
```

**问题**:

1. ❌ 代码重复：每种 Collection 都要实现 insert/retrieve/delete
1. ❌ 扩展性差：新增索引类型需要修改 Collection
1. ❌ 职责不清：Collection 既管数据又限定索引能力

### 新设计

```python
# 目标：统一 Collection + 动态索引
UnifiedCollection:
    - raw_data: Dict[id, {text, metadata}]  # 原始数据
    - indexes: Dict[name, IndexObject]       # 动态索引
    - add_index(name, type, config)          # 添加索引
    - remove_index(name)                     # 删除索引
    - query_by_index(name, query)            # 按索引查询
```

**优势**:

1. ✅ 单一职责：Collection 只管数据 + 索引容器
1. ✅ 灵活性：可动态添加任意类型索引
1. ✅ 可扩展：新索引类型无需修改 Collection

______________________________________________________________________

## 📐 新架构设计

### 核心类设计

```python
# packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/

# ==================== 1. UnifiedCollection ====================
class UnifiedCollection:
    """统一数据容器 - 管理原始数据 + 多种索引

    设计原则：
    - 数据只存一份（raw_data）
    - 索引可以有多个（动态添加/删除）
    - 每个索引独立工作
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.raw_data: Dict[str, Dict] = {}  # id -> {text, metadata, created_at}
        self.indexes: Dict[str, BaseIndex] = {}  # index_name -> Index对象
        self.index_metadata: Dict[str, Dict] = {}  # index配置信息

    # ---------- 数据操作 ----------
    def insert(self, text: str, metadata: Optional[Dict] = None,
               index_names: Optional[List[str]] = None) -> str:
        """插入数据（可选择加入哪些索引）

        Args:
            text: 原始文本
            metadata: 元数据
            index_names: 要加入的索引列表（None=所有索引）

        Returns:
            data_id: 数据ID
        """
        data_id = self._generate_id(text, metadata)
        self.raw_data[data_id] = {
            "text": text,
            "metadata": metadata or {},
            "created_at": time.time()
        }

        # 加入指定索引
        target_indexes = index_names or list(self.indexes.keys())
        for idx_name in target_indexes:
            if idx_name in self.indexes:
                self.indexes[idx_name].add(data_id, text, metadata)

        return data_id

    def get(self, data_id: str) -> Optional[Dict]:
        """获取原始数据"""
        return self.raw_data.get(data_id)

    def delete(self, data_id: str) -> bool:
        """完全删除（数据 + 所有索引）"""
        if data_id not in self.raw_data:
            return False

        # 从所有索引中移除
        for index in self.indexes.values():
            index.remove(data_id)

        # 删除原始数据
        del self.raw_data[data_id]
        return True

    # ---------- 索引管理 ----------
    def add_index(self, name: str, index_type: str, config: Dict[str, Any]) -> bool:
        """动态添加索引

        Args:
            name: 索引名称（如 "fifo_queue", "vector_faiss"）
            index_type: 索引类型（"faiss", "lsh", "graph", "bm25", "fifo"）
            config: 索引配置（如 dim, max_size 等）

        Returns:
            是否添加成功
        """
        if name in self.indexes:
            logger.warning(f"Index '{name}' already exists")
            return False

        # 通过工厂创建索引
        index = IndexFactory.create(index_type, config)
        self.indexes[name] = index
        self.index_metadata[name] = {
            "type": index_type,
            "config": config,
            "created_at": time.time()
        }

        logger.info(f"Added index '{name}' of type '{index_type}'")
        return True

    def remove_index(self, name: str) -> bool:
        """删除索引（不影响原始数据）"""
        if name not in self.indexes:
            return False

        del self.indexes[name]
        del self.index_metadata[name]
        return True

    def list_indexes(self) -> List[Dict]:
        """列出所有索引"""
        return [
            {"name": name, "type": meta["type"], "config": meta["config"]}
            for name, meta in self.index_metadata.items()
        ]

    # ---------- 索引操作 ----------
    def insert_to_index(self, data_id: str, index_name: str) -> bool:
        """将已有数据加入指定索引"""
        if data_id not in self.raw_data or index_name not in self.indexes:
            return False

        data = self.raw_data[data_id]
        self.indexes[index_name].add(data_id, data["text"], data["metadata"])
        return True

    def remove_from_index(self, data_id: str, index_name: str) -> bool:
        """从索引移除（保留原始数据）"""
        if index_name not in self.indexes:
            return False

        self.indexes[index_name].remove(data_id)
        return True

    def query_by_index(self, index_name: str, query: Any, **params) -> List[str]:
        """通过指定索引查询

        Args:
            index_name: 索引名称
            query: 查询内容（根据索引类型不同：文本/向量/图节点）
            **params: 查询参数（top_k, threshold 等）

        Returns:
            匹配的 data_id 列表
        """
        if index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' not found")

        return self.indexes[index_name].query(query, **params)

    def retrieve(self, index_name: str, query: Any, **params) -> List[Dict]:
        """检索完整数据（query_by_index + get）"""
        data_ids = self.query_by_index(index_name, query, **params)
        return [self.raw_data[id] for id in data_ids if id in self.raw_data]


# ==================== 2. MemoryManager 简化 ====================
class MemoryManager:
    """Collection 生命周期管理器

    职责：
    - 注册/注销 Collection
    - 持久化/加载
    - 懒加载支持
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.collections: Dict[str, UnifiedCollection] = {}
        self.data_dir = data_dir or get_default_data_dir()

    def create_collection(self, name: str, config: Dict = None) -> UnifiedCollection:
        """创建 Collection"""
        if name in self.collections:
            logger.warning(f"Collection '{name}' already exists")
            return self.collections[name]

        collection = UnifiedCollection(name, config or {})
        self.collections[name] = collection
        return collection

    def get_collection(self, name: str) -> Optional[UnifiedCollection]:
        """获取 Collection（支持懒加载）"""
        if name in self.collections:
            return self.collections[name]

        # 尝试从磁盘加载
        if self.has_on_disk(name):
            return self.load_collection(name)

        return None

    def remove_collection(self, name: str) -> bool:
        """删除 Collection"""
        if name in self.collections:
            del self.collections[name]

        # 删除磁盘文件
        collection_path = self._get_collection_path(name)
        if collection_path.exists():
            shutil.rmtree(collection_path)

        return True

    def persist(self, name: str) -> bool:
        """持久化 Collection"""
        if name not in self.collections:
            return False

        collection = self.collections[name]
        save_path = self._get_collection_path(name)
        save_path.mkdir(parents=True, exist_ok=True)

        # 保存原始数据
        with open(save_path / "raw_data.json", "w") as f:
            json.dump(collection.raw_data, f)

        # 保存索引元信息
        with open(save_path / "index_metadata.json", "w") as f:
            json.dump(collection.index_metadata, f)

        # 保存各个索引
        for idx_name, index in collection.indexes.items():
            index.save(save_path / f"index_{idx_name}")

        return True

    def load_collection(self, name: str) -> Optional[UnifiedCollection]:
        """从磁盘加载 Collection"""
        load_path = self._get_collection_path(name)
        if not load_path.exists():
            return None

        # 加载原始数据
        with open(load_path / "raw_data.json", "r") as f:
            raw_data = json.load(f)

        # 加载索引元信息
        with open(load_path / "index_metadata.json", "r") as f:
            index_metadata = json.load(f)

        # 创建 Collection
        collection = UnifiedCollection(name, {})
        collection.raw_data = raw_data
        collection.index_metadata = index_metadata

        # 重建索引
        for idx_name, meta in index_metadata.items():
            index = IndexFactory.create(meta["type"], meta["config"])
            index.load(load_path / f"index_{idx_name}")
            collection.indexes[idx_name] = index

        self.collections[name] = collection
        return collection


# ==================== 3. 索引基类和工厂 ====================
class BaseIndex(ABC):
    """索引基类"""

    @abstractmethod
    def add(self, data_id: str, text: str, metadata: Dict):
        """添加数据到索引"""

    @abstractmethod
    def remove(self, data_id: str):
        """从索引移除"""

    @abstractmethod
    def query(self, query: Any, **params) -> List[str]:
        """查询（返回 data_id 列表）"""

    @abstractmethod
    def save(self, path: Path):
        """保存索引"""

    @abstractmethod
    def load(self, path: Path):
        """加载索引"""


class IndexFactory:
    """索引工厂 - 统一创建各种索引"""

    _registry = {
        "faiss": FAISSIndex,
        "lsh": LSHIndex,
        "graph": GraphIndex,
        "bm25": BM25Index,
        "fifo": FIFOQueueIndex,
        "segment": SegmentIndex,
        # ... 更多索引类型
    }

    @classmethod
    def create(cls, index_type: str, config: Dict) -> BaseIndex:
        if index_type not in cls._registry:
            raise ValueError(f"Unknown index type: {index_type}")

        return cls._registry[index_type](config)

    @classmethod
    def register(cls, index_type: str, index_class: Type[BaseIndex]):
        cls._registry[index_type] = index_class
```

______________________________________________________________________

## 🔄 迁移路径

### Step 1: 保留现有代码

```bash
# 不删除现有 Collection，先添加新的 UnifiedCollection
neuromem/
├── memory_collection/
│   ├── base_collection.py         # 保留
│   ├── vdb_collection.py          # 保留（标记为 deprecated）
│   ├── graph_collection.py        # 保留（标记为 deprecated）
│   ├── hybrid_collection.py       # 保留（标记为 deprecated）
│   └── unified_collection.py      # 新增 ✨
├── memory_manager.py              # 修改（支持两种 Collection）
└── search_engine/
    └── index_factory.py           # 新增 ✨
```

### Step 2: 适配层

```python
# memory_manager.py 增加兼容逻辑
class MemoryManager:
    def create_collection(self, config: Dict) -> BaseMemoryCollection:
        backend_type = config.get("backend_type", "unified")

        if backend_type == "unified":
            # 新方式：使用 UnifiedCollection
            return UnifiedCollection(config)
        elif backend_type == "vdb":
            # 旧方式：兼容现有代码
            return VDBMemoryCollection(config)
        # ... 其他类型
```

### Step 3: 逐步迁移

1. ✅ 新 Service 全部使用 UnifiedCollection
1. ✅ 旧 Service 继续使用原 Collection（不破坏）
1. ✅ 测试通过后，逐个迁移旧 Service
1. ✅ 最终移除旧 Collection

______________________________________________________________________

## 📝 实施任务清单

### Task 1.1: 实现 UnifiedCollection (2天)

**文件**: `neuromem/memory_collection/unified_collection.py`

- [ ] 实现基础数据管理（insert/get/delete）
- [ ] 实现索引管理（add_index/remove_index/list_indexes）
- [ ] 实现索引操作（insert_to_index/remove_from_index）
- [ ] 实现查询方法（query_by_index/retrieve）
- [ ] 单元测试（100+ 测试用例）

### Task 1.2: 实现索引基类和工厂 (1天)

**文件**: `neuromem/search_engine/base_index.py`, `index_factory.py`

- [ ] 定义 BaseIndex 抽象接口
- [ ] 实现 IndexFactory 注册机制
- [ ] 适配现有索引（FAISS, Graph, BM25）
- [ ] 新增索引（FIFO, LSH, Segment）

### Task 1.3: 简化 MemoryManager (0.5天)

**文件**: `neuromem/memory_manager.py`

- [ ] 移除 Collection 类型注册表（只需一种）
- [ ] 简化 create_collection 逻辑
- [ ] 添加兼容层（backend_type 参数）
- [ ] 更新持久化逻辑

### Task 1.4: 测试和验证 (0.5天)

- [ ] 单元测试：UnifiedCollection 所有方法
- [ ] 集成测试：Manager + Collection 配合
- [ ] 性能测试：对比旧 Collection
- [ ] 内存测试：确保无泄漏

______________________________________________________________________

## 🧪 测试用例示例

```python
def test_unified_collection_basic():
    """测试基础数据操作"""
    coll = UnifiedCollection("test", {})

    # 插入数据
    id1 = coll.insert("Hello", {"source": "user"})
    assert id1 in coll.raw_data

    # 获取数据
    data = coll.get(id1)
    assert data["text"] == "Hello"

    # 删除数据
    assert coll.delete(id1)
    assert id1 not in coll.raw_data


def test_dynamic_index_management():
    """测试动态索引管理"""
    coll = UnifiedCollection("test", {})

    # 添加 FAISS 索引
    assert coll.add_index("vector", "faiss", {"dim": 768})
    assert "vector" in coll.indexes

    # 添加 FIFO 索引
    assert coll.add_index("queue", "fifo", {"max_size": 10})
    assert "queue" in coll.indexes

    # 列出索引
    indexes = coll.list_indexes()
    assert len(indexes) == 2

    # 删除索引
    assert coll.remove_index("queue")
    assert "queue" not in coll.indexes


def test_index_operations():
    """测试索引操作"""
    coll = UnifiedCollection("test", {})
    coll.add_index("queue", "fifo", {"max_size": 10})

    # 插入数据到索引
    id1 = coll.insert("Text1", index_names=["queue"])
    assert coll.indexes["queue"].contains(id1)

    # 从索引移除（数据保留）
    coll.remove_from_index(id1, "queue")
    assert not coll.indexes["queue"].contains(id1)
    assert id1 in coll.raw_data

    # 重新加入索引
    coll.insert_to_index(id1, "queue")
    assert coll.indexes["queue"].contains(id1)
```

______________________________________________________________________

## 📊 预期效果

| 指标              | 当前              | 重构后            |
| ----------------- | ----------------- | ----------------- |
| Collection 类数量 | 4+                | 1                 |
| 代码行数          | ~3000             | ~1500             |
| 扩展新索引        | 需修改 Collection | 只需实现 Index 类 |
| 测试覆盖率        | ~60%              | >90%              |
| 性能开销          | 基准              | \<5%              |

______________________________________________________________________

**下一步**: 阅读 `02_SERVICE_IMPLEMENTATION_PLAN.md` 了解 MemoryService 层实现
