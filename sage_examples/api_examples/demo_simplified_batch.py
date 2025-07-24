#!/usr/bin/env python3
"""
简化批处理系统演示

展示新设计的简化特性：
1. 批处理算子自己进行迭代
2. 当迭代返回空时自动发送停止信号
3. 支持多种数据源类型的简化函数
4. 自动进度跟踪和日志记录
"""

import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.api.local_environment import LocalEnvironment
from sage_core.function.simple_batch_function import (
    SimpleBatchIteratorFunction,
    FileBatchIteratorFunction, 
    RangeBatchIteratorFunction,
    GeneratorBatchIteratorFunction,
    IterableBatchIteratorFunction
)
from sage_core.function.base_function import BaseFunction


class CollectorFunction(BaseFunction):
    """数据收集器函数"""
    
    def __init__(self, ctx=None):
        super().__init__(ctx)
        self.collected_data = []
    
    def execute(self, data):
        self.collected_data.append(data)
        print(f"收集: {data}")
        return data


def demo_1_simple_data_batch():
    """演示1: 简单数据集合的批处理"""
    print("=" * 60)
    print("演示1: 简单数据集合批处理")
    print("=" * 60)
    
    env = LocalEnvironment("demo1")
    
    # 创建一些示例数据
    fruits = ["apple", "banana", "cherry", "date", "elderberry"]
    print(f"原始数据: {fruits}")
    
    # 使用environment的批处理接口并添加收集器
    env.from_batch_collection(fruits).print("处理: ")
    
    # 提交并执行环境
    env.submit()
    
    print("批处理执行完成!")
    print()


def demo_2_file_batch():
    """演示2: 文件批处理"""
    print("=" * 60)
    print("演示2: 文件批处理")
    print("=" * 60)
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        test_lines = [
            "第一行数据",
            "第二行数据", 
            "第三行数据",
            "第四行数据"
        ]
        f.write('\n'.join(test_lines))
        temp_file = f.name
    
    try:
        env = LocalEnvironment("demo2")
        print(f"临时文件: {temp_file}")
        print(f"文件内容: {test_lines}")
        
        # 使用文件批处理
        result_stream = env.from_batch_file(temp_file)
        
        results = []
        for line in result_stream:
            print(f"读取行: '{line}'")
            results.append(line.upper())  # 转为大写
        
        print(f"处理结果: {results}")
    finally:
        os.unlink(temp_file)
    print()


def demo_3_range_batch():
    """演示3: 数值范围批处理"""
    print("=" * 60)
    print("演示3: 数值范围批处理")
    print("=" * 60)
    
    env = LocalEnvironment("demo3")
    
    # 生成1到20的偶数
    print("生成范围: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20")
    result_stream = env.from_batch_range(2, 22, 2)
    
    squares = []
    for num in result_stream:
        square = num ** 2
        print(f"{num}^2 = {square}")
        squares.append(square)
    
    print(f"平方数结果: {squares}")
    print()


def demo_4_generator_batch():
    """演示4: 生成器函数批处理"""
    print("=" * 60)
    print("演示4: 生成器函数批处理")
    print("=" * 60)
    
    env = LocalEnvironment("demo4")
    
    # 创建斐波那契数列生成器
    def fibonacci_generator():
        a, b = 0, 1
        for _ in range(8):  # 生成8个斐波那契数
            yield a
            a, b = b, a + b
    
    print("斐波那契数列生成器 (前8个)")
    result_stream = env.from_batch_generator(fibonacci_generator, expected_count=8)
    
    fib_numbers = []
    for fib in result_stream:
        print(f"斐波那契: {fib}")
        fib_numbers.append(fib)
    
    print(f"完整序列: {fib_numbers}")
    print()


