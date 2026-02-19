#!/usr/bin/env python3
"""
SAGE Runtime CLI
Flownet 运行时健康检查与诊断命令

提供 `sage runtime` 命令组，用于检查 sageFlownet 运行时的状态、健康度和版本信息。
"""

import subprocess
import sys
from typing import Optional

import typer

app = typer.Typer(name="runtime", help="⚙️ Flownet 运行时管理与健康诊断")


def _get_flownet_version() -> Optional[str]:
    """获取本地 sageFlownet 版本"""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sage.flownet; print(sage.flownet.__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _get_sage_kernel_version() -> Optional[str]:
    """获取本地 sage-kernel 版本"""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from sage.kernel._version import __version__; print(__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _check_kernel_runtime_alive() -> bool:
    """检查 sage-kernel 运行时是否可用（JobManager 可达性探测）"""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from sage.kernel.runtime.jobmanager_client import JobManagerClient; "
                    "c = JobManagerClient(); "
                    "print('ok' if c.ping() else 'unreachable')"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except Exception:
        return False


def _check_flownet_installed() -> bool:
    """检查 sageFlownet 是否已安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import sage.flownet; import sageFlownet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


@app.command("status")
def runtime_status():
    """显示 Flownet 运行时整体状态（版本、连通性、组件）"""
    typer.echo("⚙️  SAGE Flownet 运行时状态")
    typer.echo("=" * 50)

    # 1. 版本信息
    typer.echo("\n📦 版本信息:")
    flownet_ver = _get_flownet_version()
    kernel_ver = _get_sage_kernel_version()
    typer.echo(f"   sageFlownet: {flownet_ver or '未安装'}")
    typer.echo(f"   sage-kernel:  {kernel_ver or '未安装'}")

    # 2. Flownet 安装检查
    typer.echo("\n🔌 Flownet 运行时安装:")
    if _check_flownet_installed():
        typer.echo("   ✅ sageFlownet 已安装")
    else:
        typer.echo("   ❌ sageFlownet 未安装 (pip install isage-flow)")

    # 3. Kernel 运行时连通性
    typer.echo("\n🌐 Kernel 运行时连通性:")
    if _check_kernel_runtime_alive():
        typer.echo("   ✅ JobManager 可达")
    else:
        typer.echo("   ⚠️  JobManager 不可达 (本地模式或服务未启动)")

    # 4. 集群节点状态（快速检查）
    typer.echo("\n🏗️  集群信息:")
    try:
        from ...management.config_manager import get_config_manager

        config_manager = get_config_manager()
        head_config = config_manager.get_head_config()
        workers = config_manager.get_workers_ssh_hosts()
        head_host = head_config.get("host", "N/A")
        head_port = head_config.get("head_port", "N/A")
        typer.echo(f"   Head 节点: {head_host}:{head_port}")
        typer.echo(f"   Worker 节点: {len(workers)} 个已配置")
    except Exception as e:
        typer.echo(f"   未能读取集群配置: {e}")

    typer.echo("\n" + "=" * 50)
    typer.echo("💡 运行 'sage runtime health' 获取完整健康报告")
    typer.echo("💡 运行 'sage runtime info' 查看详细运行时信息")


@app.command("health")
def runtime_health():
    """执行 Flownet 运行时完整健康检查"""
    typer.echo("🏥 Flownet 运行时健康检查")
    typer.echo("=" * 50)

    checks: list[tuple[str, bool, str]] = []

    # Check 1: sageFlownet 安装
    installed = _check_flownet_installed()
    checks.append(
        ("sageFlownet 安装", installed, "pip install isage-flow" if not installed else "")
    )

    # Check 2: sage-kernel 版本
    kernel_ver = _get_sage_kernel_version()
    checks.append(
        (
            "sage-kernel 已安装",
            kernel_ver is not None,
            "pip install -e packages/sage-kernel" if not kernel_ver else "",
        )
    )

    # Check 3: JobManager 连通性
    jm_alive = _check_kernel_runtime_alive()
    checks.append(
        (
            "JobManager 连通",
            jm_alive,
            "在本地模式下这是预期的（单节点运行无需 JobManager 服务）" if not jm_alive else "",
        )
    )

    # Check 4: Python 版本
    py_version = sys.version_info
    py_ok = py_version >= (3, 10)
    checks.append(
        (
            "Python >= 3.10",
            py_ok,
            f"当前: Python {py_version.major}.{py_version.minor}" if not py_ok else "",
        )
    )

    # Check 5: sage-common 可用性
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import sage.common; print('ok')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        common_ok = result.returncode == 0
    except Exception:
        common_ok = False
    checks.append(
        ("sage-common 可用", common_ok, "pip install isage-common" if not common_ok else "")
    )

    # 打印结果
    typer.echo("\n检查项目:")
    pass_count = sum(1 for _, ok, _ in checks if ok)
    for name, ok, hint in checks:
        status = "✅" if ok else "❌"
        typer.echo(f"   {status} {name}")
        if hint and not ok:
            typer.echo(f"       💡 {hint}")

    # 总结
    typer.echo(f"\n结果: {pass_count}/{len(checks)} 项通过")
    if pass_count == len(checks):
        typer.echo("🎉 所有检查通过！Flownet 运行时健康状况良好")
    elif pass_count >= len(checks) - 1:
        typer.echo("⚠️  基本健康，少数项目需关注（见上方提示）")
    else:
        typer.echo("❌ 多项检查失败，请根据上方提示修复后重试")
        raise typer.Exit(1)


@app.command("info")
def runtime_info():
    """显示 Flownet 运行时详细信息"""
    typer.echo("ℹ️   Flownet 运行时详细信息")
    typer.echo("=" * 50)

    # Python 环境
    import platform

    typer.echo("\n🐍 Python 环境:")
    typer.echo(f"   版本: {sys.version}")
    typer.echo(f"   路径: {sys.executable}")
    typer.echo(f"   平台: {platform.platform()}")

    # 运行时组件
    typer.echo("\n📦 已安装的 SAGE 运行时组件:")
    components = [
        ("sage.common", "sage-common (L1)"),
        ("sage.platform", "sage-platform (L2)"),
        ("sage.kernel", "sage-kernel (L3)"),
        ("sage.flownet", "sageFlownet (运行时后端)"),
    ]
    for module, label in components:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"import {module}; print(getattr({module}, '__version__', 'installed'))",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                ver = result.stdout.strip()
                typer.echo(f"   ✅ {label} ({ver})")
            else:
                typer.echo(f"   ❌ {label} (未安装)")
        except Exception:
            typer.echo(f"   ❌ {label} (检查失败)")

    # 集群配置
    typer.echo("\n🏗️  集群配置:")
    try:
        from ...management.config_manager import get_config_manager

        cm = get_config_manager()
        head = cm.get_head_config()
        workers = cm.get_workers_ssh_hosts()
        remote = cm.get_remote_config()

        typer.echo(f"   Head 主机: {head.get('host', 'N/A')}")
        typer.echo(f"   Head 端口: {head.get('head_port', 'N/A')}")
        typer.echo(
            f"   Dashboard: {head.get('dashboard_host', '0.0.0.0')}:{head.get('dashboard_port', 'N/A')}"
        )
        typer.echo(f"   Worker 节点数: {len(workers)}")
        typer.echo(f"   Conda 环境: {head.get('conda_env', 'sage')}")
        runtime_cmd = remote.get("runtime_command") or remote.get("ray_command", "自动检测")
        typer.echo(f"   运行时命令: {runtime_cmd}")
    except Exception as e:
        typer.echo(f"   无法读取集群配置: {e}")


@app.command("version")
def runtime_version():
    """显示 Flownet 运行时版本信息"""
    typer.echo("📦 SAGE 运行时版本信息")
    typer.echo("=" * 50)

    flownet_ver = _get_flownet_version()
    kernel_ver = _get_sage_kernel_version()

    typer.echo(f"sageFlownet: {flownet_ver or '未安装'}")
    typer.echo(f"sage-kernel:  {kernel_ver or '未安装'}")
    typer.echo(f"Python:       {sys.version.split()[0]}")
    typer.echo("")
    typer.echo("提示: 安装最新版本: pip install isage-flow")
    typer.echo("仓库: https://github.com/intellistream/sageFlownet")


if __name__ == "__main__":
    app()
