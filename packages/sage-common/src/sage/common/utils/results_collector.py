"""
Results Collector
=================

通用结果收集器，用于在 Pipeline 执行过程中收集评测指标。
线程安全实现，支持 Pipeline 并行运行。

使用示例:
    from sage.common.utils.results_collector import ResultsCollector

    collector = ResultsCollector()
    collector.reset()

    # 在 Operators 中添加结果
    collector.add_sample(sample_id=0, f1=0.35, compression_rate=2.5)

    # Pipeline 运行后获取结果
    results = collector.get_results()
    # [{"sample_id": 0, "f1": 0.35, "compression_rate": 2.5, ...}, ...]

    aggregated = collector.get_aggregated()
    # {"avg_f1": 0.35, "std_f1": 0.02, "avg_compression_rate": 2.5, ...}
"""

from __future__ import annotations

import json
import statistics
import threading
from pathlib import Path
from typing import Any


class ResultsCollector:
    """
    结果收集器 - 单例模式

    用于收集评测 Operators 产生的结果，支持：
    - 线程安全的结果添加
    - 样本级和聚合级结果获取
    - JSON 导出
    """

    _instance: ResultsCollector | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ResultsCollector:
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._init_internal()
                    cls._instance = instance
        return cls._instance

    def _init_internal(self) -> None:
        """内部初始化"""
        self._results: dict[int | str, dict[str, Any]] = {}
        self._data_lock = threading.Lock()
        self._sample_counter = 0
        self._metadata: dict[str, Any] = {}

    def reset(self) -> None:
        """
        清空所有收集的结果

        在开始新的实验前调用此方法。
        """
        with self._data_lock:
            self._results.clear()
            self._sample_counter = 0
            self._metadata.clear()

    def add_sample(
        self,
        sample_id: int | str | None = None,
        metrics: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> int | str:
        """
        添加单个样本的结果

        Args:
            sample_id: 样本 ID，如果为 None 则自动生成
            metrics: 指标字典
            **kwargs: 额外的指标（会合并到 metrics 中）

        Returns:
            使用的 sample_id
        """
        with self._data_lock:
            # 自动生成 sample_id
            if sample_id is None:
                sample_id = self._sample_counter
                self._sample_counter += 1

            # 合并 metrics 和 kwargs
            all_metrics = metrics.copy() if metrics else {}
            all_metrics.update(kwargs)

            # 如果该 sample_id 已存在，合并指标
            if sample_id in self._results:
                self._results[sample_id].update(all_metrics)
            else:
                self._results[sample_id] = {"sample_id": sample_id, **all_metrics}

            return sample_id

    def update_sample(
        self,
        sample_id: int | str,
        metrics: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        更新已存在样本的指标

        Args:
            sample_id: 样本 ID
            metrics: 要更新的指标字典
            **kwargs: 额外的指标
        """
        with self._data_lock:
            if sample_id not in self._results:
                self._results[sample_id] = {"sample_id": sample_id}

            if metrics:
                self._results[sample_id].update(metrics)
            self._results[sample_id].update(kwargs)

    def get_results(self) -> list[dict[str, Any]]:
        """
        获取所有样本的结果

        Returns:
            样本结果列表，按 sample_id 排序
        """
        with self._data_lock:
            sorted_results = sorted(
                self._results.values(),
                key=lambda x: (
                    x.get("sample_id", 0)
                    if isinstance(x.get("sample_id"), int)
                    else hash(x.get("sample_id", ""))
                ),
            )
            return [r.copy() for r in sorted_results]

    def get_sample(self, sample_id: int | str) -> dict[str, Any] | None:
        """
        获取指定样本的结果

        Args:
            sample_id: 样本 ID

        Returns:
            样本结果字典，不存在则返回 None
        """
        with self._data_lock:
            result = self._results.get(sample_id)
            return result.copy() if result else None

    def get_aggregated(self) -> dict[str, Any]:
        """
        获取聚合统计指标

        Returns:
            聚合指标字典，包含各指标的 avg, std, min, max
        """
        with self._data_lock:
            if not self._results:
                return {"num_samples": 0}

            results = list(self._results.values())

        # 收集所有数值型指标
        metric_values: dict[str, list[float]] = {}
        for result in results:
            for key, value in result.items():
                if key == "sample_id":
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if key not in metric_values:
                        metric_values[key] = []
                    metric_values[key].append(float(value))

        # 计算统计指标
        aggregated: dict[str, Any] = {"num_samples": len(results)}

        for metric_name, values in metric_values.items():
            if not values:
                continue

            aggregated[f"avg_{metric_name}"] = statistics.mean(values)

            if len(values) > 1:
                aggregated[f"std_{metric_name}"] = statistics.stdev(values)
            else:
                aggregated[f"std_{metric_name}"] = 0.0

            aggregated[f"min_{metric_name}"] = min(values)
            aggregated[f"max_{metric_name}"] = max(values)

        return aggregated

    def get_metric_values(self, metric_name: str) -> list[float]:
        """
        获取指定指标的所有值

        Args:
            metric_name: 指标名称

        Returns:
            该指标的所有值列表
        """
        with self._data_lock:
            values = []
            for result in self._results.values():
                if metric_name in result:
                    value = result[metric_name]
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        values.append(float(value))
            return values

    def set_metadata(self, **kwargs: Any) -> None:
        """
        设置实验元数据

        Args:
            **kwargs: 元数据键值对
        """
        with self._data_lock:
            self._metadata.update(kwargs)

    def get_metadata(self) -> dict[str, Any]:
        """
        获取实验元数据

        Returns:
            元数据字典
        """
        with self._data_lock:
            return self._metadata.copy()

    def export_json(self, path: str | Path, include_metadata: bool = True) -> None:
        """
        导出结果到 JSON 文件

        Args:
            path: 输出文件路径
            include_metadata: 是否包含元数据
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        export_data: dict[str, Any] = {
            "results": self.get_results(),
            "aggregated": self.get_aggregated(),
        }

        if include_metadata:
            export_data["metadata"] = self.get_metadata()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_json(cls, path: str | Path) -> ResultsCollector:
        """
        从 JSON 文件加载结果

        Args:
            path: JSON 文件路径

        Returns:
            填充了数据的 ResultsCollector 实例
        """
        collector = cls()
        collector.reset()

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # 加载结果
        if "results" in data:
            for result in data["results"]:
                sample_id = result.pop("sample_id", None)
                collector.add_sample(sample_id=sample_id, metrics=result)

        # 加载元数据
        if "metadata" in data:
            collector.set_metadata(**data["metadata"])

        return collector

    def __len__(self) -> int:
        """返回收集的样本数量"""
        with self._data_lock:
            return len(self._results)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"ResultsCollector(samples={len(self)})"


# 便捷访问函数
def get_collector() -> ResultsCollector:
    """
    获取全局 ResultsCollector 实例

    Returns:
        ResultsCollector 单例
    """
    return ResultsCollector()
