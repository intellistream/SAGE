"""
Workload 4 Generation 单元测试
"""

import time
from pathlib import Path

import pytest


def test_batch_llm_generator_init():
    """测试 BatchLLMGenerator 初始化"""
    from workload4.generation import BatchLLMGenerator
    
    generator = BatchLLMGenerator(
        llm_base_url="http://localhost:8904/v1",
        llm_model="Qwen/Qwen2.5-3B-Instruct",
        max_tokens=100,
    )
    
    assert generator.llm_base_url == "http://localhost:8904/v1"
    assert generator.llm_model == "Qwen/Qwen2.5-3B-Instruct"
    assert generator.max_tokens == 100
    assert generator.total_calls == 0


def test_batch_llm_generator_build_prompt():
    """测试 prompt 构建"""
    from workload4.generation import BatchLLMGenerator
    
    generator = BatchLLMGenerator(
        llm_base_url="http://localhost:8904/v1",
        llm_model="test-model",
    )
    
    query = "What is SAGE?"
    context = "SAGE is a framework for AI pipelines."
    
    prompt = generator._build_prompt(query, context)
    
    assert "What is SAGE?" in prompt
    assert "SAGE is a framework for AI pipelines." in prompt
    assert "Context:" in prompt
    assert "Question:" in prompt


def test_batch_llm_generator_execute_mock():
    """测试批量生成（Mock）"""
    from workload4.generation import BatchLLMGenerator, create_mock_batch_context
    
    # 创建 Mock BatchContext
    batch_context = create_mock_batch_context(num_items=3)
    
    # 创建生成器（使用不存在的 URL，会触发错误处理）
    generator = BatchLLMGenerator(
        llm_base_url="http://localhost:9999/v1",
        llm_model="test-model",
        max_tokens=50,
        max_retries=1,
    )
    
    # 执行生成
    results = generator.execute(batch_context)
    
    # 验证结果
    assert len(results) == 3
    for query_id, response, metrics in results:
        assert query_id.startswith("query_")
        assert response.startswith("[Error:")  # 因为 URL 不存在
        assert metrics.task_id.startswith("joined_")


def test_workload4_metrics_sink_init(tmp_path):
    """测试 Workload4MetricsSink 初始化"""
    from workload4.generation import Workload4MetricsSink
    
    output_dir = tmp_path / "metrics"
    
    sink = Workload4MetricsSink(
        metrics_output_dir=str(output_dir),
        verbose=False,
    )
    
    assert sink.metrics_output_dir == output_dir
    assert sink.count == 0
    assert sink.jsonl_file.exists()
    assert sink.csv_file.exists()


def test_workload4_metrics_sink_execute(tmp_path):
    """测试指标收集"""
    from workload4.generation import Workload4MetricsSink
    from workload4.models import Workload4Metrics
    
    output_dir = tmp_path / "metrics"
    
    sink = Workload4MetricsSink(
        metrics_output_dir=str(output_dir),
        verbose=False,
    )
    
    # 创建测试指标
    metrics = Workload4Metrics(
        task_id="test_task_1",
        query_id="test_query_1",
        query_arrival_time=time.time(),
        join_time=time.time() + 0.1,
        generation_time=time.time() + 0.2,
        end_to_end_time=0.2,
        join_matched_docs=5,
        vdb1_results=10,
        vdb2_results=8,
        semantic_join_score=0.85,
    )
    
    # 执行 sink
    data = ("test_query_1", "Test response", metrics)
    sink.execute(data)
    
    # 验证
    assert sink.count == 1
    assert len(sink.metrics) == 1
    
    # 验证文件写入
    assert sink.jsonl_file.exists()
    assert sink.csv_file.exists()
    
    # 读取 JSONL 验证
    with open(sink.jsonl_file) as f:
        lines = f.readlines()
        assert len(lines) == 2  # header + 1 task
        
        import json
        header = json.loads(lines[0])
        assert header["type"] == "header"
        
        task_record = json.loads(lines[1])
        assert task_record["type"] == "task"
        assert task_record["task_id"] == "test_task_1"


