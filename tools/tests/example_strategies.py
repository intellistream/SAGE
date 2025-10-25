#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Examples 专用测试配置和策略
为不同类型的示例定义特定的测试策略
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# 导入项目根目录查找函数
from test_examples import find_project_root


@dataclass
class TestStrategy:
    """测试策略配置"""

    name: str
    timeout: int
    requires_config: bool
    requires_data: bool
    mock_inputs: Optional[Dict[str, str]] = None
    environment_vars: Optional[Dict[str, str]] = None
    success_patterns: Optional[List[str]] = None
    failure_patterns: Optional[List[str]] = None
    pre_run_setup: Optional[Callable] = None
    post_run_cleanup: Optional[Callable] = None


class ExampleTestStrategies:
    """示例测试策略集合"""

    @staticmethod
    def get_strategies() -> Dict[str, TestStrategy]:
        """获取所有测试策略"""
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
                timeout=60,
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
        }

    @staticmethod
    def get_category_skip_patterns() -> Dict[str, List[str]]:
        """获取各类别需要跳过的文件模式"""
        return {
            "rag": [
                "*_interactive.py",  # 交互式示例
                "*_demo.py",  # 演示文件
                "*_benchmark.py",  # 基准测试
            ],
            "service": ["*_server.py", "*_daemon.py"],  # 长期运行的服务  # 守护进程
            "video": ["*_large_file.py", "*_gpu_required.py"],  # 处理大文件  # 需要GPU
        }

    @staticmethod
    def get_mock_data_generators() -> Dict[str, Callable]:
        """获取模拟数据生成器"""
        return {
            "rag": ExampleTestStrategies._generate_rag_mock_data,
            "memory": ExampleTestStrategies._generate_memory_mock_data,
            "video": ExampleTestStrategies._generate_video_mock_data,
        }

    @staticmethod
    def _generate_rag_mock_data() -> Dict[str, Any]:
        """生成RAG测试的模拟数据"""
        return {
            "documents": """
                Document 1: Artificial Intelligence (AI) is the simulation of human intelligence in machines.
                Document 2: Machine Learning is a subset of AI that learns from data.
                Document 3: Deep Learning uses neural networks with multiple layers.
            """,
            "queries": [
                "What is AI?",
                "How does machine learning work?",
                "Explain deep learning",
            ],
        }

    @staticmethod
    def _generate_memory_mock_data() -> Dict[str, Any]:
        """生成内存测试的模拟数据"""
        return {
            "test_data": "This is test data for memory storage",
            "metadata": {"source": "test", "type": "example"},
        }

    @staticmethod
    def _generate_video_mock_data() -> Dict[str, str]:
        """生成视频测试的模拟数据"""
        # 创建一个简单的测试视频文件路径
        return {
            "video_path": "/tmp/test_video.mp4",
            "frame_count": "10",
            "duration": "1.0",
        }


class ExampleTestFilters:
    """示例测试过滤器"""

    @staticmethod
    def should_skip_file(file_path: Path, category: str, example_info=None) -> tuple[bool, str]:
        """判断是否应该跳过某个文件的测试

        Args:
            file_path: 文件路径
            category: 文件类别
            example_info: 示例信息对象（包含test_tags）

        Returns:
            (should_skip, reason): 是否跳过和跳过原因
        """
        import os

        # 检查文件内的测试标记
        if example_info and hasattr(example_info, "test_tags"):
            # 检查跳过标记
            if "skip" in example_info.test_tags:
                return True, "文件包含 @test:skip 标记"

            # 检查 CI 环境下的跳过标记
            is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
            if is_ci:
                # 检查 skip_ci 标记（支持 skip_ci 或 skip_ci=true）
                for tag in example_info.test_tags:
                    if tag == "skip_ci" or tag.startswith("skip_ci="):
                        return True, "文件包含 @test_skip_ci 标记，在 CI 环境中跳过"

            # 检查需要API密钥的标记
            if "require-api" in example_info.test_tags:
                return True, "需要API密钥，在测试环境中跳过"

            # 检查需要用户交互的标记
            if "interactive" in example_info.test_tags:
                return True, "需要用户交互，自动测试中跳过"

            # 检查不稳定测试标记
            if "unstable" in example_info.test_tags:
                return True, "标记为不稳定测试，跳过"

            # 检查需要GPU的标记
            if "gpu" in example_info.test_tags:
                return True, "需要GPU支持，在测试环境中跳过"

        return False, ""

    @staticmethod
    def estimate_test_priority(file_path: Path, category: str) -> int:
        """估算测试优先级 (1=高, 2=中, 3=低)"""
        # 基础教程最高优先级
        if category == "tutorials":
            if "hello_world" in file_path.name:
                return 1
            return 2

        # RAG示例中等优先级
        if category == "rag":
            if "simple" in file_path.name:
                return 2
            return 3

        # 其他类别默认低优先级
        return 3


