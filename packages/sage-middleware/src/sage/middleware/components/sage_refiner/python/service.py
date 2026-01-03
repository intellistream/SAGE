"""
RefinerService - 上下文压缩服务
==============================

提供统一的Refiner服务接口，支持：
- 多种算法动态切换
- 缓存管理
- 性能监控
- 服务生命周期管理
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

# Import from isage-refiner PyPI package
from sage_refiner import RefinerAlgorithm, RefinerConfig

from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
)


class RefinerCache:
    """LRU缓存实现"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: dict[str, float] = {}

    def _make_key(self, query: str, documents: list[Any], budget: int) -> str:
        """生成缓存键"""
        # 简单的哈希方案
        content = f"{query}|{json.dumps(documents, sort_keys=True)}|{budget}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, query: str, documents: list[Any], budget: int) -> RefineResult | None:
        """获取缓存"""
        key = self._make_key(query, documents, budget)

        if key not in self.cache:
            return None

        # 检查TTL
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None

        # 移到末尾（LRU）
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, query: str, documents: list[Any], budget: int, result: RefineResult) -> None:
        """存入缓存"""
        key = self._make_key(query, documents, budget)

        # 如果超过大小，删除最老的
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]

        self.cache[key] = result
        self.timestamps[key] = time.time()

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.timestamps.clear()

    def stats(self) -> dict[str, Any]:
        """缓存统计"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
        }


class RefinerService:
    """
    Refiner服务

    统一管理多种压缩算法，提供缓存、监控等功能。
    """

    def __init__(self, config: RefinerConfig | dict[str, Any] | None = None):
        """
        初始化服务

        Args:
            config: RefinerConfig对象或配置字典
        """
        # 处理配置
        if config is None:
            self.config = RefinerConfig()
        elif isinstance(config, dict):
            self.config = RefinerConfig.from_dict(config)
        else:
            self.config = config

        # 日志
        self.logger = logging.getLogger(__name__)

        # 算法实例（延迟加载）
        self.refiner: BaseRefiner | None = None

        # 缓存
        self.cache: RefinerCache | None = None
        if self.config.enable_cache:
            self.cache = RefinerCache(max_size=self.config.cache_size, ttl=self.config.cache_ttl)

        # 性能统计
        self.stats_data = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_refine_time": 0.0,
            "total_original_tokens": 0,
            "total_refined_tokens": 0,
        }

    def _get_refiner(self) -> BaseRefiner:
        """获取或创建Refiner实例"""
        if self.refiner is not None:
            return self.refiner

        # 根据算法类型创建实例
        algorithm = self.config.algorithm

        if algorithm == RefinerAlgorithm.LONG_REFINER:
            from sage.libs.foundation.context.compression.algorithms.long_refiner import (
                LongRefinerAlgorithm,
            )

            self.refiner = LongRefinerAlgorithm(self.config.to_dict())

        elif algorithm == RefinerAlgorithm.SIMPLE:
            from sage.libs.foundation.context.compression.algorithms.simple import (
                SimpleRefiner,
            )

            self.refiner = SimpleRefiner(self.config.to_dict())

        elif algorithm == RefinerAlgorithm.NONE:
            # 不压缩，返回原始内容
            from sage.libs.foundation.context.compression.algorithms.simple import (
                SimpleRefiner,
            )

            config = self.config.to_dict()
            config["budget"] = float("inf")  # 无限budget
            self.refiner = SimpleRefiner(config)

        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # 初始化
        if not self.refiner.is_initialized:
            algo_name = algorithm.value if hasattr(algorithm, "value") else str(algorithm)
            self.logger.info(f"Initializing refiner: {algo_name}")
            self.refiner.initialize()
            self.logger.info(f"Refiner initialized: {algo_name}")

        return self.refiner

    def refine(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        budget: int | None = None,
        use_cache: bool = True,
        **kwargs,
    ) -> RefineResult:
        """
        精炼文档

        Args:
            query: 用户查询
            documents: 文档列表
            budget: token预算（可选）
            use_cache: 是否使用缓存
            **kwargs: 其他参数

        Returns:
            RefineResult: 精炼结果
        """
        self.stats_data["total_requests"] += 1

        use_budget = budget if budget is not None else self.config.budget

        # 检查缓存
        if use_cache and self.cache is not None:
            cached = self.cache.get(query, documents, use_budget)
            if cached is not None:
                self.stats_data["cache_hits"] += 1
                self.logger.debug("Cache hit")
                return cached
            self.stats_data["cache_misses"] += 1

        # 执行精炼
        refiner = self._get_refiner()
        result = refiner.refine(query, documents, use_budget, **kwargs)

        # 更新统计
        self.stats_data["total_refine_time"] += result.metrics.refine_time
        self.stats_data["total_original_tokens"] += result.metrics.original_tokens
        self.stats_data["total_refined_tokens"] += result.metrics.refined_tokens

        # 存入缓存
        if use_cache and self.cache is not None:
            self.cache.put(query, documents, use_budget, result)

        return result

    def refine_batch(
        self,
        queries: list[str],
        documents_list: list[list[str | dict[str, Any]]],
        budget: int | None = None,
        **kwargs,
    ) -> list[RefineResult]:
        """
        批量精炼

        Args:
            queries: 查询列表
            documents_list: 文档列表的列表
            budget: token预算
            **kwargs: 其他参数

        Returns:
            List[RefineResult]: 精炼结果列表
        """
        refiner = self._get_refiner()
        use_budget = budget if budget is not None else self.config.budget

        results = refiner.refine_batch(queries, documents_list, use_budget, **kwargs)

        # 更新统计
        for result in results:
            self.stats_data["total_requests"] += 1
            self.stats_data["total_refine_time"] += result.metrics.refine_time
            self.stats_data["total_original_tokens"] += result.metrics.original_tokens
            self.stats_data["total_refined_tokens"] += result.metrics.refined_tokens

        return results

    def switch_algorithm(self, algorithm: str | RefinerAlgorithm) -> None:
        """
        切换压缩算法

        Args:
            algorithm: 新的算法名称
        """
        if isinstance(algorithm, str):
            algorithm = RefinerAlgorithm(algorithm)

        self.logger.info(f"Switching algorithm from {self.config.algorithm} to {algorithm}")

        # 关闭当前refiner
        if self.refiner is not None:
            self.refiner.shutdown()
            self.refiner = None

        # 更新配置
        self.config.algorithm = algorithm

        # 清空缓存
        if self.cache is not None:
            self.cache.clear()

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache is not None:
            self.cache.clear()
            self.logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """获取服务统计信息"""
        stats = self.stats_data.copy()

        # 计算平均值
        if stats["total_requests"] > 0:
            stats["avg_refine_time"] = stats["total_refine_time"] / stats["total_requests"]
            stats["avg_compression_rate"] = (
                stats["total_original_tokens"] / stats["total_refined_tokens"]
                if stats["total_refined_tokens"] > 0
                else 0.0
            )
        else:
            stats["avg_refine_time"] = 0.0
            stats["avg_compression_rate"] = 0.0

        # 缓存统计
        if self.cache is not None:
            stats["cache_stats"] = self.cache.stats()
            if self.stats_data["total_requests"] > 0:
                stats["cache_hit_rate"] = (
                    self.stats_data["cache_hits"] / self.stats_data["total_requests"]
                )

        # 配置信息
        stats["config"] = {
            "algorithm": (
                self.config.algorithm.value
                if hasattr(self.config.algorithm, "value")
                else self.config.algorithm
            ),
            "budget": self.config.budget,
            "enable_cache": self.config.enable_cache,
        }

        return stats

    def shutdown(self) -> None:
        """关闭服务"""
        self.logger.info("Shutting down RefinerService")

        if self.refiner is not None:
            self.refiner.shutdown()
            self.refiner = None

        if self.cache is not None:
            self.cache.clear()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()
