# 测试策略

> **目标**: 确保重构后系统功能完整、性能稳定
>
> **原则**: 单元测试 → 集成测试 → 端到端测试 → 性能测试

______________________________________________________________________

## 🎯 测试目标

### 测试覆盖率目标

| 层级               | 覆盖率目标    | 测试类型            |
| ------------------ | ------------- | ------------------- |
| neuromem (L2)      | >90%          | 单元测试            |
| MemoryService (L5) | >85%          | 单元测试 + 集成测试 |
| 端到端             | 100% 功能覆盖 | E2E 测试            |
| 性能               | 基准 ±5%      | Benchmark           |

### 测试分层

```
┌─────────────────────────────────────────┐
│  E2E Tests (端到端测试)                   │  ← 验证完整业务流程
│  - 13 个 Service 完整使用流程              │
│  - 配置加载 → Service 创建 → 增删查改       │
├─────────────────────────────────────────┤
│  Integration Tests (集成测试)             │  ← 验证组件协作
│  - Service + Collection                  │
│  - Collection + Indexes                  │
│  - Manager + Persistence                 │
├─────────────────────────────────────────┤
│  Unit Tests (单元测试)                    │  ← 验证单个组件
│  - UnifiedCollection                     │
│  - BaseIndex 实现                         │
│  - MemoryService 实现                     │
├─────────────────────────────────────────┤
│  Performance Tests (性能测试)             │  ← 验证性能指标
│  - 插入/检索速度                          │
│  - 内存占用                              │
│  - 并发能力                              │
└─────────────────────────────────────────┘
```

______________________________________________________________________

## 🧪 单元测试

### neuromem 层测试

#### UnifiedCollection 测试

