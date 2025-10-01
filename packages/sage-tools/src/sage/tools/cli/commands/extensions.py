#!/usr/bin/env python3
"""
SAGE Extensions Manager
======================

管理SAGE框架的C++扩展安装和检查
"""

import os
import shutil
import subprocess
import sysconfig
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer

app = typer.Typer(name="extensions", help="🧩 扩展管理 - 安装和管理C++扩展")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    🧩 SAGE 扩展管理系统

    管理SAGE框架的C++扩展安装和检查
    """
    if ctx.invoked_subcommand is None:
        # 如果没有子命令，显示帮助信息
        typer.echo(f"{Colors.BOLD}{Colors.BLUE}🧩 SAGE 扩展管理{Colors.RESET}")
        typer.echo("=" * 40)
        typer.echo()
        typer.echo("可用命令:")
        typer.echo("  install   - 安装C++扩展")
        typer.echo("  status    - 检查扩展状态")
        typer.echo("  clean     - 清理构建文件")
        typer.echo("  info      - 显示扩展信息")
        typer.echo()
        typer.echo("使用 'sage extensions COMMAND --help' 查看具体命令的帮助")


class Colors:
    """终端颜色"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_info(msg: str):
    typer.echo(f"{Colors.BLUE}ℹ️ {msg}{Colors.RESET}")


