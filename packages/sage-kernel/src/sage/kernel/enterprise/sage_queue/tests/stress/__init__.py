"""
SAGE Queue 压力测试模块

包含多进程、多线程、内存压力等各种极限场景的测试
"""

# 压力测试配置
STRESS_TEST_CONFIGS = {
    "light_stress": {
        "num_processes": 4,
        "num_queues": 2,
        "messages_per_process": 100,
        "message_size": 512,
        "test_duration": 10
    },
    "medium_stress": {
        "num_processes": 8,
        "num_queues": 4,
        "messages_per_process": 500,
        "message_size": 1024,
        "test_duration": 30
    },
    "heavy_stress": {
        "num_processes": 16,
        "num_queues": 8,
        "messages_per_process": 1000,
        "message_size": 2048,
        "test_duration": 60
    },
    "extreme_stress": {
        "num_processes": 32,
        "num_queues": 16,
        "messages_per_process": 2000,
        "message_size": 4096,
        "test_duration": 120
    }
}

# 内存压力测试阈值
MEMORY_THRESHOLDS = {
    "light": 50,    # MB
    "medium": 100,  # MB
    "heavy": 200,   # MB
    "extreme": 500  # MB
}

# 性能基准
PERFORMANCE_BENCHMARKS_STRESS = {
    "min_throughput_under_stress": 1000,  # messages/sec under stress
    "max_memory_growth_per_hour": 10,     # MB/hour
    "max_error_rate": 0.05,               # 5% error rate
    "min_success_rate": 0.95              # 95% success rate
}
