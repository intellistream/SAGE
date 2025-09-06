import pytest
import json
import numpy as np
from typing import List, Dict, Any
try:
    from sageflow import DataStream, MultiModalMessage, Operator
    CPP_AVAILABLE = True
except ImportError as e:
    CPP_AVAILABLE = False
    DataStream = MultiModalMessage = Operator = None
    print(f"C++绑定不可用: {e}")

from sageflow import Stream

class TestEndToEndCPPIntegration:
    """端到端C++/Python集成测试"""
    
    @pytest.fixture
    def large_dataset(self):
        """生成1000条测试数据"""
        data = []
        for i in range(1000):
            data.append({
                "id": i,
                "value": i * 1.5,
                "text": f"message_{i}",
                "vector": [float(i % 10 + j * 0.1) for j in range(3)]
            })
        return data
    
    @pytest.fixture
    def large_json_file(self, tmp_path):
        """保存大型数据集到JSON文件"""
        data_file = tmp_path / "large_test_data.json"
        sample_data = [{"id": i, "value": i * 2, "text": f"test_{i}"} for i in range(100)]
        with open(data_file, 'w') as f:
            json.dump(sample_data, f)
        return str(data_file)
    
    @pytest.mark.skipif(not CPP_AVAILABLE, reason="C++绑定不可用")
    def test_cpp_operator_binding(self, large_dataset):
        """测试Python DSL调用C++ operator"""
        if not CPP_AVAILABLE:
            pytest.skip("跳过C++测试")
        
        def cpp_map_func(msg: MultiModalMessage) -> MultiModalMessage:
            """使用C++ MultiModalMessage的map函数"""
            # 尝试C++ API调用
            try:
                new_msg = MultiModalMessage()
                content = msg.get_content_as_string()
                new_content = f"CPP Processed: {content}"
                new_msg.set_content_as_string(new_content)
                return new_msg
            except AttributeError as e:
                pytest.fail(f"C++ API签名不匹配: {e}")
        
        # 测试Python DSL中嵌入C++ operator
        stream = Stream.from_list(large_dataset)
        try:
            # 尝试直接使用C++ DataStream
            cpp_stream = DataStream()
            for item in large_dataset[:10]:  # 测试前10条
                msg = MultiModalMessage()
                msg.set_content_as_string(json.dumps(item))
                cpp_stream.add_message(msg)
            
            processed = cpp_stream.process()  # 假设process方法
            assert len(processed) == 10
            assert "CPP Processed" in processed[0].get_content_as_string()
        except AttributeError as e:
            pytest.fail(f"pybind11绑定错误 - C++ API不匹配: {e}")
    
    def test_python_fallback_end_to_end(self, large_dataset):
        """测试Python模拟端到端（C++不可用时的fallback）"""
        def complex_pipeline(item: Dict[str, Any]) -> Dict[str, Any]:
            # 复杂转换：添加计算字段、向量操作
            value = item["value"]
            text = item["text"]
            vector = item.get("vector", [])
            
            # 向量归一化（简化）
            if vector:
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = [v / norm for v in vector]
            
            return {
                **item,
                "processed_value": value * 2 + len(text),
                "normalized_vector": vector,
                "timestamp": "2025-01-01",
                "status": "processed"
            }
        
        def quality_filter(item: Dict[str, Any]) -> bool:
            # 质量过滤：value > 1000, 文本长度 > 5
            return (item["value"] > 1000 and 
                   len(item["text"]) > 5 and 
                   item.get("status") == "processed")
        
        # 端到端管道：map -> filter -> aggregate -> sink
        def aggregate_by_status(group: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not group:
                return {"count": 0, "total_value": 0}
            total = sum(g["processed_value"] for g in group)
            return {
                "group_size": len(group),
                "total_processed_value": total,
                "avg_value": total / len(group)
            }
        
        def status_key(item: Dict[str, Any]) -> str:
            return item.get("status", "unknown")
        
        # 执行复杂管道
        start_time = time.time()
        result = (Stream.from_list(large_dataset)
                  .map(complex_pipeline)
                  .filter(quality_filter)
                  .aggregate(status_key, aggregate_by_status)
                  .sink("print://")
                  .execute())
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"端到端处理1000条数据耗时: {duration:.3f}s")
        
        # 验证结果
        assert isinstance(result, list)
        assert len(result) > 0  # 应该有聚合结果
        for agg in result:
            assert "group_size" in agg
            assert "total_processed_value" in agg
            assert agg["group_size"] > 0
            assert duration < 2.0  # 性能要求
    
    def test_mixed_cpp_python_pipeline(self, large_dataset):
        """测试混合C++/Python管道（暴露绑定问题）"""
        if CPP_AVAILABLE:
            try:
                # 尝试混合使用
                stream = Stream.from_list(large_dataset)
                
                # Python部分
                def python_preprocess(item):
                    return {**item, "python_processed": True}
                
                python_stream = stream.map(python_preprocess)
                
                # 尝试传递给C++ (会失败暴露问题)
                try:
                    cpp_result = DataStream.from_python_stream(python_stream)  # 假设API
                    pytest.fail("意外成功 - 需要验证实际绑定")
                except AttributeError as e:
                    # 预期失败，暴露绑定问题
                    assert "from_python_stream" in str(e) or "DataStream" in str(e)
                    print(f"✓ 暴露pybind11绑定问题: {e}")
                
                # Python fallback验证
                final_result = python_stream.execute()
                assert len(final_result) == len(large_dataset)
                assert all(r.get("python_processed") for r in final_result)
                
            except Exception as e:
                pytest.fail(f"混合管道测试失败: {e}")
        else:
            # C++不可用时测试Python-only端到端
            self.test_python_fallback_end_to_end(large_dataset)
    
    def test_error_cases_end_to_end(self, large_dataset):
        """测试端到端错误场景"""
        def failing_map(item):
            if item["id"] == 500:
                raise ValueError(f"数据错误 at ID {item['id']}")
            return item
        
        with pytest.raises(RuntimeError, match="执行失败"):
            (Stream.from_list(large_dataset)
             .map(failing_map)
             .execute())
        
        # 测试空数据集
        empty_result = (Stream.from_list([])
                        .map(lambda x: x)
                        .filter(lambda x: True)
                        .execute())
        assert empty_result == []
        
        # 测试无效sink URI
        with pytest.raises(ValueError, match="不支持的sink"):
            (Stream.from_list([{"test": 1}])
             .sink("invalid://sink")
             .execute())
    
    @pytest.mark.performance
    def test_end_to_end_performance(self, large_dataset):
        """端到端性能测试"""
        def fast_map(item):
            return {"id": item["id"], "value": item["value"] * 1.1}
        
        def fast_filter(item):
            return item["value"] > 100
        
        start = time.time()
        result = (Stream.from_list(large_dataset)
                  .map(fast_map)
                  .filter(fast_filter)
                  .config(parallelism=2)  # 测试配置
                  .execute())
        end = time.time()
        
        duration = end - start
        expected_count = len([d for d in large_dataset if d["value"] * 1.1 > 100])  # 约667条
        
        print(f"端到端性能: {duration:.3f}s for {len(result)} items (expected ~{expected_count})")
        
        assert abs(len(result) - expected_count) <= 1
        assert duration < 0.8  # 性能基准

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not performance"])