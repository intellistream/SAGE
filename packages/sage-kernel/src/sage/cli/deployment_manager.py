#!/usr/bin/env python3
"""
SAGE Deployment Manager
处理项目文件部署到远程节点
"""

import typer
import subprocess
import tempfile
import os
import tarfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from .config_manager import get_config_manager

class DeploymentManager:
    """部署管理器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        
        # 智能检测项目根目录
        # 如果是开发环境，使用源码路径；如果是安装包，使用当前工作目录
        current_file = Path(__file__).resolve()
        
        # 检查是否在site-packages中（已安装的包）
        if 'site-packages' in str(current_file):
            # 使用当前工作目录作为项目根目录
            self.project_root = Path.cwd()
            typer.echo(f"🔍 检测到已安装包环境，使用当前目录: {self.project_root}")
        else:
            # 开发环境，使用相对路径
            self.project_root = current_file.parent.parent.parent
            typer.echo(f"🔍 检测到开发环境，使用源码路径: {self.project_root}")
        
        # 验证项目根目录
        if not (self.project_root / "setup.py").exists():
            # 如果setup.py不存在，尝试查找包含setup.py的父目录
            for parent in self.project_root.parents:
                if (parent / "setup.py").exists():
                    self.project_root = parent
                    typer.echo(f"🔍 找到项目根目录: {self.project_root}")
                    break
            else:
                typer.echo(f"⚠️  警告: 未找到setup.py，使用目录: {self.project_root}")
    
    def create_deployment_package(self) -> str:
        """创建部署包"""
        typer.echo("📦 创建部署包...")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="sage_deploy_")
        package_path = os.path.join(temp_dir, "sage_deployment.tar.gz")
        
        try:
            with tarfile.open(package_path, "w:gz") as tar:
                # 直接添加整个项目目录的内容，但使用相对路径
                # 这样解压时会创建项目结构
                
                # 添加主要源码目录
                tar.add(self.project_root / "sage", arcname="sage")
                tar.add(self.project_root / "app", arcname="app")
                tar.add(self.project_root / "config", arcname="config")
                tar.add(self.project_root / "frontend", arcname="frontend")
                tar.add(self.project_root / "data", arcname="data")
                # 添加安装相关目录
                if (self.project_root / "installation").exists():
                    tar.add(self.project_root / "installation", arcname="installation")
                
                if (self.project_root / "scripts").exists():
                    tar.add(self.project_root / "scripts", arcname="scripts")
                
                # 添加文档目录
                if (self.project_root / "docs").exists():
                    tar.add(self.project_root / "docs", arcname="docs")
                
                # # 添加数据目录（如果存在且不太大）
                # data_dir = self.project_root / "data"
                # if data_dir.exists():
                #     # 只添加小的配置文件，跳过大数据文件
                #     for item in data_dir.iterdir():
                #         if item.is_file() and item.suffix in ['.yaml', '.yml', '.json', '.txt', '.md']:
                #             tar.add(item, arcname=f"data/{item.name}")
                
                # 添加安装文件
                tar.add(self.project_root / "setup.py", arcname="setup.py")
                # tar.add(self.project_root / "requirements.txt", arcname="requirements.txt")
                tar.add(self.project_root / "README.md", arcname="README.md")
                
                # 添加其他必要文件
                for filename in ["MANIFEST.in", "LICENSE"]:
                    file_path = self.project_root / filename
                    if file_path.exists():
                        tar.add(file_path, arcname=filename)
            
            typer.echo(f"✅ 部署包已创建: {package_path}")
            return package_path
            
        except Exception as e:
            typer.echo(f"❌ 创建部署包失败: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
    
    def execute_ssh_command(self, host: str, port: int, command: str, timeout: int = 60) -> bool:
        """执行SSH命令"""
        ssh_config = self.config_manager.get_ssh_config()
        ssh_user = ssh_config.get('user', 'sage')
        ssh_key_path = os.path.expanduser(ssh_config.get('key_path', '~/.ssh/id_rsa'))
        
        typer.echo(f"🔗 连接到 {ssh_user}@{host}:{port}")
        
        try:
            ssh_cmd = [
                'ssh',
                '-i', ssh_key_path,
                '-p', str(port),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', f'ConnectTimeout={ssh_config.get("connect_timeout", 10)}',
                '-o', 'ServerAliveInterval=60',
                '-o', 'ServerAliveCountMax=3',
                f'{ssh_user}@{host}',
                command
            ]
            
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.stdout:
                typer.echo(result.stdout)
            if result.stderr:
                typer.echo(result.stderr, err=True)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            typer.echo(f"❌ SSH命令超时 ({timeout}s)")
            return False
        except Exception as e:
            typer.echo(f"❌ SSH命令失败: {e}")
            return False
    
    def transfer_file(self, local_path: str, host: str, port: int, remote_path: str) -> bool:
        """传输文件到远程主机"""
        ssh_config = self.config_manager.get_ssh_config()
        ssh_user = ssh_config.get('user', 'sage')
        ssh_key_path = os.path.expanduser(ssh_config.get('key_path', '~/.ssh/id_rsa'))
        
        typer.echo(f"📤 传输文件到 {ssh_user}@{host}:{port}:{remote_path}")
        
        try:
            scp_cmd = [
                'scp',
                '-i', ssh_key_path,
                '-P', str(port),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', f'ConnectTimeout={ssh_config.get("connect_timeout", 10)}',
                local_path,
                f'{ssh_user}@{host}:{remote_path}'
            ]
            
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                typer.echo("✅ 文件传输成功")
                return True
            else:
                typer.echo(f"❌ 文件传输失败: {result.stderr}")
                return False
                
        except Exception as e:
            typer.echo(f"❌ 文件传输失败: {e}")
            return False
    
    def deploy_to_worker(self, host: str, port: int) -> bool:
        """部署到单个worker节点"""
        typer.echo(f"\n🚀 部署到Worker节点: {host}:{port}")
        
        try:
            # 1. 创建部署包
            package_path = self.create_deployment_package()
            
            # 2. 传输部署包
            remote_package_path = "/tmp/sage_deployment.tar.gz"
            if not self.transfer_file(package_path, host, port, remote_package_path):
                return False
            
            # 3. 在远程主机上解压和安装
            remote_config = self.config_manager.get_remote_config()
            sage_home = remote_config.get('sage_home', '/home/sage')
            python_path = remote_config.get('python_path', '/opt/conda/envs/sage/bin/python')
            conda_env = remote_config.get('conda_env', 'sage')
            
            install_commands = f"""
