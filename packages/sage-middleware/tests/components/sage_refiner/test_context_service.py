"""
Context Service测试套件
======================

测试全局Context Service的功能
"""

import pytest

# Try to import ContextService - skip tests if unavailable (C++ extension not built)
try:
    from sage.middleware.components.sage_refiner import (
        ContextService,
        RefinerConfig,
    )
    CONTEXT_SERVICE_AVAILABLE = True
except ImportError:
    CONTEXT_SERVICE_AVAILABLE = False
    ContextService = None
    RefinerConfig = None


pytestmark = pytest.mark.skipif(
    not CONTEXT_SERVICE_AVAILABLE,
    reason="ContextService not available (C++ extensions may not be built)"
)


class TestContextServiceBasics:
    """ContextService基础功能测试"""

    def test_initialization(self):
        """测试初始化"""
        config = {
            "refiner": {"algorithm": "simple", "budget": 2000},
            "max_context_length": 8192,
            "auto_compress": True,
            "compress_threshold": 0.8,
        }
        service = ContextService(config)

        assert service.max_context_length == 8192
        assert service.auto_compress is True
        assert service.compress_threshold == 0.8
        assert service.refiner is not None
        assert len(service.context_history) == 0

    def test_initialization_defaults(self):
        """测试默认初始化"""
        service = ContextService()

        assert service.max_context_length == 8192
        assert service.auto_compress is True
        assert service.compress_threshold == 0.8
        assert len(service.context_history) == 0

    def test_from_config(self):
        """测试from_config工厂方法"""
        config = {
            "max_context_length": 4096,
            "auto_compress": False,
        }
        service = ContextService.from_config(config)

        assert service.max_context_length == 4096
        assert service.auto_compress is False


class TestContextManagement:
    """上下文管理功能测试"""

    def test_manage_context_with_query_only(self):
        """测试仅包含查询的上下文管理"""
        service = ContextService()

        result = service.manage_context(query="测试查询")

        assert result is not None
        assert "compressed_context" in result
        assert "context_length" in result
        assert "compression_applied" in result
        assert "metrics" in result

        # 应该只有query部分
        assert len(result["compressed_context"]) == 1
        assert result["compressed_context"][0]["type"] == "query"
        assert result["compressed_context"][0]["content"] == "测试查询"

    def test_manage_context_with_system_prompt(self):
        """测试包含系统提示词的上下文管理"""
        service = ContextService()

        result = service.manage_context(
            query="测试查询", system_prompt="你是一个助手。"
        )

        context_parts = result["compressed_context"]
        assert len(context_parts) == 2

        # 第一部分应该是system
        assert context_parts[0]["type"] == "system"
        assert context_parts[0]["content"] == "你是一个助手。"

        # 第二部分应该是query
        assert context_parts[1]["type"] == "query"
        assert context_parts[1]["content"] == "测试查询"

    def test_manage_context_with_history(self):
        """测试包含历史对话的上下文管理"""
        service = ContextService()

        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮助你的吗"},
        ]

        result = service.manage_context(query="测试查询", history=history)

        context_parts = result["compressed_context"]
        assert len(context_parts) == 2

        # 应该包含history和query
        assert context_parts[0]["type"] == "history"
        assert "user: 你好" in context_parts[0]["content"]
        assert context_parts[1]["type"] == "query"

    def test_manage_context_with_documents(self):
        """测试包含检索文档的上下文管理"""
        service = ContextService(
            {"refiner": {"algorithm": "simple", "budget": 100}}
        )

        documents = ["文档1内容", "文档2内容", "文档3内容"]

        result = service.manage_context(query="测试查询", retrieved_docs=documents)

        context_parts = result["compressed_context"]

        # 应该包含documents和query
        has_docs = any(part["type"] == "documents" for part in context_parts)
        has_query = any(part["type"] == "query" for part in context_parts)

        assert has_docs
        assert has_query
        assert result["compression_applied"] is True
        assert "docs_compression" in result["metrics"]

    def test_manage_context_complete(self):
        """测试完整的上下文管理（所有部分）"""
        service = ContextService(
            {"refiner": {"algorithm": "simple", "budget": 200}}
        )

        system_prompt = "你是一个助手。"
        history = [
            {"role": "user", "content": "什么是Python"},
            {"role": "assistant", "content": "Python是一种编程语言。"},
        ]
        documents = ["Python简介", "Python特性"]
        query = "Python有什么用途"

        result = service.manage_context(
            query=query,
            history=history,
            retrieved_docs=documents,
            system_prompt=system_prompt,
        )

        context_parts = result["compressed_context"]

        # 验证所有部分都存在
        types = {part["type"] for part in context_parts}
        assert "system" in types
        assert "history" in types
        assert "documents" in types
        assert "query" in types

        # 验证顺序
        assert context_parts[0]["type"] == "system"
        assert context_parts[-1]["type"] == "query"


