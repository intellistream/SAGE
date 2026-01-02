#!/usr/bin/env python3
"""
SAGE Extensions Manager
======================

管理SAGE框架的C++扩展安装和检查
"""

import os
import shutil
import site
import subprocess
import sysconfig
from pathlib import Path

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
    DIM = "\033[2m"
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

            result = SimpleResult(result.returncode if hasattr(result, "returncode") else 0)
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


def find_sage_root() -> Path | None:
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


EXTENSION_PATHS: dict[str, str] = {
    "sage_db": "packages/sage-middleware/src/sage/middleware/components/sage_db",
    "sage_flow": "packages/sage-middleware/src/sage/middleware/components/sage_flow",
    "sage_tsdb": "packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB",
}

EXTENSION_MODULES: dict[str, str] = {
    "sage_db": "sage.middleware.components.sage_db.python._sage_db",
    "sage_flow": "sage.middleware.components.sage_flow.python._sage_flow",
    "sage_tsdb": "sage.middleware.components.sage_tsdb.python._sage_tsdb",
}


def _extension_is_available(ext_name: str, timeout: float = 3.0) -> bool:
    module_name = EXTENSION_MODULES.get(ext_name)
    if not module_name:
        return False

    import queue
    import threading

    result_queue: queue.Queue[bool] = queue.Queue()

    def _try_import():
        try:
            __import__(module_name)
            result_queue.put(True)
        except Exception:
            result_queue.put(False)

    import_thread = threading.Thread(target=_try_import, daemon=True)
    import_thread.start()
    import_thread.join(timeout=timeout)

    if import_thread.is_alive():
        return False

    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return False


def _resolve_extensions_to_install(extension: str | None) -> list[str]:
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


