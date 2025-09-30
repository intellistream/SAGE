#!/usr/bin/env python3#!/usr/bin/env python3

# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-

""""""

SAGE C++ Extensions 测试的 pytest 集成SAGE C++ Extensions 测试的 pytest 集成

测试 C++ 扩展的安装、导入和示例程序运行测试 C++ 扩展的安装、导入和示例程序运行

""""""



import subprocessimport subprocess

import sysimport sys

from pathlib import Pathfrom pathlib import Path



import pytestimport pytest



# 添加项目路径# 添加项目路径

current_dir = Path(__file__).parentcurrent_dir = Path(__file__).parent

sage_root = current_dir.parent.parentsage_root = current_dir.parent.parent

sys.path.insert(0, str(sage_root / "packages" / "sage-tools" / "src"))sys.path.insert(0, str(sage_root / "packages" / "sage-tools" / "src"))





class TestCppExtensions:class TestCppExtensions:

    """C++ 扩展测试集成到 pytest"""    """C++ 扩展测试集成到 pytest"""



    # 扩展安装超时时间（秒）    # 扩展安装超时时间（秒）

    EXTENSION_INSTALL_TIMEOUT = 600  # 10分钟    EXTENSION_INSTALL_TIMEOUT = 600  # 10分钟



    @classmethod    @classmethod

    def setup_class(cls):    def setup_class(cls):

        """在测试类开始前检查并安装必要的扩展"""        """在测试类开始前检查并安装必要的扩展"""

        cls._ensure_extensions_installed()        cls._ensure_extensions_installed()



    @classmethod    @classmethod

    def _check_extension_status(cls):    def _check_extension_status(cls):

        """检查扩展安装状态        """检查扩展安装状态



        Returns:        Returns:

            tuple: (success: bool, result: subprocess.CompletedProcess)            tuple: (success: bool, result: subprocess.CompletedProcess)

        """        """

        try:        try:

            result = subprocess.run(            result = subprocess.run(

                [sys.executable, "-m", "sage.tools.cli", "extensions", "status"],                [sys.executable, "-m", "sage.tools.cli", "extensions", "status"],

                capture_output=True,                capture_output=True,

                text=True,                text=True,

                cwd=str(sage_root),                cwd=str(sage_root),

            )            )



            # 如果状态检查失败或者输出中包含缺失扩展的标识            # 如果状态检查失败或者输出中包含缺失扩展的标识

            success = result.returncode == 0 and "✗" not in result.stdout            success = result.returncode == 0 and "✗" not in result.stdout

            return success, result            return success, result



        except Exception as e:        except Exception as e:

            return False, None            return False, None



    @classmethod    @classmethod

    def _ensure_extensions_installed(cls):    def _ensure_extensions_installed(cls):

        """检查扩展状态，如果未安装则自动安装"""        """检查扩展状态，如果未安装则自动安装"""

        try:        try:

            # 检查扩展状态            # 检查扩展状态

            success, result = cls._check_extension_status()            success, result = cls._check_extension_status()



            if not success:            if not success:

                print("\n🔧 检测到扩展未完全安装，正在自动安装...")                print("\n🔧 检测到扩展未完全安装，正在自动安装...")

                print("ℹ️ 这可能需要几分钟时间，请耐心等待...\n")                print("ℹ️ 这可能需要几分钟时间，请耐心等待...\n")



                # 自动安装所有扩展，增加超时时间                # 自动安装所有扩展，增加超时时间

                install_result = subprocess.run(                install_result = subprocess.run(

                    [                    [

                        sys.executable,                        sys.executable,

                        "-m",                        "-m",

                        "sage.tools.cli",                        "sage.tools.cli",

                        "extensions",                        "extensions",

                        "install",                        "install",

                        "all",                        "all",

                    ],                    ],

                    cwd=str(sage_root),                    cwd=str(sage_root),

                    timeout=cls.EXTENSION_INSTALL_TIMEOUT,                    timeout=cls.EXTENSION_INSTALL_TIMEOUT,

                    text=True,                    text=True,

                    # 不捕获输出，让用户看到安装进度                    # 不捕获输出，让用户看到安装进度

                )                )



                if install_result.returncode != 0:                if install_result.returncode != 0:

                    pytest.skip("❌ 扩展安装失败，请手动运行: sage extensions install")                    pytest.skip("❌ 扩展安装失败，请手动运行: sage extensions install")

                else:                else:

                    print("✅ 扩展安装完成\n")                    print("✅ 扩展安装完成\n")

                    # 再次检查状态确认安装成功                    # 再次检查状态确认安装成功

                    cls._verify_extensions_installed()                    cls._verify_extensions_installed()



        except subprocess.TimeoutExpired:        except subprocess.TimeoutExpired:

            pytest.skip("⚠️ 扩展安装超时，请手动运行: sage extensions install")            pytest.skip("⚠️ 扩展安装超时，请手动运行: sage extensions install")

        except Exception as e:        except Exception as e:

            pytest.skip(f"⚠️ 检查/安装扩展时出错: {e}")            pytest.skip(f"⚠️ 检查/安装扩展时出错: {e}")



    @classmethod    @classmethod

    def _verify_extensions_installed(cls):    def _verify_extensions_installed(cls):

        """验证扩展安装状态"""        """验证扩展安装状态"""

        try:        try:

            success, result = cls._check_extension_status()            success, result = cls._check_extension_status()



            if not success:            if not success:

                pytest.skip("❌ 扩展安装验证失败，请手动检查")                pytest.skip("❌ 扩展安装验证失败，请手动检查")

            else:            else:

                print("✅ 扩展安装验证成功")                print("✅ 扩展安装验证成功")



        except Exception as e:        except Exception as e:

            pytest.skip(f"⚠️ 验证扩展状态时出错: {e}")            pytest.skip(f"⚠️ 验证扩展状态时出错: {e}")



    def test_sage_db_import(self):    def test_sage_db_import(self):

        """测试 sage_db 扩展导入"""        """测试 sage_db 扩展导入"""

        try:        try:

            from sage.middleware.components.sage_db.python.sage_db import (  # noqa: F401            from sage.middleware.components.sage_db.python.sage_db import (  # noqa: F401

                SageDB,                SageDB,

            )            )



            assert True, "sage_db 扩展导入成功"            assert True, "sage_db 扩展导入成功"

        except ImportError as e:        except ImportError as e:

            if "libsage_db.so" in str(e):            if "libsage_db.so" in str(e):

                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")

            else:            else:

                pytest.fail(f"sage_db 扩展导入失败: {e}")                pytest.fail(f"sage_db 扩展导入失败: {e}")



    def test_sage_flow_import(self):    def test_sage_flow_import(self):

        """测试 sage_flow 扩展导入"""        """测试 sage_flow 扩展导入"""

        try:        try:

            from sage.middleware.components.sage_flow.python.sage_flow import (  # noqa: F401            from sage.middleware.components.sage_flow.python.sage_flow import (  # noqa: F401

                StreamEnvironment,                StreamEnvironment,

            )            )



            assert True, "sage_flow 扩展导入成功"            assert True, "sage_flow 扩展导入成功"

        except ImportError as e:        except ImportError as e:

            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):

                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")

            else:            else:

                pytest.fail(f"sage_flow 扩展导入失败: {e}")                pytest.fail(f"sage_flow 扩展导入失败: {e}")

