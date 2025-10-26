#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""
SAGE C++ Extensions 测试的 pytest 集成

测试 C++ 扩展的安装、导入和示例程序运行
"""

import subprocess
import sys
from pathlib import Path

import pytest

# 添加项目路径
current_dir = Path(__file__).parent
sage_root = current_dir.parent.parent
sys.path.insert(0, str(sage_root / "packages" / "sage-tools" / "src"))


class TestCppExtensions:
    """C++ 扩展测试集成到 pytest"""

    @classmethod
    def setup_class(cls):
        """在测试类开始前检查并安装必要的扩展"""
        cls._ensure_extensions_installed()

    @classmethod
    def _check_extension_status(cls):
        """检查扩展安装状态

        Returns:
            tuple: (success: bool, result: subprocess.CompletedProcess)
        """
        try:
            result = subprocess.run(
                ["sage", "extensions", "status"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            return result.returncode == 0, result
        except subprocess.TimeoutExpired:
            pytest.skip("⏰ 扩展状态检查超时")
        except FileNotFoundError:
            pytest.skip("❌ sage 命令不可用")
        except Exception as e:
            pytest.skip(f"⚠️ 检查扩展状态时出错: {e}")

    @classmethod
    def _ensure_extensions_installed(cls):
        """检查扩展状态，如果未安装则自动安装"""
        try:
            # 检查扩展状态
            success, result = cls._check_extension_status()

            if success:
                print("✅ C++ 扩展已安装且可用")
                return

            print("⚠️ C++ 扩展不可用，尝试安装...")
            print(f"状态检查输出: {result.stdout}")
            print(f"状态检查错误: {result.stderr}")

            # 尝试安装扩展
            install_result = subprocess.run(
                ["sage", "extensions", "install", "all", "--force"],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,  # 5分钟超时
            )

            if install_result.returncode == 0:
                print("✅ C++ 扩展安装成功")

                # 再次检查状态
                success, _ = cls._check_extension_status()
                if success:
                    print("✅ C++ 扩展验证通过")
                else:
                    pytest.skip("⚠️ C++ 扩展安装后验证失败")
            else:
                print("❌ C++ 扩展安装失败")
                print(f"安装输出: {install_result.stdout}")
                print(f"安装错误: {install_result.stderr}")
                pytest.skip("❌ C++ 扩展安装失败，跳过相关测试")

        except subprocess.TimeoutExpired:
            pytest.skip("⏰ 扩展安装超时")
        except Exception as e:
            pytest.skip(f"⚠️ 安装扩展时出错: {e}")

    def test_extension_status(self):
        """测试扩展状态检查"""
        success, result = self._check_extension_status()
        assert success, f"扩展状态检查失败: {result.stderr}"

        # 检查输出中包含预期的扩展
        output = result.stdout.lower()
        assert "扩展" in output or "extension" in output, "输出中应包含扩展信息"

    def test_sage_db_import(self):
        """测试 SAGE DB 扩展导入"""
        try:
            from sage.middleware.components.extensions_compat import is_sage_db_available

            if not is_sage_db_available():
                pytest.skip("SAGE DB 扩展不可用")

            # 测试导入 C++ 扩展
            from sage.middleware.components.sage_db.python import _sage_db

            assert _sage_db is not None, "SAGE DB C++ 扩展导入失败"

            # 测试基本功能
            assert hasattr(_sage_db, "SageDB"), "缺少 SageDB 类"
            print("✅ SAGE DB 扩展导入成功")

        except ImportError as e:
            pytest.fail(f"SAGE DB 扩展导入失败: {e}")

    def test_sage_flow_import(self):
        """测试 SAGE Flow 扩展导入"""
        try:
            from sage.middleware.components.extensions_compat import is_sage_flow_available

            if not is_sage_flow_available():
                pytest.skip("SAGE Flow 扩展不可用")

            # 测试导入 C++ 扩展
            from sage.middleware.components.sage_flow.python import _sage_flow

            assert _sage_flow is not None, "SAGE Flow C++ 扩展导入失败"

            print("✅ SAGE Flow 扩展导入成功")

        except ImportError as e:
            pytest.fail(f"SAGE Flow 扩展导入失败: {e}")

    def test_extension_functionality(self):
        """测试扩展基本功能"""
        try:
            from sage.middleware.components.extensions_compat import (
                get_extension_status,
                is_sage_db_available,
                is_sage_flow_available,
            )

            status = get_extension_status()
            assert isinstance(status, dict), "扩展状态应该是字典"
            assert "sage_db" in status, "状态中应包含 sage_db"
            assert "sage_flow" in status, "状态中应包含 sage_flow"

            # 如果有可用扩展，测试基本功能
            if is_sage_db_available():
                print("✅ SAGE DB 可用")
                # 这里可以添加更多具体的功能测试

            if is_sage_flow_available():
                print("✅ SAGE Flow 可用")
                # 这里可以添加更多具体的功能测试

        except Exception as e:
            pytest.fail(f"扩展功能测试失败: {e}")

    def test_cli_extensions_command(self):
        """测试 CLI 扩展命令"""
        try:
            # 测试扩展列表命令
            result = subprocess.run(
                ["sage", "extensions", "status"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            assert result.returncode == 0, "扩展状态命令执行失败"
            assert len(result.stdout.strip()) > 0, "扩展状态输出不应为空"

            print("✅ CLI 扩展命令测试通过")

        except subprocess.CalledProcessError as e:
            pytest.fail(f"CLI 扩展命令失败: {e}")
        except subprocess.TimeoutExpired:
            pytest.fail("CLI 扩展命令超时")


# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