def test_workload4_metrics_sink_close(tmp_path):
    """测试 Sink 关闭和汇总报告"""
    from workload4.generation import Workload4MetricsSink
    from workload4.models import Workload4Metrics
    
    output_dir = tmp_path / "metrics"
    
    sink = Workload4MetricsSink(
        metrics_output_dir=str(output_dir),
        verbose=False,
    )
    
    # 添加多个指标
    for i in range(10):
        metrics = Workload4Metrics(
            task_id=f"task_{i}",
            query_id=f"query_{i}",
            query_arrival_time=time.time(),
            join_time=time.time() + 0.1,
            generation_time=time.time() + 0.2,
            end_to_end_time=0.2 + i * 0.01,
            join_matched_docs=5 + i,
            semantic_join_score=0.8 + i * 0.01,
        )
        sink.execute((f"query_{i}", "Response", metrics))
    
    # 关闭 sink
    sink.close()
    
    # 验证汇总报告生成
    summary_files = list(output_dir.glob("summary_*.json"))
    assert len(summary_files) == 1
    
    # 读取汇总报告
    import json
    with open(summary_files[0]) as f:
        report = json.load(f)
    
    assert report["summary"]["total_tasks"] == 10
    assert "latency_statistics" in report
    assert "intermediate_results" in report
    assert "quality_metrics" in report


def test_workload4_metrics_sink_percentile():
    """测试百分位计算"""
    from workload4.generation import Workload4MetricsSink
    
    sink = Workload4MetricsSink(verbose=False)
    
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    # 使用线性插值，P50 = (5 + 6) / 2 = 5.5
    assert sink._percentile(data, 50) == 5.5
    assert sink._percentile(data, 95) == 9.55
    assert sink._percentile(data, 99) == 9.91
    
    # 空数据
    assert sink._percentile([], 50) == 0.0


def test_create_mock_batch_context():
    """测试 Mock BatchContext 创建"""
    from workload4.generation import create_mock_batch_context
    
    batch = create_mock_batch_context(num_items=5)
    
    assert batch.batch_size == 5
    assert len(batch.items) == 5
    assert batch.batch_type == "global"
    
    # 验证 items 结构
    for item in batch.items:
        assert item.query.query_id.startswith("query_")
        assert len(item.matched_docs) == 3
        assert item.semantic_score == 0.85


def test_batch_llm_generator_stats():
    """测试统计功能"""
    from workload4.generation import BatchLLMGenerator
    
    generator = BatchLLMGenerator(
        llm_base_url="http://localhost:8904/v1",
        llm_model="test-model",
    )
    
    # 初始统计
    stats = generator.get_stats()
    assert stats["total_calls"] == 0
    assert stats["failed_calls"] == 0
    assert stats["total_tokens"] == 0
    
    # 模拟调用
    generator.total_calls = 10
    generator.total_tokens = 1000
    generator.failed_calls = 1
    
    stats = generator.get_stats()
    assert stats["total_calls"] == 10
    assert stats["failed_calls"] == 1
    assert stats["avg_tokens_per_call"] == 100


def test_workload4_metrics_sink_stats(tmp_path):
    """测试 Sink 统计功能"""
    from workload4.generation import Workload4MetricsSink
    from workload4.models import Workload4Metrics
    
    output_dir = tmp_path / "metrics"
    
    sink = Workload4MetricsSink(
        metrics_output_dir=str(output_dir),
        verbose=False,
    )
    
    # 初始统计
    stats = sink.get_stats()
    assert stats["count"] == 0
    assert stats["throughput_qps"] == 0
    
    # 添加指标
    time.sleep(0.1)  # 确保有时间差
    for i in range(5):
        metrics = Workload4Metrics(
            task_id=f"task_{i}",
            query_id=f"query_{i}",
        )
        sink.execute((f"query_{i}", "Response", metrics))
    
    # 获取统计
    stats = sink.get_stats()
    assert stats["count"] == 5
    assert stats["throughput_qps"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