```python
# tests/unit/test_unified_collection.py

import pytest
from sage.middleware.components.sage_mem.neuromem import (
    UnifiedCollection, MemoryManager
)


class TestUnifiedCollectionBasic:
    """测试 UnifiedCollection 基础功能"""

    def setup_method(self):
        """每个测试前创建新 Collection"""
        self.coll = UnifiedCollection("test", {})

    def test_insert_and_get(self):
        """测试插入和获取"""
        data_id = self.coll.insert("Hello World", {"source": "test"})

        # 验证数据存在
        assert data_id in self.coll.raw_data

        # 验证数据正确
        data = self.coll.get(data_id)
        assert data["text"] == "Hello World"
        assert data["metadata"]["source"] == "test"
        assert "created_at" in data

    def test_insert_without_metadata(self):
        """测试无元数据插入"""
        data_id = self.coll.insert("No metadata")
        data = self.coll.get(data_id)

        assert data["text"] == "No metadata"
        assert data["metadata"] == {}

    def test_delete(self):
        """测试删除"""
        data_id = self.coll.insert("To be deleted")

        # 删除前存在
        assert self.coll.get(data_id) is not None

        # 删除
        assert self.coll.delete(data_id) is True

        # 删除后不存在
        assert self.coll.get(data_id) is None

    def test_delete_nonexistent(self):
        """测试删除不存在的数据"""
        assert self.coll.delete("nonexistent_id") is False


class TestUnifiedCollectionIndexManagement:
    """测试索引管理"""

    def setup_method(self):
        self.coll = UnifiedCollection("test", {})

    def test_add_index(self):
        """测试添加索引"""
        result = self.coll.add_index(
            "vector",
            "faiss",
            {"dim": 768}
        )

        assert result is True
        assert "vector" in self.coll.indexes
        assert self.coll.index_metadata["vector"]["type"] == "faiss"

    def test_add_duplicate_index(self):
        """测试重复添加索引"""
        self.coll.add_index("vector", "faiss", {"dim": 768})

        # 再次添加应该失败
        result = self.coll.add_index("vector", "faiss", {"dim": 768})
        assert result is False

    def test_remove_index(self):
        """测试删除索引"""
        self.coll.add_index("vector", "faiss", {"dim": 768})

        # 删除
        assert self.coll.remove_index("vector") is True
        assert "vector" not in self.coll.indexes

    def test_remove_nonexistent_index(self):
        """测试删除不存在的索引"""
        assert self.coll.remove_index("nonexistent") is False

    def test_list_indexes(self):
        """测试列出索引"""
        self.coll.add_index("index1", "faiss", {"dim": 768})
        self.coll.add_index("index2", "bm25", {})

        indexes = self.coll.list_indexes()
        assert len(indexes) == 2

        index_names = [idx["name"] for idx in indexes]
        assert "index1" in index_names
        assert "index2" in index_names


class TestUnifiedCollectionIndexOperations:
    """测试索引操作"""

    def setup_method(self):
        self.coll = UnifiedCollection("test", {})
        self.coll.add_index("queue", "fifo", {"max_size": 10})

    def test_insert_to_specific_index(self):
        """测试插入到指定索引"""
        data_id = self.coll.insert(
            "Test",
            index_names=["queue"]
        )

        # 数据存在
        assert data_id in self.coll.raw_data

        # 索引包含数据
        queue_index = self.coll.indexes["queue"]
        assert queue_index.contains(data_id)

    def test_insert_to_index_later(self):
        """测试事后加入索引"""
        # 先插入数据（不加索引）
        data_id = self.coll.insert("Test", index_names=[])

        # 后加入索引
        result = self.coll.insert_to_index(data_id, "queue")
        assert result is True

        # 验证索引包含数据
        queue_index = self.coll.indexes["queue"]
        assert queue_index.contains(data_id)

    def test_remove_from_index(self):
        """测试从索引移除（保留数据）"""
        data_id = self.coll.insert("Test", index_names=["queue"])

        # 从索引移除
        result = self.coll.remove_from_index(data_id, "queue")
        assert result is True

        # 数据仍存在
        assert self.coll.get(data_id) is not None

        # 索引不包含
        queue_index = self.coll.indexes["queue"]
        assert not queue_index.contains(data_id)

    def test_delete_removes_from_all_indexes(self):
        """测试删除数据同时从所有索引移除"""
        self.coll.add_index("vector", "faiss", {"dim": 768})

        data_id = self.coll.insert("Test", index_names=["queue", "vector"])

        # 删除数据
        self.coll.delete(data_id)

        # 所有索引都不包含
        assert not self.coll.indexes["queue"].contains(data_id)
        assert not self.coll.indexes["vector"].contains(data_id)


@pytest.mark.parametrize("index_type,config", [
    ("faiss", {"dim": 768}),
    ("lsh", {"dim": 768, "num_tables": 10}),
    ("bm25", {}),
    ("fifo", {"max_size": 10}),
    ("segment", {"strategy": "time", "segment_size": 50}),
])
def test_all_index_types(index_type, config):
    """参数化测试所有索引类型"""
    coll = UnifiedCollection("test", {})

    # 添加索引
    result = coll.add_index(f"{index_type}_index", index_type, config)
    assert result is True

    # 插入数据
    data_id = coll.insert("Test data", index_names=[f"{index_type}_index"])
    assert data_id is not None
```

#### MemoryManager 测试