set -e
echo "=================================="
echo "开始在 $(hostname) 上部署SAGE..."
echo "=================================="

# 创建目标目录
mkdir -p {sage_home}
cd {sage_home}

# 备份现有安装
if [ -d "SAGE" ]; then
    echo "📦 备份现有SAGE安装..."
    mv SAGE SAGE_backup_$(date +%Y%m%d_%H%M%S) || true
fi

# 解压新版本
echo "📂 解压SAGE项目文件..."
mkdir -p {sage_home}/SAGE
tar -xzf {remote_package_path} -C {sage_home}/SAGE
cd {sage_home}/SAGE

# 检查解压结果
echo "📋 检查解压的文件结构..."
pwd
ls -la
echo "检查是否存在setup.py:"
ls -la setup.py || echo "setup.py 不存在！"

# 初始化conda环境
echo "🐍 初始化conda环境..."
CONDA_FOUND=false
for conda_path in \\
    "$HOME/miniconda3/etc/profile.d/conda.sh" \\
    "$HOME/anaconda3/etc/profile.d/conda.sh" \\
    "/opt/conda/etc/profile.d/conda.sh" \\
    "/usr/local/miniconda3/etc/profile.d/conda.sh" \\
    "/usr/local/anaconda3/etc/profile.d/conda.sh"; do
    if [ -f "$conda_path" ]; then
        source "$conda_path"
        echo "✅ 找到conda: $conda_path"
        CONDA_FOUND=true
        break
    fi
