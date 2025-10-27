"""
Data models for Examples testing framework

This module defines the data structures used throughout the examples testing system.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExampleTestResult:
    """示例测试结果"""

    file_path: str
    test_name: str
    status: str  # "passed", "failed", "skipped", "timeout"
    execution_time: float
    output: str
    error: Optional[str] = None
    dependencies_met: bool = True
    requires_user_input: bool = False


@dataclass
class ExampleInfo:
    """示例文件信息"""

    file_path: str
    category: str  # tutorials, rag, memory, etc.
    imports: List[str]
    has_main: bool
    requires_config: bool
    requires_data: bool
    estimated_runtime: str  # "quick", "medium", "slow"
    dependencies: List[str]
    test_tags: List[str]  # 测试标记，从文件注释中提取
