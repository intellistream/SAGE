#!/usr/bin/env python3
"""
测试改进后的 from_batch 接口的多态性
"""

from sage.core.api.base_environment import BaseEnvironment
from sage.core.function.base_function import BaseFunction
from sage.runtime.communication.queue.base_queue_descriptor import BaseQueueDescriptor


class MockEnvironment(BaseEnvironment):
    """测试用的环境实现"""
    def submit(self):
        pass
    
    def get_qd(self, name: str, maxsize: int = 10000) -> 'BaseQueueDescriptor':
        """实现抽象方法 get_qd"""
        # 返回一个模拟的队列描述符，这里可以返回 None 或者一个简单的模拟对象
        return None


class CustomBatchFunction(BaseFunction):
    """自定义批处理函数示例"""
    def __init__(self, start=0, end=10):
        super().__init__()
        self.start = start
        self.end = end
        
    def get_data_iterator(self):
        return iter(range(self.start, self.end))
        
    def get_total_count(self):
        return self.end - self.start


def test_from_batch_polymorphism():
    """测试 from_batch 方法的多态性"""
    env = MockEnvironment("test_env", {})
    
    print("Testing from_batch polymorphism...")
    
    # 1. 测试自定义批处理函数类
    print("\n1. Testing custom batch function class:")
    batch_stream1 = env.from_batch(CustomBatchFunction, start=0, end=5)
    print(f"   ✓ Created stream from CustomBatchFunction")
    
    # 2. 测试数据列表
    print("\n2. Testing list data:")
    data_list = ["apple", "banana", "cherry", "date", "elderberry"]
    batch_stream2 = env.from_batch(data_list)
    print(f"   ✓ Created stream from list with {len(data_list)} items")
    
    # 3. 测试元组
    print("\n3. Testing tuple data:")
    data_tuple = (1, 2, 3, 4, 5)
    batch_stream3 = env.from_batch(data_tuple)
    print(f"   ✓ Created stream from tuple with {len(data_tuple)} items")
    
    # 4. 测试集合
    print("\n4. Testing set data:")
    data_set = {10, 20, 30, 40, 50}
    batch_stream4 = env.from_batch(data_set)
    print(f"   ✓ Created stream from set")
    
    # 5. 测试字符串（按字符迭代）
    print("\n5. Testing string data:")
    data_string = "hello"
    batch_stream5 = env.from_batch(data_string)
    print(f"   ✓ Created stream from string: '{data_string}'")
    
    # 6. 测试 range 对象
    print("\n6. Testing range object:")
    data_range = range(0, 100, 2)  # 偶数 0-98
    batch_stream6 = env.from_batch(data_range)
    print(f"   ✓ Created stream from range(0, 100, 2)")
    
    # 7. 测试生成器
    print("\n7. Testing generator:")
    def number_generator():
        for i in range(5):
            yield f"generated_{i}"
    
    batch_stream7 = env.from_batch(number_generator())
    print(f"   ✓ Created stream from generator")
    
    # 8. 测试带配置参数
    print("\n8. Testing with configuration parameters:")
    batch_stream8 = env.from_batch(
        data_list, 
        progress_log_interval=2,
        delay=0.1
    )
    print(f"   ✓ Created stream with configuration parameters")
    
    # 9. 测试自定义函数类与参数
    print("\n9. Testing custom function class with parameters:")
    batch_stream9 = env.from_batch(
        CustomBatchFunction,
        start=10,
        end=20,
        progress_log_interval=5
    )
    print(f"   ✓ Created stream from CustomBatchFunction with parameters")
    
    print(f"\n✅ All tests passed! Created {len(env.pipeline)} transformations")
    
    # 检查创建的流类型
    print(f"\nPipeline transformations:")
    for i, transformation in enumerate(env.pipeline):
        print(f"   {i+1}. {transformation.__class__.__name__}")
    
    # Assert success instead of returning True
    assert len(env.pipeline) > 0


def test_error_handling():
    """测试错误处理"""
    env = MockEnvironment("test_env", {})
    
    print("\nTesting error handling...")
    
    # 测试不支持的类型
    try:
        unsupported_data = 12345  # 数字不可迭代
        batch_stream = env.from_batch(unsupported_data)
        print("   ❌ Should have raised TypeError")
        assert False, "Should have raised TypeError"
    except TypeError as e:
        print(f"   ✓ Correctly raised TypeError: {e}")
    
    print("✅ Error handling test passed!")
    # Assert success instead of returning True


if __name__ == "__main__":
    success1 = test_from_batch_polymorphism()
    success2 = test_error_handling()
    
    if success1 and success2:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n❌ Some tests failed!")
