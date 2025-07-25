"""
BaseEnvironment批处理接口完整使用示例

演示如何在实际的SAGE环境中使用新的批处理接口
"""

import os
import tempfile
from typing import Iterator, Any
from core.function.batch_function import BatchFunction


# 创建一些示例数据文件用于演示
def create_sample_data_files():
    """创建示例数据文件"""
    files = {}
    
    # 1. 创建简单文本文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        for i in range(100):
            f.write(f"line_{i:03d}: This is sample data line {i}\n")
        files['simple_text'] = f.name
    
    # 2. 创建CSV文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("id,name,value,category\n")
        for i in range(50):
            f.write(f"{i},item_{i},{i*10.5},category_{i%5}\n")
        files['csv_data'] = f.name
    
    # 3. 创建JSON Lines文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
        import json
        for i in range(30):
            data = {
                "id": i,
                "timestamp": f"2024-01-{i+1:02d}T00:00:00",
                "value": i * 3.14,
                "tags": [f"tag_{j}" for j in range(i % 3 + 1)]
            }
            f.write(json.dumps(data) + "\n")
        files['jsonl_data'] = f.name
    
    return files


def cleanup_files(files):
    """清理临时文件"""
    for file_path in files.values():
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            pass


# 自定义批处理函数示例
class CSVBatchFunction(BatchFunction):
    """CSV文件批处理函数"""
    
    def __init__(self, file_path: str, skip_header: bool = True, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.file_path = file_path
        self.skip_header = skip_header
        self._total_count = None
    
    def get_total_count(self) -> int:
        if self._total_count is None:
            with open(self.file_path, 'r') as f:
                self._total_count = sum(1 for _ in f)
                if self.skip_header:
                    self._total_count -= 1
        return self._total_count
    
    def get_data_source(self) -> Iterator[Any]:
        with open(self.file_path, 'r') as f:
            if self.skip_header:
                next(f)  # 跳过header
            for line in f:
                yield line.strip().split(',')


class JSONLBatchFunction(BatchFunction):
    """JSON Lines文件批处理函数"""
    
    def __init__(self, file_path: str, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.file_path = file_path
        self._total_count = None
    
    def get_total_count(self) -> int:
        if self._total_count is None:
            with open(self.file_path, 'r') as f:
                self._total_count = sum(1 for _ in f)
        return self._total_count
    
    def get_data_source(self) -> Iterator[Any]:
        import json
        with open(self.file_path, 'r') as f:
            for line in f:
                yield json.loads(line.strip())


class FibonacciPrimeBatchFunction(BatchFunction):
    """斐波那契素数批处理函数"""
    
    def __init__(self, count: int, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.count = count
    
    def get_total_count(self) -> int:
        return self.count
    
    def get_data_source(self) -> Iterator[Any]:
        def is_prime(n):
            if n < 2: return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0: return False
            return True
        
        a, b = 0, 1
        found = 0
        while found < self.count:
            if is_prime(a):
                yield {"fibonacci": a, "index": found, "is_prime": True}
                found += 1
            a, b = b, a + b


# 模拟环境类（在实际使用中，会是真实的StreamingEnvironment或LocalEnvironment）
class MockSageEnvironment:
    """模拟SAGE环境"""
    
    def __init__(self, name: str):
        self.name = name
        self.platform = "local"
        self.memory_collection = None
        self.pipeline = []
        self.logger = self._create_logger()
        
        # 导入批处理方法
        from core.environment.base_environment import BaseEnvironment
        self._bind_batch_methods(BaseEnvironment)
    
    def _create_logger(self):
        class MockLogger:
            def info(self, msg): print(f"[INFO] {msg}")
            def debug(self, msg): print(f"[DEBUG] {msg}")
            def warning(self, msg): print(f"[WARNING] {msg}")
            def error(self, msg): print(f"[ERROR] {msg}")
        return MockLogger()
    
    def _bind_batch_methods(self, base_class):
        """绑定批处理方法"""
        self.from_batch_collection = base_class.from_batch_collection.__get__(self)
        self.from_batch_file = base_class.from_batch_file.__get__(self)
        self.from_batch_range = base_class.from_batch_range.__get__(self)
        self.from_batch_generator = base_class.from_batch_generator.__get__(self)
        self.from_batch_custom = base_class.from_batch_custom.__get__(self)


def demonstrate_comprehensive_usage():
    """演示综合使用场景"""
    
    print("=" * 80)
    print("SAGE 批处理接口综合使用示例")
    print("=" * 80)
    
    # 创建示例数据文件
    print("\n1. 准备示例数据...")
    files = create_sample_data_files()
    print(f"   ✓ 创建了 {len(files)} 个示例数据文件")
    
    try:
        # 创建环境
        env = MockSageEnvironment("batch_demo_env")
        print(f"\n2. 创建环境: {env.name}")
        
        # 场景1: 处理简单数据集合
        print("\n" + "-" * 60)
        print("场景1: 处理内存中的数据集合")
        print("-" * 60)
        
        # 模拟用户数据
        user_data = [
            {"id": i, "name": f"user_{i}", "score": i * 2.5}
            for i in range(20)
        ]
        
        batch_stream1 = env.from_batch_collection(
            user_data,
            progress_log_interval=5
        )
        print(f"   ✓ 创建集合批处理源，数据量: {len(user_data)}")
        
        # 场景2: 处理文本文件
        print("\n" + "-" * 60)
        print("场景2: 处理文本文件 - 自动行数统计")
        print("-" * 60)
        
        batch_stream2 = env.from_batch_file(
            files['simple_text'],
            progress_log_interval=20
        )
        print(f"   ✓ 创建文件批处理源: {os.path.basename(files['simple_text'])}")
        
        # 场景3: 数值计算任务
        print("\n" + "-" * 60)
        print("场景3: 大规模数值计算")
        print("-" * 60)
        
        batch_stream3 = env.from_batch_range(
            1, 10001,  # 1万个数字
            progress_log_interval=1000
        )
        print("   ✓ 创建数字范围批处理源: 1-10000")
        
        # 场景4: 使用生成器处理复杂数据
        print("\n" + "-" * 60)
        print("场景4: 动态数据生成")
        print("-" * 60)
        
        def generate_sensor_data():
            """模拟传感器数据生成"""
            import random
            import time
            
            for i in range(100):
                yield {
                    "sensor_id": f"sensor_{i % 10}",
                    "timestamp": time.time() + i,
                    "temperature": 20 + random.normal(0, 5),
                    "humidity": 50 + random.normal(0, 10),
                    "reading_id": i
                }
        
        batch_stream4 = env.from_batch_generator(
            generate_sensor_data,
            100,
            progress_log_interval=25
        )
        print("   ✓ 创建传感器数据生成器批处理源")
        
        # 场景5: 自定义CSV处理
        print("\n" + "-" * 60)
        print("场景5: 自定义CSV数据处理")
        print("-" * 60)
        
        batch_stream5 = env.from_batch_custom(
            CSVBatchFunction,
            files['csv_data'],
            skip_header=True,
            progress_log_interval=10
        )
        print("   ✓ 创建自定义CSV批处理源")
        
        # 场景6: JSON Lines处理
        print("\n" + "-" * 60)
        print("场景6: JSON Lines数据处理")
        print("-" * 60)
        
        batch_stream6 = env.from_batch_custom(
            JSONLBatchFunction,
            files['jsonl_data'],
            progress_log_interval=5
        )
        print("   ✓ 创建JSON Lines批处理源")
        
        # 场景7: 数学计算任务
        print("\n" + "-" * 60)
        print("场景7: 斐波那契素数生成")
        print("-" * 60)
        
        batch_stream7 = env.from_batch_custom(
            FibonacciPrimeBatchFunction,
            count=10,  # 前10个斐波那契素数
            progress_log_interval=2
        )
        print("   ✓ 创建斐波那契素数批处理源")
        
        # 总结创建的批处理源
        print(f"\n" + "=" * 80)
        print(f"总计创建了 {len(env.pipeline)} 个批处理数据源")
        print("=" * 80)
        
        # 显示推荐的使用模式
        print("\n推荐的实际使用模式:")
        show_usage_patterns()
        
    finally:
        # 清理临时文件
        cleanup_files(files)
        print(f"\n✓ 清理了 {len(files)} 个临时文件")


def show_usage_patterns():
    """显示推荐的使用模式"""
    
    patterns = [
        {
            "场景": "小规模测试数据",
            "推荐接口": "from_batch_collection",
            "示例": "env.from_batch_collection([1, 2, 3, 4, 5])"
        },
        {
            "场景": "文件批处理",
            "推荐接口": "from_batch_file",
            "示例": "env.from_batch_file('/path/to/data.txt')"
        },
        {
            "场景": "数值计算",
            "推荐接口": "from_batch_range", 
            "示例": "env.from_batch_range(1, 1000000)"
        },
        {
            "场景": "动态数据生成",
            "推荐接口": "from_batch_generator",
            "示例": "env.from_batch_generator(data_gen_func, expected_count)"
        },
        {
            "场景": "复杂数据处理",
            "推荐接口": "from_batch_custom",
            "示例": "env.from_batch_custom(CustomBatchFunction, ...)"
        }
    ]
    
    print("\n   接口选择指南:")
    print("   " + "-" * 60)
    for pattern in patterns:
        print(f"   • {pattern['场景']}: {pattern['推荐接口']}")
        print(f"     {pattern['示例']}")
        print()


def show_pipeline_integration_examples():
    """展示与处理管道的集成示例"""
    
    print("\n" + "=" * 80)
    print("批处理与处理管道集成示例")
    print("=" * 80)
    
    examples = [
        {
            "title": "文件处理管道",
            "code": """
# 处理日志文件并统计
log_stream = env.from_batch_file("/var/log/app.log")
result = (log_stream
          .filter(lambda line: "ERROR" in line)
          .map(parse_log_line)
          .key_by(lambda log: log.timestamp.hour)
          .reduce(lambda count, _: count + 1)
          .sink(print_results))
"""
        },
        {
            "title": "数值计算管道", 
            "code": """
# 计算大数据集的统计信息
numbers = env.from_batch_range(1, 1000001)
stats = (numbers
         .map(lambda x: x * x)  # 计算平方
         .filter(lambda x: x % 2 == 0)  # 筛选偶数
         .reduce(lambda sum, x: sum + x)  # 求和
         .sink(output_sink))
"""
        },
        {
            "title": "数据转换管道",
            "code": """
# 批处理ETL任务
raw_data = env.from_batch_custom(DatabaseBatchFunction, "SELECT * FROM raw_table")
processed = (raw_data
            .map(clean_data)
            .filter(validate_data) 
            .map(transform_data)
            .sink(target_database_sink))
"""
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}:")
        print("-" * len(example['title']) + "-")
        print(example['code'])


if __name__ == "__main__":
    demonstrate_comprehensive_usage()
    show_pipeline_integration_examples()
    
    print("\n" + "=" * 80)
    print("总结:")
    print("• 新的批处理接口提供了统一、简洁的API")
    print("• 引擎自动处理批次大小计算和进度跟踪")  
    print("• 支持多种数据源类型，覆盖常见使用场景")
    print("• 与现有处理管道完全兼容")
    print("• 大大减少了用户需要编写的样板代码")
    print("=" * 80)
