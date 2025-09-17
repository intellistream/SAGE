#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 配置文件
"""

import os
import time
from pathlib import Path

import pytest


def pytest_addoption(parser):
    """添加 pytest 命令行选项"""
    parser.addoption(
        "--examples-category",
        action="append",
        default=[],
        help="Run examples tests for specific categories",
    )
    parser.addoption(
        "--examples-quick-only",
        action="store_true",
        default=False,
        help="Run only quick examples tests",
    )
    parser.addoption(
        "--use-real-api",
        action="store_true",
        default=False,
        help="Use real API calls instead of test mode (requires valid API keys)",
    )


def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "examples: marks tests as examples tests")
    config.addinivalue_line(
        "markers", "quick_examples: marks tests as quick examples tests"
    )
    config.addinivalue_line(
        "markers", "slow_examples: marks tests as slow examples tests"
    )
    
    # 设置环境变量以便传递给子进程
    if config.getoption("--use-real-api", default=False):
        os.environ["SAGE_USE_REAL_API"] = "true"


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    if config.getoption("--examples-quick-only"):
        # 只运行快速示例测试
        quick_marker = pytest.mark.quick_examples
        for item in items:
            if "examples" in item.nodeid:
                item.add_marker(quick_marker)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """测试开始前的hook"""
    # 在CI环境中减少输出
    if os.environ.get("CI") == "true":
        # CI环境：只记录时间，不输出开始信息
        item._example_start_time = time.time()
        return

    example_name = "unknown"
    test_type = "测试"

    if "test_individual_example" in item.nodeid:
        test_type = "示例"
        if hasattr(item, "callspec") and "example_file" in item.callspec.params:
            example_file = item.callspec.params["example_file"]
            if hasattr(example_file, "file_path"):
                example_name = Path(example_file.file_path).name
    else:
        # 其他类型的测试
        test_type = "集成测试"
        example_name = item.name

    print(f"\n🧪 开始{test_type}: {example_name}")
    item._example_start_time = time.time()


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """测试结束后的hook"""
    if hasattr(item, "_example_start_time"):
        duration = time.time() - item._example_start_time

        # 在CI环境中减少输出
        if os.environ.get("CI") == "true":
            # CI环境：只在测试失败或超过10秒时输出
            if duration > 10.0:
                example_name = _get_example_name(item)
                print(f"🐌 {example_name} 耗时较长 ({duration:.2f}s)")
            return

        example_name = _get_example_name(item)
        test_type = _get_test_type(item)

        # 根据时间长短显示不同的状态图标
        if duration < 0.5:
            status_icon = "⚡"  # 非常快
            time_desc = "极快"
        elif duration < 2.0:
            status_icon = "✅"  # 正常
            time_desc = "正常"
        elif duration < 10.0:
            status_icon = "⏱️"  # 较慢
            time_desc = "较慢"
        else:
            status_icon = "🐌"  # 很慢
            time_desc = "很慢"

        print(f"{status_icon} {example_name} 完成 ({duration:.2f}s) - {time_desc}")


def _get_example_name(item):
    """获取示例名称"""
    if "test_individual_example" in item.nodeid:
        if hasattr(item, "callspec") and "example_file" in item.callspec.params:
            example_file = item.callspec.params["example_file"]
            if hasattr(example_file, "file_path"):
                return Path(example_file.file_path).name
    return item.name


def _get_test_type(item):
    """获取测试类型"""
    if "test_individual_example" in item.nodeid:
        return "示例"
    return "集成测试"


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    """测试报告hook - 处理失败的情况"""
    if report.when == "call":
        # 在CI环境中只显示失败和跳过的测试
        if os.environ.get("CI") == "true":
            if not (report.failed or report.skipped):
                return

        example_name = _get_example_name_from_report(report)
        test_type = _get_test_type_from_report(report)

        if report.failed:
            print(f"❌ {example_name} {test_type}失败")
        elif report.skipped:
            print(f"⏭️  {example_name} {test_type}已跳过")


def _get_example_name_from_report(report):
    """从报告中获取示例名称"""
    if "test_individual_example" in report.nodeid:
        # 尝试从nodeid中提取example名称
        if "[" in report.nodeid and "]" in report.nodeid:
            return report.nodeid.split("[")[1].split("]")[0]
    return report.nodeid.split("::")[-1]


def _get_test_type_from_report(report):
    """从报告中获取测试类型"""
    if "test_individual_example" in report.nodeid:
        return "示例"
    return "集成测试"


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

            # 只有当有示例文件时才进行参数化
            if examples:
                metafunc.parametrize(
                    "example_file",
                    examples,
                    ids=[Path(e.file_path).name for e in examples],
                )
            else:
                # 如果没有示例文件，跳过测试
                metafunc.parametrize("example_file", [], ids=[])

        except Exception as e:
            # 如果无法导入或发生其他错误，跳过动态生成
            print(f"⚠️ 无法生成示例测试: {e}")
            metafunc.parametrize("example_file", [], ids=[])
