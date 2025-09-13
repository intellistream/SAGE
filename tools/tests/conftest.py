#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 配置文件
"""

import pytest
from pathlib import Path

def pytest_addoption(parser):
    """添加 pytest 命令行选项"""
    parser.addoption(
        "--examples-category",
        action="append",
        default=[],
        help="Run examples tests for specific categories"
    )
    parser.addoption(
        "--examples-quick-only",
        action="store_true",
        default=False,
        help="Run only quick examples tests"
    )

def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "examples: marks tests as examples tests")
    config.addinivalue_line("markers", "quick_examples: marks tests as quick examples tests")
    config.addinivalue_line("markers", "slow_examples: marks tests as slow examples tests")

def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    if config.getoption("--examples-quick-only"):
        # 只运行快速示例测试
        quick_marker = pytest.mark.quick_examples
        for item in items:
            if "examples" in item.nodeid:
                item.add_marker(quick_marker)

def pytest_generate_tests(metafunc):
    """动态生成测试用例"""
    if "example_file" in metafunc.fixturenames:
        # 这里需要导入，避免循环导入
        try:
            from test_examples import ExampleAnalyzer
            
            # 为每个示例文件生成一个测试用例
            analyzer = ExampleAnalyzer()
            examples = analyzer.discover_examples()
            
            # 过滤示例
            categories = metafunc.config.getoption("--examples-category")
            if categories:
                examples = [e for e in examples if e.category in categories]
            
            if metafunc.config.getoption("--examples-quick-only"):
                examples = [e for e in examples if e.estimated_runtime == "quick"]
            
            metafunc.parametrize("example_file", examples, ids=[Path(e.file_path).name for e in examples])
        except ImportError:
            # 如果无法导入，跳过动态生成
            pass