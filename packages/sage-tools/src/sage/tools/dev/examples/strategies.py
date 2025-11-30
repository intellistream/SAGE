"""
Test Strategies for Examples

This module defines testing strategies for different categories of examples,
including timeout settings, environment variables, and success/failure patterns.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class TestStrategy:
    """测试策略配置"""

    name: str
    timeout: int
    requires_config: bool
    requires_data: bool
    mock_inputs: dict[str, str] | None = None
    environment_vars: dict[str, str] | None = None
    success_patterns: list[str] | None = None
    failure_patterns: list[str] | None = None
    pre_run_setup: Callable | None = None
    post_run_cleanup: Callable | None = None


class ExampleTestStrategies:
    """示例测试策略集合"""

    @staticmethod
    def get_strategies() -> dict[str, TestStrategy]:
        """获取所有测试策略

        Returns:
            字典，键为类别名称，值为对应的测试策略
        """
        return {
            "tutorials": TestStrategy(
                name="tutorials",
                timeout=30,
                requires_config=False,
                requires_data=False,
                success_patterns=[
                    "Hello, World!",
                    "Pipeline completed",
                    "Execution finished",
                    "✓",
                ],
                failure_patterns=["Error:", "Exception:", "Traceback", "Failed to"],
                environment_vars={
                    "SAGE_LOG_LEVEL": "WARNING",
                    "SAGE_EXAMPLES_MODE": "test",
                },
            ),
            "rag": TestStrategy(
                name="rag",
                timeout=120,
                requires_config=True,
                requires_data=True,
                mock_inputs={
                    "user_question": "What is artificial intelligence?",
                    "test_query": "Tell me about machine learning",
                },
                success_patterns=[
                    "Answer:",
                    "Response:",
                    "Retrieved",
                    "Generated answer",
                    "RAG pipeline completed",
                ],
                failure_patterns=[
                    "API key not found",
                    "Connection failed",
                    "Model not found",
                    "Index not found",
                ],
                environment_vars={
                    "OPENAI_API_KEY": "test-key-placeholder",  # pragma: allowlist secret
                    "SAGE_RAG_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                    "SAGE_TEST_MODE": "true",
                },
            ),
            "memory": TestStrategy(
                name="memory",
                timeout=120,  # 增加到120秒，Pipeline-as-Service示例需要更多时间
                requires_config=False,
                requires_data=True,
                success_patterns=[
                    "Memory initialized",
                    "Data stored",
                    "Retrieved from memory",
                    "Memory service started",
                ],
                failure_patterns=[
                    "Memory service failed",
                    "Storage error",
                    "Connection refused",
                ],
                environment_vars={
                    "SAGE_MEMORY_MODE": "test",
                    "SAGE_LOG_LEVEL": "WARNING",
                },
            ),
            "agents": TestStrategy(
                name="agents",
                timeout=120,
                requires_config=True,
                requires_data=False,
                success_patterns=[
                    "Agent initialized",
                    "Task completed",
                    "Agent response",
                    "Processing finished",
                ],
                failure_patterns=[
                    "Agent failed",
                    "API key missing",
                    "Connection failed",
                    "Model not available",
                ],
                environment_vars={
                    "SAGE_AGENT_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                    "OPENAI_API_KEY": "test-key-placeholder",  # pragma: allowlist secret
                },
            ),
            "service": TestStrategy(
                name="service",
                timeout=90,
                requires_config=True,
                requires_data=False,
                success_patterns=[
                    "Service started",
                    "Server running",
                    "API endpoint active",
                    "Health check passed",
                ],
                failure_patterns=[
                    "Port already in use",
                    "Service failed to start",
                    "Connection refused",
                ],
                environment_vars={
                    "SAGE_SERVICE_MODE": "test",
                    "SAGE_PORT": "0",  # 随机端口
                    "SAGE_LOG_LEVEL": "ERROR",
                },
            ),
            "video": TestStrategy(
                name="video",
                timeout=180,
                requires_config=True,
                requires_data=True,
                success_patterns=[
                    "Video processed",
                    "Frames extracted",
                    "Analysis completed",
                ],
                failure_patterns=[
                    "Video file not found",
                    "Codec not supported",
                    "Processing failed",
                ],
                environment_vars={"SAGE_VIDEO_MODE": "test", "SAGE_LOG_LEVEL": "ERROR"},
            ),
            "batch": TestStrategy(
                name="batch",
                timeout=180,
                requires_config=False,
                requires_data=False,
                success_patterns=[
                    "batch test completed",
                    "Batch Processing Tests Summary",
                    "✅",
                    "Processing completed",
                ],
                failure_patterns=[
                    "Failed to start",
                    "Connection refused",
                    "Timeout",
                    "Error:",
                    "Exception:",
                ],
                environment_vars={
                    "SAGE_BATCH_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                },
            ),
            "streaming": TestStrategy(
                name="streaming",
                timeout=300,  # 增加到5分钟，因为streaming示例可能运行多个环境
                requires_config=False,
                requires_data=False,
                success_patterns=[
                    "Stream completed",
                    "Processing finished",
                    "✅",
                    "Test completed",
                ],
                failure_patterns=[
                    "Stream failed",
                    "Connection error",
                    "Timeout",
                ],
                environment_vars={
                    "SAGE_STREAM_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                },
            ),
            "medical_diagnosis": TestStrategy(
                name="medical_diagnosis",
                timeout=300,  # 5分钟，医学影像分析需要加载模型
                requires_config=False,
                requires_data=True,
                success_patterns=[
                    "诊断完成",
                    "Diagnosis completed",
                    "报告生成完成",
                    "Report generated",
                    "✅",
                ],
                failure_patterns=[
                    "模型加载失败",
                    "Model loading failed",
                    "数据不存在",
                    "Data not found",
                ],
                environment_vars={
                    "SAGE_MEDICAL_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                },
            ),
            "multimodal": TestStrategy(
                name="multimodal",
                timeout=180,  # 3分钟，多模态处理需要时间
                requires_config=True,
                requires_data=True,
                success_patterns=[
                    "Processing completed",
                    "处理完成",
                    "Search completed",
                    "搜索完成",
                    "✅",
                ],
                failure_patterns=[
                    "Model not found",
                    "API key missing",
                    "Connection failed",
                ],
                environment_vars={
                    "SAGE_MULTIMODAL_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                },
            ),
            "scheduler": TestStrategy(
                name="scheduler",
                timeout=90,  # 90秒，调度器对比实验
                requires_config=False,
                requires_data=False,
                success_patterns=[
                    "所有实验完成",
                    "实验完成",
                    "执行结果",
                    "✅",
                    "调度器性能对比总结",
                ],
                failure_patterns=[
                    "调度失败",
                    "Scheduler failed",
                    "Connection refused",
                    "Timeout exceeded",
                ],
                environment_vars={
                    "SAGE_SCHEDULER_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                    "SAGE_TEST_MODE": "true",
                },
            ),
            "apps": TestStrategy(
                name="apps",
                timeout=180,
                requires_config=True,
                requires_data=False,
                success_patterns=[
                    "Application started",
                    "Processing completed",
                    "✅",
                    "完成",
                ],
                failure_patterns=[
                    "Failed to start",
                    "Connection error",
                    "Model not found",
                ],
                environment_vars={
                    "SAGE_APP_MODE": "test",
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                },
            ),
            "environment": TestStrategy(
                name="environment",
                timeout=120,  # 2 minutes for environment examples
                requires_config=False,
                requires_data=False,
                success_patterns=[
                    "任务执行完成",
                    "环境创建完成",
                    "Pipeline 构建完成",
                    "✅",
                    "所有示例运行完成",
                ],
                failure_patterns=[
                    "连接失败",
                    "任务提交失败",
                    "JobManager daemon 未运行",
                    "Connection refused",
                ],
                environment_vars={
                    "SAGE_LOG_LEVEL": "ERROR",
                    "SAGE_EXAMPLES_MODE": "test",
                    "SAGE_TEST_MODE": "true",
                },
            ),
        }

    @staticmethod
    def get_category_skip_patterns() -> dict[str, list[str]]:
        """获取各类别需要跳过的文件模式

        Returns:
            字典，键为类别名称，值为该类别需要跳过的文件模式列表
        """
        return {
            "rag": [
                "*_interactive.py",  # 交互式示例
                "*_demo.py",  # 演示文件
                "*_benchmark.py",  # 基准测试
            ],
            "service": [
                "*_server.py",  # 长期运行的服务
                "*_daemon.py",  # 守护进程
            ],
            "video": [
                "*_large_file.py",  # 处理大文件
                "*_gpu_required.py",  # 需要GPU
            ],
        }
