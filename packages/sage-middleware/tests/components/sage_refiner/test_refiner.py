"""
Refiner测试套件
==============

基础功能测试
"""

import pytest
from sage.middleware.components.sage_refiner import (
    RefinerAlgorithm,
    RefinerConfig,
    RefinerService,
    SimpleRefiner,
)


class TestRefinerConfig:
    """配置类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = RefinerConfig()
        assert config.algorithm == RefinerAlgorithm.LONG_REFINER
        assert config.budget == 2048
        assert not config.enable_cache

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "algorithm": "simple",
            "budget": 1000,
            "enable_cache": True,
        }
        config = RefinerConfig.from_dict(config_dict)
        assert config.algorithm == RefinerAlgorithm.SIMPLE
        assert config.budget == 1000
        assert config.enable_cache

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=1000)
        config_dict = config.to_dict()
        assert config_dict["algorithm"] == "simple"
        assert config_dict["budget"] == 1000


class TestSimpleRefiner:
    """SimpleRefiner测试"""

    def test_initialization(self):
        """测试初始化"""
        refiner = SimpleRefiner({})
        assert not refiner.is_initialized
        refiner.initialize()
        assert refiner.is_initialized

    def test_basic_refine(self):
        """测试基础精炼"""
        refiner = SimpleRefiner({"budget": 50})
        refiner.initialize()

        query = "测试查询"
        documents = [
            "这是第一个文档，包含一些测试内容。",
            "这是第二个文档，也包含一些测试内容。",
            "这是第三个文档，同样包含测试内容。",
        ]

        result = refiner.refine(query, documents)

        assert result is not None
        assert result.refined_content is not None
        assert isinstance(result.refined_content, list)
        assert result.metrics.original_tokens > 0
        assert result.metrics.refined_tokens > 0
        assert result.metrics.compression_rate > 0

    def test_refine_with_budget(self):
        """测试budget限制"""
        refiner = SimpleRefiner({"budget": 10})
        refiner.initialize()

        query = "测试"
        documents = ["这是一个很长的文档" * 20]

        result = refiner.refine(query, documents)

        # 精炼后的token数应该小于等于budget
        assert result.metrics.refined_tokens <= 10 + 5  # 允许一些误差

    def test_batch_refine(self):
        """测试批量精炼"""
        refiner = SimpleRefiner({"budget": 50})
        refiner.initialize()

        queries = ["查询1", "查询2"]
        documents_list = [["文档1", "文档2"], ["文档3", "文档4"]]

        results = refiner.refine_batch(queries, documents_list)

        assert len(results) == 2
        assert all(isinstance(r.refined_content, list) for r in results)


class TestRefinerService:
    """RefinerService测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE)
        service = RefinerService(config)

        assert service.config.algorithm == RefinerAlgorithm.SIMPLE
        assert service.refiner is None  # 延迟加载

    def test_service_refine(self):
        """测试服务精炼"""
        config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=50)
        service = RefinerService(config)

        query = "测试"
        documents = ["文档1", "文档2"]

        result = service.refine(query, documents)

        assert result is not None
        assert service.refiner is not None  # 应该已经初始化

    def test_service_cache(self):
        """测试缓存功能"""
        config = RefinerConfig(
            algorithm=RefinerAlgorithm.SIMPLE, budget=50, enable_cache=True
        )
        service = RefinerService(config)

        query = "测试"
        documents = ["文档1", "文档2"]

        # 第一次调用
        result1 = service.refine(query, documents)
        assert service.stats_data["cache_misses"] == 1
        assert service.stats_data["cache_hits"] == 0

        # 第二次调用（应该命中缓存）
        result2 = service.refine(query, documents)
        assert service.stats_data["cache_hits"] == 1

        # 结果应该相同
        assert result1.refined_content == result2.refined_content

    def test_algorithm_switching(self):
        """测试算法切换"""
        config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE)
        service = RefinerService(config)

        # 初始算法
        assert service.config.algorithm == RefinerAlgorithm.SIMPLE

        # 切换算法
        service.switch_algorithm(RefinerAlgorithm.NONE)
        assert service.config.algorithm == RefinerAlgorithm.NONE
        assert service.refiner is None  # 应该清空旧的refiner

    def test_service_stats(self):
        """测试统计信息"""
        config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=50)
        service = RefinerService(config)

        query = "测试"
        documents = ["文档1", "文档2"]

        service.refine(query, documents)

        stats = service.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_original_tokens"] > 0
        assert "avg_refine_time" in stats
        assert "config" in stats

    def test_context_manager(self):
        """测试上下文管理器"""
        config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE)

        with RefinerService(config) as service:
            result = service.refine("测试", ["文档"])
            assert result is not None

        # 退出后应该清理
        # （这里无法直接验证，但不应该抛出异常）


class TestRefinerAlgorithm:
    """算法枚举测试"""

    def test_algorithm_values(self):
        """测试算法值"""
        assert RefinerAlgorithm.LONG_REFINER.value == "long_refiner"
        assert RefinerAlgorithm.SIMPLE.value == "simple"
        assert RefinerAlgorithm.NONE.value == "none"

    def test_list_available(self):
        """测试列出可用算法"""
        algorithms = RefinerAlgorithm.list_available()
        assert "long_refiner" in algorithms
        assert "simple" in algorithms
        assert "none" in algorithms


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
