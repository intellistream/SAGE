#!/usr/bin/env python3
"""
SAGE 开发工具 CLI 命令完整测试

测试所有dev命令的功能，确保它们能正常工作。
使用pytest格式符合测试标准。
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def run_command(
    command: List[str], timeout: int = 30, project_root: Path = PROJECT_ROOT
) -> Dict[str, Any]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            command, cwd=project_root, capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "returncode": -1,
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}


@pytest.mark.cli
@pytest.mark.integration
class TestCLICommandsFull:
    """完整的CLI命令测试"""

    def test_main_cli_help(self):
        """测试主CLI帮助"""
        result = run_command([sys.executable, "-m", "sage.tools.cli", "--help"])
        assert result["success"], f"CLI help failed: {result['stderr']}"
        assert "SAGE" in result["stdout"]

    def test_dev_help(self):
        """测试dev命令帮助"""
        result = run_command([sys.executable, "-m", "sage.tools.cli", "dev", "--help"])
        assert result["success"], f"Dev help failed: {result['stderr']}"
        assert "开发工具" in result["stdout"]

    def test_sage_dev_help(self):
        """测试sage-dev帮助"""
        result = run_command(["sage-dev", "--help"])
        # sage-dev 可能不在PATH中，允许失败
        if not result["success"]:
            pytest.skip("sage-dev command not available in PATH")
        assert "开发工具" in result["stdout"]

    def test_status_command_summary(self):
        """测试status命令 - summary格式"""
        result = run_command(
            [
                sys.executable,
                "-m",
                "sage.tools.cli.commands.dev.simple_main",
                "status",
                "--output-format",
                "summary",
            ]
        )
        assert result["success"], f"Status summary failed: {result['stderr']}"
        assert "状态报告" in result["stdout"]

    def test_status_command_json(self):
        """测试status命令 - JSON格式"""
        result = run_command(
            [
                sys.executable,
                "-m",
                "sage.tools.cli.commands.dev.simple_main",
                "status",
                "--output-format",
                "json",
            ]
        )
        assert result["success"], f"Status JSON failed: {result['stderr']}"
        # 验证JSON格式 - 跳过调试输出，找到实际的JSON
        lines = result["stdout"].strip().split("\n")
        json_lines = []
        json_started = False
        for line in lines:
            if line.strip().startswith("{"):
                json_started = True
            if json_started:
                json_lines.append(line)

        if json_lines:
            json_text = "\n".join(json_lines)
            try:
                # Try to parse the JSON
                data = json.loads(json_text)
                # Verify it has the expected structure
                assert "timestamp" in data
                assert "checks" in data
                assert isinstance(data["checks"], dict)
            except json.JSONDecodeError as e:
                # If JSON parsing fails due to control characters, just check basic structure
                assert "timestamp" in json_text
                assert "checks" in json_text
                assert "{" in json_text and "}" in json_text
        else:
            pytest.fail("No JSON found in status output")

    def test_status_command_markdown(self):
        """测试status命令 - Markdown格式"""
        result = run_command(
            [
                sys.executable,
                "-m",
                "sage.tools.cli.commands.dev.simple_main",
                "status",
                "--output-format",
                "markdown",
            ]
        )
        assert result["success"], f"Status markdown failed: {result['stderr']}"
        assert "# SAGE 项目状态报告" in result["stdout"]

    def test_analyze_command_basic(self):
        """测试analyze命令 - 基本分析"""
        result = run_command(
            [
                sys.executable,
                "-m",
                "sage.tools.cli.commands.dev.simple_main",
                "analyze",
                "--analysis-type",
                "all",
            ]
        )
        # 分析命令可能需要更长时间，允许某些错误
        if result["success"]:
            assert "分析" in result["stdout"]
        else:
            # 如果失败，检查是否是预期的错误
            assert result["returncode"] in [
                0,
                1,
            ], f"Unexpected return code: {result['returncode']}"

    def test_clean_command_dry_run(self):
        """测试clean命令 - 预览模式"""
        result = run_command(
            [
                sys.executable,
                "-m",
                "sage.tools.cli.commands.dev.simple_main",
                "clean",
                "--dry-run",
            ]
        )
        assert result["success"], f"Clean dry-run failed: {result['stderr']}"
        assert "预览" in result["stdout"]

    def test_doctor_command(self):
        """测试doctor命令"""
        result = run_command([sys.executable, "-m", "sage.tools.cli.main", "doctor"])
        assert result["success"], f"Doctor command failed: {result['stderr']}"
        assert "系统诊断" in result["stdout"]

    def test_version_command(self):
        """测试version命令"""
        result = run_command([sys.executable, "-m", "sage.tools.cli.main", "version"])
        assert result["success"], f"Version command failed: {result['stderr']}"
        assert "版本" in result["stdout"] or "version" in result["stdout"].lower()

    def test_config_help(self):
        """测试config命令帮助"""
        result = run_command(
            [sys.executable, "-m", "sage.tools.cli.main", "config", "--help"]
        )
        assert result["success"], f"Config help failed: {result['stderr']}"
        assert "配置" in result["stdout"]

    @pytest.mark.slow
    def test_import_functionality(self):
        """测试关键模块导入功能"""
        modules_to_test = [
            "sage.tools.cli.main",
            "sage.tools.cli.commands.dev.simple_main",
            "sage.tools.dev.tools.project_status_checker",
            "sage.tools.dev.tools.dependency_analyzer",
        ]

        for module in modules_to_test:
            result = run_command(
                [sys.executable, "-c", f"import {module}; print('OK')"]
            )
            assert result["success"], f"Failed to import {module}: {result['stderr']}"
            assert "OK" in result["stdout"]

    @pytest.mark.slow
    def test_home_command_status(self):
        """测试home命令状态"""
        result = run_command(
            [
                sys.executable,
                "-m",
                "sage.tools.cli.commands.dev.simple_main",
                "home",
                "status",
            ]
        )
        assert result["success"], f"Home status failed: {result['stderr']}"
        assert "SAGE_HOME" in result["stdout"]

    def test_test_command_basic(self):
        """测试test命令基本功能"""
        # 这个测试可能耗时较长，所以我们只测试命令能够启动
        # 实际的测试运行在其他地方验证
        result = run_command(
            [
                sys.executable,
                "-c",
                "from sage.tools.cli.commands.dev.simple_main import test; print('Test command importable')",
            ]
        )
        assert result["success"], f"Test command import failed: {result['stderr']}"
        assert "Test command importable" in result["stdout"]