class ExampleEnvironmentManager:
    """示例执行环境管理器"""

    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []

    def setup_category_environment(self, category: str) -> Dict[str, str]:
        """为特定类别设置环境"""
        strategy = ExampleTestStrategies.get_strategies().get(category)
        if not strategy:
            return {}

        env_vars = strategy.environment_vars.copy() if strategy.environment_vars else {}

        # 添加通用测试环境变量
        env_vars.update(
            {
                "SAGE_TEST_MODE": "true",
                "SAGE_EXAMPLES_TEST": "true",
                "PYTHONPATH": self._get_sage_python_path(),
            }
        )

        # 为需要配置的类别创建临时配置文件
        if strategy.requires_config:
            config_path = self._create_temp_config(category)
            env_vars["SAGE_CONFIG_PATH"] = str(config_path)

        # 为需要数据的类别创建模拟数据
        if strategy.requires_data:
            data_path = self._create_temp_data(category)
            env_vars["SAGE_DATA_PATH"] = str(data_path)

        return env_vars

    def _get_sage_python_path(self) -> str:
        """获取SAGE的Python路径"""
        try:
            project_root = find_project_root()
            sage_paths = [
                str(project_root / "packages" / "sage" / "src"),
                str(project_root / "packages" / "sage-common" / "src"),
                str(project_root / "packages" / "sage-kernel" / "src"),
                str(project_root / "packages" / "sage-libs" / "src"),
                str(project_root / "packages" / "sage-middleware" / "src"),
                str(project_root / "packages" / "sage-tools" / "src"),
            ]
            return ":".join(sage_paths)
        except FileNotFoundError:
            # 如果找不到项目根目录，返回空字符串或抛出错误
            raise FileNotFoundError("Cannot find SAGE project root directory for Python path setup")

    def _create_temp_config(self, category: str) -> Path:
        """创建临时配置文件"""
        import tempfile

        import yaml

        config_data = {"test_mode": True, "log_level": "WARNING", "category": category}

        if category == "rag":
            config_data.update(
                {
                    "llm": {
                        "provider": "mock",
                        "model": "test-model",
                        "api_key": "test-key",  # pragma: allowlist secret
                    },
                    "embedding": {"provider": "mock", "model": "test-embedding"},
                    "retriever": {"type": "mock", "top_k": 3},
                }
            )

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(config_data, temp_file)
        temp_file.close()

        self.temp_files.append(temp_file.name)
        return Path(temp_file.name)

    def _create_temp_data(self, category: str) -> Path:
        """创建临时数据目录和文件"""
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix=f"sage_test_{category}_")
        self.temp_dirs.append(temp_dir)

        data_generators = ExampleTestStrategies.get_mock_data_generators()
        if category in data_generators:
            mock_data = data_generators[category]()

            # 根据类别创建对应的数据文件
            if category == "rag":
                docs_file = Path(temp_dir) / "documents.txt"
                with open(docs_file, "w") as f:
                    f.write(mock_data["documents"])

            elif category == "memory":
                data_file = Path(temp_dir) / "test_data.json"
                import json

                with open(data_file, "w") as f:
                    json.dump(mock_data, f)

        return Path(temp_dir)

    def cleanup(self):
        """清理临时文件和目录"""
        import os
        import shutil

        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except Exception:
                pass

        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        self.temp_files.clear()
        self.temp_dirs.clear()
