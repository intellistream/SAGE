"""
Unit Tests for ResultsCollector
================================

测试 ResultsCollector 的所有功能，包括：
- 单例模式
- 线程安全
- 结果收集和聚合
- JSON 导入导出
"""

import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sage.benchmark.benchmark_refiner.experiments.results_collector import (
    ResultsCollector,
    get_collector,
)


class TestResultsCollectorBasic:
    """基础功能测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_singleton_pattern(self):
        """测试单例模式"""
        collector1 = ResultsCollector()
        collector2 = ResultsCollector()
        assert collector1 is collector2

    def test_get_collector_function(self):
        """测试便捷函数"""
        collector = get_collector()
        assert isinstance(collector, ResultsCollector)
        assert collector is ResultsCollector()

    def test_add_sample_basic(self):
        """测试添加样本"""
        collector = ResultsCollector()
        collector.reset()

        sample_id = collector.add_sample(sample_id=0, metrics={"f1": 0.35, "latency": 1.5})

        assert sample_id == 0
        assert len(collector) == 1

        result = collector.get_sample(0)
        assert result is not None
        assert result["f1"] == 0.35
        assert result["latency"] == 1.5

    def test_add_sample_auto_id(self):
        """测试自动生成 sample_id"""
        collector = ResultsCollector()
        collector.reset()

        id1 = collector.add_sample(metrics={"f1": 0.3})
        id2 = collector.add_sample(metrics={"f1": 0.4})

        assert id1 == 0
        assert id2 == 1
        assert len(collector) == 2

    def test_add_sample_with_kwargs(self):
        """测试使用 kwargs 添加指标"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id=0, f1=0.35, compression_rate=2.5)

        result = collector.get_sample(0)
        assert result["f1"] == 0.35
        assert result["compression_rate"] == 2.5

    def test_update_sample(self):
        """测试更新样本"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id=0, f1=0.35)
        collector.update_sample(0, compression_rate=2.5)

        result = collector.get_sample(0)
        assert result["f1"] == 0.35
        assert result["compression_rate"] == 2.5

    def test_update_sample_creates_if_not_exists(self):
        """测试更新不存在的样本时自动创建"""
        collector = ResultsCollector()
        collector.reset()

        collector.update_sample(10, f1=0.5)

        result = collector.get_sample(10)
        assert result is not None
        assert result["f1"] == 0.5

    def test_get_results_sorted(self):
        """测试获取结果时按 sample_id 排序"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id=2, f1=0.3)
        collector.add_sample(sample_id=0, f1=0.5)
        collector.add_sample(sample_id=1, f1=0.4)

        results = collector.get_results()
        assert len(results) == 3
        assert results[0]["sample_id"] == 0
        assert results[1]["sample_id"] == 1
        assert results[2]["sample_id"] == 2

    def test_get_sample_not_found(self):
        """测试获取不存在的样本"""
        collector = ResultsCollector()
        collector.reset()

        result = collector.get_sample(999)
        assert result is None

    def test_reset(self):
        """测试重置"""
        collector = ResultsCollector()
        collector.add_sample(sample_id=0, f1=0.35)
        collector.set_metadata(experiment="test")

        collector.reset()

        assert len(collector) == 0
        assert collector.get_metadata() == {}

    def test_len(self):
        """测试 __len__"""
        collector = ResultsCollector()
        collector.reset()

        assert len(collector) == 0

        collector.add_sample(f1=0.3)
        assert len(collector) == 1

        collector.add_sample(f1=0.4)
        assert len(collector) == 2


