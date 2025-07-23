"""
简化批处理算子测试

测试新的简化设计：BatchOperator自己进行迭代，当迭代返回空时发送停止信号
"""

import unittest
import sys
import os
import tempfile
from unittest.mock import Mock, MagicMock
from typing import Iterator, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.function.simple_batch_function import (
    SimpleBatchIteratorFunction, 
    FileBatchIteratorFunction,
    RangeBatchIteratorFunction,
    GeneratorBatchIteratorFunction,
    IterableBatchIteratorFunction
)
from sage_core.operator.batch_operator import BatchOperator
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


class TestSimpleBatchFunctions(unittest.TestCase):
    """测试简化的批处理函数"""
    
    def setUp(self):
        self.ctx = MockRuntimeContext("test_batch")
    
    def test_simple_batch_iterator_function(self):
        """测试简单批处理迭代器函数"""
        data = ["apple", "banana", "cherry"]
        func = SimpleBatchIteratorFunction(data, self.ctx)
        
        # 测试总数
        self.assertEqual(func.get_total_count(), 3)
        
        # 测试迭代器
        iterator = func.get_data_iterator()
        results = list(iterator)
        self.assertEqual(results, data)
    
    def test_file_batch_iterator_function(self):
        """测试文件批处理迭代器函数"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name
        
        try:
            func = FileBatchIteratorFunction(temp_file, ctx=self.ctx)
            
            # 测试总数
            self.assertEqual(func.get_total_count(), 3)
            
            # 测试迭代器
            iterator = func.get_data_iterator()
            results = list(iterator)
            self.assertEqual(results, ["line1", "line2", "line3"])
        finally:
            os.unlink(temp_file)
    
    def test_range_batch_iterator_function(self):
        """测试范围批处理迭代器函数"""
        func = RangeBatchIteratorFunction(1, 6, 2, ctx=self.ctx)  # 1, 3, 5
        
        # 测试总数
        self.assertEqual(func.get_total_count(), 3)
        
        # 测试迭代器
        iterator = func.get_data_iterator()
        results = list(iterator)
        self.assertEqual(results, [1, 3, 5])
    
    def test_generator_batch_iterator_function(self):
        """测试生成器批处理迭代器函数"""
        def test_generator():
            for i in range(5):
                yield i * i
        
        func = GeneratorBatchIteratorFunction(test_generator, 5, ctx=self.ctx)
        
        # 测试总数
        self.assertEqual(func.get_total_count(), 5)
        
        # 测试迭代器
        iterator = func.get_data_iterator()
        results = list(iterator)
        self.assertEqual(results, [0, 1, 4, 9, 16])
    
    def test_iterable_batch_iterator_function(self):
        """测试可迭代对象批处理迭代器函数"""
        data_set = {1, 2, 3, 4, 5}
        func = IterableBatchIteratorFunction(data_set, ctx=self.ctx)
        
        # 测试总数（应该自动获取）
        self.assertEqual(func.get_total_count(), 5)
        
        # 测试迭代器
        iterator = func.get_data_iterator()
        results = list(iterator)
        self.assertEqual(set(results), data_set)  # 集合顺序可能不同


class TestSimplifiedBatchOperator(unittest.TestCase):
    """测试简化的批处理算子"""
    
    def setUp(self):
        self.ctx = MockRuntimeContext("test_batch_op")
        self.router = MockRouter()
        self.task = MockTask()
        
        # 创建模拟的function factory
        self.function_factory = Mock()
    
    def test_batch_operator_with_simple_data(self):
        """测试简化批处理算子处理简单数据"""
        # 创建简单批处理函数
        data = ["item1", "item2", "item3"]
        batch_func = SimpleBatchIteratorFunction(data, self.ctx)
        
        # 设置function factory返回我们的批处理函数
        self.function_factory.create_function.return_value = batch_func
        
        # 创建批处理算子
        operator = BatchOperator(self.function_factory, self.ctx, progress_log_interval=1)
        operator.router = self.router
        operator.task = self.task
        
        # 模拟处理过程 - 执行直到完成
        for _ in range(10):  # 最多10次，防止无限循环
            operator.process_packet()
            if self.task.stopped:
                break
        
        # 验证结果
        self.assertEqual(len(self.router.sent_packets), 3)  # 发送了3个数据包
        self.assertEqual(len(self.router.sent_stop_signals), 1)  # 发送了1个停止信号
        self.assertTrue(self.task.stopped)  # 任务已停止
        
        # 验证发送的数据
        sent_data = [packet.payload for packet in self.router.sent_packets]
        self.assertEqual(sent_data, data)
    
    def test_batch_operator_with_empty_data(self):
        """测试批处理算子处理空数据"""
        # 创建空数据批处理函数
        batch_func = SimpleBatchIteratorFunction([], self.ctx)
        self.function_factory.create_function.return_value = batch_func
        
        operator = BatchOperator(self.function_factory, self.ctx)
        operator.router = self.router
        operator.task = self.task
        
        # 处理一次应该立即完成
        operator.process_packet()
        
        # 验证结果
        self.assertEqual(len(self.router.sent_packets), 0)  # 没有数据包
        self.assertEqual(len(self.router.sent_stop_signals), 1)  # 发送了停止信号
        self.assertTrue(self.task.stopped)  # 任务已停止
    
    def test_batch_operator_info(self):
        """测试批处理算子信息获取"""
        data = list(range(10))
        batch_func = SimpleBatchIteratorFunction(data, self.ctx)
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
        self.assertEqual(info["total_count"], 10)
        self.assertEqual(info["completion_rate"], 0.2)


class CustomIteratorFunction:
    """自定义迭代器函数用于测试"""
    
    def __init__(self, data, ctx=None):
        self.data = data
        self.ctx = ctx
        self.logger = ctx.logger if ctx else Mock()
    
    def get_data_iterator(self):
        return iter(self.data)
    
    def get_total_count(self):
        return len(self.data)


class TestBatchOperatorCompatibility(unittest.TestCase):
    """测试批处理算子兼容性"""
    
    def setUp(self):
        self.ctx = MockRuntimeContext("compat_test")
        self.router = MockRouter()
        self.task = MockTask()
        self.function_factory = Mock()
    
    def test_custom_iterator_function(self):
        """测试自定义迭代器函数"""
        data = [f"custom_{i}" for i in range(5)]
        custom_func = CustomIteratorFunction(data, self.ctx)
        
        self.function_factory.create_function.return_value = custom_func
        
        operator = BatchOperator(self.function_factory, self.ctx)
        operator.router = self.router
        operator.task = self.task
        
        # 处理直到完成
        for _ in range(10):
            operator.process_packet()
            if self.task.stopped:
                break
        
        # 验证结果
        self.assertEqual(len(self.router.sent_packets), 5)
        sent_data = [packet.payload for packet in self.router.sent_packets]
        self.assertEqual(sent_data, data)


def run_integration_test():
    """集成测试：完整的简化批处理流程"""
    print("=" * 60)
    print("简化批处理算子集成测试")
    print("=" * 60)
    
    # 创建测试数据
    test_data = [f"record_{i:03d}" for i in range(1, 8)]
    print(f"测试数据: {len(test_data)} 条记录")
    
    # 创建批处理函数
    ctx = MockRuntimeContext("integration_test")
    batch_func = SimpleBatchIteratorFunction(test_data, ctx)
    
    print(f"预计处理记录数: {batch_func.get_total_count()}")
    
    # 创建批处理算子
    function_factory = Mock()
    function_factory.create_function.return_value = batch_func
    
    operator = BatchOperator(function_factory, ctx, progress_log_interval=2)
    operator.router = MockRouter()
    operator.task = MockTask()
    
    # 执行处理
    processed_count = 0
    while not operator.task.stopped and processed_count < 20:
        operator.process_packet()
        processed_count += 1
        
        # 获取进度信息
        info = operator.get_batch_info()
        print(f"处理进度: {info['progress_percentage']} ({info['current_count']}/{info['total_count']})")
    
    # 验证结果
    print(f"发送的数据包数量: {len(operator.router.sent_packets)}")
    print(f"发送的停止信号数量: {len(operator.router.sent_stop_signals)}")
    print(f"任务是否停止: {operator.task.stopped}")
    
    # 验证数据完整性
    sent_data = [packet.payload for packet in operator.router.sent_packets]
    data_correct = sent_data == test_data
    print(f"数据完整性: {'✓' if data_correct else '✗'}")
    
    print("=" * 60)
    print("集成测试完成")


if __name__ == "__main__":
    # 运行单元测试
    print("开始运行简化批处理算子测试...")
    unittest.main(verbosity=2, exit=False)
    
    # 运行集成测试
    print("\n" + "="*60)
    run_integration_test()
