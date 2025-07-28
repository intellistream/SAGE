"""
批处理算子和函数使用示例

这个文件展示了如何使用新的BatchOperator和BatchFunction来创建
用户友好的批处理任务。
"""

from typing import List, Any, Iterator
from sage.core.function.batch_function import BatchFunction, SimpleBatchFunction, FileBatchFunction
from sage.core.operator.batch_operator import BatchOperator, BatchSourceOperator


class NumberRangeBatchFunction(BatchFunction):
    """
    数字范围批处理函数示例
    
    生成指定范围内的数字序列
    """
    
    def __init__(self, start: int, end: int, step: int = 1, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.start = start
        self.end = end
        self.step = step
    
    def get_total_count(self) -> int:
        return max(0, (self.end - self.start + self.step - 1) // self.step)
    
    def get_data_source(self) -> Iterator[Any]:
        return iter(range(self.start, self.end, self.step))


class CustomDataBatchFunction(BatchFunction):
    """
    自定义数据批处理函数示例
    
    处理用户提供的自定义数据生成逻辑
    """
    
    def __init__(self, data_generator_func, total_count: int, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.data_generator_func = data_generator_func
        self.total_count = total_count
    
    def get_total_count(self) -> int:
        return self.total_count
    
    def get_data_source(self) -> Iterator[Any]:
        return self.data_generator_func()


def create_sample_batch_tasks():
    """
    创建示例批处理任务的工厂函数
    """
    
    # 示例1: 简单数据列表批处理
    def create_simple_list_batch():
        data = [f"item_{i}" for i in range(100)]
        return SimpleBatchFunction(data)
    
    # 示例2: 数字范围批处理
    def create_number_range_batch():
        return NumberRangeBatchFunction(start=1, end=1001, step=1)
    
    # 示例3: 文件批处理
    def create_file_batch(file_path: str):
        return FileBatchFunction(file_path)
    
    # 示例4: 自定义数据生成批处理
    def create_custom_batch():
        def fibonacci_generator():
            a, b = 0, 1
            for _ in range(50):  # 生成前50个斐波那契数
                yield a
                a, b = b, a + b
        
        return CustomDataBatchFunction(fibonacci_generator, 50)
    
    return {
        "simple_list": create_simple_list_batch,
        "number_range": create_number_range_batch, 
        "file_batch": create_file_batch,
        "custom_fibonacci": create_custom_batch
    }


class BatchTaskExample:
    """
    批处理任务使用示例类
    """
    
    @staticmethod
    def example_usage():
        """
        批处理使用示例
        """
        # 创建一个简单的模拟context
        class MockContext:
            def __init__(self, name):
                self.name = name
                self.logger = MockLogger()
        
        class MockLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
        
        print("=== 批处理算子使用示例 ===")
        
        # 1. 创建简单列表批处理
        print("\n1. 简单列表批处理:")
        data = ["apple", "banana", "cherry", "date", "elderberry"]
        ctx = MockContext("simple_batch_example")
        simple_batch = SimpleBatchFunction(data, ctx)
        
        print(f"总记录数: {simple_batch.get_total_count()}")
        
        # 模拟处理过程
        for i in range(7):  # 多处理几次以展示完成状态
            result = simple_batch.execute()
            current, total = simple_batch.get_progress()
            completion = simple_batch.get_completion_rate()
            
            print(f"第{i+1}次执行: 结果={result}, 进度={current}/{total} ({completion:.1%}), 完成={simple_batch.is_finished()}")
            
            if simple_batch.is_finished():
                break
        
        # 2. 数字范围批处理
        print("\n2. 数字范围批处理:")
        ctx2 = MockContext("number_batch_example")
        number_batch = NumberRangeBatchFunction(1, 6, 1, ctx2)
        print(f"总记录数: {number_batch.get_total_count()}")
        
        while not number_batch.is_finished():
            result = number_batch.execute()
            current, total = number_batch.get_progress()
            completion = number_batch.get_completion_rate()
            
            print(f"处理结果: {result}, 进度: {current}/{total} ({completion:.1%})")
        
        print("\n=== 示例完成 ===")


if __name__ == "__main__":
    # 运行示例
    BatchTaskExample.example_usage()
