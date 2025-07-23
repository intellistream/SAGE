"""
测试BaseEnvironment的批处理接口

验证新添加的批处理相关方法是否正确工作
"""

import unittest
import sys
import os
import tempfile
from unittest.mock import Mock, patch
from typing import Iterator, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.function.batch_function import BatchFunction
from sage_core.transformation.batch_transformation import BatchTransformation


class MockEnvironment:
    """模拟环境类用于测试"""
    
    def __init__(self):
        self.pipeline = []
        self.logger = Mock()
        self.platform = "local"  # 添加platform属性
        self.name = "test_env"   # 添加name属性
        self.memory_collection = None  # 添加memory_collection属性
        
        # 导入所需的方法
        from sage_core.environment.base_environment import BaseEnvironment
        
        # 绑定批处理方法到这个mock环境
        self.from_batch_collection = BaseEnvironment.from_batch_collection.__get__(self)
        self.from_batch_file = BaseEnvironment.from_batch_file.__get__(self)
        self.from_batch_range = BaseEnvironment.from_batch_range.__get__(self)
        self.from_batch_generator = BaseEnvironment.from_batch_generator.__get__(self)
        self.from_batch_custom = BaseEnvironment.from_batch_custom.__get__(self)


class MockDataStream:
    """模拟数据流"""
    def __init__(self, env, transformation):
        self.env = env
        self.transformation = transformation


class TestBatchEnvironmentInterfaces(unittest.TestCase):
    """测试批处理环境接口"""
    
    def setUp(self):
        self.env = MockEnvironment()
        
        # Mock DataStream
        self.original_datastream = None
        try:
            from sage_core.api.datastream import DataStream
            self.original_datastream = DataStream
        except ImportError:
            pass
        
        # 替换DataStream为mock版本
        with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
            pass
    
    def test_from_batch_collection(self):
        """测试from_batch_collection接口"""
        with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
            data = ["item1", "item2", "item3", "item4", "item5"]
            
            result = self.env.from_batch_collection(data)
            
            # 验证transformation被添加到pipeline
            self.assertEqual(len(self.env.pipeline), 1)
            
            transformation = self.env.pipeline[0]
            self.assertIsInstance(transformation, BatchTransformation)
            
            # 验证日志调用
            self.env.logger.info.assert_called_with("Batch collection source created with 5 items")
    
    def test_from_batch_file(self):
        """测试from_batch_file接口"""
        with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
            # 创建临时测试文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
                f.write("line1\nline2\nline3\n")
                temp_file_path = f.name
            
            try:
                result = self.env.from_batch_file(temp_file_path)
                
                # 验证transformation被添加到pipeline
                self.assertEqual(len(self.env.pipeline), 1)
                
                transformation = self.env.pipeline[0]
                self.assertIsInstance(transformation, BatchTransformation)
                
                # 验证日志调用
                expected_log = f"Batch file source created for: {temp_file_path}"
                self.env.logger.info.assert_called_with(expected_log)
                
            finally:
                # 清理临时文件
                os.unlink(temp_file_path)
    
    def test_from_batch_range(self):
        """测试from_batch_range接口"""
        with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
            result = self.env.from_batch_range(1, 11, step=2)
            
            # 验证transformation被添加到pipeline
            self.assertEqual(len(self.env.pipeline), 1)
            
            transformation = self.env.pipeline[0]
            self.assertIsInstance(transformation, BatchTransformation)
            
            # 验证日志调用 - 应该计算出5个数字 (1,3,5,7,9)
            expected_log = "Batch range source created: 1-11 (step=2, total=5)"
            self.env.logger.info.assert_called_with(expected_log)
    
    def test_from_batch_generator(self):
        """测试from_batch_generator接口"""
        with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
            def test_generator():
                for i in range(10):
                    yield i * i
            
            result = self.env.from_batch_generator(test_generator, 10)
            
            # 验证transformation被添加到pipeline
            self.assertEqual(len(self.env.pipeline), 1)
            
            transformation = self.env.pipeline[0]
            self.assertIsInstance(transformation, BatchTransformation)
            
            # 验证日志调用
            expected_log = "Batch generator source created with 10 expected items"
            self.env.logger.info.assert_called_with(expected_log)
    
    def test_from_batch_custom(self):
        """测试from_batch_custom接口"""
        with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
            class TestBatchFunction(BatchFunction):
                def get_total_count(self) -> int:
                    return 5
                
                def get_data_source(self) -> Iterator[Any]:
                    return iter(range(5))
            
            result = self.env.from_batch_custom(TestBatchFunction)
            
            # 验证transformation被添加到pipeline
            self.assertEqual(len(self.env.pipeline), 1)
            
            transformation = self.env.pipeline[0]
            self.assertIsInstance(transformation, BatchTransformation)
            
            # 验证日志调用
            expected_log = "Custom batch source created with TestBatchFunction"
            self.env.logger.info.assert_called_with(expected_log)


