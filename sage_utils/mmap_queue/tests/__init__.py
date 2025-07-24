"""
SAGE Memory-Mapped Queue 测试套件
Test suite for SAGE high-performance memory-mapped queue

该测试套件包含了全面的功能测试、性能测试、安全测试和集成测试

使用方法:
1. 快速开始: python run_all_tests.py
2. 单个测试: python test_quick_validation.py
3. 生成报告: python generate_test_report.py

测试模块:
- test_quick_validation: 快速验证测试
- test_basic_functionality: 基本功能测试  
- test_safety: 安全测试套件
- test_performance_benchmark: 性能基准测试
- test_comprehensive: 综合测试套件
- test_multiprocess_concurrent: 多进程并发测试
- test_ray_integration: Ray Actor集成测试
"""

__version__ = "1.0.0"
__author__ = "SAGE Project"

# 测试模块列表（按推荐运行顺序）
TEST_MODULES = [
    {
        "module": "test_quick_validation",
        "description": "快速验证测试", 
        "required": True,
        "estimated_time": 5
    },
    {
        "module": "test_basic_functionality",
        "description": "基本功能测试",
        "required": True,
        "estimated_time": 30
    },
    {
        "module": "test_safety", 
        "description": "安全测试套件",
        "required": True,
        "estimated_time": 45
    },
    {
        "module": "test_performance_benchmark",
        "description": "性能基准测试",
        "required": False,
        "estimated_time": 60
    },
    {
        "module": "test_comprehensive",
        "description": "综合测试套件", 
        "required": False,
        "estimated_time": 90
    },
    {
        "module": "test_multiprocess_concurrent",
        "description": "多进程并发测试",
        "required": False,
        "estimated_time": 60
    },
    {
        "module": "test_ray_integration",
        "description": "Ray Actor集成测试",
        "required": False,
        "estimated_time": 45,
        "dependencies": ["ray"]
    }
]

# 测试配置
TEST_CONFIG = {
    "default_queue_size": 64 * 1024,  # 64KB
    "test_timeout": 30.0,  # 30 seconds
    "multiprocess_method": "spawn",
    "cleanup_on_exit": True,
    "max_concurrent_processes": 8,
    "memory_limit_mb": 512,
    "temp_queue_prefix": "sage_test_"
}

# 性能基准参考值
PERFORMANCE_BENCHMARKS = {
    "min_throughput_msg_per_sec": 50000,  # 最低吞吐量要求
    "max_latency_ms": 1.0,                # 最大延迟要求
    "min_memory_efficiency": 0.8,         # 最低内存效率要求
    "max_memory_usage_mb": 100             # 最大内存使用量
}

def get_test_info(module_name: str):
    """获取测试模块信息"""
    for test in TEST_MODULES:
        if test["module"] == module_name:
            return test
    return None

def get_required_tests():
    """获取必需测试列表"""
    return [test for test in TEST_MODULES if test["required"]]

def get_optional_tests():
    """获取可选测试列表"""
    return [test for test in TEST_MODULES if not test["required"]]

def estimate_total_time():
    """估算总测试时间"""
    return sum(test["estimated_time"] for test in TEST_MODULES)