class TestResultsCollectorAggregation:
    """聚合功能测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_get_aggregated_empty(self):
        """测试空收集器的聚合"""
        collector = ResultsCollector()
        collector.reset()

        aggregated = collector.get_aggregated()
        assert aggregated["num_samples"] == 0

    def test_get_aggregated_single_sample(self):
        """测试单个样本的聚合"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id=0, f1=0.35, latency=1.5)

        aggregated = collector.get_aggregated()
        assert aggregated["num_samples"] == 1
        assert aggregated["avg_f1"] == 0.35
        assert aggregated["std_f1"] == 0.0
        assert aggregated["min_f1"] == 0.35
        assert aggregated["max_f1"] == 0.35

    def test_get_aggregated_multiple_samples(self):
        """测试多个样本的聚合"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(f1=0.3)
        collector.add_sample(f1=0.4)
        collector.add_sample(f1=0.5)

        aggregated = collector.get_aggregated()
        assert aggregated["num_samples"] == 3
        assert abs(aggregated["avg_f1"] - 0.4) < 0.001
        assert aggregated["min_f1"] == 0.3
        assert aggregated["max_f1"] == 0.5
        assert aggregated["std_f1"] > 0

    def test_get_aggregated_ignores_non_numeric(self):
        """测试聚合时忽略非数值字段"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(f1=0.35, query="What is AI?", enabled=True)

        aggregated = collector.get_aggregated()
        assert "avg_f1" in aggregated
        assert "avg_query" not in aggregated
        assert "avg_enabled" not in aggregated

    def test_get_metric_values(self):
        """测试获取指定指标的所有值"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(f1=0.3, latency=1.0)
        collector.add_sample(f1=0.4, latency=1.5)
        collector.add_sample(f1=0.5)  # 无 latency

        f1_values = collector.get_metric_values("f1")
        assert f1_values == [0.3, 0.4, 0.5]

        latency_values = collector.get_metric_values("latency")
        assert latency_values == [1.0, 1.5]

        missing_values = collector.get_metric_values("nonexistent")
        assert missing_values == []


class TestResultsCollectorMetadata:
    """元数据测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_set_and_get_metadata(self):
        """测试设置和获取元数据"""
        collector = ResultsCollector()
        collector.reset()

        collector.set_metadata(
            experiment="refiner_comparison",
            algorithm="longrefiner",
            dataset="nq",
        )

        metadata = collector.get_metadata()
        assert metadata["experiment"] == "refiner_comparison"
        assert metadata["algorithm"] == "longrefiner"
        assert metadata["dataset"] == "nq"

    def test_metadata_update(self):
        """测试元数据更新"""
        collector = ResultsCollector()
        collector.reset()

        collector.set_metadata(key1="value1")
        collector.set_metadata(key2="value2")
        collector.set_metadata(key1="updated")

        metadata = collector.get_metadata()
        assert metadata["key1"] == "updated"
        assert metadata["key2"] == "value2"


