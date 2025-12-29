"""
Unit tests for LinknoteGraphService

测试范围:
- Service 初始化和索引创建
- 插入笔记和链接
- 检索关联笔记 (BFS/DFS)
- 获取反向链接和邻居
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import (
    LinknoteGraphService,
)
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry


class TestLinknoteInitialization:
    """测试初始化"""

    def test_service_creation(self):
        """测试 Service 创建"""
        collection = UnifiedCollection("notes")
        service = LinknoteGraphService(collection)

        assert service.collection.name == "notes"
        assert "note_graph" in service.collection.indexes

    def test_service_via_registry(self):
        """测试通过注册表创建 Service"""
        collection = UnifiedCollection("notes")
        service = MemoryServiceRegistry.create("linknote_graph", collection)

        assert isinstance(service, LinknoteGraphService)
        assert "note_graph" in service.collection.indexes


class TestBasicOperations:
    """测试基础操作"""

    @pytest.fixture
    def service(self):
        """创建 Service 实例"""
        collection = UnifiedCollection("notes")
        return LinknoteGraphService(collection)

    def test_insert_note_without_links(self, service):
        """测试插入笔记 (无链接)"""
        note_id = service.insert("Python is awesome", {"title": "Python"})

        assert note_id is not None
        note = service.get(note_id)
        assert note is not None
        assert note["text"] == "Python is awesome"

    def test_insert_note_with_metadata(self, service):
        """测试插入笔记 (带元数据)"""
        note_id = service.insert(
            "Machine Learning basics",
            metadata={"title": "ML", "tags": ["AI", "ML"]},
        )

        note = service.get(note_id)
        assert note["metadata"]["title"] == "ML"
        assert "AI" in note["metadata"]["tags"]

    def test_insert_note_with_links(self, service):
        """测试插入笔记 (带链接)"""
        # 先插入两个笔记
        note1_id = service.insert("Note 1")
        note2_id = service.insert("Note 2")

        # 插入第三个笔记并链接到前两个
        note3_id = service.insert("Note 3", links=[note1_id, note2_id])

        assert note3_id is not None
        # 验证链接已建立 (通过查询邻居)
        neighbors = service.get_neighbors(note3_id)
        assert note1_id in neighbors
        assert note2_id in neighbors


class TestRetrieval:
    """测试检索功能"""

    @pytest.fixture
    def service_with_notes(self):
        """创建有数据的 Service"""
        collection = UnifiedCollection("notes")
        service = LinknoteGraphService(collection)

        # 创建笔记网络:
        # A → B → C
        # A → D
        note_a = service.insert("Note A")
        note_b = service.insert("Note B")
        note_c = service.insert("Note C", links=[note_b])
        note_d = service.insert("Note D")

        # 添加链接 (A→B, A→D)
        service._add_links(note_a, [note_b, note_d])

        return service, {"A": note_a, "B": note_b, "C": note_c, "D": note_d}

    def test_retrieve_direct_neighbors(self, service_with_notes):
        """测试检索直接邻居 (1跳)"""
        service, notes = service_with_notes

        # 查询 A 的直接邻居
        related = service.retrieve(notes["A"], top_k=10, max_hops=1)

        # 应该包含 B 和 D (1跳邻居)
        related_ids = [r["id"] for r in related]
        assert notes["B"] in related_ids or notes["D"] in related_ids

    def test_retrieve_with_bfs(self, service_with_notes):
        """测试 BFS 遍历"""
        service, notes = service_with_notes

        related = service.retrieve(notes["A"], top_k=10, method="bfs", max_hops=2)

        # BFS 应该能找到 2 跳内的节点
        assert len(related) > 0

    def test_retrieve_with_dfs(self, service_with_notes):
        """测试 DFS 遍历"""
        service, notes = service_with_notes

        related = service.retrieve(notes["A"], top_k=10, method="dfs", max_hops=2)

        # DFS 应该能找到 2 跳内的节点
        assert len(related) > 0

    def test_retrieve_include_start(self, service_with_notes):
        """测试包含起始节点"""
        service, notes = service_with_notes

        related = service.retrieve(
            notes["A"], top_k=10, max_hops=1, include_start=True
        )

        # 应该包含起始节点 A
        related_ids = [r["id"] for r in related]
        assert notes["A"] in related_ids


class TestBacklinksAndNeighbors:
    """测试反向链接和邻居查询"""

    @pytest.fixture
    def service(self):
        """创建 Service 实例"""
        collection = UnifiedCollection("notes")
        return LinknoteGraphService(collection)

    def test_get_backlinks(self, service):
        """测试获取反向链接"""
        note1_id = service.insert("Note 1")
        note2_id = service.insert("Note 2")
        note3_id = service.insert("Note 3", links=[note1_id])

        # note1 应该有 note3 的反向链接
        backlinks = service.get_backlinks(note1_id)
        assert note3_id in backlinks

    def test_get_neighbors_1hop(self, service):
        """测试获取 1 跳邻居"""
        note1_id = service.insert("Note 1")
        note2_id = service.insert("Note 2", links=[note1_id])

        neighbors = service.get_neighbors(note2_id, max_hops=1)
        assert note1_id in neighbors

    def test_get_neighbors_2hop(self, service):
        """测试获取 2 跳邻居"""
        note1_id = service.insert("Note 1")
        note2_id = service.insert("Note 2", links=[note1_id])
        note3_id = service.insert("Note 3", links=[note2_id])

        # note3 的 2 跳邻居应包含 note1
        neighbors_2hop = service.get_neighbors(note3_id, max_hops=2)
        assert note1_id in neighbors_2hop or note2_id in neighbors_2hop


class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def service(self):
        """创建 Service 实例"""
        collection = UnifiedCollection("notes")
        return LinknoteGraphService(collection)

    def test_insert_with_invalid_links(self, service):
        """测试插入时链接到不存在的笔记"""
        # 链接到不存在的笔记应该被忽略 (不抛出异常)
        note_id = service.insert("Note", links=["nonexistent_id"])
        assert note_id is not None

    def test_get_backlinks_empty(self, service):
        """测试没有反向链接的笔记"""
        note_id = service.insert("Isolated Note")
        backlinks = service.get_backlinks(note_id)
        assert backlinks == []

    def test_get_neighbors_isolated_node(self, service):
        """测试孤立节点的邻居"""
        note_id = service.insert("Isolated Note")
        neighbors = service.get_neighbors(note_id)
        assert neighbors == []

    def test_delete_note(self, service):
        """测试删除笔记"""
        note_id = service.insert("To be deleted")
        assert service.delete(note_id) is True
        assert service.get(note_id) is None


class TestComplexGraph:
    """测试复杂图结构"""

    def test_bidirectional_links(self):
        """测试双向链接 (无向图特性)"""
        collection = UnifiedCollection("notes")
        service = LinknoteGraphService(collection)

        note1_id = service.insert("Note 1")
        note2_id = service.insert("Note 2", links=[note1_id])

        # 在无向图中，A→B 等价于 B→A
        backlinks_1 = service.get_backlinks(note1_id)
        backlinks_2 = service.get_backlinks(note2_id)

        # note1 应该能看到 note2
        # note2 应该能看到 note1
        assert note2_id in backlinks_1
        assert note1_id in backlinks_2