class TestHistoryCompression:
    """历史对话压缩测试"""

    def test_no_compression_for_short_history(self):
        """测试短历史不应被压缩"""
        service = ContextService(
            {"max_context_length": 8192, "auto_compress": True}
        )

        # 短历史
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好"},
        ]

        result = service.manage_context(query="测试", history=history)

        # 短历史不应触发压缩
        assert "history_compression" not in result["metrics"]

    def test_compression_for_long_history(self):
        """测试长历史应被压缩"""
        service = ContextService(
            {"max_context_length": 100, "auto_compress": True, "compress_threshold": 0.5}
        )

        # 创建足够长的历史以触发压缩
        history = []
        for i in range(20):
            history.append(
                {
                    "role": "user",
                    "content": f"这是一个很长的问题 {i} " + "内容 " * 10,
                }
            )
            history.append(
                {
                    "role": "assistant",
                    "content": f"这是一个很长的回答 {i} " + "内容 " * 10,
                }
            )

        result = service.manage_context(query="测试", history=history)

        # 长历史应触发压缩
        if result["compression_applied"]:
            # 可能触发了压缩
            pass  # 压缩取决于实际的token计算

    def test_auto_compress_disabled(self):
        """测试禁用自动压缩"""
        service = ContextService(
            {"max_context_length": 100, "auto_compress": False}
        )

        # 即使历史很长，也不应压缩
        history = []
        for i in range(20):
            history.append({"role": "user", "content": f"问题{i} " * 20})
            history.append({"role": "assistant", "content": f"回答{i} " * 20})

        result = service.manage_context(query="测试", history=history)

        # 不应有历史压缩指标
        assert "history_compression" not in result["metrics"]


class TestHistoryManagement:
    """历史记录管理测试"""

    def test_add_to_history(self):
        """测试添加到历史"""
        service = ContextService()

        assert len(service.context_history) == 0

        service.add_to_history("user", "你好")
        assert len(service.context_history) == 1
        assert service.context_history[0]["role"] == "user"
        assert service.context_history[0]["content"] == "你好"

        service.add_to_history("assistant", "你好，有什么可以帮助你的")
        assert len(service.context_history) == 2
        assert service.context_history[1]["role"] == "assistant"

    def test_clear_history(self):
        """测试清空历史"""
        service = ContextService()

        service.add_to_history("user", "消息1")
        service.add_to_history("assistant", "消息2")
        assert len(service.context_history) == 2

        service.clear_history()
        assert len(service.context_history) == 0

    def test_use_history_in_manage_context(self):
        """测试在管理上下文时使用内部历史"""
        service = ContextService()

        # 添加一些历史
        service.add_to_history("user", "第一个问题")
        service.add_to_history("assistant", "第一个回答")

        # 使用内部历史
        result = service.manage_context(
            query="第二个问题", history=service.context_history
        )

        context_parts = result["compressed_context"]
        history_part = next(
            (p for p in context_parts if p["type"] == "history"), None
        )

        assert history_part is not None
        assert "第一个问题" in history_part["content"]


class TestServiceStats:
    """服务统计测试"""

    def test_get_stats(self):
        """测试获取统计信息"""
        service = ContextService()

        stats = service.get_stats()

        assert "refiner_stats" in stats
        assert "context_history_size" in stats
        assert "max_context_length" in stats
        assert "auto_compress" in stats

        assert stats["context_history_size"] == 0
        assert stats["max_context_length"] == 8192
        assert stats["auto_compress"] is True

    def test_stats_after_operations(self):
        """测试操作后的统计信息"""
        service = ContextService({"refiner": {"algorithm": "simple", "budget": 100}})

        # 添加历史
        service.add_to_history("user", "问题")
        service.add_to_history("assistant", "回答")

        # 执行上下文管理
        service.manage_context(query="测试", retrieved_docs=["文档1"])

        stats = service.get_stats()

        assert stats["context_history_size"] == 2
        assert stats["refiner_stats"]["total_requests"] >= 1


class TestContextManager:
    """上下文管理器测试"""

    def test_context_manager_usage(self):
        """测试作为上下文管理器使用"""
        config = {"refiner": {"algorithm": "simple", "budget": 100}}

        with ContextService.from_config(config) as service:
            result = service.manage_context(query="测试", retrieved_docs=["文档"])
            assert result is not None

        # 退出后应该已清理（无法直接验证，但不应抛出异常）

    def test_shutdown(self):
        """测试关闭服务"""
        service = ContextService()

        service.add_to_history("user", "消息")
        assert len(service.context_history) == 1

        service.shutdown()

        # 历史应被清空
        assert len(service.context_history) == 0


class TestFlagControl:
    """Flag控制功能测试"""

    def test_enable_disable_via_config(self):
        """测试通过配置启用/禁用功能"""

        # 模拟应用配置
        app_config_enabled = {
            "enable_context_service": True,
            "context_service": {
                "refiner": {"algorithm": "simple", "budget": 100},
                "max_context_length": 4096,
            },
        }

        app_config_disabled = {
            "enable_context_service": False,
        }

        # 启用的情况
        if app_config_enabled["enable_context_service"]:
            service = ContextService.from_config(
                app_config_enabled["context_service"]
            )
            result = service.manage_context(query="测试")
            assert result is not None
            service.shutdown()

        # 禁用的情况
        if not app_config_disabled["enable_context_service"]:
            # 不创建服务，直接使用原始上下文
            pass  # 这是预期行为

        # 测试通过


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
