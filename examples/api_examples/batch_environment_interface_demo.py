"""
BaseEnvironment批处理接口使用示例

展示如何使用新的batch相关环境接口来创建批处理数据源
"""

import sys
import os
from typing import Iterator, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage.core.function.batch_function import BatchFunction


# 模拟环境类用于演示
class MockEnvironment:
    """模拟环境类，用于演示批处理接口"""
    
    def __init__(self, name: str):
        self.name = name
        self.pipeline = []
        self.logger = MockLogger()

    def from_batch_collection(self, data: list, **kwargs):
        """模拟批处理集合接口"""
        print(f"创建批处理集合数据源: {len(data)} 条记录")
        return MockDataStream("batch_collection", data)

    def from_batch_file(self, file_path: str, encoding: str = 'utf-8', **kwargs):
        """模拟批处理文件接口"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                line_count = sum(1 for _ in f)
            print(f"创建批处理文件数据源: {file_path} ({line_count} 行)")
            return MockDataStream("batch_file", file_path)
        except FileNotFoundError:
            print(f"文件未找到，创建模拟数据源: {file_path}")
            return MockDataStream("batch_file", file_path)

    def from_batch_range(self, start: int, end: int, step: int = 1, **kwargs):
        """模拟批处理范围接口"""
        total_count = max(0, (end - start + step - 1) // step)
        print(f"创建批处理范围数据源: {start}-{end} (step={step}, total={total_count})")
        return MockDataStream("batch_range", f"{start}-{end}")

    def from_batch_generator(self, generator_func: callable, total_count: int, **kwargs):
        """模拟批处理生成器接口"""
        print(f"创建批处理生成器数据源: 预期 {total_count} 条记录")
        return MockDataStream("batch_generator", generator_func)

    def from_batch_custom(self, batch_function_class, *args, **kwargs):
        """模拟自定义批处理接口"""
        print(f"创建自定义批处理数据源: {batch_function_class.__name__}")
        return MockDataStream("batch_custom", batch_function_class.__name__)


class MockLogger:
    """模拟日志记录器"""
    def info(self, msg): print(f"INFO: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")


class MockDataStream:
    """模拟数据流"""
    def __init__(self, source_type, data):
        self.source_type = source_type
        self.data = data
    
    def __repr__(self):
        return f"DataStream[{self.source_type}]({self.data})"


# 自定义批处理函数示例
class WordsBatchFunction(BatchFunction):
    """单词批处理函数示例"""
    
    def __init__(self, words: list, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.words = words
    
    def get_total_count(self) -> int:
        return len(self.words)
    
    def get_data_source(self) -> Iterator[Any]:
        return iter(self.words)


class FibonacciBatchFunction(BatchFunction):
    """斐波那契数列批处理函数示例"""
    
    def __init__(self, count: int, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.count = count
    
    def get_total_count(self) -> int:
        return self.count
    
    def get_data_source(self) -> Iterator[Any]:
        a, b = 0, 1
        for _ in range(self.count):
            yield a
            a, b = b, a + b


def demonstrate_batch_interfaces():
    """演示所有批处理接口的使用"""
    
    print("=" * 60)
    print("BaseEnvironment 批处理接口使用示例")
    print("=" * 60)
    
    # 创建模拟环境
    env = MockEnvironment("demo_env")
    
    # 1. 批处理集合
    print("\n1. from_batch_collection - 从数据集合创建批处理")
    print("-" * 50)
    
    data = ["apple", "banana", "cherry", "date", "elderberry"]
    batch_stream1 = env.from_batch_collection(data)
    print(f"创建的数据流: {batch_stream1}")
    
    # 带配置参数
    batch_stream1_config = env.from_batch_collection(
        data, 
        progress_log_interval=2
    )
    print(f"带配置的数据流: {batch_stream1_config}")
    
    # 2. 批处理文件
    print("\n2. from_batch_file - 从文件创建批处理")
    print("-" * 50)
    
    # 由于演示目的，使用不存在的文件路径
    batch_stream2 = env.from_batch_file("/path/to/data.txt")
    print(f"创建的数据流: {batch_stream2}")
    
    # 指定编码
    batch_stream2_encoding = env.from_batch_file(
        "/path/to/chinese_data.txt",
        encoding="gb2312",
        progress_log_interval=1000
    )
    print(f"带编码配置的数据流: {batch_stream2_encoding}")
    
    # 3. 批处理范围
    print("\n3. from_batch_range - 从数字范围创建批处理")
    print("-" * 50)
    
    batch_stream3 = env.from_batch_range(1, 101)  # 1到100
    print(f"创建的数据流: {batch_stream3}")
    
    # 带步长
    batch_stream3_step = env.from_batch_range(0, 100, step=2)  # 偶数
    print(f"偶数序列数据流: {batch_stream3_step}")
    
    # 4. 批处理生成器
    print("\n4. from_batch_generator - 从生成器创建批处理")
    print("-" * 50)
    
    def fibonacci_generator():
        """斐波那契生成器"""
        a, b = 0, 1
        for _ in range(20):
            yield a
            a, b = b, a + b
    
    batch_stream4 = env.from_batch_generator(fibonacci_generator, 20)
    print(f"创建的数据流: {batch_stream4}")
    
    def square_generator():
        """平方数生成器"""
        for i in range(10):
            yield i * i
    
    batch_stream4_squares = env.from_batch_generator(square_generator, 10)
    print(f"平方数数据流: {batch_stream4_squares}")
    
    # 5. 自定义批处理
    print("\n5. from_batch_custom - 从自定义函数创建批处理")
    print("-" * 50)
    
    batch_stream5 = env.from_batch_custom(WordsBatchFunction, ["hello", "world", "test"])
    print(f"创建的数据流: {batch_stream5}")
    
    batch_stream5_fib = env.from_batch_custom(FibonacciBatchFunction, count=15)
    print(f"斐波那契数据流: {batch_stream5_fib}")
    
    # 6. 对比传统方式
    print("\n6. 与传统from_source方式的对比")
    print("-" * 50)
    
    print("传统方式:")
    print("  - 需要手动管理停止逻辑")
    print("  - 无法预知总数量")
    print("  - 无进度跟踪")
    print("  - 用户需要处理StopSignal")
    
    print("\n批处理方式:")
    print("  - 自动管理停止逻辑")
    print("  - 引擎自动判断批次大小")
    print("  - 内置进度跟踪")
    print("  - 用户只需声明数据源")
    
    # 7. 实际使用建议
    print("\n7. 实际使用建议")
    print("-" * 50)
    
    print("选择合适的批处理接口:")
    print("  - 小量数据或测试: from_batch_collection")
    print("  - 文件处理: from_batch_file") 
    print("  - 数值计算: from_batch_range")
    print("  - 复杂数据生成: from_batch_generator")
    print("  - 高度自定义: from_batch_custom")
    
    print("\n配置参数:")
    print("  - progress_log_interval: 控制进度日志频率")
    print("  - delay: 控制处理延迟(默认0.1秒)")
    print("  - encoding: 文件编码(默认utf-8)")


def show_code_examples():
    """展示代码使用示例"""
    
    print("\n" + "=" * 60)
    print("代码使用示例")
    print("=" * 60)
    
    code_examples = [
        {
            "title": "简单数据处理",
            "code": """
