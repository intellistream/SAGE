#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE C++ Extensions 测试的 pytest 集成
测试 C++ 扩展的安装、导入和示例程序运行
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

# 添加项目路径
current_dir = Path(__file__).parent
sage_root = current_dir.parent.parent
sys.path.insert(0, str(sage_root / "packages" / "sage-tools" / "src"))


class TestCppExtensions:
    """C++ 扩展测试集成到 pytest"""

    def test_sage_db_import(self):
        """测试 sage_db 扩展导入"""
        try:
            from sage.middleware.components.sage_db.python.sage_db import \
                SageDB

            assert True, "sage_db 扩展导入成功"
        except ImportError as e:
            pytest.fail(f"sage_db 扩展导入失败: {e}")

    def test_sage_flow_import(self):
        """测试 sage_flow 扩展导入"""
        try:
            from sage.middleware.components.sage_flow.python.sage_flow import \
                StreamEnvironment

            assert True, "sage_flow 扩展导入成功"
        except ImportError as e:
            pytest.fail(f"sage_flow 扩展导入失败: {e}")

    def test_sage_db_microservice_import(self):
        """测试 sage_db micro_service 导入"""
        try:
            from sage.middleware.components.sage_db.python.micro_service.sage_db_service import \
                SageDBService

            assert True, "sage_db micro_service 导入成功"
        except ImportError as e:
            pytest.fail(f"sage_db micro_service 导入失败: {e}")

    def test_sage_flow_microservice_import(self):
        """测试 sage_flow micro_service 导入"""
        try:
            from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import \
                SageFlowService

            assert True, "sage_flow micro_service 导入成功"
        except ImportError as e:
            pytest.fail(f"sage_flow micro_service 导入失败: {e}")

    @pytest.mark.example
    def test_sage_db_example(self):
        """测试 sage_db 示例程序"""
        example_path = (
            sage_root / "examples" / "service" / "sage_db" / "hello_sage_db_app.py"
        )

        if not example_path.exists():
            pytest.skip(f"示例文件不存在: {example_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(example_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(sage_root),
            )

            assert result.returncode == 0, f"sage_db 示例运行失败: {result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("sage_db 示例运行超时")
        except Exception as e:
            pytest.fail(f"sage_db 示例运行异常: {e}")

    @pytest.mark.example
    def test_sage_flow_example(self):
        """测试 sage_flow 示例程序"""
        example_path = (
            sage_root / "examples" / "service" / "sage_flow" / "hello_sage_flow_app.py"
        )

        if not example_path.exists():
            pytest.skip(f"示例文件不存在: {example_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(example_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(sage_root),
            )

            assert result.returncode == 0, f"sage_flow 示例运行失败: {result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.fail("sage_flow 示例运行超时")
        except Exception as e:
            pytest.fail(f"sage_flow 示例运行异常: {e}")

    @pytest.mark.parametrize(
        "extension,import_statement",
        [
            (
                "sage_db",
                "from sage.middleware.components.sage_db.python.sage_db import SageDB",
            ),
            (
                "sage_flow",
                "from sage.middleware.components.sage_flow.python.sage_flow import StreamEnvironment",
            ),
            (
                "sage_db_service",
                "from sage.middleware.components.sage_db.python.micro_service.sage_db_service import SageDBService",
            ),
            (
                "sage_flow_service",
                "from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import SageFlowService",
            ),
        ],
    )
    def test_extension_imports_parametrized(self, extension, import_statement):
        """参数化测试扩展导入"""
        try:
            exec(import_statement)
        except ImportError as e:
            pytest.fail(f"{extension} 扩展导入失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