```python
# tests/unit/test_memory_manager.py

import pytest
import tempfile
import shutil
from pathlib import Path
from sage.middleware.components.sage_mem.neuromem import (
    MemoryManager, UnifiedCollection
)


class TestMemoryManagerBasic:
    """测试 MemoryManager 基础功能"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = MemoryManager(str(self.temp_dir))

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_create_collection(self):
        """测试创建 Collection"""
        coll = self.manager.create_collection("test", {})

        assert coll is not None
        assert coll.name == "test"
        assert "test" in self.manager.collections

    def test_create_duplicate_collection(self):
        """测试重复创建（应返回现有）"""
        coll1 = self.manager.create_collection("test", {})
        coll2 = self.manager.create_collection("test", {})

        assert coll1 is coll2

    def test_get_collection(self):
        """测试获取 Collection"""
        self.manager.create_collection("test", {})

        coll = self.manager.get_collection("test")
        assert coll is not None
        assert coll.name == "test"

    def test_get_nonexistent_collection(self):
        """测试获取不存在的 Collection"""
        coll = self.manager.get_collection("nonexistent")
        assert coll is None

    def test_remove_collection(self):
        """测试删除 Collection"""
        self.manager.create_collection("test", {})

        result = self.manager.remove_collection("test")
        assert result is True
        assert "test" not in self.manager.collections


class TestMemoryManagerPersistence:
    """测试持久化"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = MemoryManager(str(self.temp_dir))

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_persist_collection(self):
        """测试持久化 Collection"""
        coll = self.manager.create_collection("test", {})
        coll.add_index("vector", "faiss", {"dim": 768})
        coll.insert("Hello World")

        # 持久化
        result = self.manager.persist("test")
        assert result is True

        # 验证文件存在
        coll_path = self.temp_dir / "test"
        assert coll_path.exists()
        assert (coll_path / "raw_data.json").exists()
        assert (coll_path / "index_metadata.json").exists()

    def test_load_collection(self):
        """测试加载 Collection"""
        # 1. 创建 + 持久化
        coll = self.manager.create_collection("test", {})
        coll.add_index("vector", "faiss", {"dim": 768})
        data_id = coll.insert("Hello World", {"source": "test"})
        self.manager.persist("test")

        # 2. 创建新 Manager（模拟重启）
        new_manager = MemoryManager(str(self.temp_dir))

        # 3. 加载
        loaded_coll = new_manager.load_collection("test")
        assert loaded_coll is not None

        # 4. 验证数据完整
        data = loaded_coll.get(data_id)
        assert data["text"] == "Hello World"
        assert data["metadata"]["source"] == "test"

        # 5. 验证索引恢复
        assert "vector" in loaded_coll.indexes
```

______________________________________________________________________

### MemoryService 层测试

```python
# tests/unit/test_fifo_queue_service.py

import pytest
from sage.middleware.components.sage_mem.neuromem import UnifiedCollection
from sage.middleware.components.sage_mem.services import FIFOQueueService


class TestFIFOQueueService:
    """测试 FIFO Queue Service"""

    def setup_method(self):
        self.collection = UnifiedCollection("test", {})
        self.service = FIFOQueueService(
            self.collection,
            {"max_size": 3}  # 最多保留 3 条
        )

    def test_insert_within_limit(self):
        """测试容量内插入"""
        id1 = self.service.insert("Text 1")
        id2 = self.service.insert("Text 2")

        # 所有数据都在
        assert self.service.get(id1) is not None
        assert self.service.get(id2) is not None

    def test_insert_exceeds_limit(self):
        """测试超容量插入（FIFO 淘汰）"""
        id1 = self.service.insert("Text 1")
        id2 = self.service.insert("Text 2")
        id3 = self.service.insert("Text 3")
        id4 = self.service.insert("Text 4")  # 会淘汰 id1

        # id1 被淘汰
        assert self.service.get(id1) is None

        # id2, id3, id4 仍在
        assert self.service.get(id2) is not None
        assert self.service.get(id3) is not None
        assert self.service.get(id4) is not None

    def test_retrieve_recent(self):
        """测试检索最近数据"""
        self.service.insert("Text 1")
        self.service.insert("Text 2")
        self.service.insert("Text 3")

        # 检索最近 2 条
        results = self.service.retrieve("", top_k=2)

        assert len(results) == 2
        # 应该是 Text 3 和 Text 2（最新的）
        texts = [r["text"] for r in results]
        assert "Text 3" in texts
        assert "Text 2" in texts
```

______________________________________________________________________

## 🔗 集成测试