def _run_build_script(ext_dir: Path, ext_name: str, sage_root: Path):
    """运行构建脚本并将输出重定向到日志文件"""
    import subprocess
    import threading
    import time

    original_cwd = os.getcwd()
    os.chdir(ext_dir)
    try:
        # 将日志放在.sage目录下
        log_dir = sage_root / ".sage" / "logs" / "extensions"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{ext_name}_build.log"

        typer.echo(f"{Colors.DIM}   构建日志: {log_file}{Colors.RESET}")
        typer.echo(f"{Colors.DIM}   实时查看: tail -f {log_file}{Colors.RESET}\n")

        # 添加进度指示
        # 进度显示状态
        progress_state = {"running": True, "last_update": time.time()}

        def show_progress():
            """显示构建进度动画"""
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            idx = 0
            start_time = time.time()

            while progress_state["running"]:
                elapsed = int(time.time() - start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60

                # 显示进度动画和时间
                spinner = spinner_chars[idx % len(spinner_chars)]
                typer.echo(
                    f"\r{Colors.BLUE}{spinner}{Colors.RESET} 正在构建 {ext_name}... "
                    f"[{minutes:02d}:{seconds:02d}]  "
                    f"{Colors.DIM}(构建可能需要几分钟){Colors.RESET}",
                    nl=False,
                )

                idx += 1
                time.sleep(0.1)

            # 清除进度行
            typer.echo("\r" + " " * 80 + "\r", nl=False)

        # 启动进度显示线程
        progress_thread = threading.Thread(target=show_progress, daemon=True)
        progress_thread.start()

        try:
            with open(log_file, "w") as f:
                result = subprocess.run(
                    ["bash", "build.sh", "--install-deps"],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
        finally:
            # 停止进度显示
            progress_state["running"] = False
            # 等待线程结束，但不要无限等待
            if progress_thread.is_alive():
                progress_thread.join(timeout=2.0)
            typer.echo()  # 换行

            # 确保输出被刷新
            import sys

            sys.stdout.flush()
            sys.stderr.flush()

        # 如果构建失败，显示最后几行日志
        if result.returncode != 0:
            typer.echo(f"\n{Colors.YELLOW}构建失败，最后50行日志:{Colors.RESET}")
            try:
                with open(log_file) as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        typer.echo(f"  {line.rstrip()}")
            except Exception:
                pass

        return result
    finally:
        os.chdir(original_cwd)


def _artifact_pattern_and_site(ext_name: str) -> tuple[str | None, Path | None]:
    if ext_name == "sage_flow":
        return "_sage_flow*.so", Path("sage/middleware/components/sage_flow/python")
    if ext_name == "sage_db":
        return "_sage_db*.so", Path("sage/middleware/components/sage_db/python")
    if ext_name == "sage_tsdb":
        return "_sage_tsdb*.so", Path("sage/middleware/components/sage_tsdb/python")
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

    # 始终复制到仓库的 python 目录（这个总是有权限的）
    repo_target_dir = ext_dir / "python"
    repo_target_dir.mkdir(parents=True, exist_ok=True)
    for so_file in candidates:
        shutil.copy2(so_file, repo_target_dir / so_file.name)
    print_success(f"已安装 Python 扩展模块到: {repo_target_dir}")

    # 尝试复制到 site-packages（可能没有权限，但不是必需的）
    try:
        # 在CI环境中使用用户site-packages（匹配pip install --user的行为）
        if _is_ci_environment():
            platlib = Path(site.USER_SITE) if site.USER_SITE else Path.cwd() / ".local"
        else:
            platlib = Path(sysconfig.get_paths()["platlib"])
    except Exception as exc:
        print_warning(f"无法获取 site-packages 路径: {exc}")
        return

    if site_rel is None:
        return

    site_target_dir = platlib / site_rel

    # 检查是否有写权限
    try:
        site_target_dir.mkdir(parents=True, exist_ok=True)
        # 测试写权限
        test_file = site_target_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as exc:
        print_warning(
            f"没有写入 site-packages 的权限，跳过: {site_target_dir}\n"
            f"  原因: {exc}\n"
            f"  扩展已安装到项目目录: {repo_target_dir}"
        )
        return

    try:
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
    except (PermissionError, OSError) as exc:
        print_warning(
            f"复制到 site-packages 时权限不足: {exc}\n  扩展已安装到项目目录: {repo_target_dir}"
        )


def _is_ci_environment() -> bool:
    return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("GITLAB_CI"))


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
    typer.echo("   1. 检查系统依赖: ./tools/install/core/install_system_deps.sh --verify-only")
    typer.echo(f"   2. 手动构建: cd {ext_dir} && bash build.sh --clean --install-deps")
    typer.echo(f"   3. 查看构建日志: {(ext_dir / 'build' / 'CMakeFiles' / 'CMakeError.log')}")


def _diagnose_build_failure(ext_name: str, ext_dir: Path, result) -> None:
    print_error(f"{ext_name} 构建失败")
    stderr = getattr(result, "stderr", None)
    if stderr:
        typer.echo(f"错误信息: {stderr}")

    _print_ci_failure_report(ext_dir)
    _print_manual_diagnostics(ext_dir)


def _install_extension(ext_name: str, ext_dir: Path, sage_root: Path, force: bool) -> bool:
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
        result = _run_build_script(ext_dir, ext_name, sage_root)
    except Exception as exc:
        print_error(f"{ext_name} 构建失败: {exc}")
        typer.echo(f"异常详情: {type(exc).__name__}: {exc}")
        return False

    if result.returncode != 0:
        _diagnose_build_failure(ext_name, ext_dir, result)
        return False

    print_success(f"{ext_name} 构建成功 ✓")

    # 复制产物（权限错误不应导致失败，因为已经复制到项目目录）
    try:
        _copy_python_artifacts(ext_name, ext_dir)
    except Exception as exc:
        # 如果是权限错误，只是警告，不视为失败
        if isinstance(exc, (PermissionError, OSError)):
            print_warning(f"复制扩展产物到 site-packages 时权限不足（已安装到项目目录）: {exc}")
        else:
            print_warning(f"复制扩展产物时发生问题: {exc}")
            # 对于其他错误，仍然视为失败
            if not _is_ci_environment():
                return False

    return True


def _print_install_summary(success_count: int, total_count: int) -> None:
    import sys

    typer.echo(f"\n{Colors.BOLD}安装完成{Colors.RESET}")
    typer.echo(f"成功: {success_count}/{total_count}")

    if success_count == total_count:
        print_success("🎉 所有扩展安装成功！")
        typer.echo("\n运行 'sage extensions status' 验证安装")
    else:
        failures = total_count - success_count
        print_warning(f"⚠️ 部分扩展安装失败 ({failures}个)")

    # 确保所有输出都被刷新
    sys.stdout.flush()
    sys.stderr.flush()


def _print_install_banner() -> None:
    """
    Print a banner for the SAGE C++ extension installer to the terminal.
    """
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🧩 SAGE C++ 扩展安装器{Colors.RESET}")
    typer.echo("=" * 50)


def _missing_build_tools_instructions() -> None:
    print_error("缺少必要的构建工具，无法安装C++扩展")
    typer.echo("\n请安装以下工具:")
    typer.echo("  • gcc/g++ (C++ 编译器)")
    typer.echo("  • cmake (构建系统)")
    typer.echo("  • make (构建工具)")
    typer.echo("\nUbuntu/Debian: sudo apt install build-essential cmake")
    typer.echo("CentOS/RHEL: sudo yum groupinstall 'Development Tools' && sudo yum install cmake")
    typer.echo("macOS: xcode-select --install && brew install cmake")


def _ensure_build_environment() -> None:
    """
    Ensure that the required build tools for C++ extension installation are available.
    If any required tools are missing, print instructions for installing them and exit the program.
    """
    if check_build_tools():
        return
    _missing_build_tools_instructions()
    raise typer.Exit(1)


def _check_and_fix_libstdcxx() -> None:
    """
    Check if conda environment has compatible libstdc++ for C++20 compilation.
    If not, attempt to upgrade it or warn the user.
    """
    # Only relevant for conda environments
    conda_prefix = os.getenv("CONDA_PREFIX")
    if not conda_prefix:
        return

    # Check GCC version
    try:
        result = subprocess.run(["gcc", "-dumpversion"], capture_output=True, text=True, check=True)
        gcc_major_version = int(result.stdout.strip().split(".")[0])
    except Exception:
        # Can't determine GCC version, skip check
        return

    # Only check if GCC >= 11 (which uses newer GLIBCXX)
    if gcc_major_version < 11:
        return

    # Check conda libstdc++ version
    conda_libstdcxx = Path(conda_prefix) / "lib" / "libstdc++.so.6"
    if not conda_libstdcxx.exists():
        return

    try:
        result = subprocess.run(
            ["strings", str(conda_libstdcxx)],
            capture_output=True,
            text=True,
            check=True,
        )
        glibcxx_versions = [
            line for line in result.stdout.splitlines() if line.startswith("GLIBCXX_")
        ]

        # Check if we have at least GLIBCXX_3.4.30 (needed for C++20/GCC 11+)
        has_modern_glibcxx = any("GLIBCXX_3.4.3" in v for v in glibcxx_versions)

        if not has_modern_glibcxx:
            print_warning("检测到conda环境的libstdc++版本过低 (需要 GLIBCXX_3.4.30+)")
            print_info("正在尝试更新libstdc++...")

            # Try to update using conda
            try:
                result = subprocess.run(
                    ["conda", "install", "-c", "conda-forge", "libstdcxx-ng", "-y"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    print_success("libstdc++已更新 ✓")
                else:
                    print_warning("无法自动更新libstdc++")
                    typer.echo("\n💡 请手动运行:")
                    typer.echo("   conda install -c conda-forge libstdcxx-ng")
            except subprocess.TimeoutExpired:
                print_warning("更新超时")
            except Exception as e:
                print_warning(f"更新失败: {e}")
                typer.echo("\n💡 请手动运行:")
                typer.echo("   conda install -c conda-forge libstdcxx-ng")
    except Exception:
        # If we can't check, just continue
        pass


def _resolve_project_root() -> Path:
    """
    Locate and return the root directory of the SAGE project.

    Returns:
        Path: The path to the SAGE project root directory.

    Raises:
        typer.Exit: If the SAGE project root cannot be found, prints an error message and exits.
    """
    sage_root = find_sage_root()
    if sage_root:
        return sage_root
    print_error("未找到SAGE项目根目录")
    typer.echo("请在SAGE项目目录中运行此命令")
    raise typer.Exit(1)


def _install_selected_extensions(
    extensions_to_install: list[str], sage_root: Path, force: bool
) -> tuple[int, int]:
    success_count = 0
    total_count = len(extensions_to_install)

    for ext_name in extensions_to_install:
        if not force and _extension_is_available(ext_name):
            print_success(f"{ext_name} 已安装且可用，跳过重新构建（使用 --force 重新安装）")
            success_count += 1
            continue

        rel_path = EXTENSION_PATHS[ext_name]
        ext_dir = sage_root / rel_path
        if _install_extension(ext_name, ext_dir, sage_root, force):
            success_count += 1

    return success_count, total_count


@app.command()
def install(
    extension: str | None = typer.Argument(
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
    _print_install_banner()

    _ensure_build_environment()

    # Check and fix libstdc++ compatibility issues
    _check_and_fix_libstdcxx()

    sage_root = _resolve_project_root()

    print_info(f"SAGE项目根目录: {sage_root}")

    # 显示日志文件位置（放在.sage目录下）
    sage_logs_dir = sage_root / ".sage" / "logs" / "extensions"
    sage_logs_dir.mkdir(parents=True, exist_ok=True)

    extensions_to_install = _resolve_extensions_to_install(extension)
    for ext_name in extensions_to_install:
        build_log = sage_logs_dir / f"{ext_name}_build.log"
        typer.echo(f"{Colors.DIM}📝 {ext_name} 构建日志: {build_log}{Colors.RESET}")
    typer.echo("")

    success_count, total_count = _install_selected_extensions(
        extensions_to_install, sage_root, force
    )

    _print_install_summary(success_count, total_count)


@app.command()
def status():
    """检查扩展安装状态"""
    typer.echo(f"{Colors.BOLD}{Colors.BLUE}🔍 SAGE 扩展状态检查{Colors.RESET}")
    typer.echo("=" * 40)

    extensions = {
        "sage.middleware.components.sage_db.python._sage_db": "数据库扩展 (C++)",
        "sage.middleware.components.sage_flow.python._sage_flow": "流处理引擎扩展 (C++)",
        "sage.middleware.components.sage_tsdb.python._sage_tsdb": "时序数据库扩展 (C++)",
    }

    available_count = 0

    for module_name, description in extensions.items():
        try:
            # 使用线程和超时机制避免卡死（更可靠的跨平台方案）
            import queue
            import threading

            result_queue = queue.Queue()

            def try_import():
                try:
                    __import__(module_name)
                    result_queue.put(("success", None))
                except Exception as e:
                    result_queue.put(("error", e))

            import_thread = threading.Thread(target=try_import, daemon=True)
            import_thread.start()

            # 等待5秒超时
            import_thread.join(timeout=5.0)

            if import_thread.is_alive():
                # 线程仍在运行，说明超时了
                print_warning(f"{description} ✗")
                typer.echo("  原因: 导入超时（可能存在初始化问题）")
            else:
                # 检查结果
                try:
                    status, error = result_queue.get_nowait()
                    if status == "success":
                        print_success(f"{description} ✓")
                        available_count += 1
                    else:
                        print_warning(f"{description} ✗")
                        if isinstance(error, ImportError):
                            typer.echo(f"  原因: {error}")
                        else:
                            typer.echo(f"  原因: {error}")
                except queue.Empty:
                    print_warning(f"{description} ✗")
                    typer.echo("  原因: 无法获取导入结果")
        except Exception as e:
            print_warning(f"{description} ✗")
            typer.echo(f"  原因: {e}")

    typer.echo(f"\n总计: {available_count}/{len(extensions)} 扩展可用")

    if available_count < len(extensions):
        typer.echo(f"\n{Colors.YELLOW}💡 提示:{Colors.RESET}")
        typer.echo("运行 'sage extensions install' 安装缺失的扩展")

    # 确保输出被刷新
    import sys

    sys.stdout.flush()
    sys.stderr.flush()


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
        "sage_tsdb": "packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB",
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
        "sage_tsdb": {
            "description": "时序数据库 Python 绑定",
            "features": ["C++17 核心", "流式 Join", "窗口聚合", "高效索引"],
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
            elif ext_name == "sage_tsdb":
                __import__("sage.middleware.components.sage_tsdb.python._sage_tsdb")
            else:
                __import__(f"sage_ext.{ext_name}")
            typer.echo(f"  安装: {Colors.GREEN}✓ 已安装{Colors.RESET}")
        except ImportError:
            typer.echo(f"  安装: {Colors.RED}✗ 未安装{Colors.RESET}")


if __name__ == "__main__":
    app()
