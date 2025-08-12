"""
SAGE包安装管理器
负责Python包的安装、更新和管理
"""

import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class PackageInstaller:
    """Python包安装管理器"""
    
    def __init__(self, project_root: str, env_vars: Dict[str, str] = None):
        """
        初始化包安装器
        
        Args:
            project_root: SAGE项目根目录
            env_vars: 环境变量字典（用于激活特定conda环境）
        """
        self.project_root = Path(project_root)
        self.env_vars = env_vars or {}
        
    def install_package(self, 
                       package: str, 
                       use_conda: bool = True,
                       progress_callback: Optional[Callable] = None) -> bool:
        """
        安装单个包
        
        Args:
            package: 包名称（可包含版本，如 'numpy==1.21.0'）
            use_conda: 是否优先使用conda安装
            progress_callback: 进度回调函数
            
        Returns:
            安装是否成功
        """
        try:
            if progress_callback:
                progress_callback(f"安装包: {package}")
            
            logger.info(f"📦 安装包: {package}")
            
            # 尝试conda安装
            if use_conda and self._try_conda_install(package):
                logger.info(f"✅ 通过conda成功安装: {package}")
                return True
            
            # 回退到pip安装
            if self._try_pip_install(package):
                logger.info(f"✅ 通过pip成功安装: {package}")
                return True
            
            logger.error(f"❌ 包安装失败: {package}")
            return False
            
        except Exception as e:
            logger.error(f"❌ 安装包时发生错误 {package}: {e}")
            return False
    
    def install_packages(self, 
                        packages: List[str], 
                        use_conda: bool = True,
                        progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """
        批量安装包
        
        Args:
            packages: 包名称列表
            use_conda: 是否优先使用conda安装
            progress_callback: 进度回调函数
            
        Returns:
            安装结果字典 {package_name: success}
        """
        results = {}
        total = len(packages)
        
        for i, package in enumerate(packages, 1):
            if progress_callback:
                progress_callback(f"正在安装 ({i}/{total}): {package}")
            
            results[package] = self.install_package(
                package, use_conda, progress_callback
            )
            
            # 简短暂停，避免过快安装导致的问题
            time.sleep(0.1)
        
        return results
    
    def install_requirements_file(self, 
                                 requirements_file: str,
                                 progress_callback: Optional[Callable] = None) -> bool:
        """
        从requirements文件安装包
        
        Args:
            requirements_file: requirements文件路径
            progress_callback: 进度回调函数
            
        Returns:
            安装是否成功
        """
        req_path = Path(requirements_file)
        if not req_path.exists():
            logger.error(f"❌ Requirements文件不存在: {requirements_file}")
            return False
        
        try:
            if progress_callback:
                progress_callback(f"安装requirements: {requirements_file}")
            
            logger.info(f"📋 从requirements文件安装: {requirements_file}")
            
            cmd = ["pip", "install", "-r", str(req_path)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env_vars,
                check=True
            )
            
            logger.info(f"✅ Requirements安装成功")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Requirements安装失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
    
    def install_local_package(self, 
                             package_path: str, 
                             editable: bool = True,
                             progress_callback: Optional[Callable] = None) -> bool:
        """
        安装本地包（开发模式）
        
        Args:
            package_path: 本地包路径
            editable: 是否使用可编辑模式(-e)
            progress_callback: 进度回调函数
            
        Returns:
            安装是否成功
        """
        pkg_path = Path(package_path)
        if not pkg_path.exists():
            logger.error(f"❌ 本地包路径不存在: {package_path}")
            return False
        
        try:
            if progress_callback:
                progress_callback(f"安装本地包: {package_path}")
            
            logger.info(f"🔧 安装本地包: {package_path}")
            
            cmd = ["pip", "install"]
            if editable:
                cmd.append("-e")
            cmd.append(str(pkg_path))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env_vars,
                check=True
            )
            
            logger.info(f"✅ 本地包安装成功")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 本地包安装失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
    
    def _try_conda_install(self, package: str) -> bool:
        """尝试使用conda安装包"""
        try:
            # 寻找conda可执行文件
            conda_cmds = ["conda", "mamba", "micromamba"]
            conda_executable = None
            
            for cmd in conda_cmds:
                try:
                    subprocess.run([cmd, "--version"], capture_output=True, check=True)
                    conda_executable = cmd
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            if not conda_executable:
                return False
            
            # 构建conda安装命令
            cmd = [conda_executable, "install", package, "-y"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env_vars,
                timeout=300  # 5分钟超时
            )
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def _try_pip_install(self, package: str) -> bool:
        """尝试使用pip安装包"""
        try:
            cmd = ["pip", "install", package]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env_vars,
                check=True,
                timeout=300  # 5分钟超时
            )
            
            return True
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
    
    def get_installed_packages(self) -> List[Dict[str, str]]:
        """
        获取已安装包列表
        
        Returns:
            包信息列表 [{"name": "package_name", "version": "1.0.0"}, ...]
        """
        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                env=self.env_vars,
                check=True
            )
            
            import json
            packages = json.loads(result.stdout)
            return packages
            
        except Exception as e:
            logger.error(f"获取已安装包列表失败: {e}")
            return []
    
    def is_package_installed(self, package_name: str) -> bool:
        """
        检查包是否已安装
        
        Args:
            package_name: 包名称
            
        Returns:
            是否已安装
        """
        try:
            result = subprocess.run(
                ["pip", "show", package_name],
                capture_output=True,
                text=True,
                env=self.env_vars
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