done

if [ "$CONDA_FOUND" = "false" ]; then
    echo "❌ 未找到conda，尝试直接使用python"
    PYTHON_CMD=python
else
    # 激活环境
    echo "🔧 激活conda环境: {conda_env}"
    if conda activate {conda_env} 2>/dev/null; then
        echo "✅ conda环境激活成功"
    else
        echo "⚠️  conda环境激活失败，使用指定的python路径"
    fi
    PYTHON_CMD="{python_path}"
fi

# 检查Python环境
echo "🔍 检查Python环境..."
$PYTHON_CMD --version
$PYTHON_CMD -c "import sys; print('Python路径:', sys.executable)"

# 先安装Cython（如果需要）
echo "� 检查并安装Cython..."
$PYTHON_CMD -c "import Cython" 2>/dev/null || $PYTHON_CMD -m pip install Cython

# 安装SAGE包 - 这会自动安装requirements.txt中的依赖
echo "📦 执行 pip install . 安装SAGE..."
$PYTHON_CMD -m pip install .

# 验证安装
echo "✅ 验证SAGE安装..."
$PYTHON_CMD -c "import sage; print('SAGE安装成功')" || echo "⚠️  SAGE导入测试失败"

# 清理
rm -f {remote_package_path}

echo "=================================="
echo "✅ SAGE部署完成在 $(hostname)"
echo "=================================="
"""
            
            if not self.execute_ssh_command(host, port, install_commands, 180):
                return False
            
            # 4. 传输配置文件
            local_config_path = self.config_manager.config_path
            if local_config_path.exists():
                remote_config_dir = "~/.sage"
                remote_config_path = "~/.sage/config.yaml"
                
                typer.echo(f"📋 传输配置文件: {local_config_path} -> {host}:{remote_config_path}")
                
                # 创建配置目录
                if not self.execute_ssh_command(host, port, f"mkdir -p {remote_config_dir}"):
                    typer.echo("⚠️  创建远程配置目录失败，但继续...")
                
                # 传输配置文件
                if not self.transfer_file(str(local_config_path), host, port, remote_config_path):
                    typer.echo("⚠️  配置文件传输失败，但继续...")
                else:
                    typer.echo("✅ 配置文件传输成功")
            else:
                typer.echo(f"⚠️  本地配置文件不存在: {local_config_path}")
            
            # 5. 清理本地临时文件
            temp_dir = os.path.dirname(package_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            typer.echo(f"✅ Worker节点 {host} 部署成功")
            return True
            
        except Exception as e:
            typer.echo(f"❌ Worker节点 {host} 部署失败: {e}")
            return False
    
    def deploy_to_all_workers(self) -> Tuple[int, int]:
        """部署到所有worker节点"""
        typer.echo("🚀 开始部署到所有Worker节点...")
        
        workers = self.config_manager.get_workers_ssh_hosts()
        if not workers:
            typer.echo("❌ 未配置任何worker节点")
            return 0, 0
        
        success_count = 0
        total_count = len(workers)
        
        for i, (host, port) in enumerate(workers, 1):
            typer.echo(f"\n📋 部署进度: {i}/{total_count}")
            if self.deploy_to_worker(host, port):
                success_count += 1
        
        typer.echo(f"\n📊 部署结果: {success_count}/{total_count} 个节点部署成功")
        return success_count, total_count


if __name__ == "__main__":
    # 测试部署管理器
    deployment_manager = DeploymentManager()
    try:
        success, total = deployment_manager.deploy_to_all_workers()
        if success == total:
            typer.echo("✅ 所有节点部署成功！")
        else:
            typer.echo("⚠️  部分节点部署失败")
    except Exception as e:
        typer.echo(f"❌ 部署失败: {e}")