def print_success(msg: str):
    typer.echo(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg: str):
    typer.echo(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_warning(msg: str):
    typer.echo(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")


def run_command(cmd, check=True, capture_output=True):
    """运行命令"""
    print_info(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            check=check,
            capture_output=capture_output,
            text=True,
        )
        # 如果不捕获输出但仍想返回结果，创建一个简单的结果对象
        if not capture_output:

            class SimpleResult:
                def __init__(self, returncode):
                    self.returncode = returncode
                    self.stdout = ""
                    self.stderr = ""

            result = SimpleResult(
                result.returncode if hasattr(result, "returncode") else 0
            )
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        if capture_output:
            if e.stdout:
                typer.echo(f"STDOUT: {e.stdout}")
            if e.stderr:
                typer.echo(f"STDERR: {e.stderr}")
        raise


def check_build_tools() -> bool:
    """检查构建工具"""
    print_info("检查构建工具...")
    tools_available = True

    # 检查 gcc/g++
    try:
        result = run_command(["gcc", "--version"], check=False)
        if result.returncode == 0:
            print_success("gcc 可用 ✓")
        else:
            print_warning("gcc 不可用")
            tools_available = False
    except Exception:
        print_warning("gcc 不可用")
        tools_available = False

    # 检查 cmake
    try:
        result = run_command(["cmake", "--version"], check=False)
        if result.returncode == 0:
            print_success("cmake 可用 ✓")
        else:
            print_warning("cmake 不可用")
            tools_available = False
    except Exception:
        print_warning("cmake 不可用")
        tools_available = False

    return tools_available


def find_sage_root() -> Optional[Path]:
    """查找SAGE项目根目录"""
    current = Path.cwd()

    # 向上查找包含packages目录的SAGE项目根目录
    for parent in [current] + list(current.parents):
        packages_dir = parent / "packages"
        # 检查是否包含SAGE项目的典型结构
        if packages_dir.exists() and packages_dir.is_dir():
            sage_middleware_dir = packages_dir / "sage-middleware"
            sage_common_dir = packages_dir / "sage-common"
            if sage_middleware_dir.exists() and sage_common_dir.exists():
                return parent

    # 检查当前Python环境中的sage包位置
    try:
        import sage

        sage_path = Path(sage.__file__).parent.parent
        # 如果从安装的包中找到，尝试找到项目根目录
        for parent in sage_path.parents:
            packages_dir = parent / "packages"
            if packages_dir.exists():
                sage_middleware_dir = packages_dir / "sage-middleware"
                if sage_middleware_dir.exists():
                    return parent
    except ImportError:
        pass

    return None


EXTENSION_PATHS: Dict[str, str] = {
    "sage_db": "packages/sage-middleware/src/sage/middleware/components/sage_db",
    "sage_flow": "packages/sage-middleware/src/sage/middleware/components/sage_flow",
}


def _resolve_extensions_to_install(extension: Optional[str]) -> List[str]:
    if extension is None or extension == "all":
        return list(EXTENSION_PATHS.keys())
    if extension not in EXTENSION_PATHS:
        print_error(f"未知扩展: {extension}")
        typer.echo(f"可用扩展: {', '.join(EXTENSION_PATHS.keys())}")
        raise typer.Exit(1)
    return [extension]


def _clean_previous_build(ext_dir: Path) -> None:
    build_dir = ext_dir / "build"
    if build_dir.exists():
        print_info(f"清理构建目录: {build_dir}")
        shutil.rmtree(build_dir)


def _run_build_script(ext_dir: Path):
    original_cwd = os.getcwd()
    os.chdir(ext_dir)
    try:
        return run_command(
            ["bash", "build.sh", "--install-deps"],
            check=False,
            capture_output=False,
        )
    finally:
        os.chdir(original_cwd)


def _artifact_pattern_and_site(ext_name: str) -> Tuple[Optional[str], Optional[Path]]:
    if ext_name == "sage_flow":
        return "_sage_flow*.so", Path("sage/middleware/components/sage_flow/python")
    if ext_name == "sage_db":
        return "_sage_db*.so", Path("sage/middleware/components/sage_db/python")
    return None, None


def _copy_python_artifacts(ext_name: str, ext_dir: Path) -> None:
    build_dir = ext_dir / "build"
    pattern, site_rel = _artifact_pattern_and_site(ext_name)

    if pattern is None:
        return

    if not build_dir.exists():
        print_warning(f"未找到构建目录: {build_dir}")
        return

    candidates = list(build_dir.rglob(pattern))
    if not candidates:
        print_warning(f"未找到 {pattern} 构建产物")
        return

    repo_target_dir = ext_dir / "python"
    repo_target_dir.mkdir(parents=True, exist_ok=True)
    for so_file in candidates:
        shutil.copy2(so_file, repo_target_dir / so_file.name)
    print_success(f"已安装 Python 扩展模块到: {repo_target_dir}")

    try:
        platlib = Path(sysconfig.get_paths()["platlib"])
    except Exception as exc:
        print_warning(f"无法复制到 site-packages（可能未安装包）: {exc}")
        return

    if site_rel is None:
        return

    site_target_dir = platlib / site_rel
    site_target_dir.mkdir(parents=True, exist_ok=True)

    for so_file in candidates:
        shutil.copy2(so_file, site_target_dir / so_file.name)

    python_source_dir = ext_dir / "python"
    if python_source_dir.exists():
        for py_file in python_source_dir.rglob("*.py"):
            rel_path = py_file.relative_to(python_source_dir)
            target_py_file = site_target_dir / rel_path
            target_py_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(py_file, target_py_file)

        micro_service_dir = python_source_dir / "micro_service"
        if micro_service_dir.exists():
            target_micro_service = site_target_dir / "micro_service"
            if target_micro_service.exists():
                shutil.rmtree(target_micro_service)
            shutil.copytree(micro_service_dir, target_micro_service)
            print_success(
                f"已安装 {ext_name} micro_service 模块到 site-packages: {target_micro_service}"
            )

    print_success(f"已安装 Python 扩展模块到 site-packages: {site_target_dir}")


def _is_ci_environment() -> bool:
    return bool(
        os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("GITLAB_CI")
    )


def _print_ci_failure_report(ext_dir: Path) -> None:
    if not _is_ci_environment():
        return

    typer.echo(
        f"\n{Colors.RED}==================== CI环境构建失败详细诊断 ===================={Colors.RESET}"
    )

    build_dir = ext_dir / "build"
    if build_dir.exists():
        typer.echo(f"{Colors.YELLOW}📁 构建目录内容:{Colors.RESET}")
        try:
            for item in build_dir.rglob("*"):
                if item.is_file() and item.name.endswith((".log", ".txt")):
                    typer.echo(f"   📄 {item.relative_to(build_dir)}")
        except Exception:
            pass

        cmake_error_log = build_dir / "CMakeFiles" / "CMakeError.log"
        if cmake_error_log.exists():
            typer.echo(f"\n{Colors.YELLOW}📋 CMake错误日志 (最后20行):{Colors.RESET}")
            try:
                lines = cmake_error_log.read_text(encoding="utf-8").splitlines()
                for line in lines[-20:]:
                    typer.echo(f"   {line}")
            except Exception as exc:
                typer.echo(f"   无法读取CMake错误日志: {exc}")

        cmake_output_log = build_dir / "CMakeFiles" / "CMakeOutput.log"
        if cmake_output_log.exists():
            typer.echo(f"\n{Colors.YELLOW}📋 CMake输出日志 (最后10行):{Colors.RESET}")
            try:
                lines = cmake_output_log.read_text(encoding="utf-8").splitlines()
                for line in lines[-10:]:
                    typer.echo(f"   {line}")
            except Exception as exc:
                typer.echo(f"   无法读取CMake输出日志: {exc}")

        make_output = build_dir / "make_output.log"
        if make_output.exists():
            typer.echo(f"\n{Colors.YELLOW}🔨 Make输出日志 (最后30行):{Colors.RESET}")
            try:
                lines = make_output.read_text(encoding="utf-8").splitlines()
                for line in lines[-30:]:
                    typer.echo(f"   {line}")
            except Exception as exc:
                typer.echo(f"   无法读取Make输出日志: {exc}")

    typer.echo(
        f"{Colors.RED}================================================================{Colors.RESET}"
    )


def _print_manual_diagnostics(ext_dir: Path) -> None:
    print_warning("🔍 构建诊断信息:")

    build_dir = ext_dir / "build"
    if build_dir.exists():
        cmake_cache = build_dir / "CMakeCache.txt"
        if cmake_cache.exists():
            typer.echo(f"📋 CMake 缓存文件存在: {cmake_cache}")
            try:
                content = cmake_cache.read_text(encoding="utf-8")
                for key in ["BLAS_FOUND", "LAPACK_FOUND", "FAISS_FOUND"]:
                    for line in content.splitlines():
                        if key in line and not line.startswith("//"):
                            value = line.split("=")[-1] if "=" in line else "unknown"
                            typer.echo(f"   {key}: {value}")
                            break
            except Exception:
                pass

    typer.echo("\n💡 故障排除建议:")
    typer.echo(
        "   1. 检查系统依赖: ./tools/install/install_system_deps.sh --verify-only"
    )
    typer.echo(f"   2. 手动构建: cd {ext_dir} && bash build.sh --clean --install-deps")
    typer.echo(
        f"   3. 查看构建日志: {(ext_dir / 'build' / 'CMakeFiles' / 'CMakeError.log')}"
    )


def _diagnose_build_failure(ext_name: str, ext_dir: Path, result) -> None:
    print_error(f"{ext_name} 构建失败")
    stderr = getattr(result, "stderr", None)
    if stderr:
        typer.echo(f"错误信息: {stderr}")

    _print_ci_failure_report(ext_dir)
    _print_manual_diagnostics(ext_dir)


def _install_extension(ext_name: str, ext_dir: Path, force: bool) -> bool:
    typer.echo(f"\n{Colors.YELLOW}━━━ 安装 {ext_name} ━━━{Colors.RESET}")

    if not ext_dir.exists():
        print_warning(f"扩展目录不存在: {ext_dir}")
        return False

    build_script = ext_dir / "build.sh"
    if not build_script.exists():
        print_warning(f"未找到构建脚本: {build_script}")
        return False

    try:
        print_info(f"构建 {ext_name}...")
        if force:
            _clean_previous_build(ext_dir)
        result = _run_build_script(ext_dir)
    except Exception as exc:
        print_error(f"{ext_name} 构建失败: {exc}")
        typer.echo(f"异常详情: {type(exc).__name__}: {exc}")
        return False

    if result.returncode != 0:
        _diagnose_build_failure(ext_name, ext_dir, result)
        return False

    print_success(f"{ext_name} 构建成功 ✓")
    try:
        _copy_python_artifacts(ext_name, ext_dir)
    except Exception as exc:
        print_warning(f"复制扩展产物时发生问题: {exc}")
        return False

    return True


def _print_install_summary(success_count: int, total_count: int) -> None:
    typer.echo(f"\n{Colors.BOLD}安装完成{Colors.RESET}")
    typer.echo(f"成功: {success_count}/{total_count}")

    if success_count == total_count:
        print_success("🎉 所有扩展安装成功！")
        typer.echo("\n运行 'sage extensions status' 验证安装")
    else:
        failures = total_count - success_count
        print_warning(f"⚠️ 部分扩展安装失败 ({failures}个)")


@app.command()
def install(
    extension: Optional[str] = typer.Argument(
        None, help="要安装的扩展名 (sage_db, sage_flow, 或 all)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新构建"),
):
    """
    安装C++扩展

    Examples:
        sage extensions install                # 安装所有扩展
        sage extensions install sage_db       # 只安装数据库扩展
        sage extensions install all --force   # 强制重新安装所有扩展
    """
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🧩 SAGE C++ 扩展安装器{Colors.RESET}")
    typer.echo("=" * 50)

    # 检查构建工具
    if not check_build_tools():
        print_error("缺少必要的构建工具，无法安装C++扩展")
        typer.echo("\n请安装以下工具:")
        typer.echo("  • gcc/g++ (C++ 编译器)")
        typer.echo("  • cmake (构建系统)")
        typer.echo("  • make (构建工具)")
        typer.echo("\nUbuntu/Debian: sudo apt install build-essential cmake")
        typer.echo(
            "CentOS/RHEL: sudo yum groupinstall 'Development Tools' && sudo yum install cmake"
        )
        typer.echo("macOS: xcode-select --install && brew install cmake")
        raise typer.Exit(1)

    # 查找SAGE根目录
    sage_root = find_sage_root()
    if not sage_root:
        print_error("未找到SAGE项目根目录")
        typer.echo("请在SAGE项目目录中运行此命令")
        raise typer.Exit(1)

    print_info(f"SAGE项目根目录: {sage_root}")

    extensions_to_install = _resolve_extensions_to_install(extension)
    success_count = 0
    total_count = len(extensions_to_install)

    for ext_name in extensions_to_install:
        rel_path = EXTENSION_PATHS[ext_name]
        ext_dir = sage_root / rel_path
        if _install_extension(ext_name, ext_dir, force):
            success_count += 1

    _print_install_summary(success_count, total_count)


@app.command()
def status():
    """检查扩展安装状态"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🔍 SAGE 扩展状态检查{Colors.RESET}")
    typer.echo("=" * 40)

    extensions = {
        "sage.middleware.components.sage_db.python._sage_db": "数据库扩展 (C++)",
        "sage.middleware.components.sage_flow.python._sage_flow": "流处理引擎扩展 (C++)",
    }

    available_count = 0

    for module_name, description in extensions.items():
        try:
            __import__(module_name)
            print_success(f"{description} ✓")
            available_count += 1
        except ImportError as e:
            print_warning(f"{description} ✗")
            typer.echo(f"  原因: {e}")

    typer.echo(f"\n总计: {available_count}/{len(extensions)} 扩展可用")

    if available_count < len(extensions):
        typer.echo(f"\n{Colors.YELLOW}💡 提示:{Colors.RESET}")
        typer.echo("运行 'sage extensions install' 安装缺失的扩展")


@app.command()
def clean():
    """清理扩展构建文件"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🧹 清理扩展构建文件{Colors.RESET}")

    sage_root = find_sage_root()
    if not sage_root:
        print_error("未找到SAGE项目根目录")
        raise typer.Exit(1)

    import shutil

    cleaned_count = 0

    # 按真实扩展源码位置进行清理
    mapping = {
        "sage_db": "packages/sage-middleware/src/sage/middleware/components/sage_db",
        "sage_flow": "packages/sage-middleware/src/sage/middleware/components/sage_flow",
    }

    for ext_name, rel_path in mapping.items():
        ext_dir = sage_root / rel_path
        if not ext_dir.exists():
            continue

        # 清理build目录
        build_dir = ext_dir / "build"
        if build_dir.exists():
            print_info(f"清理 {ext_name}/build")
            shutil.rmtree(build_dir)
            cleaned_count += 1

        # 清理编译产物
        for pattern in ["*.so", "*.o", "*.a"]:
            for file in ext_dir.rglob(pattern):
                if file.is_file():
                    print_info(f"删除 {file.relative_to(sage_root)}")
                    file.unlink()

    if cleaned_count > 0:
        print_success(f"清理完成，共处理 {cleaned_count} 个目录")
    else:
        typer.echo("没有需要清理的文件")


@app.command()
def info():
    """显示扩展信息"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}📋 SAGE C++ 扩展信息{Colors.RESET}")
    typer.echo("=" * 50)

    extensions_info = {
        "sage_db": {
            "description": "数据库接口扩展",
            "features": ["原生C++接口", "高性能查询", "内存优化"],
            "status": "experimental",
        },
        "sage_flow": {
            "description": "流处理引擎 Python 绑定",
            "features": ["pybind11 模块", "向量流", "回调 sink"],
            "status": "experimental",
        },
    }

    for ext_name, info in extensions_info.items():
        typer.echo(f"\n{Colors.YELLOW}{ext_name}{Colors.RESET}")
        typer.echo(f"  描述: {info['description']}")
        typer.echo(f"  特性: {', '.join(info['features'])}")
        typer.echo(f"  状态: {info['status']}")

        # 检查是否已安装
        try:
            if ext_name == "sage_db":
                __import__("sage.middleware.components.sage_db.python._sage_db")
            elif ext_name == "sage_flow":
                __import__("sage.middleware.components.sage_flow.python._sage_flow")
            else:
                __import__(f"sage_ext.{ext_name}")
            typer.echo(f"  安装: {Colors.GREEN}✓ 已安装{Colors.RESET}")
        except ImportError:
            typer.echo(f"  安装: {Colors.RED}✗ 未安装{Colors.RESET}")


if __name__ == "__main__":
    app()
