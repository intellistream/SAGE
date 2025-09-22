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
    
    def __init__(self, project_root: str, ui=None):
        """
        初始化环境管理器
        
        Args:
            project_root: SAGE项目根目录
            ui: 用户界面对象，用于显示详细信息
        """
        self.project_root = Path(project_root)
        self.ui = ui
        self.conda_executable = None  # 延迟查找conda可执行文件
        
    def _show_info(self, message: str):
        """显示信息到UI界面"""
        if self.ui:
            self.ui.show_info(message)
        logger.info(message)
        
    def _show_success(self, message: str):
        """显示成功信息到UI界面"""
        if self.ui:
            self.ui.show_success(message)
        logger.info(message)
        
    def _show_error(self, message: str):
        """显示错误信息到UI界面"""
        if self.ui:
            self.ui.show_error(message)
        logger.error(message)
        
    def _show_warning(self, message: str):
        """显示警告信息到UI界面"""
        if self.ui:
            self.ui.show_warning(message)
        logger.warning(message)
        
    def _find_conda_executable(self, show_search_info: bool = True) -> str:
        """查找conda可执行文件
        
        Args:
            show_search_info: 是否显示搜索信息
        """
        conda_paths = ["conda", "mamba", "micromamba"]
        
        if show_search_info:
            self._show_info("🔍 搜索conda包管理器...")
        
        for conda_cmd in conda_paths:
            try:
                result = subprocess.run(
                    [conda_cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                    if show_search_info:
                        self._show_success(f"✅ 找到 {conda_cmd}: {version_info}")
                    return conda_cmd
                else:
                    if show_search_info:
                        self._show_info(f"❌ {conda_cmd} 不可用")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                if show_search_info:
                    self._show_info(f"❌ {conda_cmd} 未找到")
                continue
                
        if show_search_info:
            self._show_error("❌ 未找到conda/mamba/micromamba，请先安装conda")
        raise RuntimeError("❌ 未找到conda/mamba/micromamba，请先安装conda")
    
    def _ensure_conda_executable(self, show_search_info: bool = False) -> str:
        """确保conda可执行文件已找到
        
        Args:
            show_search_info: 是否显示搜索信息
            
        Returns:
            conda可执行文件路径
        """
        if self.conda_executable is None:
            self.conda_executable = self._find_conda_executable(show_search_info)
        return self.conda_executable
    
    def list_environments(self) -> List[str]:
        """列出所有conda环境"""
        try:
            self._show_info("📋 获取conda环境列表...")
            conda_cmd = self._ensure_conda_executable(show_search_info=False)  # 不显示搜索信息
            result = subprocess.run(
                [conda_cmd, "env", "list", "--json"],
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
                    self._show_info(f"   找到环境: {env_name}")
                    
            self._show_info(f"   共发现 {len(env_names)} 个非base环境")
            return env_names
            
        except subprocess.CalledProcessError as e:
            self._show_error(f"❌ 获取环境列表失败: {e}")
            return []
    
    def environment_exists(self, env_name: str) -> bool:
        """检查环境是否存在"""
        exists = env_name in self.list_environments()
        if exists:
            self._show_info(f"✅ 环境 {env_name} 已存在")
        else:
            self._show_info(f"❌ 环境 {env_name} 不存在")
        return exists
    
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
            conda_cmd = self._ensure_conda_executable(show_search_info=True)  # 在创建环境时显示搜索信息
            self._show_info(f"🚀 开始创建conda环境: {env_name}")
            self._show_info(f"   📋 Python版本: {python_version}")
            self._show_info(f"   🔧 使用工具: {conda_cmd}")
            
            cmd = [
                conda_cmd, "create",
                "-n", env_name,
                f"python={python_version}",
                "-y", "-v"
            ]
            
            self._show_info(f"   🔄 执行命令: {' '.join(cmd)}")
            
            # 实时显示conda输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line:
                        # 过滤并显示有用的conda输出
                        if any(keyword in line.lower() for keyword in ['collecting', 'downloading', 'extracting', 'preparing', 'executing', 'done']):
                            self._show_info(f"   conda: {line}")
                        elif 'error' in line.lower() or 'failed' in line.lower():
                            self._show_error(f"   conda错误: {line}")
            
            return_code = process.poll()
            
            if return_code == 0:
                self._show_success(f"✅ 环境 {env_name} 创建成功")
                return True
            else:
                self._show_error(f"❌ 环境创建失败，退出码: {return_code}")
                return False
            
        except Exception as e:
            self._show_error(f"❌ 环境创建过程中发生异常: {e}")
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
            conda_cmd = self._ensure_conda_executable(show_search_info=False)  # 不显示搜索信息
            result = subprocess.run(
                [conda_cmd, "info", "--envs", "--json"],
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
            
            conda_cmd = self._ensure_conda_executable(show_search_info=False)  # 不显示搜索信息
            cmd = [
                conda_cmd, "env", "remove",
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
            conda_cmd = self._ensure_conda_executable(show_search_info=False)  # 不显示搜索信息
            result = subprocess.run(
                [conda_cmd, "list", "-n", env_name, "--json"],
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