class TestBatchTransformation(unittest.TestCase):
    """测试BatchTransformation类"""
    
    def setUp(self):
        self.env = Mock()
        self.env.platform = "local"
        self.env.name = "test_env"
        self.env.memory_collection = None
        
    def test_batch_transformation_creation(self):
        """测试BatchTransformation的创建"""
        from sage_core.function.batch_function import SimpleBatchFunction
        
        transformation = BatchTransformation(
            self.env,
            SimpleBatchFunction,
            data=["test1", "test2", "test3"],
            progress_log_interval=50
        )
        
        # 验证属性设置
        self.assertEqual(transformation.delay, 0.1)  # 默认延迟
        self.assertEqual(transformation.progress_log_interval, 50)
        self.assertTrue(transformation.is_spout)
        
        # 验证operator_kwargs包含进度日志间隔
        kwargs = transformation.get_operator_kwargs()
        self.assertEqual(kwargs['progress_log_interval'], 50)
    
    def test_batch_transformation_default_values(self):
        """测试BatchTransformation的默认值"""
        from sage_core.function.batch_function import SimpleBatchFunction
        
        transformation = BatchTransformation(
            self.env,
            SimpleBatchFunction,
            data=["test"]
        )
        
        # 验证默认值
        self.assertEqual(transformation.delay, 0.1)
        self.assertEqual(transformation.progress_log_interval, 100)
        
        kwargs = transformation.get_operator_kwargs()
        self.assertEqual(kwargs['progress_log_interval'], 100)


def run_integration_test():
    """集成测试：验证整个批处理接口流程"""
    print("=" * 60)
    print("批处理环境接口集成测试")
    print("=" * 60)
    
    env = MockEnvironment()
    
    # 测试所有接口
    with patch('sage_core.environment.base_environment.DataStream', MockDataStream):
        
        print("\n1. 测试集合批处理接口...")
        data = list(range(100))
        stream1 = env.from_batch_collection(data, progress_log_interval=10)
        print(f"   ✓ 成功创建集合批处理，数据量: {len(data)}")
        
        print("\n2. 测试范围批处理接口...")
        stream2 = env.from_batch_range(1, 1001, step=5)
        print(f"   ✓ 成功创建范围批处理，范围: 1-1001 (step=5)")
        
        print("\n3. 测试生成器批处理接口...")
        def fibonacci_gen():
            a, b = 0, 1
            for _ in range(50):
                yield a
                a, b = b, a + b
        
        stream3 = env.from_batch_generator(fibonacci_gen, 50)
        print(f"   ✓ 成功创建生成器批处理，预期数量: 50")
        
        print("\n4. 测试自定义批处理接口...")
        class CustomBatch(BatchFunction):
            def get_total_count(self): return 25
            def get_data_source(self): return iter(range(25))
        
        stream4 = env.from_batch_custom(CustomBatch)
        print(f"   ✓ 成功创建自定义批处理")
        
        print(f"\n总共创建了 {len(env.pipeline)} 个批处理transformation")
        
        # 验证所有transformation都是BatchTransformation类型
        all_batch = all(isinstance(t, BatchTransformation) for t in env.pipeline)
        print(f"   ✓ 所有transformation都是BatchTransformation类型: {all_batch}")
        
        print("\n集成测试完成！")


if __name__ == "__main__":
    # 运行单元测试
    print("开始运行批处理环境接口测试...")
    unittest.main(verbosity=2, exit=False)
    
    # 运行集成测试
    print("\n" + "="*60)
    run_integration_test()
