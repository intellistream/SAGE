"""Flownet 运行时版本检查和同步工具

替换原有的 ray_version_checker.py，检查 sageFlownet 运行时状态和版本。
"""

import subprocess
from typing import Optional

import typer


def get_local_flownet_version() -> Optional[str]:
    """获取本地 sageFlownet 运行时版本"""
    try:
        result = subprocess.run(
            ["python", "-c", "import sage.flownet; print(sage.flownet.__version__)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # 尝试直接从 sageFlownet 包获取
    try:
        result = subprocess.run(
            ["python", "-c", "from sage.flownet._version import __version__; print(__version__)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return None


def get_remote_flownet_version(
    host: str, port: int, user: str, ssh_key_path: str, conda_env: str = "sage"
) -> Optional[str]:
    """获取远程主机的 sageFlownet 运行时版本

    检测顺序：
    1. conda 环境中 Python 导入 sage.flownet
    2. 系统级 python3/python 导入
    """
    try:
        detect_cmd = f"""
exec 2>/dev/null

# 1. 尝试 conda 环境
if [ "{conda_env}" = "base" ]; then
    CONDA_PYTHON="$HOME/miniconda3/bin/python3"
else
    CONDA_PYTHON="$HOME/miniconda3/envs/{conda_env}/bin/python3"
fi

if [ -f "$CONDA_PYTHON" ]; then
    version=$("$CONDA_PYTHON" -c "import sage.flownet; print(sage.flownet.__version__)" 2>/dev/null)
    if [ -n "$version" ]; then
        echo "$version"
        exit 0
    fi
fi

# 2. 系统 python3
for py_cmd in python3 python; do
    if command -v "$py_cmd" &>/dev/null; then
        version=$("$py_cmd" -c "import sage.flownet; print(sage.flownet.__version__)" 2>/dev/null)
        if [ -n "$version" ]; then
            echo "$version"
            exit 0
        fi
    fi
done

exit 1
"""

        ssh_cmd = [
            "ssh",
            "-i",
            ssh_key_path,
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=5",
            f"{user}@{host}",
            "bash -s",
        ]

        result = subprocess.run(
            ssh_cmd,
            input=detect_cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None


def check_runtime_version_parity(
    workers: list[tuple[str, int]],
    user: str,
    ssh_key_path: str,
    conda_env: str = "sage",
    silent: bool = False,
) -> bool:
    """检查所有节点的 Flownet 运行时版本一致性

    返回: True 如果所有节点版本一致，False 否则
    """
    local_version = get_local_flownet_version()

    if not silent:
        if local_version:
            typer.echo(f"📦 本地 sageFlownet 版本: {local_version}")
        else:
            typer.echo("⚠️  本地未检测到 sageFlownet 运行时")

    if not workers:
        return True

    all_consistent = True
    for host, port in workers:
        remote_version = get_remote_flownet_version(
            host=host, port=port, user=user, ssh_key_path=ssh_key_path, conda_env=conda_env
        )

        if not silent:
            if remote_version:
                typer.echo(f"   {host}:{port} → sageFlownet {remote_version}")
            else:
                typer.echo(f"   {host}:{port} → sageFlownet 未安装或不可达")

        if local_version and remote_version and local_version != remote_version:
            if not silent:
                typer.echo(f"   ⚠️  版本不一致: 本地 {local_version} ≠ 远程 {remote_version}")
            all_consistent = False

    return all_consistent
