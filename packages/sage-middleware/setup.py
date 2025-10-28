#!/usr/bin/env python3
"""
SAGE Middleware Package Setup with C Extensions
自动编译C++扩展的安装脚本
"""

import os
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install


class BuildCExtensions(build_ext):
    """自定义C扩展编译命令"""

    def run(self):
        """编译C扩展"""
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") == "1":
            print("⏭️ 跳过C扩展编译（SAGE_SKIP_C_EXTENSIONS=1）")
        else:
            # 在所有模式下尝试构建需要的扩展，失败不阻断安装
            self.build_sage_db()
            self.build_sage_flow()
        super().run()

    def _shared_env(self):
        env = os.environ.copy()
        shared_deps = (
            Path(__file__).parent
            / "src"
            / "sage"
            / "middleware"
            / "components"
            / "cmake"
            / "sage_shared_dependencies.cmake"
        )
        if shared_deps.exists() and "SAGE_COMMON_DEPS_FILE" not in env:
            env["SAGE_COMMON_DEPS_FILE"] = str(shared_deps)

        env.setdefault("SAGE_PYBIND11_VERSION", "2.13.0")
        env.setdefault("SAGE_ENABLE_GPERFTOOLS", os.environ.get("SAGE_ENABLE_GPERFTOOLS", "0"))
        # SAGE_GPERFTOOLS_ROOT、SAGE_GPERFTOOLS_LIB 直接继承用户环境即可
        return env

    def build_sage_db(self):
        """编译sage_db C扩展"""
        sage_db_dir = Path(__file__).parent / "src/sage/middleware/components/sage_db"

        if not sage_db_dir.exists():
            print("⚠️  sage_db目录不存在，跳过编译")
            return

        # Check if submodule is initialized
        submodule_dir = sage_db_dir / "sageDB"
        if submodule_dir.exists() and not any(submodule_dir.iterdir()):
            print("⚠️  sage_db 子模块目录为空（未初始化），跳过编译")
            print("   💡 提示: 运行 'git submodule update --init --recursive' 初始化子模块")
            return

        build_script = sage_db_dir / "build.sh"
        if not build_script.exists():
            print("⚠️  build.sh不存在，跳过C扩展编译")
            return

        print("🔧 编译sage_db C扩展...")
        try:
            # 切换到sage_db目录并运行build.sh
            result = subprocess.run(
                ["bash", "build.sh"],
                cwd=sage_db_dir,
                env=self._shared_env(),
                check=True,
                capture_output=True,
                text=True,
            )
            print("✅ sage_db C扩展编译成功")
            # Only print first 50 lines to avoid log spam
            stdout_lines = result.stdout.split("\n")
            if len(stdout_lines) > 50:
                print("\n".join(stdout_lines[:25]))
                print(f"... ({len(stdout_lines) - 50} lines omitted) ...")
                print("\n".join(stdout_lines[-25:]))
            else:
                print(result.stdout)

            # 验证 .so 文件是否生成
            python_dir = sage_db_dir / "python"
            so_files = list(python_dir.glob("_sage_db*.so"))
            if so_files:
                print(f"✅ 找到生成的扩展文件: {so_files[0].name}")
            else:
                print("⚠️  警告: 未找到生成的 .so 文件，但构建脚本成功返回")
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_db C扩展编译失败: {e}")
            print(f"📋 标准输出:\n{e.stdout}")
            print(f"📋 错误输出:\n{e.stderr}")
            # C扩展编译失败不应该阻止安装
            print("⚠️  继续安装Python部分（C扩展将不可用）")
        except Exception as e:
            print(f"❌ 编译过程出错: {e}")
            print("⚠️  继续安装Python部分（C扩展将不可用）")

    def build_sage_flow(self):
        """编译 sage_flow 组件（可能包含C/C++/Python扩展）"""
        sage_flow_dir = Path(__file__).parent / "src/sage/middleware/components/sage_flow"

        if not sage_flow_dir.exists():
            print("⚠️  sage_flow 目录不存在，跳过构建")
            return

        # 如果是子模块但未初始化，目录可能为空
        try:
            if not any(sage_flow_dir.iterdir()):
                print("ℹ️ 检测到 sage_flow 目录为空，可能是未初始化的子模块，跳过构建")
                return
        except Exception:
            # 目录不可读，直接跳过
            return

        # Check if submodule is initialized
        submodule_dir = sage_flow_dir / "sageFlow"
        if submodule_dir.exists() and not any(submodule_dir.iterdir()):
            print("⚠️  sage_flow 子模块目录为空（未初始化），跳过编译")
            print("   💡 提示: 运行 'git submodule update --init --recursive' 初始化子模块")
            return

        build_script = sage_flow_dir / "build.sh"
        if not build_script.exists():
            print("ℹ️ 未找到 sage_flow/build.sh，可能不需要本地构建，跳过")
            return

        print("🔧 编译 sage_flow 组件...")
        try:
            result = subprocess.run(
                ["bash", "build.sh"],
                cwd=sage_flow_dir,
                env=self._shared_env(),
                check=True,
                capture_output=True,
                text=True,
            )
            print("✅ sage_flow 构建成功")
            # Only print first 50 lines to avoid log spam
            stdout_lines = result.stdout.split("\n")
            if len(stdout_lines) > 50:
                print("\n".join(stdout_lines[:25]))
                print(f"... ({len(stdout_lines) - 50} lines omitted) ...")
                print("\n".join(stdout_lines[-25:]))
            else:
                print(result.stdout)

            # 验证 .so 文件是否生成
            python_dir = sage_flow_dir / "python"
            so_files = list(python_dir.glob("_sage_flow*.so"))
            if so_files:
                print(f"✅ 找到生成的扩展文件: {so_files[0].name}")
            else:
                print("⚠️  警告: 未找到生成的 .so 文件，但构建脚本成功返回")
                # 列出 python/ 目录内容以供调试
                if python_dir.exists():
                    files = list(python_dir.iterdir())
                    print(f"   python/ 目录内容 ({len(files)} 个文件):")
                    for f in files[:10]:  # 只显示前10个
                        print(f"   - {f.name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ sage_flow 构建失败: {e}")
            print(f"📋 标准输出:\n{e.stdout}")
            print(f"📋 错误输出:\n{e.stderr}")
            print("⚠️  继续安装Python部分（sage_flow 相关示例可能不可用）")
        except Exception as e:
            print(f"❌ 构建过程出错: {e}")
            print("⚠️  继续安装Python部分（sage_flow 相关示例可能不可用）")


class CustomInstall(install):
    """自定义安装命令"""

    def run(self):
        # 在生产安装模式下编译C扩展
        print("🔧 生产安装模式：编译C扩展...")
        self.run_command("build_ext")
        # 然后安装
        super().run()


class CustomDevelop(develop):
    """自定义开发安装命令"""

    def run(self):
        # 开发模式下默认也尝试构建C扩展（与生产一致），可通过环境变量关闭
        if os.environ.get("SAGE_SKIP_C_EXTENSIONS") == "1":
            print("⏭️ 开发模式：跳过C扩展编译（SAGE_SKIP_C_EXTENSIONS=1）")
        else:
            print("🔧 开发模式：编译C扩展（可通过 SAGE_SKIP_C_EXTENSIONS=1 跳过）")
            self.run_command("build_ext")
        super().run()


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_ext": BuildCExtensions,
            "install": CustomInstall,
            "develop": CustomDevelop,
        },
    )
