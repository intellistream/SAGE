"""Ray 版本检查和同步工具"""

import re
import subprocess
from typing import Optional

import typer


def get_local_ray_version() -> Optional[str]:
    """获取本地 Ray 版本"""
    try:
        result = subprocess.run(
            ["ray", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # 输出格式: "ray, version 2.9.0"
            match = re.search(r"version\s+([\d.]+)", result.stdout)
            if match:
                return match.group(1)
        return None
    except Exception:
        return None


def get_remote_ray_version(
    host: str, port: int, user: str, ssh_key_path: str, conda_env: str = "sage"
) -> Optional[str]:
    """获取远程主机的 Ray 版本

    检测顺序：
    1. conda 环境中的 ray (base: miniconda3/bin, 其他: miniconda3/envs/{conda_env}/bin)
    2. 系统级 ray 命令
    3. 系统 python3/python 导入
    """
    try:
        # 检测脚本：优先检测 conda 环境
        detect_cmd = f"""
# 静默所有警告
exec 2>/dev/null

# 1. 优先检测 conda 环境中的 ray
# base 环境路径不同：$CONDA_BASE/bin vs $CONDA_BASE/envs/{conda_env}/bin
if [ "{conda_env}" = "base" ]; then
    CONDA_RAY="$HOME/miniconda3/bin/ray"
    CONDA_PYTHON="$HOME/miniconda3/bin/python3"
else
    CONDA_RAY="$HOME/miniconda3/envs/{conda_env}/bin/ray"
    CONDA_PYTHON="$HOME/miniconda3/envs/{conda_env}/bin/python3"
fi

if [ -x "$CONDA_RAY" ]; then
    "$CONDA_RAY" --version 2>/dev/null && exit 0
fi

if [ -x "$CONDA_PYTHON" ]; then
    "$CONDA_PYTHON" -c "import ray; print(f'ray, version {{ray.__version__}}')" 2>/dev/null && exit 0
fi

# 2. 尝试激活 conda 环境后检测
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh" 2>/dev/null
    conda activate {conda_env} 2>/dev/null
    if command -v ray >/dev/null 2>&1; then
        ray --version 2>/dev/null && exit 0
    fi
    python3 -c "import ray; print(f'ray, version {{ray.__version__}}')" 2>/dev/null && exit 0
fi

# 3. 尝试系统级 ray 命令
if command -v ray >/dev/null 2>&1; then
    ray --version 2>/dev/null && exit 0
fi

# 4. 尝试系统 python3 导入
python3 -c "import ray; print(f'ray, version {{ray.__version__}}')" 2>/dev/null && exit 0

# 5. 尝试系统 python 导入
python -c "import ray; print(f'ray, version {{ray.__version__}}')" 2>/dev/null && exit 0

# 没找到 ray
exit 1
"""

        ssh_cmd = [
            "ssh",
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "LogLevel=ERROR",
            f"{user}@{host}",
            "bash -s",
        ]

        # 创建干净的环境变量
        import os

        clean_env = os.environ.copy()
        clean_env["LC_ALL"] = "C"
        clean_env["LANG"] = "C"

        result = subprocess.run(
            ssh_cmd,
            input=detect_cmd,
            capture_output=True,
            text=True,
            timeout=15,
            env=clean_env,
        )

        # 从 stdout 提取版本号
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or "warning" in line.lower() or "setlocale" in line.lower():
                    continue
                match = re.search(r"ray,?\s*version\s+([\d.]+)", line, re.IGNORECASE)
                if match:
                    return match.group(1)

        return None
    except Exception as e:
        typer.echo(f"[dim]Debug {host}: 检测异常: {e}[/dim]", err=True)
        return None


def install_ray_on_remote(
    host: str,
    port: int,
    user: str,
    ssh_key_path: str,
    target_version: str,
    conda_env: str = "sage",
) -> bool:
    """在远程主机上安装指定版本的 Ray

    优先安装到 conda 环境中。
    """
    typer.echo(f"📦 在 {host} 上安装 Ray {target_version}...")

    install_script = f"""
# 静默 locale 警告
export LC_ALL=C 2>/dev/null || true
export LANG=C 2>/dev/null || true

set -e
export PYTHONUNBUFFERED=1

echo "检测 Python 环境..."

# 优先使用 conda 环境
# base 环境路径不同：$CONDA_BASE/bin vs $CONDA_BASE/envs/{conda_env}/bin
if [ "{conda_env}" = "base" ]; then
    CONDA_PYTHON="$HOME/miniconda3/bin/python3"
    CONDA_PIP="$HOME/miniconda3/bin/pip"
else
    CONDA_PYTHON="$HOME/miniconda3/envs/{conda_env}/bin/python3"
    CONDA_PIP="$HOME/miniconda3/envs/{conda_env}/bin/pip"
fi

if [ -x "$CONDA_PIP" ]; then
    echo "使用 conda 环境: {conda_env}"
    PIP_CMD="$CONDA_PIP"
    PYTHON_CMD="$CONDA_PYTHON"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    echo "激活 conda 环境: {conda_env}"
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate {conda_env} 2>/dev/null || true
    PIP_CMD="pip"
    PYTHON_CMD="python3"
elif command -v pip3 >/dev/null 2>&1; then
    echo "使用系统 pip3"
    PIP_CMD="pip3"
    PYTHON_CMD="python3"
elif command -v pip >/dev/null 2>&1; then
    echo "使用系统 pip"
    PIP_CMD="pip"
    PYTHON_CMD="python"
else
    echo "错误: 未找到 pip 命令"
    exit 1
fi

echo "使用 $PIP_CMD 安装 Ray..."

# 卸载旧版本
echo "卸载旧版本 Ray..."
$PIP_CMD uninstall -y ray 2>/dev/null || true

# 安装指定版本
echo "安装 Ray {target_version}..."
$PIP_CMD install "ray[default]=={target_version}"

# 验证安装
echo "验证安装..."
$PYTHON_CMD -c "import ray; print(f'Ray {{ray.__version__}} 安装成功')"

echo "安装完成."
"""

    try:
        import os

        ssh_cmd = [
            "ssh",
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            f"{user}@{host}",
            "bash -s",
        ]

        clean_env = os.environ.copy()
        clean_env["LC_ALL"] = "C"
        clean_env["LANG"] = "C"

        result = subprocess.run(
            ssh_cmd,
            input=install_script,
            capture_output=True,
            text=True,
            timeout=300,
            env=clean_env,
        )

        if result.stdout:
            for line in result.stdout.split("\n"):
                if "setlocale" not in line.lower() and "warning" not in line.lower():
                    typer.echo(line)
        if result.stderr:
            for line in result.stderr.split("\n"):
                if "setlocale" not in line.lower() and "warning" not in line.lower():
                    if line.strip():
                        typer.echo(line, err=True)

        return result.returncode == 0

    except Exception as e:
        typer.echo(f"❌ 安装失败: {e}")
        return False


def check_and_sync_ray_version(
    host: str,
    port: int,
    user: str,
    ssh_key_path: str,
    conda_env: str = "sage",
) -> bool:
    """检查并同步 Ray 版本

    Returns:
        True if version is compatible or successfully synced, False otherwise
    """
    # 获取本地版本
    local_version = get_local_ray_version()
    if not local_version:
        typer.echo("[yellow]⚠️  无法获取本地 Ray 版本[/yellow]")
        return True

    # 获取远程版本（传入 conda_env 参数）
    remote_version = get_remote_ray_version(host, port, user, ssh_key_path, conda_env)

    if not remote_version:
        typer.echo(f"[yellow]⚠️  {host}: 未检测到 Ray，尝试安装...[/yellow]")
        return install_ray_on_remote(host, port, user, ssh_key_path, local_version, conda_env)

    # 比较版本
    if remote_version == local_version:
        typer.echo(f"[green]✅ {host}: Ray 版本一致 ({local_version})[/green]")
        return True

    # 版本不一致
    typer.echo(f"[yellow]⚠️  {host}: Ray 版本不一致[/yellow]")
    typer.echo(f"   本地版本: {local_version}")
    typer.echo(f"   远程版本: {remote_version}")

    if typer.confirm(f"是否将 {host} 的 Ray 升级到 {local_version}?", default=True):
        return install_ray_on_remote(host, port, user, ssh_key_path, local_version, conda_env)
    else:
        typer.echo(f"[yellow]⚠️  跳过 {host} 的版本同步，可能导致集群不稳定[/yellow]")
        return True
