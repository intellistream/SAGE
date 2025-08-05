"""
Core Service模块测试包

该包包含了sage.core.service模块的所有测试用例，按照测试组织架构规范设计。

测试文件映射:
- test_base_service.py     -> sage.core.service.base_service
"""

# 测试配置
SERVICE_TEST_CONFIG = {
    "timeout": 30,  # 测试超时时间（秒）
    "retry_count": 3,  # 失败重试次数
    "parallel_safe": True,  # 是否支持并行测试
}

# 测试覆盖的功能点
COVERED_MODULES = [
    "base_service"
]

# 待扩展的测试模块（如果有其他服务模块的话）
PENDING_MODULES = []
