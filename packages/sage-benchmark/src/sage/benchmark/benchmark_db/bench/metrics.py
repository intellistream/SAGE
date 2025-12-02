"""
Performance Metrics

提供性能指标的计算和存储
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class BenchmarkMetrics:
    """存储测评指标"""

    # 基础信息
    algorithm_name: str = ""
    dataset_name: str = ""

    # 插入性能
    latency_insert: list[float] = field(default_factory=list)  # 每批次插入延迟 (us)
    insert_throughput: list[float] = field(default_factory=list)  # 插入吞吐量 (ops/s)
    batch_insert_throughput: list[list[float]] = field(default_factory=list)  # 每个子批次的吞吐量

    # 查询性能
    latency_query: list[float] = field(default_factory=list)  # 查询延迟 (us)
    continuous_query_latencies: list[list[float]] = field(default_factory=list)  # 连续查询延迟
    continuous_query_results: list[list[np.ndarray]] = field(default_factory=list)  # 连续查询结果

    # 内存占用
    update_memory_footprint: float = 0.0  # 更新时内存峰值 (bytes)
    search_memory_footprint: float = 0.0  # 查询时内存峰值 (bytes)

    # 维护状态
    maintenance_budget_used: float = 0.0  # 维护预算使用 (us)
    maintenance_deletion_ratio_final: float = 0.0  # 最终删除率
    maintenance_live_points: int = 0  # 活跃数据点数
    maintenance_deleted_points: int = 0  # 已删除数据点数

    # Cache miss 统计 - 插入操作
    cache_miss_per_batch: list[int] = field(default_factory=list)  # 每个批次插入的 cache miss
    cache_references_per_batch: list[int] = field(
        default_factory=list
    )  # 每个批次插入的 cache references
    cache_miss_rate_per_batch: list[float] = field(
        default_factory=list
    )  # 每个批次插入的 cache miss 率

    # Cache miss 统计 - 查询操作（连续查询）
    query_cache_miss_per_batch: list[int] = field(default_factory=list)  # 连续查询的 cache miss
    query_cache_references_per_batch: list[int] = field(
        default_factory=list
    )  # 连续查询的 cache references
    query_cache_miss_rate_per_batch: list[float] = field(
        default_factory=list
    )  # 连续查询的 cache miss 率

    # Cache miss 统计 - 查询操作（search操作）
    query_cache_miss_per_search: list[int] = field(default_factory=list)  # search操作的 cache miss
    query_cache_references_per_search: list[int] = field(
        default_factory=list
    )  # search操作的 cache references
    query_cache_miss_rate_per_search: list[float] = field(
        default_factory=list
    )  # search操作的 cache miss 率

    # 其他
    total_time: float = 0.0  # 总时间 (us)
    run_count: int = 0
    distance: str = ""
    search_type: str = ""
    count: int = 10  # k for kNN
    search_times: int = 0
    num_searches: int = 0
    private_queries: bool = False

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "algorithm_name": self.algorithm_name,
            "dataset_name": self.dataset_name,
            "latency_insert": self.latency_insert,
            "insert_throughput": self.insert_throughput,
            "batch_insert_throughput": self.batch_insert_throughput,
            "latency_query": self.latency_query,
            "continuous_query_latencies": self.continuous_query_latencies,
            "update_memory_footprint": self.update_memory_footprint,
            "search_memory_footprint": self.search_memory_footprint,
            "maintenance_budget_used": self.maintenance_budget_used,
            "maintenance_deletion_ratio_final": self.maintenance_deletion_ratio_final,
            "maintenance_live_points": self.maintenance_live_points,
            "maintenance_deleted_points": self.maintenance_deleted_points,
            "cache_miss_per_batch": self.cache_miss_per_batch,
            "cache_references_per_batch": self.cache_references_per_batch,
            "cache_miss_rate_per_batch": self.cache_miss_rate_per_batch,
            "query_cache_miss_per_batch": self.query_cache_miss_per_batch,
            "query_cache_references_per_batch": self.query_cache_references_per_batch,
            "query_cache_miss_rate_per_batch": self.query_cache_miss_rate_per_batch,
            "query_cache_miss_per_search": self.query_cache_miss_per_search,
            "query_cache_references_per_search": self.query_cache_references_per_search,
            "query_cache_miss_rate_per_search": self.query_cache_miss_rate_per_search,
            "total_time": self.total_time,
            "run_count": self.run_count,
            "distance": self.distance,
            "search_type": self.search_type,
            "count": self.count,
            "search_times": self.search_times,
            "num_searches": self.num_searches,
            "private_queries": self.private_queries,
        }

    def mean_query_throughput(self) -> float:
        """计算平均查询吞吐量 (queries/second)"""
        # 使用周期性查询计算吞吐量
        # continuous_query_latencies 存储的是每次批量查询的总延迟（秒）
        if not self.continuous_query_latencies or len(self.continuous_query_latencies) == 0:
            return 0.0

        all_latencies = []
        for batch in self.continuous_query_latencies:
            if isinstance(batch, (list, np.ndarray)):
                all_latencies.extend(batch)
            else:
                all_latencies.append(batch)

        if len(all_latencies) == 0:
            return 0.0

        # 获取每次批量查询的查询数（假设是数据集的查询集大小）
        queries_per_batch = getattr(self, "queries_per_continuous_query", 10000)

        # 总查询数 = 批次数 × 每批次查询数
        total_queries = len(all_latencies) * queries_per_batch

        # 总时间（秒）
        total_time_seconds = sum(all_latencies)

        if total_time_seconds == 0:
            return 0.0

        # 吞吐量 = 总查询数 / 总时间
        return total_queries / total_time_seconds

    def mean_recall(self) -> float:
        """计算平均召回率（需要在外部设置）"""
        # 召回率需要通过与 groundtruth 比较计算，这里返回存储的值
        return getattr(self, "recall", 0.0)

    def mean_latency(self) -> float:
        """
        计算平均批量查询延迟 (毫秒)

        注意：这里使用周期性查询延迟 (continuous_query_latencies)
        continuous_query_latencies 存储的是每次批量查询的总延迟（秒）
        返回的是批量查询的平均延迟，而不是单个查询向量的延迟
        """
        if not self.continuous_query_latencies or len(self.continuous_query_latencies) == 0:
            return 0.0

        all_latencies = []
        for batch in self.continuous_query_latencies:
            if isinstance(batch, (list, np.ndarray)):
                all_latencies.extend(batch)
            else:
                all_latencies.append(batch)

        if len(all_latencies) == 0:
            return 0.0

        # 转换为毫秒
        latencies_ms = [lat * 1000 for lat in all_latencies]

        return float(np.mean(latencies_ms))

    def p50_latency(self) -> float:
        """
        计算 P50 批量查询延迟 (毫秒)

        基于周期性查询延迟计算，P50 是所有批量查询延迟的中位数
        """
        if not self.continuous_query_latencies or len(self.continuous_query_latencies) == 0:
            return 0.0

        all_latencies = []
        for batch in self.continuous_query_latencies:
            if isinstance(batch, (list, np.ndarray)):
                all_latencies.extend(batch)
            else:
                all_latencies.append(batch)

        if len(all_latencies) == 0:
            return 0.0

        latencies_ms = [lat * 1000 for lat in all_latencies]

        return float(np.percentile(latencies_ms, 50))

    def p95_latency(self) -> float:
        """
        计算 P95 批量查询延迟 (毫秒)

        基于周期性查询延迟计算，P95 是所有批量查询延迟的 95 百分位
        """
        if not self.continuous_query_latencies or len(self.continuous_query_latencies) == 0:
            return 0.0

        all_latencies = []
        for batch in self.continuous_query_latencies:
            if isinstance(batch, (list, np.ndarray)):
                all_latencies.extend(batch)
            else:
                all_latencies.append(batch)

        if len(all_latencies) == 0:
            return 0.0

        latencies_ms = [lat * 1000 for lat in all_latencies]

        return float(np.percentile(latencies_ms, 95))

    def p99_latency(self) -> float:
        """
        计算 P99 批量查询延迟 (毫秒)

        基于周期性查询延迟计算，P99 是所有批量查询延迟的 99 百分位
        """
        if not self.continuous_query_latencies or len(self.continuous_query_latencies) == 0:
            return 0.0

        all_latencies = []
        for batch in self.continuous_query_latencies:
            if isinstance(batch, (list, np.ndarray)):
                all_latencies.extend(batch)
            else:
                all_latencies.append(batch)

        if len(all_latencies) == 0:
            return 0.0

        latencies_ms = [lat * 1000 for lat in all_latencies]

        return float(np.percentile(latencies_ms, 99))

    def mean_insert_throughput(self) -> float:
        """计算平均插入吞吐量 (ops/s)"""
        if not self.insert_throughput or len(self.insert_throughput) == 0:
            return 0.0
        return float(np.mean(self.insert_throughput))


def generate_timestamps(rows: int, event_rate: float = 4000.0) -> np.ndarray:
    """
    生成均匀递增的事件时间戳

    Args:
        rows: 行数
        event_rate: 事件速率 (events/s)

    Returns:
        事件时间戳数组 (微秒)
    """
    interval_micros = int(1e6 / event_rate)
    event_timestamps = np.arange(0, rows * interval_micros, interval_micros, dtype=np.int64)
    return event_timestamps


def get_latency_percentile(
    fraction: float, event_time: np.ndarray, processed_time: np.ndarray
) -> float:
    """
    计算延迟的百分位数

    Args:
        fraction: 百分位 (0~1)
        event_time: 事件时间戳
        processed_time: 处理时间戳

    Returns:
        延迟值 (微秒)
    """
    valid_latency = (processed_time - event_time)[
        (processed_time >= event_time) & (processed_time != 0)
    ]

    if valid_latency.size == 0:
        print("Warning: No valid latency found")
        return 0.0

    valid_latency_sorted = np.sort(valid_latency)
    idx = int(len(valid_latency_sorted) * fraction)
    if idx >= len(valid_latency_sorted):
        idx = len(valid_latency_sorted) - 1

    return float(valid_latency_sorted[idx])
