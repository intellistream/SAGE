# TODO Part 3: MemoryManager 重构

> **状态**: ✅ **已完成** (2024-12)

## 背景

`MemoryManager` 是 Collection 的统一管理器：

```
MemoryManager
├── collections: dict[name, Collection]        # 内存中的 Collection
├── collection_metadata: dict[name, metadata]  # 元数据
├── collection_status: dict[name, status]      # 状态（loaded / on_disk）
└── data_dir: str                              # 持久化目录
```

**核心职责**：

- 创建 Collection（根据 backend_type）
- 管理 Collection 生命周期
- 懒加载支持
- 持久化管理

______________________________________________________________________

## 完成情况汇总

| 子任务                  | 状态    | 说明                                           |
| ----------------------- | ------- | ---------------------------------------------- |
| 3.1 Collection 创建逻辑 | ✅ 完成 | 使用注册表 + 工厂模式                          |
| 3.2 懒加载优化          | ✅ 完成 | 统一使用注册表获取类                           |
| 3.3 持久化路径统一      | ✅ 完成 | 支持新旧路径兼容                               |
| 3.4 批量操作            | ✅ 完成 | list_collections, unload_collection, clear_all |

______________________________________________________________________

## 任务概述

本任务负责优化 MemoryManager，解决现有问题。

**涉及文件**：

- `neuromem/memory_manager.py`

______________________________________________________________________

## 3.1 修复 Collection 创建逻辑 ✅

**原问题**：

```python
# 旧代码 - 类型判断硬编码
if "vdb" in backend_type:
    new_collection = VDBMemoryCollection(vdb_config)
elif "kv" in backend_type:
    new_collection = KVMemoryCollection(kv_config)
elif "graph" in backend_type:
    new_collection = GraphMemoryCollection(name)  # ⚠️ 参数格式不一致！
```

**问题**：

1. 字符串匹配不严谨（`"my_vdb_store"` 也会匹配）
1. 构造函数参数不统一
1. 无法扩展新类型

**改进方案**：使用注册表 + 工厂模式

```python
class MemoryManager:
    # 类级别注册表
    _collection_registry: dict[str, type[BaseMemoryCollection]] = {
        "vdb": VDBMemoryCollection,
        "vector": VDBMemoryCollection,
        "kv": KVMemoryCollection,
        "text": KVMemoryCollection,
        "graph": GraphMemoryCollection,
    }

    @classmethod
    def register_collection_type(cls, type_name: str, collection_class: type):
        """注册新的 Collection 类型"""
        cls._collection_registry[type_name.lower()] = collection_class

    def create_collection(self, config: dict[str, Any]) -> BaseMemoryCollection | None:
        name = config.get("name")
        if not name:
            self.logger.warning("`name` is required")
            return None

        if name in self.collection_metadata:
            self.logger.warning(f"Collection '{name}' already exists")
            return None

        backend_type = config.get("backend_type", "").lower()

        # 精确匹配
        collection_class = self._collection_registry.get(backend_type)
        if not collection_class:
            self.logger.warning(f"Unknown backend_type: {backend_type}")
            return None

        # 统一使用 config 创建（Part 1 完成后所有 Collection 都支持）
        new_collection = collection_class(config)

        self.collections[name] = new_collection
        self.collection_metadata[name] = {
            "description": config.get("description", ""),
            "backend_type": backend_type,
        }
        self.collection_status[name] = "loaded"

        return new_collection
```

**验收标准**：

- [ ] 使用注册表替代 if-elif 链
- [ ] 支持 `register_collection_type()` 扩展
- [ ] 所有 Collection 使用统一的 `config` 创建

______________________________________________________________________

## 3.2 优化懒加载逻辑

**当前问题**：

- 懒加载时创建新实例，可能丢失运行时状态
- 每次访问都检查状态，性能开销

**改进方案**：

```python
def get_collection(self, name: str) -> BaseMemoryCollection | None:
    """获取 Collection，支持懒加载"""

    # 1. 优先返回内存中的实例
    if name in self.collections:
        return self.collections[name]

    # 2. 检查是否在磁盘上
    if name not in self.collection_metadata:
        self.logger.warning(f"Collection '{name}' not found")
        return None

    # 3. 懒加载
    self.logger.info(f"Lazy loading collection '{name}' from disk")
    return self._load_collection(name)

def _load_collection(self, name: str) -> BaseMemoryCollection | None:
    """从磁盘加载 Collection"""
    metadata = self.collection_metadata[name]
    backend_type = metadata["backend_type"]

    collection_class = self._collection_registry.get(backend_type)
    if not collection_class:
        self.logger.error(f"Cannot load: unknown backend_type '{backend_type}'")
        return None

    # 使用 Collection 自己的 load 方法
    load_path = os.path.join(self.data_dir, backend_type + "_collection", name)

    try:
        collection = collection_class.load(name, load_path)
        self.collections[name] = collection
        self.collection_status[name] = "loaded"
        return collection
    except Exception as e:
        self.logger.error(f"Failed to load collection '{name}': {e}")
        return None
```

