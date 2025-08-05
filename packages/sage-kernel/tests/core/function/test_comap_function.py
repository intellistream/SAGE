"""
测试CoMapFunction的单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock
from abc import ABC, abstractmethod

from sage.api.function.comap_function import BaseCoMapFunction


class MockCoMapFunction(BaseCoMapFunction):
    """测试用的Mock CoMap Function"""
    
    def __init__(self):
        super().__init__()
        self.map0_called = False
        self.map1_called = False
        self.map2_called = False
        self.map3_called = False
        self.map0_inputs = []
        self.map1_inputs = []
        self.map2_inputs = []
        self.map3_inputs = []
        
    def map0(self, data):
        self.map0_called = True
        self.map0_inputs.append(data)
        return f"stream0_processed_{data}"
        
    def map1(self, data):
        self.map1_called = True
        self.map1_inputs.append(data)
        return f"stream1_processed_{data}"
        
    def map2(self, data):
        self.map2_called = True
        self.map2_inputs.append(data)
        return f"stream2_processed_{data}"
        
    def map3(self, data):
        self.map3_called = True
        self.map3_inputs.append(data)
        return f"stream3_processed_{data}"


class PartialCoMapFunction(BaseCoMapFunction):
    """只实现必需方法的CoMap Function"""
    
    def map0(self, data):
        return f"only_stream0_{data}"
        
    def map1(self, data):
        return f"only_stream1_{data}"


@pytest.mark.unit
class TestBaseCoMapFunction:
    """BaseCoMapFunction基类测试"""
    
    def test_is_comap_property(self):
        """测试is_comap属性"""
        func = MockCoMapFunction()
        assert func.is_comap is True
        
    def test_comap_function_creation(self):
        """测试CoMapFunction创建"""
        func = MockCoMapFunction()
        assert not func.map0_called
        assert not func.map1_called
        assert not func.map2_called
        assert not func.map3_called
        assert func.map0_inputs == []
        assert func.map1_inputs == []
        
    def test_map0_method(self):
        """测试map0方法"""
        func = MockCoMapFunction()
        test_data = "test_data_0"
        
        result = func.map0(test_data)
        
        assert func.map0_called
        assert test_data in func.map0_inputs
        assert result == "stream0_processed_test_data_0"
        
    def test_map1_method(self):
        """测试map1方法"""
        func = MockCoMapFunction()
        test_data = "test_data_1"
        
        result = func.map1(test_data)
        
        assert func.map1_called
        assert test_data in func.map1_inputs
        assert result == "stream1_processed_test_data_1"
        
    def test_map2_method_default_implementation(self):
        """测试map2方法的默认实现"""
        func = PartialCoMapFunction()
        test_data = "test_data_2"
        
        # map2有默认实现，应该返回None
        result = func.map2(test_data)
        assert result is None
        
    def test_map3_method_default_implementation(self):
        """测试map3方法的默认实现"""
        func = PartialCoMapFunction()
        test_data = "test_data_3"
        
        # map3有默认实现，应该返回None
        result = func.map3(test_data)
        assert result is None
        
    def test_map4_method_default_implementation(self):
        """测试map4方法的默认实现"""
        func = PartialCoMapFunction()
        test_data = "test_data_4"
        
        # map4有默认实现，应该返回None
        result = func.map4(test_data)
        assert result is None
        
    def test_multiple_stream_processing(self):
        """测试多流处理"""
        func = MockCoMapFunction()
        
        # 处理不同流的数据
        result0 = func.map0("data_0")
        result1 = func.map1("data_1")
        result2 = func.map2("data_2")
        
        assert result0 == "stream0_processed_data_0"
        assert result1 == "stream1_processed_data_1"
        assert result2 == "stream2_processed_data_2"
        
        # 验证所有流都被正确调用
        assert func.map0_called
        assert func.map1_called
        assert func.map2_called
        
    def test_stream_independence(self):
        """测试流之间的独立性"""
        func = MockCoMapFunction()
        
        # 多次调用同一个流
        func.map0("first_call")
        func.map0("second_call")
        func.map1("first_call")
        
        # 验证每个流的调用历史
        assert len(func.map0_inputs) == 2
        assert "first_call" in func.map0_inputs
        assert "second_call" in func.map0_inputs
        
        assert len(func.map1_inputs) == 1
        assert "first_call" in func.map1_inputs
        
        # map2没有被调用
        assert not func.map2_called
        assert len(func.map2_inputs) == 0
        
    def test_abstract_methods_enforcement(self):
        """测试抽象方法强制实现"""
        
        # 尝试创建只实现map0的类，应该失败
        class IncompleteCoMapFunction(BaseCoMapFunction):
            def map0(self, data):
                return data
            # 缺少map1的实现
                
        with pytest.raises(TypeError):
            IncompleteCoMapFunction()
            
    def test_inheritance_from_base_function(self):
        """测试从BaseFunction的继承"""
        func = MockCoMapFunction()
        
        # 验证继承的属性
        assert hasattr(func, 'ctx')
        assert hasattr(func, 'router')
        assert hasattr(func, 'logger')
        assert hasattr(func, 'name')
        
        # 验证CoMap特定属性
        assert func.is_comap is True


@pytest.mark.unit
class TestCoMapFunctionDataTypes:
    """CoMapFunction数据类型处理测试"""
    
    def test_string_data_processing(self):
        """测试字符串数据处理"""
        func = MockCoMapFunction()
        
        result = func.map0("hello world")
        assert result == "stream0_processed_hello world"
        
    def test_numeric_data_processing(self):
        """测试数值数据处理"""
        func = MockCoMapFunction()
        
        result = func.map1(42)
        assert result == "stream1_processed_42"
        
    def test_list_data_processing(self):
        """测试列表数据处理"""
        func = MockCoMapFunction()
        
        test_list = [1, 2, 3]
        result = func.map0(test_list)
        assert result == f"stream0_processed_{test_list}"
        
    def test_dict_data_processing(self):
        """测试字典数据处理"""
        func = MockCoMapFunction()
        
        test_dict = {"key": "value"}
        result = func.map1(test_dict)
        assert result == f"stream1_processed_{test_dict}"
        
    def test_none_data_processing(self):
        """测试None数据处理"""
        func = MockCoMapFunction()
        
        result = func.map0(None)
        assert result == "stream0_processed_None"


class ComplexCoMapFunction(BaseCoMapFunction):
    """复杂的CoMap Function实现"""
    
    def __init__(self):
        super().__init__()
        self.stream_counters = {"stream0": 0, "stream1": 0, "stream2": 0}
        
    def map0(self, data):
        self.stream_counters["stream0"] += 1
        return {"stream": 0, "data": data, "count": self.stream_counters["stream0"]}
        
    def map1(self, data):
        self.stream_counters["stream1"] += 1
        return {"stream": 1, "data": data, "count": self.stream_counters["stream1"]}
        
    def map2(self, data):
        self.stream_counters["stream2"] += 1
        return {"stream": 2, "data": data, "count": self.stream_counters["stream2"]}


@pytest.mark.integration
class TestCoMapFunctionIntegration:
    """CoMapFunction集成测试"""
    
    def test_complex_comap_function(self):
        """测试复杂CoMap Function"""
        func = ComplexCoMapFunction()
        
        # 处理多个流的数据
        result0_1 = func.map0("data1")
        result1_1 = func.map1("data1")
        result0_2 = func.map0("data2")
        result2_1 = func.map2("data1")
        
        # 验证结果
        assert result0_1 == {"stream": 0, "data": "data1", "count": 1}
        assert result1_1 == {"stream": 1, "data": "data1", "count": 1}
        assert result0_2 == {"stream": 0, "data": "data2", "count": 2}
        assert result2_1 == {"stream": 2, "data": "data1", "count": 1}
        
        # 验证计数器
        assert func.stream_counters["stream0"] == 2
        assert func.stream_counters["stream1"] == 1
        assert func.stream_counters["stream2"] == 1
        
    def test_comap_with_context(self):
        """测试带上下文的CoMap Function"""
        func = MockCoMapFunction()
        
        # 模拟上下文注入
        mock_ctx = Mock()
        mock_ctx.name = "comap_test"
        mock_ctx.logger = Mock()
        func.ctx = mock_ctx
        
        # 验证继承的属性工作正常
        assert func.name == "comap_test"
        assert func.logger is mock_ctx.logger
        
        # 验证CoMap功能正常
        result = func.map0("test_with_context")
        assert result == "stream0_processed_test_with_context"
        
    def test_comap_error_handling(self):
        """测试CoMap Function错误处理"""
        
        class ErrorCoMapFunction(BaseCoMapFunction):
            def map0(self, data):
                if data == "error":
                    raise ValueError("Stream 0 error")
                return f"stream0_{data}"
                
            def map1(self, data):
                if data == "error":
                    raise RuntimeError("Stream 1 error")
                return f"stream1_{data}"
                
        func = ErrorCoMapFunction()
        
        # 正常情况
        assert func.map0("normal") == "stream0_normal"
        assert func.map1("normal") == "stream1_normal"
        
        # 异常情况
        with pytest.raises(ValueError, match="Stream 0 error"):
            func.map0("error")
            
        with pytest.raises(RuntimeError, match="Stream 1 error"):
            func.map1("error")


@pytest.mark.integration
class TestCoMapFunctionUsagePatterns:
    """CoMapFunction使用模式测试"""
    
    def test_stream_routing_pattern(self):
        """测试流路由模式"""
        
        class RouterCoMapFunction(BaseCoMapFunction):
            def __init__(self):
                super().__init__()
                self.results = []
                
            def map0(self, data):
                # 流0: 数据验证
                if isinstance(data, dict) and "valid" in data:
                    self.results.append(("validated", data))
                    return data
                return None
                
            def map1(self, data):
                # 流1: 数据转换
                if isinstance(data, str):
                    transformed = data.upper()
                    self.results.append(("transformed", transformed))
                    return transformed
                return data
                
        func = RouterCoMapFunction()
        
        # 测试不同类型的数据路由
        func.map0({"valid": True, "data": "test"})
        func.map1("hello")
        func.map0({"invalid": True})
        
        # 验证路由结果
        assert len(func.results) == 2
        assert ("validated", {"valid": True, "data": "test"}) in func.results
        assert ("transformed", "HELLO") in func.results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