# 处理简单数据列表
data = ["item1", "item2", "item3", "item4", "item5"]
batch_stream = env.from_batch_collection(data)

# 可以直接用于pipeline
result = (batch_stream
          .map(ProcessFunction)
          .filter(FilterFunction)
          .sink(OutputFunction))
"""
        },
        {
            "title": "文件批处理",
            "code": """
# 处理大文件 - 引擎自动统计行数
batch_stream = env.from_batch_file("/path/to/large_file.txt")

# 指定编码和进度间隔
batch_stream = env.from_batch_file(
    "/path/to/chinese_file.txt",
    encoding="gb2312",
    progress_log_interval=1000
)
"""
        },
        {
            "title": "数值计算",
            "code": """
# 生成数字序列进行计算
numbers = env.from_batch_range(1, 1000001)  # 100万个数字

# 计算平方和
result = (numbers
          .map(lambda x: x * x)
          .reduce(lambda a, b: a + b)
          .sink(PrintSink))
"""
        },
        {
            "title": "自定义数据生成",
            "code": """
# 使用生成器函数
def generate_random_data():
    import random
    for _ in range(10000):
        yield {
            'id': random.randint(1, 1000),
            'value': random.random(),
            'timestamp': time.time()
        }

batch_stream = env.from_batch_generator(generate_random_data, 10000)
"""
        },
        {
            "title": "高度自定义批处理",
            "code": """
class DatabaseBatchFunction(BatchFunction):
    def __init__(self, query: str, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.query = query
    
    def get_total_count(self) -> int:
        # 执行COUNT查询获取总数
        return db.execute(f"SELECT COUNT(*) FROM ({self.query})").fetchone()[0]
    
    def get_data_source(self) -> Iterator[Any]:
        # 返回查询结果迭代器
        return db.execute(self.query)

# 使用自定义批处理
batch_stream = env.from_batch_custom(
    DatabaseBatchFunction, 
    query="SELECT * FROM users WHERE active = 1"
)
"""
        }
    ]
    
    for example in code_examples:
        print(f"\n{example['title']}:")
        print("-" * len(example['title']) + "-")
        print(example['code'])


if __name__ == "__main__":
    demonstrate_batch_interfaces()
    show_code_examples()
    
    print("\n" + "=" * 60)
    print("总结:")
    print("- 新的批处理接口大大简化了批处理任务的创建")
    print("- 引擎自动判断批次大小，用户无需手动管理")
    print("- 支持多种数据源类型，满足不同场景需求")
    print("- 内置进度跟踪和错误处理，提升用户体验")
    print("=" * 60)
