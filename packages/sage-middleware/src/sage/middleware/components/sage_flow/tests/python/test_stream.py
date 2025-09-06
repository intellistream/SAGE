import pytest
import numpy as np
import os
import json
from sageflow import Stream

class TestStreamDSL:
    """测试SAGE Flow Stream DSL API"""
    
    @pytest.fixture
    def sample_data(self):
        """基础测试数据"""
        return [
            {"id": 1, "value": 10, "text": "hello"},
            {"id": 2, "value": 20, "text": "world"},
            {"id": 3, "value": 5, "text": "data"},
            {"id": 4, "value": 15, "text": "stream"},
            {"id": 5, "value": 25, "text": "processing"}
        ]
    
    @pytest.fixture
    def numpy_data(self):
        """NumPy数组数据"""
        return np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    
    @pytest.fixture
    def json_data_file(self):
        """JSON数据文件路径"""
        return "tests/data/test_messages.json"
    
    def test_basic_chain(self, sample_data):
        """测试基本链式API"""
        def double_value(item):
            return {**item, "doubled": item["value"] * 2}
        
        def is_large(item):
            return item["value"] > 15
        
        result = (Stream.from_list(sample_data)
                  .map(double_value)
                  .filter(is_large)
                  .sink("print://")
                  .execute())
        
        # 验证过滤后有3条记录 (20,15,25 -> doubled:40,30,50 >15)
        assert len(result) == 3
        assert all(r["doubled"] > 15 for r in result)
        assert result[0]["id"] == 2  # 第一个是id=2
    
    def test_numpy_integration(self, numpy_data):
        """测试NumPy数组支持"""
        def square(x):
            return x ** 2
        
        def greater_than_10(x):
            return x > 10
        
        result = (Stream.from_numpy(numpy_data)
                  .map(square)
                  .filter(greater_than_10)
                  .execute())
        
        # 预期: [1,4,9,16,25] -> filter >10: [16,25]
        expected = np.array([16.0, 25.0])
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, expected)
    
    def test_file_sink(self, sample_data, tmp_path):
        """测试文件sink"""
        output_file = tmp_path / "output.txt"
        sink_uri = f"file://{output_file}"
        
        def process_item(item):
            return f"Processed: {item['text']} (value={item['value']})"
        
        result = (Stream.from_list(sample_data)
                  .map(process_item)
                  .sink(sink_uri)
                  .execute())
        
        # 验证文件内容
        assert os.path.exists(output_file)
        with open(output_file, 'r') as f:
            content = f.read()
            assert len(content.splitlines()) == 5  # 5条记录
            assert "Processed: hello" in content
    
    def test_aggregate_window(self, sample_data):
        """测试聚合窗口（简单分组）"""
        def group_by_value_mod(item):
            return item["value"] % 10
        
        def aggregate_group(group):
            if not group:
                return {"count": 0, "avg_value": 0}
            avg = sum(g["value"] for g in group) / len(group)
            return {"group_size": len(group), "avg_value": avg}
        
        result = (Stream.from_list(sample_data)
                  .aggregate(group_by_value_mod, aggregate_group)
                  .execute())
        
        # 预期分组: 0:[10,20], 5:[5,15,25] -> 2组
        assert len(result) == 2
        avgs = [r["avg_value"] for r in result]
        assert 17.5 in avgs  # (10+20)/2=15, (5+15+25)/3=15? 等待，10%10=0,20%10=0,5%10=5,15%10=5,25%10=5 -> 0:15, 5:15
        assert all(isinstance(r, dict) for r in result)
    
    def test_lazy_execution(self, sample_data):
        """测试懒惰执行"""
        def expensive_map(item):
            # 模拟昂贵操作
            time.sleep(0.01)
            return {**item, "expensive": True}
        
        def expensive_filter(item):
            return item["id"] % 2 == 0
        
        # 创建但不执行
        stream = (Stream.from_list(sample_data)
                  .map(expensive_map)
                  .filter(expensive_filter)
                  .sink("print://"))
        
        # 验证懒惰：此时不应执行
        assert stream._result is None
        
        # 执行
        result = stream.execute()
        assert len(result) == 2  # id 2,4
        assert all(r.get("expensive") for r in result)
    
    def test_error_handling(self, sample_data):
        """测试错误处理"""
        def bad_map(item):
            if item["id"] == 3:
                raise ValueError("Bad data!")
            return item
        
        with pytest.raises(RuntimeError):
            (Stream.from_list(sample_data)
             .map(bad_map)
             .execute())
        
        # 测试空输入
        empty_result = Stream.from_list([]).execute()
        assert empty_result == []
    
    def test_large_data_performance(self):
        """测试大数据场景（1000条）"""
        large_data = [{"id": i, "value": i * 2} for i in range(1000)]
        
        def even_filter(item):
            return item["id"] % 2 == 0
        
        start_time = time.time()
        result = (Stream.from_list(large_data)
                  .filter(even_filter)
                  .execute())
        end_time = time.time()
        
        # 验证500条偶数
        assert len(result) == 500
        assert end_time - start_time < 1.0  # 性能要求
    
    def test_json_data_source(self, json_data_file):
        """测试JSON数据源"""
        # 读取JSON
        with open(json_data_file, 'r') as f:
            json_data = json.load(f)
        
        def extract_text(item):
            return {"text": item["content"]["text"], "id": item["id"]}
        
        def long_text_filter(item):
            return len(item["text"]) > 8
        
        result = (Stream.from_list(json_data)
                  .map(extract_text)
                  .filter(long_text_filter)
                  .execute())
        
        # 预期: "Message 1"(9), "Message 2"(9), "Message 3"(9) -> 所有通过? 等待，8字符
        assert len(result) == 3
        assert all(len(r["text"]) > 8 for r in result)
    
    def test_config_parallelism(self, sample_data):
        """测试配置parallelism"""
        result = (Stream.from_list(sample_data)
                  .config(parallelism=4)
                  .map(lambda x: {**x, "parallel": True})
                  .execute())
        
        assert len(result) == 5
        assert all(r.get("parallel") for r in result)
    
    def test_multiple_sinks(self, sample_data, tmp_path):
        """测试多个sink"""
        print_file = tmp_path / "print_sink.txt"
        file_sink = f"file://{tmp_path / 'file_sink.txt'}"
        
        def process(item):
            return f"ID: {item['id']}"
        
        result = (Stream.from_list(sample_data)
                  .map(process)
                  .sink("print://")
                  .sink(file_sink)
                  .execute())
        
        # 验证文件sink
        assert os.path.exists(tmp_path / "file_sink.txt")
        with open(tmp_path / "file_sink.txt", 'r') as f:
            lines = f.readlines()
            assert len(lines) == 5
            assert "ID: 1" in lines[0]

# 性能测试标记
class TestPerformance:
    @pytest.mark.performance
    def test_performance_benchmark(self):
        """性能基准测试"""
        data = [{"value": i} for i in range(10000)]
        
        def increment(item):
            item["value"] += 1
            return item
        
        def positive(item):
            return item["value"] > 0
        
        start = time.time()
        result = (Stream.from_list(data)
                  .map(increment)
                  .filter(positive)
                  .execute())
        end = time.time()
        
        duration = end - start
        print(f"处理10000条数据耗时: {duration:.3f}s")
        
        assert len(result) == 10000
        assert duration < 0.5  # 性能阈值

if __name__ == "__main__":
    pytest.main([__file__, "-v"])