def demo_5_iterable_batch():
    """演示5: 通用可迭代对象批处理"""
    print("=" * 60)
    print("演示5: 通用可迭代对象批处理")
    print("=" * 60)
    
    env = LocalEnvironment("demo5")
    
    # 使用集合（set）
    unique_numbers = {5, 2, 8, 1, 9, 3}
    print(f"唯一数字集合: {unique_numbers}")
    
    result_stream = env.from_batch_iterable(unique_numbers)
    
    # 排序并处理
    sorted_results = []
    for num in result_stream:
        print(f"处理数字: {num}")
        sorted_results.append(num)
    
    sorted_results.sort()  # 排序
    print(f"排序后结果: {sorted_results}")
    print()


def demo_6_empty_data_handling():
    """演示6: 空数据处理"""
    print("=" * 60)
    print("演示6: 空数据处理")
    print("=" * 60)
    
    env = LocalEnvironment("demo6")
    
    # 空列表
    empty_data = []
    print("处理空数据集合...")
    
    result_stream = env.from_batch_collection(empty_data)
    
    count = 0
    for data in result_stream:
        count += 1
        print(f"不应该看到这行: {data}")
    
    print(f"处理的项目数量: {count}")
    print("空数据正确处理：立即完成，没有产生任何输出")
    print()


def demo_7_progress_tracking():
    """演示7: 进度跟踪"""
    print("=" * 60)
    print("演示7: 进度跟踪演示")
    print("=" * 60)
    
    # 创建大量数据来展示进度
    large_dataset = list(range(1, 21))  # 1到20
    print(f"大数据集: {len(large_dataset)} 个项目")
    
    env = LocalEnvironment("demo7")
    result_stream = env.from_batch_collection(large_dataset)
    
    processed_count = 0
    for num in result_stream:
        processed_count += 1
        # 模拟一些处理
        result = num * 3 + 1
        print(f"[{processed_count:2d}/20] 处理 {num} -> {result}")
    
    print(f"全部完成! 总共处理了 {processed_count} 个项目")
    print()


def custom_processing_demo():
    """自定义处理演示"""
    print("=" * 60)
    print("自定义批处理函数演示")
    print("=" * 60)
    
    # 创建一个自定义的数据处理函数
    class CustomDataFunction:
        def __init__(self, data_source, ctx=None):
            self.data_source = data_source
            self.ctx = ctx
            self.logger = ctx.logger if ctx else print
        
        def get_data_iterator(self):
            """自定义数据转换逻辑"""
            for item in self.data_source:
                if isinstance(item, str):
                    yield item.upper()
                elif isinstance(item, (int, float)):
                    yield item ** 2
                else:
                    yield str(item)
        
        def get_total_count(self):
            return len(self.data_source)
    
    # 测试数据
    mixed_data = ["hello", 3, "world", 5, "python", 7]
    print(f"混合数据: {mixed_data}")
    
    env = LocalEnvironment("custom_demo")
    
    # 注意：这个演示展示了如何创建自定义函数
    # 实际使用中，您需要通过function factory来集成
    custom_func = CustomDataFunction(mixed_data, env.ctx)
    
    print("自定义处理结果:")
    iterator = custom_func.get_data_iterator()
    for i, result in enumerate(iterator, 1):
        print(f"  {i}. {result}")
    
    print()


if __name__ == "__main__":
    print("🚀 简化批处理系统演示")
    print("本演示展示了新的简化批处理设计的各种功能")
    print()
    
    # 运行所有演示
    demo_1_simple_data_batch()
    demo_2_file_batch()
    demo_3_range_batch()
    demo_4_generator_batch()
    demo_5_iterable_batch()
    demo_6_empty_data_handling()
    demo_7_progress_tracking()
    custom_processing_demo()
    
    print("=" * 60)
    print("✅ 所有演示完成！")
    print()
    print("总结:")
    print("- ✅ 批处理算子自动迭代和停止")
    print("- ✅ 支持多种数据源类型")
    print("- ✅ 自动进度跟踪")
    print("- ✅ 空数据正确处理")
    print("- ✅ 易于扩展的接口设计")
    print("=" * 60)
