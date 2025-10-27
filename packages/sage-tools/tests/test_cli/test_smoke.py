#!/usr/bin/env python3
"""
SAGE CLI 冒烟测试 (Smoke Test)

这是一个轻量级的快速验证测试，只测试最关键的核心功能：
1. CLI能否正常启动
2. 核心命令是否可访问
3. 基本功能是否工作

与 test_commands_full.py 的区别：
- Smoke Test: 快速验证，2-3分钟，关键路径
- Full Test: 详细测试，可能10-15分钟，覆盖所有功能

使用pytest格式符合测试标准。
"""

import subprocess
import sys
from pathlib import Path

import pytest


def get_project_root():
    """获取项目根目录"""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / "packages").exists():
            return current
        current = current.parent
    return Path(__file__).parent.parent.parent.parent.parent


def run_command_simple(cmd_list, timeout=20):
    """运行命令并返回成功状态"""
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=get_project_root(),
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return False, "", str(e)


@pytest.mark.cli
@pytest.mark.smoke
class TestCLISmoke:
    """CLI冒烟测试 - 快速验证核心功能"""

    def test_cli_startup(self):
        """测试CLI启动"""
        success, stdout, stderr = run_command_simple(
            [sys.executable, "-m", "sage.tools.cli", "--help"]
        )
        assert success, f"CLI startup failed: {stderr}"
        # sage.tools.cli 现在只有 dev 和 finetune 命令
        assert "dev" in stdout

    def test_dev_command_help(self):
        """测试dev命令"""
        success, stdout, stderr = run_command_simple(
            [sys.executable, "-m", "sage.tools.cli", "dev", "--help"]
        )
        assert success, f"Dev command failed: {stderr}"
        assert "开发工具" in stdout or "dev" in stdout.lower()

    def test_status_check(self):
        """测试基本状态检查"""
        success, stdout, stderr = run_command_simple(
            [sys.executable, "-m", "sage.tools.cli", "dev", "project", "status"],
            timeout=60,  # 增加超时
        )
        assert success, f"Status check failed: {stderr}"
        assert "状态报告" in stdout or "status" in stdout.lower()

    def test_backwards_compatibility(self):
        """测试向后兼容性"""
        success, stdout, stderr = run_command_simple(["sage-dev", "--help"])
        if not success:
            # sage-dev可能不在PATH中，这是可以接受的
            pytest.skip("sage-dev command not available in PATH - this is acceptable")
        assert "开发工具" in stdout or "dev" in stdout.lower()