```python
# tests/integration/test_service_collection_integration.py

import pytest
from sage.middleware.components.sage_mem.neuromem import (
    MemoryManager, UnifiedCollection
)
from sage.middleware.components.sage_mem.services import (
    MemoryServiceRegistry
)


class TestServiceCollectionIntegration:
    """测试 Service + Collection 集成"""

    def setup_method(self):
        self.manager = MemoryManager()

    def test_create_service_via_registry(self):
        """测试通过 Registry 创建 Service"""
        # 1. 创建 Collection
        collection = self.manager.create_collection("test", {})

        # 2. 创建 Service
        service = MemoryServiceRegistry.create(
            "partitional.fifo_queue",
            collection,
            {"max_size": 10}
        )

        # 3. 使用 Service
        data_id = service.insert("Test")
        results = service.retrieve("Test", top_k=5)

        assert len(results) > 0
        assert results[0]["text"] == "Test"

    def test_persist_and_reload_with_service(self):
        """测试持久化后重新加载"""
        # 1. 创建 Service + 插入数据
        collection = self.manager.create_collection("test", {})
        service = MemoryServiceRegistry.create(
            "partitional.fifo_queue",
            collection,
            {"max_size": 10}
        )
        service.insert("Test 1")
        service.insert("Test 2")

        # 2. 持久化
        self.manager.persist("test")

        # 3. 新 Manager 加载
        new_manager = MemoryManager()
        loaded_collection = new_manager.load_collection("test")

        # 4. 创建新 Service
        new_service = MemoryServiceRegistry.create(
            "partitional.fifo_queue",
            loaded_collection,
            {"max_size": 10}
        )

        # 5. 验证数据
        results = new_service.retrieve("", top_k=10)
        assert len(results) == 2


@pytest.mark.parametrize("service_name", [
    "partitional.fifo_queue",
    "partitional.lsh_hash",
    "partitional.segment",
    "partitional.feature_summary_vectorstore_combination",
    "partitional.inverted_vectorstore_combination",
    "hierarchical.semantic_inverted_knowledge_graph",
    # ... 其他 Service
])
def test_all_services_basic_flow(service_name):
    """参数化测试所有 Service 基础流程"""
    manager = MemoryManager()
    collection = manager.create_collection("test", {})

    # 创建 Service
    service = MemoryServiceRegistry.create(
        service_name,
        collection,
        {"embedding_dim": 768, "max_size": 10}
    )

    # 插入
    data_id = service.insert("Test data")
    assert data_id is not None

    # 检索
    results = service.retrieve("Test", top_k=5)
    assert isinstance(results, list)
```

______________________________________________________________________

## 🏃 端到端测试

```python
# tests/e2e/test_complete_workflow.py

import yaml
from pathlib import Path
from sage.middleware.components.sage_mem import (
    create_memory_service_from_config
)


def test_fifo_queue_complete_workflow():
    """测试 FIFO Queue 完整工作流"""
    # 1. 加载配置
    config_path = Path("configs/partitional_fifo_queue.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # 2. 创建 Service
    service = create_memory_service_from_config(config)

    # 3. 插入数据
    for i in range(5):
        service.insert(f"Message {i}", {"index": i})

    # 4. 检索
    results = service.retrieve("Message", top_k=3)
    assert len(results) == 3

    # 5. 删除
    data_id = results[0]["id"]
    assert service.delete(data_id)

    # 6. 验证删除
    results = service.retrieve("Message", top_k=10)
    assert len(results) == 4


def test_combination_service_workflow():
    """测试组合型 Service 工作流"""
    config_path = Path("configs/partitional_feature_summary_vectorstore_combination.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    service = create_memory_service_from_config(config)

    # 插入长文本
    long_text = "This is a very long document. " * 50
    service.insert(long_text, {"type": "document"})

    # 检索（应该触发三级检索）
    results = service.retrieve("long document", top_k=5)
    assert len(results) > 0

    # 详细检索
    detailed_results = service.retrieve(
        "long document",
        top_k=5,
        detailed=True
    )
    assert len(detailed_results) > 0
```

______________________________________________________________________

## ⚡ 性能测试

