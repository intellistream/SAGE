"""
测试SourceFunction的单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from abc import ABC, abstractmethod
from typing import Iterator, List, Any

from sage.core.function.source_function import SourceFunction, StopSignal


class MockSourceFunction(SourceFunction):
    """测试用的Mock Source Function"""
    
    def __init__(self, data_sequence=None):
        super().__init__()
        self.data_sequence = data_sequence or ["data1", "data2", "data3"]
        self.execute_called = False
        self.execute_call_count = 0
        self.current_index = 0
        
    def execute(self):
        self.execute_called = True
        self.execute_call_count += 1
        
        if self.current_index < len(self.data_sequence):
            data = self.data_sequence[self.current_index]
            self.current_index += 1
            return data
        else:
            return StopSignal("end_of_data")


class StaticSourceFunction(SourceFunction):
    """静态数据源"""
    
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.executed = False
        
    def execute(self):
        if not self.executed:
            self.executed = True
            return self.data
        return StopSignal("static_done")


class CounterSourceFunction(SourceFunction):
    """计数器数据源"""
    
    def __init__(self, max_count=5):
        super().__init__()
        self.max_count = max_count
        self.current_count = 0
        
    def execute(self):
        if self.current_count < self.max_count:
            value = self.current_count
            self.current_count += 1
            return value
        return StopSignal("counter_done")


class InfiniteSourceFunction(SourceFunction):
    """无限数据源（用于测试）"""
    
    def __init__(self):
        super().__init__()
        self.counter = 0
        
    def execute(self):
        value = f"infinite_data_{self.counter}"
        self.counter += 1
        return value


class ErrorSourceFunction(SourceFunction):
    """会产生错误的数据源"""
    
    def __init__(self, error_on_call=1):
        super().__init__()
        self.call_count = 0
        self.error_on_call = error_on_call
        
    def execute(self):
        self.call_count += 1
        if self.call_count == self.error_on_call:
            raise RuntimeError(f"Error on call {self.call_count}")
        return f"data_{self.call_count}"


@pytest.mark.unit
class TestStopSignal:
    """StopSignal类测试"""
    
    def test_stop_signal_creation(self):
        """测试StopSignal创建"""
        signal = StopSignal("test_stop")
        assert signal.name == "test_stop"
        
    def test_stop_signal_repr(self):
        """测试StopSignal字符串表示"""
        signal = StopSignal("end_signal")
        repr_str = repr(signal)
        assert "StopSignal" in repr_str
        assert "end_signal" in repr_str
        
    def test_stop_signal_equality(self):
        """测试StopSignal相等性"""
        signal1 = StopSignal("test")
        signal2 = StopSignal("test")
        signal3 = StopSignal("other")
        
        # StopSignal实例不相等（即使name相同）
        assert signal1 is not signal2
        assert signal1.name == signal2.name
        assert signal1.name != signal3.name


@pytest.mark.unit
class TestSourceFunction:
    """SourceFunction基类测试"""
    
    def test_source_function_creation(self):
        """测试SourceFunction创建"""
        func = MockSourceFunction()
        assert not func.execute_called
        assert func.execute_call_count == 0
        assert func.current_index == 0
        
    def test_execute_method_call(self):
        """测试execute方法调用"""
        func = MockSourceFunction(["test_data"])
        
        result = func.execute()
        
        assert func.execute_called
        assert func.execute_call_count == 1
        assert result == "test_data"
        
    def test_sequential_execution(self):
        """测试顺序执行"""
        data_sequence = ["first", "second", "third"]
        func = MockSourceFunction(data_sequence)
        
        results = []
        for i in range(len(data_sequence) + 1):  # +1 to test stop signal
            result = func.execute()
            results.append(result)
            
        assert results[0] == "first"
        assert results[1] == "second"
        assert results[2] == "third"
        assert isinstance(results[3], StopSignal)
        assert results[3].name == "end_of_data"
        
    def test_empty_data_sequence(self):
        """测试空数据序列"""
        func = MockSourceFunction([])
        
        result = func.execute()
        
        assert isinstance(result, StopSignal)
        assert result.name == "end_of_data"
        
    def test_abstract_method_enforcement(self):
        """测试抽象方法强制实现"""
        
        # 尝试直接实例化抽象类，应该失败
        with pytest.raises(TypeError):
            SourceFunction()
            
    def test_inheritance_from_base_function(self):
        """测试从BaseFunction的继承"""
        func = MockSourceFunction()
        
        # 验证继承的属性
        assert hasattr(func, 'ctx')
        assert hasattr(func, 'router')
        assert hasattr(func, 'logger')
        assert hasattr(func, 'name')


@pytest.mark.unit
class TestStaticSourceFunction:
    """StaticSourceFunction测试"""
    
    def test_static_source_creation(self):
        """测试StaticSourceFunction创建"""
        test_data = {"key": "value"}
        func = StaticSourceFunction(test_data)
        
        assert func.data is test_data
        assert not func.executed
        
    def test_static_source_single_execution(self):
        """测试StaticSourceFunction单次执行"""
        test_data = "static_test_data"
        func = StaticSourceFunction(test_data)
        
        # 第一次执行返回数据
        result1 = func.execute()
        assert result1 == test_data
        assert func.executed
        
        # 第二次执行返回停止信号
        result2 = func.execute()
        assert isinstance(result2, StopSignal)
        assert result2.name == "static_done"
        
    def test_static_source_different_data_types(self):
        """测试StaticSourceFunction不同数据类型"""
        # 字符串
        func_str = StaticSourceFunction("string_data")
        assert func_str.execute() == "string_data"
        
        # 数字
        func_num = StaticSourceFunction(42)
        assert func_num.execute() == 42
        
        # 列表
        func_list = StaticSourceFunction([1, 2, 3])
        assert func_list.execute() == [1, 2, 3]
        
        # 字典
        test_dict = {"a": 1, "b": 2}
        func_dict = StaticSourceFunction(test_dict)
        assert func_dict.execute() == test_dict


@pytest.mark.unit
class TestCounterSourceFunction:
    """CounterSourceFunction测试"""
    
    def test_counter_source_creation(self):
        """测试CounterSourceFunction创建"""
        func = CounterSourceFunction(3)
        assert func.max_count == 3
        assert func.current_count == 0
        
    def test_counter_source_default_max(self):
        """测试CounterSourceFunction默认最大值"""
        func = CounterSourceFunction()
        assert func.max_count == 5
        
    def test_counter_source_execution(self):
        """测试CounterSourceFunction执行"""
        func = CounterSourceFunction(3)
        
        # 执行计数
        results = []
        for i in range(5):  # 超过max_count
            result = func.execute()
            results.append(result)
            
        assert results[0] == 0
        assert results[1] == 1
        assert results[2] == 2
        assert isinstance(results[3], StopSignal)
        assert results[3].name == "counter_done"
        assert isinstance(results[4], StopSignal)  # 继续返回停止信号
        
    def test_counter_source_zero_count(self):
        """测试CounterSourceFunction零计数"""
        func = CounterSourceFunction(0)
        
        result = func.execute()
        assert isinstance(result, StopSignal)
        assert result.name == "counter_done"


@pytest.mark.unit
class TestInfiniteSourceFunction:
    """InfiniteSourceFunction测试"""
    
    def test_infinite_source_creation(self):
        """测试InfiniteSourceFunction创建"""
        func = InfiniteSourceFunction()
        assert func.counter == 0
        
    def test_infinite_source_execution(self):
        """测试InfiniteSourceFunction执行"""
        func = InfiniteSourceFunction()
        
        # 执行多次，应该不会返回停止信号
        results = []
        for i in range(10):
            result = func.execute()
            results.append(result)
            assert not isinstance(result, StopSignal)
            
        # 验证生成的数据
        assert results[0] == "infinite_data_0"
        assert results[1] == "infinite_data_1"
        assert results[9] == "infinite_data_9"
        
        # 验证计数器递增
        assert func.counter == 10


@pytest.mark.unit
class TestErrorSourceFunction:
    """ErrorSourceFunction测试"""
    
    def test_error_source_creation(self):
        """测试ErrorSourceFunction创建"""
        func = ErrorSourceFunction(2)
        assert func.error_on_call == 2
        assert func.call_count == 0
        
    def test_error_source_normal_execution(self):
        """测试ErrorSourceFunction正常执行"""
        func = ErrorSourceFunction(3)  # 第3次调用时出错
        
        # 前两次调用正常
        result1 = func.execute()
        assert result1 == "data_1"
        
        result2 = func.execute()
        assert result2 == "data_2"
        
        # 第三次调用出错
        with pytest.raises(RuntimeError, match="Error on call 3"):
            func.execute()
            
    def test_error_source_immediate_error(self):
        """测试ErrorSourceFunction立即出错"""
        func = ErrorSourceFunction(1)  # 第1次调用就出错
        
        with pytest.raises(RuntimeError, match="Error on call 1"):
            func.execute()
            
    def test_error_source_after_error(self):
        """测试ErrorSourceFunction错误后继续执行"""
        func = ErrorSourceFunction(2)
        
        # 第一次正常
        result1 = func.execute()
        assert result1 == "data_1"
        
        # 第二次出错
        with pytest.raises(RuntimeError):
            func.execute()
            
        # 第三次又正常（因为只在第2次调用时出错）
        result3 = func.execute()
        assert result3 == "data_3"


@pytest.mark.integration
class TestSourceFunctionIntegration:
    """SourceFunction集成测试"""
    
    def test_source_function_with_context(self):
        """测试带上下文的SourceFunction"""
        func = MockSourceFunction()
        
        # 模拟上下文注入
        mock_ctx = Mock()
        mock_ctx.name = "source_test"
        mock_ctx.logger = Mock()
        func.ctx = mock_ctx
        
        # 验证继承的属性工作正常
        assert func.name == "source_test"
        assert func.logger is mock_ctx.logger
        
        # 验证Source功能正常
        result = func.execute()
        assert result == "data1"
        
    def test_source_function_data_pipeline(self):
        """测试SourceFunction在数据管道中的应用"""
        source = CounterSourceFunction(3)
        collected_data = []
        
        # 模拟数据管道消费
        while True:
            data = source.execute()
            if isinstance(data, StopSignal):
                break
            collected_data.append(data)
            
        assert collected_data == [0, 1, 2]
        
    def test_multiple_sources_coordination(self):
        """测试多个Source协调工作"""
        source1 = StaticSourceFunction("from_source1")
        source2 = CounterSourceFunction(2)
        
        # 轮询两个源
        results = []
        source1_done = False
        source2_done = False
        
        while not (source1_done and source2_done):
            if not source1_done:
                data1 = source1.execute()
                if isinstance(data1, StopSignal):
                    source1_done = True
                else:
                    results.append(("source1", data1))
                    
            if not source2_done:
                data2 = source2.execute()
                if isinstance(data2, StopSignal):
                    source2_done = True
                else:
                    results.append(("source2", data2))
                    
        assert ("source1", "from_source1") in results
        assert ("source2", 0) in results
        assert ("source2", 1) in results
        
    def test_source_function_error_handling(self):
        """测试SourceFunction错误处理"""
        source = ErrorSourceFunction(2)
        results = []
        errors = []
        
        for i in range(4):
            try:
                data = source.execute()
                results.append(data)
            except RuntimeError as e:
                errors.append(str(e))
                
        assert len(results) == 3  # 第1次、第3次、第4次成功
        assert len(errors) == 1   # 第2次出错
        assert "Error on call 2" in errors[0]
        
    def test_source_function_resource_management(self):
        """测试SourceFunction资源管理"""
        
        class ResourceSourceFunction(SourceFunction):
            def __init__(self):
                super().__init__()
                self.resource_opened = False
                self.resource_closed = False
                self.data_count = 0
                
            def open_resource(self):
                self.resource_opened = True
                
            def close_resource(self):
                self.resource_closed = True
                
            def execute(self):
                if not self.resource_opened:
                    raise RuntimeError("Resource not opened")
                    
                if self.data_count < 3:
                    self.data_count += 1
                    return f"resource_data_{self.data_count}"
                else:
                    return StopSignal("resource_exhausted")
                    
        source = ResourceSourceFunction()
        
        # 测试资源管理
        with pytest.raises(RuntimeError, match="Resource not opened"):
            source.execute()
            
        # 正常使用
        source.open_resource()
        assert source.execute() == "resource_data_1"
        assert source.execute() == "resource_data_2"
        assert source.execute() == "resource_data_3"
        
        result = source.execute()
        assert isinstance(result, StopSignal)
        assert result.name == "resource_exhausted"
        
        source.close_resource()
        assert source.resource_closed


class FileSourceFunction(SourceFunction):
    """文件数据源示例"""
    
    def __init__(self, lines):
        super().__init__()
        self.lines = lines
        self.current_line = 0
        
    def execute(self):
        if self.current_line < len(self.lines):
            line = self.lines[self.current_line]
            self.current_line += 1
            return line.strip()
        return StopSignal("end_of_file")


class DatabaseSourceFunction(SourceFunction):
    """数据库数据源示例"""
    
    def __init__(self, query_results):
        super().__init__()
        self.query_results = query_results
        self.current_row = 0
        
    def execute(self):
        if self.current_row < len(self.query_results):
            row = self.query_results[self.current_row]
            self.current_row += 1
            return row
        return StopSignal("no_more_rows")


@pytest.mark.integration
class TestRealWorldSourcePatterns:
    """真实世界SourceFunction模式测试"""
    
    def test_file_source_function(self):
        """测试文件源函数"""
        file_lines = [
            "Line 1\n",
            "Line 2\n", 
            "Line 3\n"
        ]
        source = FileSourceFunction(file_lines)
        
        results = []
        while True:
            data = source.execute()
            if isinstance(data, StopSignal):
                break
            results.append(data)
            
        assert results == ["Line 1", "Line 2", "Line 3"]
        
    def test_database_source_function(self):
        """测试数据库源函数"""
        query_results = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"}
        ]
        source = DatabaseSourceFunction(query_results)
        
        results = []
        while True:
            data = source.execute()
            if isinstance(data, StopSignal):
                break
            results.append(data)
            
        assert results == query_results
        
    def test_batched_source_processing(self):
        """测试批处理源数据处理"""
        source = CounterSourceFunction(10)
        batch_size = 3
        batches = []
        current_batch = []
        
        while True:
            data = source.execute()
            if isinstance(data, StopSignal):
                if current_batch:  # 处理最后不完整的批次
                    batches.append(current_batch)
                break
                
            current_batch.append(data)
            if len(current_batch) == batch_size:
                batches.append(current_batch)
                current_batch = []
                
        assert len(batches) == 4  # [0,1,2], [3,4,5], [6,7,8], [9]
        assert batches[0] == [0, 1, 2]
        assert batches[1] == [3, 4, 5]
        assert batches[2] == [6, 7, 8]
        assert batches[3] == [9]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