class TestResultsCollectorExport:
    """导入导出测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_export_json(self):
        """测试 JSON 导出"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id=0, f1=0.35, compression_rate=2.5)
        collector.add_sample(sample_id=1, f1=0.40, compression_rate=3.0)
        collector.set_metadata(experiment="test")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            collector.export_json(output_path)

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "results" in data
            assert "aggregated" in data
            assert "metadata" in data
            assert len(data["results"]) == 2
            assert data["metadata"]["experiment"] == "test"

    def test_export_json_without_metadata(self):
        """测试不包含元数据的 JSON 导出"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(f1=0.35)
        collector.set_metadata(experiment="test")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            collector.export_json(output_path, include_metadata=False)

            with open(output_path) as f:
                data = json.load(f)

            assert "results" in data
            assert "aggregated" in data
            assert "metadata" not in data

    def test_export_creates_directory(self):
        """测试导出时自动创建目录"""
        collector = ResultsCollector()
        collector.reset()
        collector.add_sample(f1=0.35)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "results.json"
            collector.export_json(output_path)

            assert output_path.exists()

    def test_load_json(self):
        """测试 JSON 导入"""
        # 先导出
        collector1 = ResultsCollector()
        collector1.reset()
        collector1.add_sample(sample_id=0, f1=0.35, compression_rate=2.5)
        collector1.add_sample(sample_id=1, f1=0.40, compression_rate=3.0)
        collector1.set_metadata(experiment="test", algorithm="longrefiner")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            collector1.export_json(output_path)

            # 再导入
            collector2 = ResultsCollector.load_json(output_path)

            assert len(collector2) == 2
            assert collector2.get_sample(0)["f1"] == 0.35
            assert collector2.get_sample(1)["compression_rate"] == 3.0
            assert collector2.get_metadata()["experiment"] == "test"


class TestResultsCollectorThreadSafety:
    """线程安全测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_concurrent_add_samples(self):
        """测试并发添加样本"""
        collector = ResultsCollector()
        collector.reset()

        num_threads = 10
        samples_per_thread = 100

        def add_samples(thread_id):
            for i in range(samples_per_thread):
                sample_id = thread_id * samples_per_thread + i
                collector.add_sample(
                    sample_id=sample_id,
                    f1=0.3 + (sample_id % 10) * 0.01,
                    thread_id=thread_id,
                )

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(add_samples, i) for i in range(num_threads)]
            for future in futures:
                future.result()

        assert len(collector) == num_threads * samples_per_thread

    def test_concurrent_update_same_sample(self):
        """测试并发更新同一样本"""
        collector = ResultsCollector()
        collector.reset()
        collector.add_sample(sample_id=0, f1=0.0)

        num_updates = 100
        final_values = []
        lock = threading.Lock()

        def update_sample(value):
            collector.update_sample(0, metric=value)
            with lock:
                final_values.append(value)

        threads = []
        for i in range(num_updates):
            t = threading.Thread(target=update_sample, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        result = collector.get_sample(0)
        assert result is not None
        assert "metric" in result

    def test_concurrent_read_write(self):
        """测试并发读写"""
        collector = ResultsCollector()
        collector.reset()

        num_operations = 100
        results_collected = []
        lock = threading.Lock()

        def writer(sample_id):
            collector.add_sample(sample_id=sample_id, f1=0.3 + sample_id * 0.001)

        def reader():
            results = collector.get_results()
            with lock:
                results_collected.append(len(results))

        threads = []
        for i in range(num_operations):
            writer_thread = threading.Thread(target=writer, args=(i,))
            reader_thread = threading.Thread(target=reader)
            threads.extend([writer_thread, reader_thread])
            writer_thread.start()
            reader_thread.start()

        for t in threads:
            t.join()

        # 最终应有所有样本
        assert len(collector) == num_operations


class TestResultsCollectorStringId:
    """字符串 ID 测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_string_sample_id(self):
        """测试使用字符串作为 sample_id"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id="sample_001", f1=0.35)
        collector.add_sample(sample_id="sample_002", f1=0.40)

        assert len(collector) == 2
        assert collector.get_sample("sample_001")["f1"] == 0.35
        assert collector.get_sample("sample_002")["f1"] == 0.40

    def test_mixed_id_types(self):
        """测试混合 ID 类型"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(sample_id=0, f1=0.30)
        collector.add_sample(sample_id="str_id", f1=0.35)
        collector.add_sample(sample_id=1, f1=0.40)

        assert len(collector) == 3

        results = collector.get_results()
        # 整数 ID 应该在字符串 ID 之前（按 hash 排序）
        assert len(results) == 3


class TestResultsCollectorRepr:
    """字符串表示测试"""

    def setup_method(self):
        """每个测试前重置收集器"""
        ResultsCollector().reset()

    def test_repr_empty(self):
        """测试空收集器的字符串表示"""
        collector = ResultsCollector()
        collector.reset()

        assert repr(collector) == "ResultsCollector(samples=0)"

    def test_repr_with_samples(self):
        """测试有样本的字符串表示"""
        collector = ResultsCollector()
        collector.reset()

        collector.add_sample(f1=0.3)
        collector.add_sample(f1=0.4)

        assert repr(collector) == "ResultsCollector(samples=2)"