```python
# tests/performance/test_benchmark.py

import time
import pytest
from sage.middleware.components.sage_mem.neuromem import UnifiedCollection
from sage.middleware.components.sage_mem.services import FIFOQueueService


class TestPerformance:
    """性能测试"""

    def test_insert_performance(self):
        """测试插入性能（目标: 10000 条/秒）"""
        collection = UnifiedCollection("test", {})
        service = FIFOQueueService(collection, {"max_size": 10000})

        start = time.time()
        for i in range(10000):
            service.insert(f"Text {i}")
        elapsed = time.time() - start

        # 断言 10000 条在 1 秒内完成
        assert elapsed < 1.0, f"Insert too slow: {elapsed}s for 10000 items"

        print(f"✅ Insert: {10000 / elapsed:.0f} items/sec")

    def test_retrieve_performance(self):
        """测试检索性能（目标: 1000 查询/秒）"""
        collection = UnifiedCollection("test", {})
        service = FIFOQueueService(collection, {"max_size": 1000})

        # 插入数据
        for i in range(1000):
            service.insert(f"Text {i}")

        # 检索性能
        start = time.time()
        for _ in range(1000):
            service.retrieve("Text", top_k=5)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Retrieve too slow: {elapsed}s for 1000 queries"

        print(f"✅ Retrieve: {1000 / elapsed:.0f} queries/sec")

    @pytest.mark.slow
    def test_large_dataset_performance(self):
        """测试大数据集性能（100K 条）"""
        collection = UnifiedCollection("test", {})
        service = FIFOQueueService(collection, {"max_size": 100000})

        # 插入 100K
        start = time.time()
        for i in range(100000):
            service.insert(f"Text {i}")
        insert_time = time.time() - start

        # 检索
        start = time.time()
        results = service.retrieve("Text", top_k=100)
        retrieve_time = time.time() - start

        print(f"Insert 100K: {insert_time:.2f}s")
        print(f"Retrieve: {retrieve_time:.3f}s")

        # 性能要求
        assert insert_time < 10.0  # 10 秒内插入 100K
        assert retrieve_time < 0.1  # 100ms 内检索
```

______________________________________________________________________

## 📝 实施任务清单

### Task 4.1: 单元测试 (3天)

- [ ] UnifiedCollection 测试（20+ 测试用例）
- [ ] MemoryManager 测试（10+ 测试用例）
- [ ] BaseIndex 实现测试（每种索引 5+ 用例）
- [ ] BaseMemoryService 测试（5+ 测试用例）
- [ ] 每个 Service 实现测试（每个 5+ 用例）

### Task 4.2: 集成测试 (1天)

- [ ] Service + Collection 集成测试
- [ ] Manager + Persistence 集成测试
- [ ] Registry + Factory 集成测试

### Task 4.3: 端到端测试 (1天)

- [ ] 13 个 Service 完整流程测试
- [ ] 配置加载 + Service 创建测试
- [ ] 持久化 + 重启恢复测试

### Task 4.4: 性能测试 (0.5天)

- [ ] 插入性能基准测试
- [ ] 检索性能基准测试
- [ ] 大数据集性能测试
- [ ] 内存占用测试

### Task 4.5: CI 集成 (0.5天)

- [ ] 配置 pytest + coverage
- [ ] 配置 GitHub Actions
- [ ] 添加性能回归检测

______________________________________________________________________

## 🔍 测试工具配置

### pytest.ini

```ini
# tools/pytest.ini

[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 覆盖率
addopts =
    --cov=packages/sage-middleware/src/sage/middleware/components/sage_mem
    --cov-report=html
    --cov-report=term
    --cov-fail-under=85

# 标记
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance benchmarks
```

### GitHub Actions

```yaml
# .github/workflows/test-memory-service.yml

name: Memory Service Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

______________________________________________________________________

**下一步**: 阅读 `05_IMPLEMENTATION_CHECKLIST.md` 了解具体实施步骤
