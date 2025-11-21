"""
测试 NeuroMem Session Storage
验证基于 SAGE NeuroMem 的 session 持久化
"""

import os
import shutil
import tempfile
from datetime import datetime

import pytest

from sage.gateway.session.neuromem_storage import NeuroMemSessionStorage


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # 清理
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def storage(temp_dir):
    """创建 NeuroMem 存储实例"""
    return NeuroMemSessionStorage(data_dir=temp_dir)


class TestNeuroMemSessionStorage:
    """测试 NeuroMem Session Storage"""

    def test_initialization(self, storage, temp_dir):
        """测试存储初始化"""
        assert storage.data_dir == temp_dir
        assert os.path.exists(temp_dir)
        assert storage.text_storage is not None
        assert storage.metadata_storage is not None

    def test_save_and_load_sessions(self, storage):
        """测试保存和加载 session"""
        # 创建测试数据
        test_sessions = [
            {
                "id": "session-1",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": datetime.now().isoformat()},
                    {
                        "role": "assistant",
                        "content": "Hi there!",
                        "timestamp": datetime.now().isoformat(),
                    },
                ],
                "metadata": {"title": "First Chat", "total_tokens": 20},
            },
            {
                "id": "session-2",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "messages": [
                    {
                        "role": "user",
                        "content": "What's AI?",
                        "timestamp": datetime.now().isoformat(),
                    },
                ],
                "metadata": {"title": "AI Questions", "total_tokens": 10},
            },
        ]

        # 保存 sessions
        storage.save(test_sessions)

        # 加载 sessions
        loaded_sessions = storage.load()

        # 验证
        assert len(loaded_sessions) == 2
        assert loaded_sessions[0]["id"] == "session-1"
        assert loaded_sessions[1]["id"] == "session-2"
        assert len(loaded_sessions[0]["messages"]) == 2
        assert len(loaded_sessions[1]["messages"]) == 1

    def test_persistence_across_instances(self, temp_dir):
        """测试跨实例持久化"""
        # 第一个实例 - 保存数据
        storage1 = NeuroMemSessionStorage(data_dir=temp_dir)
        test_session = {
            "id": "persistent-session",
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "messages": [
                {
                    "role": "user",
                    "content": "Test persistence",
                    "timestamp": datetime.now().isoformat(),
                },
            ],
            "metadata": {"title": "Persistence Test"},
        }
        storage1.save([test_session])

        # 第二个实例 - 加载数据
        storage2 = NeuroMemSessionStorage(data_dir=temp_dir)
        loaded_sessions = storage2.load()

        # 验证
        assert len(loaded_sessions) == 1
        assert loaded_sessions[0]["id"] == "persistent-session"
        assert loaded_sessions[0]["metadata"]["title"] == "Persistence Test"

    def test_get_stats(self, storage):
        """测试统计信息"""
        # 保存一些 sessions
        test_sessions = [
            {
                "id": "stats-1",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "messages": [{"role": "user", "content": "Hi"}] * 3,
                "metadata": {"total_tokens": 30},
            },
            {
                "id": "stats-2",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "messages": [{"role": "user", "content": "Hello"}] * 5,
                "metadata": {"total_tokens": 50},
            },
        ]
        storage.save(test_sessions)

        # 获取统计
        stats = storage.get_stats()

        # 验证
        assert stats["total_sessions"] == 2
        assert stats["total_messages"] == 8  # 3 + 5
        assert stats["total_tokens"] == 80  # 30 + 50
        assert stats["storage_backend"] == "NeuroMem"
        assert "data_directory" in stats

    def test_clear_sessions(self, storage):
        """测试清空 sessions"""
        # 先保存一些数据
        test_session = {
            "id": "clear-test",
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "messages": [],
            "metadata": {},
        }
        storage.save([test_session])

        # 验证数据存在
        assert len(storage.load()) == 1

        # 清空
        storage.clear()

        # 验证已清空
        assert len(storage.load()) == 0

    def test_update_sessions(self, storage):
        """测试更新 sessions"""
        # 创建初始 session
        initial_session = {
            "id": "update-test",
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "messages": [{"role": "user", "content": "Initial"}],
            "metadata": {"title": "Initial Title"},
        }
        storage.save([initial_session])

        # 更新 session
        updated_session = {
            "id": "update-test",
            "created_at": initial_session["created_at"],
            "last_active": datetime.now().isoformat(),
            "messages": [
                {"role": "user", "content": "Initial"},
                {"role": "assistant", "content": "Response"},
            ],
            "metadata": {"title": "Updated Title"},
        }
        storage.save([updated_session])

        # 验证更新
        loaded = storage.load()
        assert len(loaded) == 1
        assert len(loaded[0]["messages"]) == 2
        assert loaded[0]["metadata"]["title"] == "Updated Title"

    def test_multiple_sessions(self, storage):
        """测试多个 sessions"""
        sessions = [
            {
                "id": f"session-{i}",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "messages": [{"role": "user", "content": f"Message {i}"}],
                "metadata": {"title": f"Chat {i}"},
            }
            for i in range(10)
        ]
        storage.save(sessions)

        loaded = storage.load()
        assert len(loaded) == 10

        # 验证所有 session ID 都存在
        loaded_ids = {s["id"] for s in loaded}
        expected_ids = {f"session-{i}" for i in range(10)}
        assert loaded_ids == expected_ids

    def test_empty_sessions(self, storage):
        """测试空 sessions"""
        storage.save([])
        loaded = storage.load()
        assert len(loaded) == 0

    def test_default_factory(self):
        """测试默认工厂方法"""
        storage = NeuroMemSessionStorage.default()
        assert storage is not None
        assert storage.data_dir.endswith("neuromem_sessions")

        # 清理
        if os.path.exists(storage.data_dir):
            shutil.rmtree(storage.data_dir)

    def test_corrupted_data_handling(self, storage):
        """测试处理损坏的数据"""
        # 故意保存无效的 JSON
        storage.text_storage.store("corrupted-session", "invalid json {")
        storage.text_storage.store_to_disk(storage.text_storage_path)

        # 保存一个正常的 session
        valid_session = {
            "id": "valid-session",
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "messages": [],
            "metadata": {},
        }
        storage.save([valid_session])

        # 加载应该跳过损坏的数据
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "valid-session"

    def test_metadata_fields_registration(self, storage):
        """测试元数据字段注册"""
        expected_fields = [
            "created_at",
            "last_active",
            "title",
            "message_count",
            "total_tokens",
        ]

        for field in expected_fields:
            assert storage.metadata_storage.has_field(field)
