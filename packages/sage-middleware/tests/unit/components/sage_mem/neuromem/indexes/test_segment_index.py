"""SegmentIndex 单元测试

测试分段索引的基本功能：
- 初始化和配置
- 添加、移除、查询
- 时间分段策略
- 关键词分段策略
- 持久化和加载
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import (
    SegmentIndex,
)


class TestSegmentIndexBasic:
    """测试 SegmentIndex 基础功能"""

    def test_init_default(self):
        """测试默认初始化（时间策略）"""
        index = SegmentIndex()

        assert index.strategy == "time"
        assert index.segment_size == 100
        assert index.size() == 0

    def test_init_with_config(self):
        """测试自定义配置"""
        config = {
            "strategy": "keyword",
            "segment_size": 50,
            "keyword_field": "topic",
        }
        index = SegmentIndex(config)

        assert index.strategy == "keyword"
        assert index.segment_size == 50
        assert index.keyword_field == "topic"

    def test_init_invalid_strategy(self):
        """测试无效策略"""
        config = {"strategy": "invalid"}

        with pytest.raises(ValueError, match="Unsupported strategy"):
            SegmentIndex(config)

    def test_add_and_contains(self):
        """测试添加数据和成员检查"""
        index = SegmentIndex()

        index.add("id1", "hello world", {})
        assert index.contains("id1")
        assert not index.contains("id2")
        assert index.size() == 1

        index.add("id2", "hello python", {})
        assert index.contains("id2")
        assert index.size() == 2

    def test_add_update(self):
        """测试更新已存在的数据"""
        index = SegmentIndex()

        index.add("id1", "hello world", {})
        original_segment = index.data_to_segment["id1"]
        assert index.size() == 1

        # 更新（相同 ID）
        index.add("id1", "goodbye world", {})
        assert index.size() == 1
        assert index.contains("id1")
        # 可能在不同段（取决于策略）

    def test_remove(self):
        """测试移除数据"""
        index = SegmentIndex()

        index.add("id1", "hello world", {})
        index.add("id2", "hello python", {})
        assert index.size() == 2

        index.remove("id1")
        assert not index.contains("id1")
        assert index.contains("id2")
        assert index.size() == 1

    def test_remove_nonexistent(self):
        """测试移除不存在的数据（不应报错）"""
        index = SegmentIndex()

        index.add("id1", "hello world", {})

        # 移除不存在的 ID
        index.remove("id999")  # 不应报错
        assert index.size() == 1

    def test_clear(self):
        """测试清空索引"""
        index = SegmentIndex()

        index.add("id1", "hello world", {})
        index.add("id2", "hello python", {})
        assert index.size() == 2

        index.clear()
        assert index.size() == 0
        assert not index.contains("id1")
        assert len(index.segments) == 0


class TestSegmentIndexTimeStrategy:
    """测试时间分段策略"""

    def test_time_strategy_single_segment(self):
        """测试单段（未达到大小限制）"""
        index = SegmentIndex({"strategy": "time", "segment_size": 10})

        # 添加少量数据
        for i in range(5):
            index.add(f"id{i}", f"text{i}", {})

        # 应该只有一个段
        assert len(index.segments) == 1
        assert index.size() == 5

    def test_time_strategy_multiple_segments_by_size(self):
        """测试按大小自动分段"""
        index = SegmentIndex({"strategy": "time", "segment_size": 3})

        # 添加超过 segment_size 的数据
        for i in range(10):
            index.add(f"id{i}", f"text{i}", {})

        # 应该有多个段
        assert len(index.segments) >= 3
        assert index.size() == 10

    def test_time_strategy_query_current_segment(self):
        """测试查询当前段"""
        index = SegmentIndex({"strategy": "time", "segment_size": 5})

        # 添加数据
        for i in range(8):
            index.add(f"id{i}", f"text{i}", {})

        # 查询当前段（应该返回最后一个段的数据）
        results = index.query()
        assert len(results) > 0
        # 最后添加的数据应该在当前段
        assert "id7" in results

    def test_time_strategy_query_all_segments(self):
        """测试查询所有段"""
        index = SegmentIndex({"strategy": "time", "segment_size": 3})

        # 添加数据
        for i in range(10):
            index.add(f"id{i}", f"text{i}", {})

        # 查询所有段
        results = index.query(all_segments=True)
        assert len(results) == 10

    def test_time_strategy_duration_limit(self):
        """测试时长限制分段（需要等待）"""
        # 注意：这个测试会耗时较长，使用较短的时长
        index = SegmentIndex({
            "strategy": "time",
            "segment_size": 100,  # 很大，不会触发大小限制
            "segment_duration": 1,  # 1 秒
        })

        # 添加第一条数据
        index.add("id1", "text1", {})
        first_segment = index.current_segment_id

        # 等待超过 segment_duration
        time.sleep(1.1)

        # 添加第二条数据（应该触发新段）
        index.add("id2", "text2", {})
        second_segment = index.current_segment_id

        # 应该创建了新段
        assert first_segment != second_segment
        assert len(index.segments) == 2


class TestSegmentIndexKeywordStrategy:
    """测试关键词分段策略"""

    def test_keyword_strategy_single_keyword(self):
        """测试单个关键词"""
        index = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})

        # 添加相同关键词的数据
        index.add("id1", "text1", {"category": "sports"})
        index.add("id2", "text2", {"category": "sports"})
        index.add("id3", "text3", {"category": "sports"})

        # 应该只有一个段
        assert len(index.segments) == 1
        assert index.size() == 3

    def test_keyword_strategy_multiple_keywords(self):
        """测试多个关键词"""
        index = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})

        # 添加不同关键词的数据
        index.add("id1", "text1", {"category": "sports"})
        index.add("id2", "text2", {"category": "tech"})
        index.add("id3", "text3", {"category": "sports"})
        index.add("id4", "text4", {"category": "news"})

        # 应该有 3 个段（sports, tech, news）
        assert len(index.segments) == 3
        assert index.size() == 4

    def test_keyword_strategy_query_by_keyword(self):
        """测试按关键词查询"""
        index = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})

        # 添加数据
        index.add("id1", "text1", {"category": "sports"})
        index.add("id2", "text2", {"category": "tech"})
        index.add("id3", "text3", {"category": "sports"})

        # 查询 sports 分类
        results = index.query("sports")
        assert len(results) == 2
        assert "id1" in results
        assert "id3" in results

        # 查询 tech 分类
        results = index.query("tech")
        assert len(results) == 1
        assert "id2" in results

    def test_keyword_strategy_default_keyword(self):
        """测试默认关键词（未提供关键词字段）"""
        index = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})

        # 添加没有 category 字段的数据
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})

        # 应该使用默认关键词
        results = index.query("default")
        assert len(results) == 2


class TestSegmentIndexCustomStrategy:
    """测试自定义分段策略"""

    def test_custom_strategy_explicit_segment_id(self):
        """测试显式指定 segment_id"""
        index = SegmentIndex({"strategy": "custom"})

        # 显式指定段 ID
        index.add("id1", "text1", {"segment_id": "session_1"})
        index.add("id2", "text2", {"segment_id": "session_1"})
        index.add("id3", "text3", {"segment_id": "session_2"})

        # 应该有 2 个段
        assert len(index.segments) >= 2
        assert index.size() == 3

        # 查询指定段
        results = index.query("session_1")
        assert len(results) == 2
        assert "id1" in results
        assert "id2" in results


class TestSegmentIndexQuery:
    """测试查询功能"""

    def test_query_by_segment_id(self):
        """测试按段 ID 查询"""
        index = SegmentIndex({"strategy": "time", "segment_size": 3})

        # 添加数据（会创建多个段）
        for i in range(10):
            index.add(f"id{i}", f"text{i}", {})

        # 获取第一个段的 ID
        first_segment_id = list(index.segments.keys())[0]

        # 按段 ID 查询
        results = index.query(segment_id=first_segment_id)
        assert len(results) > 0
        # 验证返回的都是该段的数据
        for data_id in results:
            assert index.data_to_segment[data_id] == first_segment_id

    def test_query_with_top_k(self):
        """测试限制返回结果数量"""
        index = SegmentIndex({"strategy": "time", "segment_size": 10})

        # 添加数据
        for i in range(10):
            index.add(f"id{i}", f"text{i}", {})

        # 限制返回 3 条
        results = index.query(top_k=3)
        assert len(results) == 3

    def test_query_empty_segment(self):
        """测试查询空段"""
        index = SegmentIndex()

        # 查询不存在的段
        results = index.query(segment_id="nonexistent")
        assert len(results) == 0


class TestSegmentIndexInfo:
    """测试段信息功能"""

    def test_get_segment_info(self):
        """测试获取段信息"""
        index = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})

        # 添加数据
        index.add("id1", "text1", {"category": "sports"})
        index.add("id2", "text2", {"category": "tech"})
        index.add("id3", "text3", {"category": "sports"})

        # 获取段信息
        info = index.get_segment_info()

        assert info["total_segments"] == 2
        assert len(info["segments"]) == 2

        # 验证每个段的信息
        for segment_id, segment_info in info["segments"].items():
            assert "size" in segment_info
            assert "metadata" in segment_info
            assert segment_info["size"] > 0


class TestSegmentIndexPersistence:
    """测试持久化功能"""

    def test_save_and_load_time_strategy(self):
        """测试保存和加载（时间策略）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "segment_index"

            # 创建并填充索引
            index1 = SegmentIndex({"strategy": "time", "segment_size": 3})
            for i in range(10):
                index1.add(f"id{i}", f"text{i}", {})

            # 保存
            index1.save(save_dir)

            # 加载到新索引
            index2 = SegmentIndex()
            index2.load(save_dir)

            # 验证配置
            assert index2.strategy == "time"
            assert index2.segment_size == 3

            # 验证数据
            assert index2.size() == 10
            assert len(index2.segments) == len(index1.segments)

            # 验证所有数据都在
            for i in range(10):
                assert index2.contains(f"id{i}")

    def test_save_and_load_keyword_strategy(self):
        """测试保存和加载（关键词策略）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "segment_index"

            # 创建并填充索引
            index1 = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})
            index1.add("id1", "text1", {"category": "sports"})
            index1.add("id2", "text2", {"category": "tech"})
            index1.add("id3", "text3", {"category": "sports"})

            # 保存
            index1.save(save_dir)

            # 加载并验证
            index2 = SegmentIndex()
            index2.load(save_dir)

            assert index2.strategy == "keyword"
            assert index2.size() == 3
            assert len(index2.segments) == 2

            # 验证查询功能
            results = index2.query("sports")
            assert len(results) == 2

    def test_load_and_continue_adding(self):
        """测试加载后继续添加数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "segment_index"

            # 创建并保存
            index1 = SegmentIndex({"strategy": "time", "segment_size": 5})
            for i in range(5):
                index1.add(f"id{i}", f"text{i}", {})
            index1.save(save_dir)

            # 加载并继续添加
            index2 = SegmentIndex()
            index2.load(save_dir)

            # 添加新数据
            for i in range(5, 10):
                index2.add(f"id{i}", f"text{i}", {})

            # 验证所有数据都在
            assert index2.size() == 10
            for i in range(10):
                assert index2.contains(f"id{i}")


class TestSegmentIndexEdgeCases:
    """测试边界情况"""

    def test_empty_index_query(self):
        """测试空索引查询"""
        index = SegmentIndex()

        results = index.query()
        assert len(results) == 0

        results = index.query(all_segments=True)
        assert len(results) == 0

    def test_single_item(self):
        """测试单条数据"""
        index = SegmentIndex()

        index.add("id1", "text1", {})

        assert index.size() == 1
        results = index.query()
        assert len(results) == 1
        assert "id1" in results

    def test_remove_from_segment(self):
        """测试从段中移除数据后段信息"""
        index = SegmentIndex({"strategy": "keyword", "keyword_field": "category"})

        index.add("id1", "text1", {"category": "sports"})
        index.add("id2", "text2", {"category": "sports"})

        # 移除一条数据
        index.remove("id1")

        # 段应该还存在，但大小减少
        results = index.query("sports")
        assert len(results) == 1
        assert "id2" in results