<<<<<<< HEAD

    def test_sage_db_microservice_import(self):            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):

        """测试 sage_db micro_service 导入"""                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")

        try:            else:

            from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (  # noqa: F401                pytest.fail(f"sage_flow 扩展导入失败: {e}")

                SageDBService,=======

            )>>>>>>> main-dev



            assert True, "sage_db micro_service 导入成功"    def test_sage_db_microservice_import(self):

        except ImportError as e:        """测试 sage_db micro_service 导入"""

            if "libsage_db.so" in str(e) or "_sage_db" in str(e):        try:

                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")            from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (  # noqa: F401

            else:                SageDBService,

                pytest.fail(f"sage_db micro_service 导入失败: {e}")            )



    def test_sage_flow_microservice_import(self):            assert True, "sage_db micro_service 导入成功"

        """测试 sage_flow micro_service 导入"""        except ImportError as e:

        try:            if "libsage_db.so" in str(e) or "_sage_db" in str(e):

            from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import (  # noqa: F401                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")

                SageFlowService,            else:

            )                pytest.fail(f"sage_db micro_service 导入失败: {e}")

<<<<<<< HEAD

            assert True, "sage_flow micro_service 导入成功"            if "libsage_db.so" in str(e) or "_sage_db" in str(e):

        except ImportError as e:                pytest.skip(f"sage_db C++ 扩展未正确安装: {e}")

            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):            else:

                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")                pytest.fail(f"sage_db micro_service 导入失败: {e}")

            else:=======

                pytest.fail(f"sage_flow micro_service 导入失败: {e}")>>>>>>> main-dev



    @pytest.mark.example    def test_sage_flow_microservice_import(self):

    def test_sage_db_example(self):        """测试 sage_flow micro_service 导入"""

        """测试 sage_db 示例程序"""        try:

        example_path = (            from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import (  # noqa: F401

            sage_root / "examples" / "service" / "sage_db" / "hello_sage_db_app.py"                SageFlowService,

        )            )



        if not example_path.exists():            assert True, "sage_flow micro_service 导入成功"

            pytest.skip(f"示例文件不存在: {example_path}")        except ImportError as e:

            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):

        try:                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")

            result = subprocess.run(            else:

                [sys.executable, str(example_path)],                pytest.fail(f"sage_flow micro_service 导入失败: {e}")

                capture_output=True,<<<<<<< HEAD

                text=True,            if "libsage_flow.so" in str(e) or "_sage_flow" in str(e):

                timeout=30,                pytest.skip(f"sage_flow C++ 扩展未正确安装: {e}")

                cwd=str(sage_root),            else:

            )                pytest.fail(f"sage_flow micro_service 导入失败: {e}")

