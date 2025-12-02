"""
benchmark_anns 测试套件

本目录包含 benchmark_anns 项目的所有测试文件。

测试文件列表：
- test_streaming.py: 流式基准测试功能测试
- test_datasets.py: 数据集实现测试
- test_congestion.py: 拥塞丢弃功能测试
- test_algorithm_structure.py: 算法目录结构验证
- test_run_benchmark.py: run_benchmark.py 完整流程测试
- test_runbook_format.py: runbook 格式解析测试
- test_runner_integration.py: BenchmarkRunner 集成测试
- test_verify_project.sh: 项目结构验证脚本
- test_compute_gt.sh: 真值计算测试脚本
- test_faiss_sift.sh: FAISS HNSW 算法测试脚本

运行测试的方式：

方式 1 (推荐): 从项目根目录运行
    cd benchmark_anns
    python tests/test_streaming.py
    python tests/test_datasets.py
    python tests/test_congestion.py
    python tests/test_algorithm_structure.py

方式 2: 运行 Shell 脚本
    cd benchmark_anns
    bash tests/test_verify_project.sh
    bash tests/test_compute_gt.sh
    bash tests/test_faiss_sift.sh

方式 3: 使用 pytest (如果安装)
    cd benchmark_anns
    pytest tests/

注意：
- 所有测试文件都使用相对路径，不依赖外部目录
- benchmark_anns 是一个独立项目，所有导入都是相对于项目根目录的
"""

__all__ = [
    "test_streaming",
    "test_datasets",
    "test_congestion",
    "test_algorithm_structure",
    "test_run_benchmark",
    "test_runbook_format",
    "test_runner_integration",
]
