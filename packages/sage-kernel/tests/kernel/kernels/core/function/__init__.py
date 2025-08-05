"""
Core Function模块测试包

该包包含了sage.core.function模块的所有测试用例，按照测试组织架构规范设计。

测试文件映射:
- test_base_function.py     -> sage.core.function.base_function
- test_comap_function.py    -> sage.core.function.comap_function  
- test_sink_function.py     -> sage.core.function.sink_function
- test_source_function.py   -> sage.core.function.source_function
"""

# 测试配置
FUNCTION_TEST_CONFIG = {
    "timeout": 30,  # 测试超时时间（秒）
    "retry_count": 3,  # 失败重试次数
    "parallel_safe": True,  # 是否支持并行测试
}

# 测试覆盖的功能点
COVERED_MODULES = [
    "base_function",
    "comap_function", 
    "sink_function",
    "source_function"
]

# 待扩展的测试模块
PENDING_MODULES = [
    "batch_function",
    "filter_function",
    "flatmap_function",
    "future_function",
    "join_function",
    "kafka_source",
    "keyby_function", 
    "lambda_function",
    "map_function",
    "simple_batch_function"
]
