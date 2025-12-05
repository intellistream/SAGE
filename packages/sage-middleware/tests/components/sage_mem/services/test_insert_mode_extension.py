"""
Unit tests for insert_mode extension (R4: MemoryInsert 插入模式扩展)

Tests for:
1. Passive insert mode (default behavior)
2. Active insert mode with insert_params
3. Backward compatibility
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    pass


class TestHierarchicalMemoryServiceInsertMode:
    """Test HierarchicalMemoryService insert mode extension"""

    @patch("sage.middleware.components.sage_mem.services.hierarchical_memory_service.MemoryManager")
    def test_passive_insert_default_tier(self, mock_manager_class):
        """Test passive insert uses default tier (first tier)"""
        from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
            HierarchicalMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection creation with insert returning stable_id
        mock_collection = MagicMock()
        mock_collection.index_info = {}
        mock_collection.insert.return_value = "stable_id_123"
        mock_manager.create_collection.return_value = mock_collection

        service = HierarchicalMemoryService(tier_mode="two_tier")
        # Override tier_capacities to avoid MagicMock comparison
        service.tier_capacities = {"stm": -1, "ltm": -1}

        # Passive insert (default)
        entry_id = service.insert(
            entry="test entry",
            vector=[0.1] * 384,
            metadata={"test": "value"},
        )

        assert entry_id is not None

    @patch("sage.middleware.components.sage_mem.services.hierarchical_memory_service.MemoryManager")
    def test_active_insert_to_ltm(self, mock_manager_class):
        """Test active insert with target_tier=ltm"""
        from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
            HierarchicalMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection creation with insert returning stable_id
        mock_collection = MagicMock()
        mock_collection.index_info = {}
        mock_collection.insert.return_value = "stable_id_456"
        mock_manager.create_collection.return_value = mock_collection

        service = HierarchicalMemoryService(tier_mode="two_tier")
        # Override tier_capacities to avoid MagicMock comparison
        service.tier_capacities = {"stm": -1, "ltm": -1}

        # Active insert with target_tier
        entry_id = service.insert(
            entry="important memory",
            vector=[0.1] * 384,
            metadata={},
            insert_mode="active",
            insert_params={"target_tier": "ltm", "priority": 10},
        )

        assert entry_id is not None

    @patch("sage.middleware.components.sage_mem.services.hierarchical_memory_service.MemoryManager")
    def test_active_insert_force_skip_capacity(self, mock_manager_class):
        """Test active insert with force=True skips capacity check"""
        from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
            HierarchicalMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection creation with insert returning stable_id
        mock_collection = MagicMock()
        mock_collection.index_info = {}
        mock_collection.insert.return_value = "stable_id_789"
        mock_manager.create_collection.return_value = mock_collection

        # Create service with small capacity
        service = HierarchicalMemoryService(
            tier_mode="two_tier", tier_capacities={"stm": 1, "ltm": -1}
        )

        # Fill the STM tier
        service._tier_counts["stm"] = 1

        # Active insert with force=True should not trigger migration
        with patch.object(service, "_migrate_overflow") as mock_migrate:
            entry_id = service.insert(
                entry="forced entry",
                vector=[0.1] * 384,
                insert_mode="active",
                insert_params={"force": True},
            )
            mock_migrate.assert_not_called()

        assert entry_id is not None


class TestGraphMemoryServiceInsertMode:
    """Test GraphMemoryService insert mode extension"""

    @patch("sage.middleware.components.sage_mem.services.graph_memory_service.MemoryManager")
    def test_passive_insert_creates_edges(self, mock_manager_class):
        """Test passive insert creates edges by default"""
        from sage.middleware.components.sage_mem.services.graph_memory_service import (
            GraphMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.indexes = {}
        mock_manager.create_collection.return_value = mock_collection

        service = GraphMemoryService(collection_name="test_graph")

        # Passive insert with links
        service.insert(
            entry="test node",
            metadata={"links": ["node_1", "node_2"]},
        )

        # Should create edges
        assert mock_collection.add_edge.called

    @patch("sage.middleware.components.sage_mem.services.graph_memory_service.MemoryManager")
    def test_active_insert_no_edges(self, mock_manager_class):
        """Test active insert with create_edges=False"""
        from sage.middleware.components.sage_mem.services.graph_memory_service import (
            GraphMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.indexes = {}
        mock_manager.create_collection.return_value = mock_collection

        service = GraphMemoryService(collection_name="test_graph")

        # Active insert with create_edges=False
        service.insert(
            entry="isolated node",
            metadata={"links": ["node_1", "node_2"]},
            insert_mode="active",
            insert_params={"create_edges": False},
        )

        # Should NOT create edges
        assert not mock_collection.add_edge.called

    @patch("sage.middleware.components.sage_mem.services.graph_memory_service.MemoryManager")
    def test_active_insert_with_node_type(self, mock_manager_class):
        """Test active insert with node_type override"""
        from sage.middleware.components.sage_mem.services.graph_memory_service import (
            GraphMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.indexes = {}
        mock_manager.create_collection.return_value = mock_collection

        service = GraphMemoryService(collection_name="test_graph")

        # Active insert with node_type
        service.insert(
            entry="entity node",
            insert_mode="active",
            insert_params={"node_type": "entity", "priority": 5},
        )

        # Verify add_node was called with correct metadata
        mock_collection.add_node.assert_called_once()
        call_kwargs = mock_collection.add_node.call_args[1]
        assert call_kwargs["metadata"]["node_type"] == "entity"
        assert call_kwargs["metadata"]["priority"] == 5


class TestShortTermMemoryServiceInsertMode:
    """Test ShortTermMemoryService insert mode extension"""

    @patch("sage.middleware.components.sage_mem.services.short_term_memory_service.MemoryManager")
    def test_passive_insert_respects_capacity(self, mock_manager_class):
        """Test passive insert respects FIFO capacity"""
        from sage.middleware.components.sage_mem.services.short_term_memory_service import (
            ShortTermMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.index_info = {}
        mock_manager.create_collection.return_value = mock_collection

        service = ShortTermMemoryService(max_dialog=2)

        # Insert 3 entries, first should be evicted
        service.insert(entry="entry1")
        service.insert(entry="entry2")
        service.insert(entry="entry3")

        assert len(service._order_queue) == 2

    @patch("sage.middleware.components.sage_mem.services.short_term_memory_service.MemoryManager")
    def test_active_insert_force_skips_capacity(self, mock_manager_class):
        """Test active insert with force=True skips manual eviction (but deque maxlen still applies)"""
        from sage.middleware.components.sage_mem.services.short_term_memory_service import (
            ShortTermMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection with insert returning stable_id
        mock_collection = MagicMock()
        mock_collection.index_info = {}
        mock_collection.insert.return_value = "stable_id"
        mock_manager.create_collection.return_value = mock_collection

        service = ShortTermMemoryService(max_dialog=2)

        # Fill capacity
        service.insert(entry="entry1")
        service.insert(entry="entry2")

        # Force insert - note: deque maxlen still limits to 2, but force skips manual deletion
        # The test verifies that force=True is processed (no error), not that it exceeds maxlen
        service.insert(
            entry="forced_entry",
            insert_mode="active",
            insert_params={"force": True},
        )

        # Due to deque maxlen=2, oldest entry is auto-evicted
        assert len(service._order_queue) == 2
        # Verify the forced entry is in the queue
        queue_texts = [item["text"] for item in service._order_queue]
        assert "forced_entry" in queue_texts


class TestBackwardCompatibility:
    """Test backward compatibility of insert mode extension"""

    @patch("sage.middleware.components.sage_mem.services.hierarchical_memory_service.MemoryManager")
    def test_insert_without_mode_uses_passive(self, mock_manager_class):
        """Test that insert without mode defaults to passive"""
        from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
            HierarchicalMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection with insert returning stable_id
        mock_collection = MagicMock()
        mock_collection.index_info = {}
        mock_collection.insert.return_value = "stable_id_compat"
        mock_manager.create_collection.return_value = mock_collection

        service = HierarchicalMemoryService()
        # Override tier_capacities to avoid MagicMock comparison
        service.tier_capacities = {"stm": -1, "mtm": -1, "ltm": -1}

        # Old-style insert (without insert_mode)
        entry_id = service.insert(
            entry="test",
            vector=[0.1] * 384,
            metadata={"tier": "stm"},
        )

        assert entry_id is not None

    @patch("sage.middleware.components.sage_mem.services.graph_memory_service.MemoryManager")
    def test_graph_insert_backward_compatible(self, mock_manager_class):
        """Test graph insert remains backward compatible"""
        from sage.middleware.components.sage_mem.services.graph_memory_service import (
            GraphMemoryService,
        )

        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.has_collection.return_value = False

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.indexes = {}
        mock_manager.create_collection.return_value = mock_collection

        service = GraphMemoryService()

        # Old-style insert
        node_id = service.insert(
            entry="node content",
            metadata={"node_type": "fact"},
        )

        assert node_id is not None
        mock_collection.add_node.assert_called_once()