=======

            assert result.returncode == 0, f"sage_db 示例运行失败: {result.stderr}">>>>>>> main-dev



        except subprocess.TimeoutExpired:    @pytest.mark.example

            pytest.fail("sage_db 示例运行超时")    def test_sage_db_example(self):

        except Exception as e:        """测试 sage_db 示例程序"""

            pytest.fail(f"sage_db 示例运行异常: {e}")        example_path = (

            sage_root / "examples" / "service" / "sage_db" / "hello_sage_db_app.py"

    @pytest.mark.example        )

    def test_sage_flow_example(self):

        """测试 sage_flow 示例程序"""        if not example_path.exists():

        example_path = (            pytest.skip(f"示例文件不存在: {example_path}")

            sage_root / "examples" / "service" / "sage_flow" / "hello_sage_flow_app.py"

        )        try:

            result = subprocess.run(

        if not example_path.exists():                [sys.executable, str(example_path)],

            pytest.skip(f"示例文件不存在: {example_path}")                capture_output=True,

                text=True,

        try:                timeout=30,

            result = subprocess.run(                cwd=str(sage_root),

                [sys.executable, str(example_path)],            )

                capture_output=True,

                text=True,            assert result.returncode == 0, f"sage_db 示例运行失败: {result.stderr}"

                timeout=30,

                cwd=str(sage_root),        except subprocess.TimeoutExpired:

            )            pytest.fail("sage_db 示例运行超时")

        except Exception as e:

            assert result.returncode == 0, f"sage_flow 示例运行失败: {result.stderr}"            pytest.fail(f"sage_db 示例运行异常: {e}")



        except subprocess.TimeoutExpired:    @pytest.mark.example

            pytest.fail("sage_flow 示例运行超时")    def test_sage_flow_example(self):

        except Exception as e:        """测试 sage_flow 示例程序"""

            pytest.fail(f"sage_flow 示例运行异常: {e}")        example_path = (

            sage_root / "examples" / "service" / "sage_flow" / "hello_sage_flow_app.py"

    @pytest.mark.parametrize(        )

        "extension,import_statement",

        [        if not example_path.exists():

            (            pytest.skip(f"示例文件不存在: {example_path}")

                "sage_db",

                "from sage.middleware.components.sage_db.python.sage_db import SageDB",        try:

            ),            result = subprocess.run(

            (                [sys.executable, str(example_path)],

                "sage_flow",                capture_output=True,

                "from sage.middleware.components.sage_flow.python.sage_flow import StreamEnvironment",                text=True,

            ),                timeout=30,

            (                cwd=str(sage_root),

                "sage_db_service",            )

                "from sage.middleware.components.sage_db.python.micro_service.sage_db_service import SageDBService",

            ),            assert result.returncode == 0, f"sage_flow 示例运行失败: {result.stderr}"

            (

                "sage_flow_service",        except subprocess.TimeoutExpired:

                "from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import SageFlowService",            pytest.fail("sage_flow 示例运行超时")

            ),        except Exception as e:

        ],            pytest.fail(f"sage_flow 示例运行异常: {e}")

    )

    def test_extension_imports_parametrized(self, extension, import_statement):    @pytest.mark.parametrize(

        """参数化测试扩展导入"""        "extension,import_statement",

        try:        [

            exec(import_statement)            (

        except ImportError as e:                "sage_db",

            if any(                "from sage.middleware.components.sage_db.python.sage_db import SageDB",

                lib in str(e)            ),

                for lib in [            (

                    "libsage_db.so",                "sage_flow",

                    "libsage_flow.so",                "from sage.middleware.components.sage_flow.python.sage_flow import StreamEnvironment",

                    "_sage_db",            ),

                    "_sage_flow",            (

                ]                "sage_db_service",

            ):                "from sage.middleware.components.sage_db.python.micro_service.sage_db_service import SageDBService",

                pytest.skip(f"{extension} C++ 扩展未正确安装: {e}")            ),

            else:            (

                pytest.fail(f"{extension} 扩展导入失败: {e}")                "sage_flow_service",

                "from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import SageFlowService",

            ),

if __name__ == "__main__":        ],

    # 运行测试    )

    pytest.main([__file__, "-v"])    def test_extension_imports_parametrized(self, extension, import_statement):
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
<<<<<<< HEAD
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
=======
>>>>>>> main-dev


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
