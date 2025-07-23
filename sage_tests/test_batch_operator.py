"""
批处理算子和函数的测试文件

测试新设计的BatchOperator和BatchFunction是否按预期工作
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock
from typing import Iterator, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.function.batch_function import BatchFunction, SimpleBatchFunction, FileBatchFunction
from sage_core.operator.batch_operator import BatchOperator, BatchSourceOperator
from sage_core.function.source_function import StopSignal
from sage_runtime.router.packet import Packet


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self, name: str):
        self.name = name
        self.logger = Mock()


class MockRouter:
    """模拟路由器"""
    def __init__(self):
        self.sent_packets = []
        self.sent_stop_signals = []
    
    def send(self, packet: Packet):
        self.sent_packets.append(packet)
    
    def send_stop_signal(self, stop_signal: StopSignal):
        self.sent_stop_signals.append(stop_signal)


class MockTask:
    """模拟任务"""
    def __init__(self):
        self.stopped = False
    
    def stop(self):
        self.stopped = True


class TestBatchFunction(unittest.TestCase):
    """批处理函数测试"""
    
    def setUp(self):
        self.ctx = MockRuntimeContext("test_batch")
    
    def test_simple_batch_function(self):
        """测试简单批处理函数"""
        data = ["apple", "banana", "cherry"]
        batch_func = SimpleBatchFunction(data, self.ctx)
        
        # 测试总数
        self.assertEqual(batch_func.get_total_count(), 3)
        
        # 测试执行过程
        results = []
        while not batch_func.is_finished():
            result = batch_func.execute()
            if result is not None:
                results.append(result)
        
        self.assertEqual(results, data)
        self.assertTrue(batch_func.is_finished())
        self.assertEqual(batch_func.get_completion_rate(), 1.0)
    
    def test_batch_function_progress_tracking(self):
        """测试批处理进度跟踪"""
        data = list(range(10))
        batch_func = SimpleBatchFunction(data, self.ctx)
        
        # 先初始化以获取正确的总数
        batch_func.initialize()
        
        # 初始状态
        current, total = batch_func.get_progress()
        self.assertEqual(current, 0)
        self.assertEqual(total, 10)
        self.assertEqual(batch_func.get_completion_rate(), 0.0)
        
        # 处理一半
        for i in range(5):
            batch_func.execute()
        
        current, total = batch_func.get_progress()
        self.assertEqual(current, 5)
        self.assertEqual(total, 10)
        self.assertEqual(batch_func.get_completion_rate(), 0.5)
        
        # 处理完成
        for i in range(5):
            batch_func.execute()
        
        self.assertTrue(batch_func.is_finished())
        self.assertEqual(batch_func.get_completion_rate(), 1.0)
    
    def test_batch_function_reset(self):
        """测试批处理重置功能"""
        data = ["a", "b", "c"]
        batch_func = SimpleBatchFunction(data, self.ctx)
        
        # 处理一些数据
        batch_func.execute()
        batch_func.execute()
        
        current, total = batch_func.get_progress()
        self.assertEqual(current, 2)
        
        # 重置
        batch_func.reset()
        current, total = batch_func.get_progress()
        self.assertEqual(current, 0)
        self.assertFalse(batch_func.is_finished())
        
        # 重新处理
        results = []
        while not batch_func.is_finished():
            result = batch_func.execute()
            if result is not None:
                results.append(result)
        
        self.assertEqual(results, data)


class TestBatchOperator(unittest.TestCase):
    """批处理算子测试"""
    
    def setUp(self):
        self.ctx = MockRuntimeContext("test_batch_op")
        self.router = MockRouter()
        self.task = MockTask()
        
        # 创建模拟的function factory
        self.function_factory = Mock()
    
    def test_batch_operator_complete_processing(self):
        """测试批处理算子完整处理过程"""
        # 创建简单批处理函数
        data = ["item1", "item2", "item3"]
        batch_func = SimpleBatchFunction(data, self.ctx)
        
        # 设置function factory返回我们的批处理函数
        self.function_factory.create_function.return_value = batch_func
        
        # 创建批处理算子
        operator = BatchOperator(self.function_factory, self.ctx)
        operator.router = self.router
        operator.task = self.task
        
        # 模拟处理过程
        packet_count = 0
        while not batch_func.is_finished():
            operator.process_packet()
            packet_count += 1
            if packet_count > 10:  # 防止无限循环
                break
        
        # 验证结果
        self.assertEqual(len(self.router.sent_packets), 3)  # 发送了3个数据包
        self.assertEqual(len(self.router.sent_stop_signals), 1)  # 发送了1个停止信号
        self.assertTrue(self.task.stopped)  # 任务已停止
        
        # 验证发送的数据
        sent_data = [packet.payload for packet in self.router.sent_packets]
        self.assertEqual(sent_data, data)
        
        # 验证停止信号
        stop_signal = self.router.sent_stop_signals[0]
        self.assertEqual(stop_signal.name, "test_batch_op")
    
    def test_batch_operator_info(self):
        """测试批处理算子信息获取"""
        data = list(range(5))
        batch_func = SimpleBatchFunction(data, self.ctx)
        
        self.function_factory.create_function.return_value = batch_func
        
        operator = BatchOperator(self.function_factory, self.ctx)
        operator.router = self.router
        
        # 处理一些数据
        operator.process_packet()  # 处理第一个
        operator.process_packet()  # 处理第二个
        
        # 获取批处理信息
        info = operator.get_batch_info()
        
        self.assertEqual(info["name"], "test_batch_op")
        self.assertEqual(info["current_count"], 2)
        self.assertEqual(info["total_count"], 5)
        self.assertEqual(info["completion_rate"], 0.4)
        self.assertFalse(info["is_finished"])
        self.assertEqual(info["progress_percentage"], "40.0%")


class CustomTestBatchFunction(BatchFunction):
    """自定义测试批处理函数"""
    
    def __init__(self, test_data: list, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.test_data = test_data
    
    def get_total_count(self) -> int:
        return len(self.test_data)
    
    def get_data_source(self) -> Iterator[Any]:
        return iter(self.test_data)


class TestCustomBatchFunction(unittest.TestCase):
    """自定义批处理函数测试"""
    
    def test_custom_batch_function(self):
        """测试自定义批处理函数"""
        ctx = MockRuntimeContext("custom_test")
        data = [f"custom_{i}" for i in range(3)]
        
        batch_func = CustomTestBatchFunction(data, ctx)
        
        # 测试基本功能
        self.assertEqual(batch_func.get_total_count(), 3)
        
        results = []
        while not batch_func.is_finished():
            result = batch_func.execute()
            if result is not None:
                results.append(result)
        
        self.assertEqual(results, data)
        self.assertTrue(batch_func.is_finished())


def run_integration_test():
    """集成测试：完整的批处理流程"""
    print("=== 批处理集成测试 ===")
    
    # 创建测试数据
    test_data = [f"record_{i:03d}" for i in range(1, 11)]
    print(f"测试数据: {len(test_data)} 条记录")
    
    # 创建批处理函数
    ctx = MockRuntimeContext("integration_test")
    batch_func = SimpleBatchFunction(test_data, ctx)
    
    print(f"预计处理记录数: {batch_func.get_total_count()}")
    
    # 创建批处理算子
    function_factory = Mock()
    function_factory.create_function.return_value = batch_func
    
    operator = BatchOperator(function_factory, ctx)
    operator.router = MockRouter()
    operator.task = MockTask()
    
    # 执行处理
    processed_count = 0
    while not batch_func.is_finished():
        operator.process_packet()
        processed_count += 1
        
        # 获取进度信息
        info = operator.get_batch_info()
        print(f"处理进度: {info['progress_percentage']} ({info['current_count']}/{info['total_count']})")
        
        if processed_count > 20:  # 防止无限循环
            break
    
    # 验证结果
    print(f"发送的数据包数量: {len(operator.router.sent_packets)}")
    print(f"发送的停止信号数量: {len(operator.router.sent_stop_signals)}")
    print(f"任务是否停止: {operator.task.stopped}")
    print(f"批处理是否完成: {batch_func.is_finished()}")
    
    print("=== 集成测试完成 ===")


if __name__ == "__main__":
    # 运行单元测试
    print("开始运行批处理算子和函数测试...")
    unittest.main(verbosity=2, exit=False)
    
    # 运行集成测试
    print("\n" + "="*50)
    run_integration_test()
