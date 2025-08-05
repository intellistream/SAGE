"""
Core Operator模块测试包

该包包含了sage.core.operator模块的所有测试用例，按照测试组织架构规范设计。

测试文件映射:
- test_base_operator.py     -> sage.core.operator.base_operator
"""

# 测试配置
OPERATOR_TEST_CONFIG = {
    "timeout": 30,  # 测试超时时间（秒）
    "retry_count": 3,  # 失败重试次数
    "parallel_safe": True,  # 是否支持并行测试
}

# 测试覆盖的功能点
COVERED_MODULES = [
    "base_operator"
]

# 待扩展的测试模块
PENDING_MODULES = [
    "batch_operator",
    "comap_operator",
    "filter_operator",
    "flatmap_operator",
    "future_operator",
    "join_operator",
    "keyby_operator",
    "map_operator",
    "sink_operator",
    "source_operator"
]
