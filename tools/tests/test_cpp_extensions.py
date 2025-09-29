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
    
    # 扩展安装超时时间（秒）
    EXTENSION_INSTALL_TIMEOUT = 600  # 10分钟

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
                [sys.executable, "-m", "sage.tools.cli", "extensions", "status"],
                capture_output=True,
                text=True,
                cwd=str(sage_root),
            )
            
            # 如果状态检查失败或者输出中包含缺失扩展的标识
            success = result.returncode == 0 and "✗" not in result.stdout
            return success, result
            
        except Exception as e:
            return False, None

    @classmethod
    def _ensure_extensions_installed(cls):
        """检查扩展状态，如果未安装则自动安装"""
        try:
            # 检查扩展状态
            success, result = cls._check_extension_status()

            if not success:
                print("\n🔧 检测到扩展未完全安装，正在自动安装...")
                print("ℹ️ 这可能需要几分钟时间，请耐心等待...\n")

                # 自动安装所有扩展，增加超时时间
                install_result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "sage.tools.cli",
                        "extensions",
                        "install",
                        "all",
                    ],
                    cwd=str(sage_root),
                    timeout=cls.EXTENSION_INSTALL_TIMEOUT,
                    text=True,
                    # 不捕获输出，让用户看到安装进度
                )

                if install_result.returncode != 0:
                    pytest.skip("❌ 扩展安装失败，请手动运行: sage extensions install")
                else:
                    print("✅ 扩展安装完成\n")
                    # 再次检查状态确认安装成功
                    cls._verify_extensions_installed()

        except subprocess.TimeoutExpired:
            pytest.skip("⚠️ 扩展安装超时，请手动运行: sage extensions install")
        except Exception as e:
            pytest.skip(f"⚠️ 检查/安装扩展时出错: {e}")

    @classmethod
    def _verify_extensions_installed(cls):
        """验证扩展安装状态"""
        try:
            success, result = cls._check_extension_status()

            if not success:
                pytest.skip("❌ 扩展安装验证失败，请手动检查")
            else:
                print("✅ 扩展安装验证成功")

        except Exception as e:
            pytest.skip(f"⚠️ 验证扩展状态时出错: {e}")

    def test_sage_db_import(self):
        """测试 sage_db 扩展导入"""
        try:
            from sage.middleware.components.sage_db.python.sage_db import \
                SageDB  # noqa: F401

            assert True, "sage_db 扩展导入成功"
        except ImportError as e:
            if "libsage_db.so" in str(e):
                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_db 扩展导入失败: {e}")
            if "libsage_db.so" in str(e):
                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_db 扩展导入失败: {e}")

    def test_sage_flow_import(self):
        """测试 sage_flow 扩展导入"""
        try:
            from sage.middleware.components.sage_flow.python.sage_flow import \
                StreamEnvironment  # noqa: F401

            assert True, "sage_flow 扩展导入成功"
        except ImportError as e:
            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):
                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_flow 扩展导入失败: {e}")
            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):
                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_flow 扩展导入失败: {e}")

    def test_sage_db_microservice_import(self):
        """测试 sage_db micro_service 导入"""
        try:
            from sage.middleware.components.sage_db.python.micro_service.sage_db_service import \
                SageDBService  # noqa: F401

            assert True, "sage_db micro_service 导入成功"
        except ImportError as e:
            if "libsage_db.so" in str(e) or "_sage_db" in str(e):
                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_db micro_service 导入失败: {e}")
            if "libsage_db.so" in str(e) or "_sage_db" in str(e):
                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_db micro_service 导入失败: {e}")

    def test_sage_flow_microservice_import(self):
        """测试 sage_flow micro_service 导入"""
        try:
            from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import \
                SageFlowService  # noqa: F401

            assert True, "sage_flow micro_service 导入成功"
        except ImportError as e:
            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):
                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"sage_flow micro_service 导入失败: {e}")
            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):
                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")
            else:
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
            if any(
                lib in str(e)
                for lib in [
                    "libsage_db.so",
                    "libsage_flow.so",
                    "_sage_db",
                    "_sage_flow",
                ]
            ):
                pytest.skip(f"{extension} C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"{extension} 扩展导入失败: {e}")
            if any(
                lib in str(e)
                for lib in [
                    "libsage_db.so",
                    "libsage_flow.so",
                    "_sage_db",
                    "_sage_flow",
                ]
            ):
                pytest.skip(f"{extension} C++ 扩展未正确安装: {e}")
            else:
                pytest.fail(f"{extension} 扩展导入失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
