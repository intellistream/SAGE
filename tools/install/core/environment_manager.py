"""
SAGE Conda环境管理器
负责conda环境的创建、激活、删除和管理
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Conda环境管理器"""
    
    def __init__(self, project_root: str):
        """
        初始化环境管理器
        
        Args:
            project_root: SAGE项目根目录
        """
        self.project_root = Path(project_root)
        self.conda_executable = self._find_conda_executable()
        
    def _find_conda_executable(self) -> str:
        """查找conda可执行文件"""
        conda_paths = ["conda", "mamba", "micromamba"]
        
        for conda_cmd in conda_paths:
            try:
                result = subprocess.run(
                    [conda_cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"Found conda executable: {conda_cmd}")
                    return conda_cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
                
        raise RuntimeError("❌ 未找到conda/mamba/micromamba，请先安装conda")
    
    def list_environments(self) -> List[str]:
        """列出所有conda环境"""
        try:
            result = subprocess.run(
                [self.conda_executable, "env", "list", "--json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            env_data = json.loads(result.stdout)
            env_names = []
            
            for env_path in env_data.get("envs", []):
                env_name = Path(env_path).name
                if env_name != "base":  # 排除base环境
                    env_names.append(env_name)
                    
            return env_names
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list environments: {e}")
            return []
    
    def environment_exists(self, env_name: str) -> bool:
        """检查环境是否存在"""
        return env_name in self.list_environments()
    
    def create_environment(self, env_name: str, python_version: str = "3.11") -> bool:
        """
        创建新的conda环境
        
        Args:
            env_name: 环境名称
            python_version: Python版本
            
        Returns:
            创建是否成功
        """
        try:
            logger.info(f"🚀 创建conda环境: {env_name} (Python {python_version})")
            
            cmd = [
                self.conda_executable, "create",
                "-n", env_name,
                f"python={python_version}",
                "-y"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"✅ 环境 {env_name} 创建成功")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 环境创建失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
    
    def activate_environment(self, env_name: str) -> Dict[str, str]:
        """
        获取激活环境所需的环境变量
        
        Args:
            env_name: 环境名称
            
        Returns:
            环境变量字典
        """
        try:
            # 获取环境路径
            result = subprocess.run(
                [self.conda_executable, "info", "--envs", "--json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            env_data = json.loads(result.stdout)
            
            for env_path in env_data.get("envs", []):
                if Path(env_path).name == env_name:
                    env_vars = os.environ.copy()
                    
                    # 设置conda环境相关变量
                    env_vars["CONDA_DEFAULT_ENV"] = env_name
                    env_vars["CONDA_PREFIX"] = env_path
                    
                    # 更新PATH
                    if os.name == "nt":  # Windows
                        conda_bin = Path(env_path) / "Scripts"
                    else:  # Unix/Linux/macOS
                        conda_bin = Path(env_path) / "bin"
                    
                    current_path = env_vars.get("PATH", "")
                    env_vars["PATH"] = f"{conda_bin}:{current_path}"
                    
                    return env_vars
                    
            raise ValueError(f"Environment {env_name} not found")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get environment info: {e}")
            return {}
    
    def delete_environment(self, env_name: str) -> bool:
        """
        删除conda环境
        
        Args:
            env_name: 环境名称
            
        Returns:
            删除是否成功
        """
        try:
            logger.info(f"🗑️ 删除conda环境: {env_name}")
            
            cmd = [
                self.conda_executable, "env", "remove",
                "-n", env_name,
                "-y"
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"✅ 环境 {env_name} 删除成功")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 环境删除失败: {e}")
            return False
    
    def get_environment_info(self, env_name: str) -> Dict:
        """
        获取环境信息
        
        Args:
            env_name: 环境名称
            
        Returns:
            环境信息字典
        """
        info = {
            "name": env_name,
            "exists": self.environment_exists(env_name),
            "python_version": None,
            "packages": []
        }
        
        if not info["exists"]:
            return info
        
        try:
            # 获取Python版本
            env_vars = self.activate_environment(env_name)
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                env=env_vars
            )
            
            if result.returncode == 0:
                version_line = result.stdout.strip()
                info["python_version"] = version_line.replace("Python ", "")
            
            # 获取已安装包列表
            result = subprocess.run(
                [self.conda_executable, "list", "-n", env_name, "--json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                import json
                packages = json.loads(result.stdout)
                info["packages"] = [
                    {"name": pkg["name"], "version": pkg["version"]}
                    for pkg in packages
                ]
                
        except Exception as e:
            logger.warning(f"Could not get full environment info: {e}")
        
        return info
