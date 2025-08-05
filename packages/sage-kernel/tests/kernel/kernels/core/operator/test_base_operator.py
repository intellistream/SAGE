"""
测试BaseOperator的单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from abc import ABC, abstractmethod

from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.api.function.source_function import StopSignal


class MockOperator(BaseOperator):
    """测试用的Mock Operator"""
    
    def __init__(self, function_factory, ctx, *args, **kwargs):
        self.process_packet_called = False
        self.process_packet_call_count = 0
        self.processed_packets = []
        super().__init__(function_factory, ctx, *args, **kwargs)
        
    def process_packet(self, packet=None):
        self.process_packet_called = True
        self.process_packet_call_count += 1
        self.processed_packets.append(packet)


class MockFunction:
    """Mock Function"""
    
    def __init__(self, name="mock_function"):
        self.name = name
        self.execute_called = False
        
    def execute(self, data=None):
        self.execute_called = True
        return f"processed_{data}"


class MockFunctionFactory:
    """Mock FunctionFactory"""
    
    def __init__(self, function=None):
        self.function = function or MockFunction()
        self.create_function_called = False
        self.create_function_call_count = 0
        
    def create_function(self, name, ctx):
        self.create_function_called = True
        self.create_function_call_count += 1
        return self.function


class MockTaskContext:
    """Mock TaskContext"""
    
    def __init__(self, name="test_operator", logger=None):
        self.name = name
        self.logger = logger or Mock()


class MockPacket:
    """Mock Packet"""
    
    def __init__(self, data=None, stream_id=0):
        self.data = data
        self.stream_id = stream_id
        
    def __repr__(self):
        return f"MockPacket(data={self.data}, stream_id={self.stream_id})"


@pytest.mark.unit
class TestBaseOperator:
    """BaseOperator基类测试"""
    
    def test_operator_creation(self):
        """测试BaseOperator创建"""
        mock_function = MockFunction("test_function")
        mock_factory = MockFunctionFactory(mock_function)
        mock_ctx = MockTaskContext("test_operator")
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        # 验证基本属性
        assert operator.ctx is mock_ctx
        assert operator.function is mock_function
        assert operator.task is None
        
        # 验证function factory被调用
        assert mock_factory.create_function_called
        assert mock_factory.create_function_call_count == 1
        
    def test_operator_creation_with_args_kwargs(self):
        """测试BaseOperator带参数创建"""
        mock_function = MockFunction()
        mock_factory = MockFunctionFactory(mock_function)
        mock_ctx = MockTaskContext()
        
        operator = MockOperator(
            mock_factory, mock_ctx, 
            "arg1", "arg2", 
            key1="value1", key2="value2"
        )
        
        assert operator.function is mock_function
        
    def test_operator_creation_function_factory_error(self):
        """测试function factory创建失败"""
        mock_factory = Mock()
        mock_factory.create_function.side_effect = RuntimeError("Factory error")
        mock_ctx = MockTaskContext()
        
        with pytest.raises(RuntimeError, match="Factory error"):
            MockOperator(mock_factory, mock_ctx)
            
    def test_name_property(self):
        """测试name属性"""
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext("operator_name_test")
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        assert operator.name == "operator_name_test"
        
    def test_logger_property(self):
        """测试logger属性"""
        mock_logger = Mock()
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext(logger=mock_logger)
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        assert operator.logger is mock_logger
        
    def test_inject_router(self):
        """测试路由器注入"""
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        mock_router = Mock()
        
        operator = MockOperator(mock_factory, mock_ctx)
        operator.inject_router(mock_router)
        
        assert operator.router is mock_router
        
        # 验证日志记录
        mock_ctx.logger.debug.assert_called()
        
    def test_receive_packet_valid_packet(self):
        """测试接收有效数据包"""
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        
        operator = MockOperator(mock_factory, mock_ctx)
        packet = MockPacket("test_data")
        
        operator.receive_packet(packet)
        
        # 验证process_packet被调用
        assert operator.process_packet_called
        assert operator.process_packet_call_count == 1
        assert packet in operator.processed_packets
        
        # 验证日志记录
        mock_ctx.logger.debug.assert_called()
        
    def test_receive_packet_none_packet(self):
        """测试接收None数据包"""
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        operator.receive_packet(None)
        
        # 验证process_packet仍然被调用
        assert operator.process_packet_called
        assert None in operator.processed_packets
        
        # 验证警告日志
        mock_ctx.logger.warning.assert_called()
        
    def test_multiple_packet_processing(self):
        """测试多个数据包处理"""
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        packets = [
            MockPacket("data1"),
            MockPacket("data2"), 
            MockPacket("data3")
        ]
        
        for packet in packets:
            operator.receive_packet(packet)
            
        assert operator.process_packet_call_count == 3
        assert len(operator.processed_packets) == 3
        assert all(p in operator.processed_packets for p in packets)
        
    def test_abstract_method_enforcement(self):
        """测试抽象方法强制实现"""
        
        # 尝试直接实例化抽象类，应该失败
        with pytest.raises(TypeError):
            BaseOperator(Mock(), Mock())


@pytest.mark.unit
class TestBaseOperatorStateMangement:
    """BaseOperator状态管理测试"""
    
    def test_save_state_with_stateful_function(self):
        """测试有状态函数的状态保存"""
        
        # 创建一个模拟的有状态函数
        mock_stateful_function = Mock()
        mock_stateful_function.save_state = Mock()
        
        # 需要模拟StatefulFunction类
        with patch('sage.core.operator.base_operator.StatefulFunction') as mock_stateful_class:
            mock_stateful_class.__instancecheck__ = lambda self, instance: instance is mock_stateful_function
            
            mock_factory = MockFunctionFactory(mock_stateful_function)
            mock_ctx = MockTaskContext()
            
            operator = MockOperator(mock_factory, mock_ctx)
            operator.save_state()
            
            # 验证save_state被调用
            mock_stateful_function.save_state.assert_called_once()
            
    def test_save_state_with_regular_function(self):
        """测试普通函数的状态保存"""
        mock_function = MockFunction()
        mock_factory = MockFunctionFactory(mock_function)
        mock_ctx = MockTaskContext()
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        # 普通函数没有save_state方法，不应该出错
        try:
            operator.save_state()
        except AttributeError:
            pytest.fail("save_state should not fail for non-stateful functions")


@pytest.mark.integration
class TestBaseOperatorIntegration:
    """BaseOperator集成测试"""
    
    def test_full_operator_lifecycle(self):
        """测试完整的操作器生命周期"""
        mock_function = MockFunction("lifecycle_function")
        mock_factory = MockFunctionFactory(mock_function)
        mock_ctx = MockTaskContext("lifecycle_operator")
        mock_router = Mock()
        
        # 1. 创建操作器
        operator = MockOperator(mock_factory, mock_ctx)
        assert operator.name == "lifecycle_operator"
        assert operator.function is mock_function
        
        # 2. 注入路由器
        operator.inject_router(mock_router)
        assert operator.router is mock_router
        
        # 3. 处理数据包
        packet = MockPacket("lifecycle_data")
        operator.receive_packet(packet)
        
        assert operator.process_packet_called
        assert packet in operator.processed_packets
        
        # 4. 状态保存
        operator.save_state()  # 应该不出错
        
    def test_operator_with_task_integration(self):
        """测试操作器与任务集成"""
        mock_function = MockFunction()
        mock_factory = MockFunctionFactory(mock_function)
        mock_ctx = MockTaskContext()
        mock_task = Mock()
        
        operator = MockOperator(mock_factory, mock_ctx)
        operator.task = mock_task
        
        assert operator.task is mock_task
        
    def test_operator_error_handling(self):
        """测试操作器错误处理"""
        
        class ErrorOperator(BaseOperator):
            def process_packet(self, packet=None):
                if packet and packet.data == "error":
                    raise ValueError("Processing error")
                    
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        
        operator = ErrorOperator(mock_factory, mock_ctx)
        
        # 正常数据包
        normal_packet = MockPacket("normal")
        try:
            operator.receive_packet(normal_packet)
        except Exception:
            pytest.fail("Normal packet should not cause error")
            
        # 错误数据包
        error_packet = MockPacket("error")
        with pytest.raises(ValueError, match="Processing error"):
            operator.receive_packet(error_packet)
            
    def test_operator_logging_integration(self):
        """测试操作器日志集成"""
        mock_logger = Mock()
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext("log_test", mock_logger)
        
        operator = MockOperator(mock_factory, mock_ctx)
        
        # 测试各种日志场景
        packet = MockPacket("log_data")
        operator.receive_packet(packet)
        
        # 验证debug日志被调用
        assert mock_logger.debug.call_count >= 1
        
        # 测试None包的警告日志
        operator.receive_packet(None)
        mock_logger.warning.assert_called()


class ComplexOperator(BaseOperator):
    """复杂操作器示例"""
    
    def __init__(self, function_factory, ctx, buffer_size=5):
        self.buffer_size = buffer_size
        self.packet_buffer = []
        self.processed_count = 0
        super().__init__(function_factory, ctx)
        
    def process_packet(self, packet=None):
        if packet is None:
            return
            
        self.packet_buffer.append(packet)
        
        # 当缓冲区满时批量处理
        if len(self.packet_buffer) >= self.buffer_size:
            self._process_buffer()
            
    def _process_buffer(self):
        """处理缓冲区中的数据包"""
        batch_data = [p.data for p in self.packet_buffer]
        # 模拟批量处理
        self.processed_count += len(self.packet_buffer)
        self.packet_buffer.clear()
        
    def flush(self):
        """强制处理剩余的数据包"""
        if self.packet_buffer:
            self._process_buffer()


@pytest.mark.integration
class TestAdvancedOperatorPatterns:
    """高级操作器模式测试"""
    
    def test_buffered_operator(self):
        """测试缓冲操作器"""
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        
        operator = ComplexOperator(mock_factory, mock_ctx, buffer_size=3)
        
        # 发送2个数据包，不足buffer_size
        operator.receive_packet(MockPacket("data1"))
        operator.receive_packet(MockPacket("data2"))
        
        assert len(operator.packet_buffer) == 2
        assert operator.processed_count == 0
        
        # 发送第3个数据包，触发批量处理
        operator.receive_packet(MockPacket("data3"))
        
        assert len(operator.packet_buffer) == 0
        assert operator.processed_count == 3
        
        # 发送剩余数据包
        operator.receive_packet(MockPacket("data4"))
        operator.receive_packet(MockPacket("data5"))
        
        assert len(operator.packet_buffer) == 2
        assert operator.processed_count == 3
        
        # 强制刷新
        operator.flush()
        
        assert len(operator.packet_buffer) == 0
        assert operator.processed_count == 5
        
    def test_operator_with_stop_signal(self):
        """测试操作器处理停止信号"""
        
        class StopSignalOperator(BaseOperator):
            def __init__(self, function_factory, ctx):
                super().__init__(function_factory, ctx)
                self.stop_signal_received = False
                
            def process_packet(self, packet=None):
                if packet and isinstance(packet.data, StopSignal):
                    self.stop_signal_received = True
                    self.logger.info(f"Received stop signal: {packet.data}")
                    
        mock_factory = MockFunctionFactory()
        mock_ctx = MockTaskContext()
        
        operator = StopSignalOperator(mock_factory, mock_ctx)
        
        # 正常数据包
        operator.receive_packet(MockPacket("normal_data"))
        assert not operator.stop_signal_received
        
        # 停止信号
        stop_signal = StopSignal("test_stop")
        operator.receive_packet(MockPacket(stop_signal))
        assert operator.stop_signal_received


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
