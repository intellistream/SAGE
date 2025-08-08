#!/usr/bin/env python3
"""
测试 PyPI 上传功能
"""

import sys
import subprocess
import os
import pytest
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🧪 测试: {description}")
    print(f"💻 命令: {' '.join(cmd)}")
    
    try:
        # 使用项目根目录作为工作目录，设置 PYTHONPATH
        project_root = Path(__file__).parent.parent.parent.parent
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent / "src")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
        
        if result.returncode == 0:
            print(f"✅ 成功")
            if result.stdout.strip():
                print("输出:")
                print(result.stdout)
        else:
            print(f"❌ 失败 (退出码: {result.returncode})")
            if result.stderr.strip():
                print("错误:")
                print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False


class TestPyPIIntegration:
    """PyPI integration tests"""
    
    def test_pypi_help_command(self):
        """测试 PyPI 帮助命令"""
        cmd = ["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "--help"]
        success = run_command(cmd, "PyPI 帮助命令")
        assert success, "PyPI 帮助命令应该成功执行"
    
    def test_pypi_info_command(self):
        """测试显示包信息"""
        cmd = ["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "info"]
        success = run_command(cmd, "显示包信息")
        assert success, "显示包信息命令应该成功执行"
    
    def test_pypi_check_command(self):
        """测试检查包配置"""
        cmd = ["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "check"]
        success = run_command(cmd, "检查包配置")
        assert success, "检查包配置命令应该成功执行"
    
    def test_pypi_build_help(self):
        """测试构建帮助"""
        cmd = ["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "build", "--help"]
        success = run_command(cmd, "构建帮助")
        assert success, "构建帮助命令应该成功执行"
    
    def test_pypi_clean_help(self):
        """测试清理帮助"""
        cmd = ["python", "-m", "sage_dev_toolkit.cli.main", "pypi", "clean", "--help"]
        success = run_command(cmd, "清理帮助")
        assert success, "清理帮助命令应该成功执行"


if __name__ == "__main__":
    # 如果直接运行此文件，执行所有测试
    pytest.main([__file__, "-v"])
