"""
测试SinkFunction的单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from abc import ABC, abstractmethod

from sage.core.function.sink_function import SinkFunction


class MockSinkFunction(SinkFunction):
    """测试用的Mock Sink Function"""
    
    def __init__(self):
        super().__init__()
        self.execute_called = False
        self.execute_call_count = 0
        self.executed_data = []
        self.should_raise = False
        self.error_message = "Test error"
        
    def execute(self, data):
        self.execute_called = True
        self.execute_call_count += 1
        self.executed_data.append(data)
        
        if self.should_raise:
            raise ValueError(self.error_message)
        
        # Sink函数通常不返回值或返回None
        return None


class ConsoleSinkFunction(SinkFunction):
    """控制台输出Sink Function示例"""
    
    def __init__(self):
        super().__init__()
        self.output_history = []
        
    def execute(self, data):
        output = f"[CONSOLE] {data}"
        self.output_history.append(output)
        print(output)  # 实际的输出操作


class FileSinkFunction(SinkFunction):
    """文件写入Sink Function示例"""
    
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.written_data = []
        
    def execute(self, data):
        # 模拟文件写入
        self.written_data.append(data)
        # 实际实现中会写入文件


class DatabaseSinkFunction(SinkFunction):
    """数据库存储Sink Function示例"""
    
    def __init__(self, connection=None):
        super().__init__()
        self.connection = connection or Mock()
        self.stored_records = []
        
    def execute(self, data):
        # 模拟数据库存储
        if isinstance(data, dict):
            self.stored_records.append(data)
            # 模拟数据库插入
            self.connection.insert(data)


@pytest.mark.unit
class TestSinkFunction:
    """SinkFunction基类测试"""
    
    def test_sink_function_creation(self):
        """测试SinkFunction创建"""
        func = MockSinkFunction()
        assert not func.execute_called
        assert func.execute_call_count == 0
        assert func.executed_data == []
        
    def test_execute_method_call(self):
        """测试execute方法调用"""
        func = MockSinkFunction()
        test_data = "test_data"
        
        result = func.execute(test_data)
        
        assert func.execute_called
        assert func.execute_call_count == 1
        assert test_data in func.executed_data
        assert result is None  # Sink函数通常不返回值
        
    def test_multiple_execute_calls(self):
        """测试多次execute调用"""
        func = MockSinkFunction()
        
        func.execute("data1")
        func.execute("data2")
        func.execute("data3")
        
        assert func.execute_call_count == 3
        assert len(func.executed_data) == 3
        assert "data1" in func.executed_data
        assert "data2" in func.executed_data
        assert "data3" in func.executed_data
        
    def test_execute_with_different_data_types(self):
        """测试不同数据类型的execute调用"""
        func = MockSinkFunction()
        
        # 字符串数据
        func.execute("string_data")
        # 数值数据
        func.execute(42)
        # 列表数据
        func.execute([1, 2, 3])
        # 字典数据
        func.execute({"key": "value"})
        # None数据
        func.execute(None)
        
        assert func.execute_call_count == 5
        assert len(func.executed_data) == 5
        
    def test_execute_error_handling(self):
        """测试execute方法错误处理"""
        func = MockSinkFunction()
        func.should_raise = True
        func.error_message = "Sink execution failed"
        
        with pytest.raises(ValueError, match="Sink execution failed"):
            func.execute("error_data")
            
        # 即使出错，也应该记录调用
        assert func.execute_called
        assert func.execute_call_count == 1
        
    def test_abstract_method_enforcement(self):
        """测试抽象方法强制实现"""
        
        # 尝试直接实例化抽象类，应该失败
        with pytest.raises(TypeError):
            SinkFunction()
            
    def test_inheritance_from_base_function(self):
        """测试从BaseFunction的继承"""
        func = MockSinkFunction()
        
        # 验证继承的属性
        assert hasattr(func, 'ctx')
        assert hasattr(func, 'router')
        assert hasattr(func, 'logger')
        assert hasattr(func, 'name')


@pytest.mark.unit
class TestConsoleSinkFunction:
    """ConsoleSinkFunction测试"""
    
    def test_console_sink_creation(self):
        """测试ConsoleSinkFunction创建"""
        func = ConsoleSinkFunction()
        assert func.output_history == []
        
    @patch('builtins.print')
    def test_console_sink_execute(self, mock_print):
        """测试ConsoleSinkFunction执行"""
        func = ConsoleSinkFunction()
        test_data = "Hello, World!"
        
        func.execute(test_data)
        
        # 验证输出历史
        assert len(func.output_history) == 1
        assert func.output_history[0] == "[CONSOLE] Hello, World!"
        
        # 验证print被调用
        mock_print.assert_called_once_with("[CONSOLE] Hello, World!")
        
    @patch('builtins.print')
    def test_console_sink_multiple_outputs(self, mock_print):
        """测试ConsoleSinkFunction多次输出"""
        func = ConsoleSinkFunction()
        
        func.execute("Message 1")
        func.execute("Message 2")
        func.execute("Message 3")
        
        assert len(func.output_history) == 3
        assert func.output_history[0] == "[CONSOLE] Message 1"
        assert func.output_history[1] == "[CONSOLE] Message 2"
        assert func.output_history[2] == "[CONSOLE] Message 3"
        
        # 验证print被调用3次
        assert mock_print.call_count == 3


@pytest.mark.unit
class TestFileSinkFunction:
    """FileSinkFunction测试"""
    
    def test_file_sink_creation(self):
        """测试FileSinkFunction创建"""
        func = FileSinkFunction("test.txt")
        assert func.filename == "test.txt"
        assert func.written_data == []
        
    def test_file_sink_execute(self):
        """测试FileSinkFunction执行"""
        func = FileSinkFunction("output.txt")
        test_data = "File content"
        
        func.execute(test_data)
        
        assert len(func.written_data) == 1
        assert func.written_data[0] == test_data
        
    def test_file_sink_multiple_writes(self):
        """测试FileSinkFunction多次写入"""
        func = FileSinkFunction("multi.txt")
        
        func.execute("Line 1")
        func.execute("Line 2")
        func.execute("Line 3")
        
        assert len(func.written_data) == 3
        assert func.written_data == ["Line 1", "Line 2", "Line 3"]


@pytest.mark.unit
class TestDatabaseSinkFunction:
    """DatabaseSinkFunction测试"""
    
    def test_database_sink_creation(self):
        """测试DatabaseSinkFunction创建"""
        mock_connection = Mock()
        func = DatabaseSinkFunction(mock_connection)
        
        assert func.connection is mock_connection
        assert func.stored_records == []
        
    def test_database_sink_creation_without_connection(self):
        """测试DatabaseSinkFunction无连接创建"""
        func = DatabaseSinkFunction()
        
        # 应该有默认的Mock连接
        assert func.connection is not None
        assert func.stored_records == []
        
    def test_database_sink_execute_dict_data(self):
        """测试DatabaseSinkFunction执行字典数据"""
        mock_connection = Mock()
        func = DatabaseSinkFunction(mock_connection)
        
        test_data = {"id": 1, "name": "John", "email": "john@example.com"}
        func.execute(test_data)
        
        # 验证数据被存储
        assert len(func.stored_records) == 1
        assert func.stored_records[0] == test_data
        
        # 验证数据库插入被调用
        mock_connection.insert.assert_called_once_with(test_data)
        
    def test_database_sink_execute_non_dict_data(self):
        """测试DatabaseSinkFunction执行非字典数据"""
        mock_connection = Mock()
        func = DatabaseSinkFunction(mock_connection)
        
        test_data = "simple string"
        func.execute(test_data)
        
        # 非字典数据不会被存储到记录中
        assert len(func.stored_records) == 0
        
        # 但是数据库插入不会被调用
        mock_connection.insert.assert_not_called()
        
    def test_database_sink_multiple_records(self):
        """测试DatabaseSinkFunction多条记录"""
        mock_connection = Mock()
        func = DatabaseSinkFunction(mock_connection)
        
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"}
        ]
        
        for record in records:
            func.execute(record)
            
        assert len(func.stored_records) == 3
        assert func.stored_records == records
        
        # 验证每条记录都调用了插入
        assert mock_connection.insert.call_count == 3


@pytest.mark.integration
class TestSinkFunctionIntegration:
    """SinkFunction集成测试"""
    
    def test_sink_function_with_context(self):
        """测试带上下文的SinkFunction"""
        func = MockSinkFunction()
        
        # 模拟上下文注入
        mock_ctx = Mock()
        mock_ctx.name = "sink_test"
        mock_ctx.logger = Mock()
        func.ctx = mock_ctx
        
        # 验证继承的属性工作正常
        assert func.name == "sink_test"
        assert func.logger is mock_ctx.logger
        
        # 验证Sink功能正常
        func.execute("test_with_context")
        assert func.execute_called
        assert "test_with_context" in func.executed_data
        
    def test_sink_function_pipeline_integration(self):
        """测试SinkFunction在管道中的集成"""
        # 模拟一个完整的数据处理到存储流程
        processed_data = []
        
        class AccumulatorSink(SinkFunction):
            def execute(self, data):
                processed_data.append(f"STORED: {data}")
                
        sink = AccumulatorSink()
        
        # 模拟管道处理后的数据
        pipeline_outputs = ["processed_item1", "processed_item2", "processed_item3"]
        
        for output in pipeline_outputs:
            sink.execute(output)
            
        # 验证所有数据都被正确存储
        assert len(processed_data) == 3
        assert "STORED: processed_item1" in processed_data
        assert "STORED: processed_item2" in processed_data
        assert "STORED: processed_item3" in processed_data
        
    def test_multiple_sink_functions(self):
        """测试多个SinkFunction协同工作"""
        console_sink = ConsoleSinkFunction()
        file_sink = FileSinkFunction("multi_sink.txt")
        
        test_data = "Multi-sink data"
        
        with patch('builtins.print'):
            # 同一数据发送到多个sink
            console_sink.execute(test_data)
            file_sink.execute(test_data)
            
        # 验证每个sink都处理了数据
        assert test_data in console_sink.output_history[0]
        assert test_data in file_sink.written_data
        
    def test_sink_function_error_recovery(self):
        """测试SinkFunction错误恢复"""
        
        class ReliableSinkFunction(SinkFunction):
            def __init__(self):
                super().__init__()
                self.successful_executions = []
                self.failed_executions = []
                
            def execute(self, data):
                try:
                    # 模拟可能失败的操作
                    if data == "error_data":
                        raise RuntimeError("Simulated sink error")
                    self.successful_executions.append(data)
                except Exception as e:
                    self.failed_executions.append((data, str(e)))
                    # 在实际应用中，可能需要重试或记录错误
                    raise
                    
        sink = ReliableSinkFunction()
        
        # 正常数据
        sink.execute("normal_data")
        assert "normal_data" in sink.successful_executions
        
        # 错误数据
        with pytest.raises(RuntimeError):
            sink.execute("error_data")
            
        assert len(sink.failed_executions) == 1
        assert sink.failed_executions[0][0] == "error_data"


class BatchSinkFunction(SinkFunction):
    """批处理Sink Function示例"""
    
    def __init__(self, batch_size=3):
        super().__init__()
        self.batch_size = batch_size
        self.batch = []
        self.committed_batches = []
        
    def execute(self, data):
        self.batch.append(data)
        
        if len(self.batch) >= self.batch_size:
            self._commit_batch()
            
    def _commit_batch(self):
        """提交当前批次"""
        if self.batch:
            self.committed_batches.append(self.batch.copy())
            self.batch.clear()
            
    def flush(self):
        """强制提交剩余数据"""
        if self.batch:
            self._commit_batch()


@pytest.mark.integration
class TestAdvancedSinkPatterns:
    """高级Sink模式测试"""
    
    def test_batch_sink_function(self):
        """测试批处理Sink Function"""
        sink = BatchSinkFunction(batch_size=2)
        
        # 添加数据，但不足一个批次
        sink.execute("item1")
        assert len(sink.committed_batches) == 0
        assert len(sink.batch) == 1
        
        # 完成一个批次
        sink.execute("item2")
        assert len(sink.committed_batches) == 1
        assert sink.committed_batches[0] == ["item1", "item2"]
        assert len(sink.batch) == 0
        
        # 添加部分数据
        sink.execute("item3")
        assert len(sink.committed_batches) == 1
        assert len(sink.batch) == 1
        
        # 强制刷新
        sink.flush()
        assert len(sink.committed_batches) == 2
        assert sink.committed_batches[1] == ["item3"]
        assert len(sink.batch) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