**验收标准**：

- [ ] 懒加载正确工作
- [ ] 加载后的 Collection 状态完整

______________________________________________________________________

## 3.3 统一持久化路径

**当前问题**：

- VDB: `data_dir/vdb_collection/{name}/`
- KV: `data_dir/kv_collection/{name}/`
- Graph: 自定义路径

**建议**：统一为 `data_dir/collections/{backend_type}/{name}/`

```python
def _get_collection_path(self, name: str, backend_type: str) -> str:
    """获取 Collection 的存储路径"""
    return os.path.join(self.data_dir, "collections", backend_type, name)

def store_collection(self, name: str) -> dict[str, Any] | None:
    """持久化单个 Collection"""
    if name not in self.collections:
        self.logger.warning(f"Collection '{name}' not in memory")
        return None

    collection = self.collections[name]
    backend_type = self.collection_metadata[name]["backend_type"]
    path = self._get_collection_path(name, backend_type)

    os.makedirs(path, exist_ok=True)
    return collection.store(path)

def store_all(self) -> dict[str, Any]:
    """持久化所有 Collection + Manager 自身状态"""
    results = {}

    for name in self.collections:
        result = self.store_collection(name)
        results[name] = result

    # 保存 Manager 元数据
    manager_state = {
        "collection_metadata": self.collection_metadata,
        "collection_status": {k: "on_disk" for k in self.collection_metadata},
    }

    with open(self.manager_path, "w") as f:
        json.dump(manager_state, f, indent=2)

    return results
```

**验收标准**：

- [ ] 路径结构统一
- [ ] Manager 状态正确保存
- [ ] 能正确加载旧格式数据（向后兼容）

______________________________________________________________________

## 3.4 添加 Collection 批量操作

**新增功能**：

```python
def list_collections(
    self,
    backend_type: str | None = None,
    status: str | None = None
) -> list[dict[str, Any]]:
    """
    列出所有 Collection

    Args:
        backend_type: 过滤类型（可选）
        status: 过滤状态（可选）

    Returns:
        [{"name": ..., "backend_type": ..., "status": ..., "description": ...}, ...]
    """
    result = []
    for name, metadata in self.collection_metadata.items():
        if backend_type and metadata["backend_type"] != backend_type:
            continue
        if status and self.collection_status.get(name) != status:
            continue
        result.append({
            "name": name,
            "backend_type": metadata["backend_type"],
            "status": self.collection_status.get(name, "unknown"),
            "description": metadata.get("description", ""),
        })
    return result

def unload_collection(self, name: str) -> bool:
    """
    从内存卸载 Collection（保留磁盘数据）
    用于内存管理
    """
    if name not in self.collections:
        return False

    # 先持久化
    self.store_collection(name)

    # 从内存删除
    del self.collections[name]
    self.collection_status[name] = "on_disk"

    self.logger.info(f"Unloaded collection '{name}'")
    return True

def clear_all(self, include_disk: bool = False):
    """
    清空所有 Collection

    Args:
        include_disk: 是否同时删除磁盘数据
    """
    self.collections.clear()

    if include_disk:
        for name, metadata in self.collection_metadata.items():
            backend_type = metadata["backend_type"]
            path = self._get_collection_path(name, backend_type)
            if os.path.exists(path):
                shutil.rmtree(path)

        self.collection_metadata.clear()
        self.collection_status.clear()

        if os.path.exists(self.manager_path):
            os.remove(self.manager_path)
```

**验收标准**：

- [ ] `list_collections()` 支持过滤
- [ ] `unload_collection()` 正确卸载
- [ ] `clear_all()` 正确清理

______________________________________________________________________

## 依赖关系

- 依赖 Part 1（Collection 接口统一）

______________________________________________________________________

## 预估工时

| 子任务                  | 预估时间 |
| ----------------------- | -------- |
| 3.1 Collection 创建逻辑 | 2h       |
| 3.2 懒加载优化          | 1h       |
| 3.3 持久化路径统一      | 2h       |
| 3.4 批量操作            | 1h       |
| 测试 & 验证             | 2h       |
| **总计**                | **8h**   |

______________________________________________________________________

## 参考资料

- 现有 `memory_manager.py`（399 行）
