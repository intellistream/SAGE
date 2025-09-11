"""
SAGE Git子模块管理器
负责Git子模块的初始化、更新和状态管理
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SubmoduleManager:
    """Git子模块管理器"""
    
    def __init__(self, project_root: str, ui=None):
        """
        初始化子模块管理器
        
        Args:
            project_root: SAGE项目根目录
            ui: 用户界面对象，用于显示详细操作信息
        """
        self.project_root = Path(project_root)
        self.ui = ui
        self.git_executable = None  # 延迟查找git可执行文件
        
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
        
    def _find_git_executable(self, show_search_info: bool = True) -> str:
        """查找git可执行文件
        
        Args:
            show_search_info: 是否显示搜索信息
        """
        if show_search_info:
            self._show_info("🔍 检查Git可执行文件...")
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_info = result.stdout.strip()
                if show_search_info:
                    self._show_success(f"✅ 找到Git: {version_info}")
                return "git"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            if show_search_info:
                self._show_error("❌ Git命令不可用")
            pass
        
        if show_search_info:
            self._show_error("❌ 未找到git命令，请先安装Git")
        raise RuntimeError("❌ 未找到git命令，请先安装Git")
    
    def _ensure_git_executable(self, show_search_info: bool = False) -> str:
        """确保git可执行文件已找到
        
        Args:
            show_search_info: 是否显示搜索信息
            
        Returns:
            git可执行文件路径
        """
        if self.git_executable is None:
            self.git_executable = self._find_git_executable(show_search_info)
        return self.git_executable
    
    def is_git_repository(self) -> bool:
        """检查是否为Git仓库"""
        try:
            git_cmd = self._ensure_git_executable()
            result = subprocess.run(
                [git_cmd, "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False
    
    def get_submodule_status(self) -> Dict[str, Dict[str, str]]:
        """
        获取所有子模块状态
        
        Returns:
            子模块状态字典 {submodule_path: {status, commit, name}}
        """
        if not self.is_git_repository():
            logger.warning("⚠️ 当前目录不是Git仓库")
            return {}
        
        try:
            git_cmd = self._ensure_git_executable()
            result = subprocess.run(
                [git_cmd, "submodule", "status"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            submodules = {}
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                # 解析子模块状态行
                # 格式: [status_char]commit_hash submodule_path (tag_or_branch)
                parts = line.strip().split()
                if len(parts) >= 2:
                    status_and_commit = parts[0]
                    submodule_path = parts[1]
                    
                    # 提取状态字符和commit hash
                    status_char = status_and_commit[0] if status_and_commit[0] in ['-', '+', 'U'] else ''
                    commit_hash = status_and_commit[1:] if status_char else status_and_commit
                    
                    # 状态解释
                    status_map = {
                        '-': 'not_initialized',
                        '+': 'updated',
                        'U': 'conflicts',
                        '': 'up_to_date'
                    }
                    
                    submodules[submodule_path] = {
                        'status': status_map.get(status_char, 'unknown'),
                        'commit': commit_hash[:8],  # 短commit hash
                        'path': submodule_path
                    }
            
            return submodules
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 获取子模块状态失败: {e}")
            return {}
    
    def initialize_submodules(self, 
                             specific_paths: Optional[List[str]] = None,
                             recursive: bool = True) -> bool:
        """
        初始化子模块
        
        Args:
            specific_paths: 指定要初始化的子模块路径，None表示所有子模块
            recursive: 是否递归初始化嵌套子模块
            
        Returns:
            初始化是否成功
        """
        if not self.is_git_repository():
            logger.error("❌ 当前目录不是Git仓库")
            return False
        
        try:
            logger.info("🔄 初始化Git子模块...")
            
            # 构建命令
            cmd = [self.git_executable, "submodule", "init"]
            if specific_paths:
                cmd.extend(specific_paths)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("✅ 子模块初始化成功")
            
            # 更新子模块
            return self.update_submodules(specific_paths, recursive)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 子模块初始化失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
    
    def update_submodules(self, 
                         specific_paths: Optional[List[str]] = None,
                         recursive: bool = True) -> bool:
        """
        更新子模块
        
        Args:
            specific_paths: 指定要更新的子模块路径，None表示所有子模块
            recursive: 是否递归更新嵌套子模块
            
        Returns:
            更新是否成功
        """
        if not self.is_git_repository():
            logger.error("❌ 当前目录不是Git仓库")
            return False
        
        try:
            logger.info("⬇️ 更新Git子模块...")
            
            # 构建命令
            cmd = [self.git_executable, "submodule", "update"]
            if recursive:
                cmd.append("--recursive")
            if specific_paths:
                cmd.extend(specific_paths)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("✅ 子模块更新成功")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 子模块更新失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
    
    def sync_submodules(self) -> bool:
        """
        同步子模块URL
        
        Returns:
            同步是否成功
        """
        if not self.is_git_repository():
            logger.error("❌ 当前目录不是Git仓库")
            return False
        
        try:
            logger.info("🔄 同步子模块URL...")
            
            result = subprocess.run(
                [self.git_executable, "submodule", "sync"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("✅ 子模块URL同步成功")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 子模块URL同步失败: {e}")
            return False
    
    def check_submodule_changes(self) -> Dict[str, List[str]]:
        """
        检查子模块是否有未提交的更改
        
        Returns:
            子模块更改字典 {submodule_path: [changed_files]}
        """
        changes = {}
        submodules = self.get_submodule_status()
        
        for submodule_path in submodules.keys():
            submodule_full_path = self.project_root / submodule_path
            
            if not submodule_full_path.exists():
                continue
            
            try:
                # 检查工作目录状态
                result = subprocess.run(
                    [self.git_executable, "status", "--porcelain"],
                    cwd=submodule_full_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    changed_files = [
                        line.strip() 
                        for line in result.stdout.strip().split('\n')
                        if line.strip()
                    ]
                    changes[submodule_path] = changed_files
                    
            except subprocess.CalledProcessError:
                # 忽略子模块检查错误
                continue
        
        return changes
    
    def get_submodule_info(self) -> List[Dict[str, str]]:
        """
        获取详细的子模块信息
        
        Returns:
            子模块信息列表
        """
        if not self.is_git_repository():
            return []
        
        submodules = []
        
        try:
            # 获取.gitmodules文件信息
            gitmodules_path = self.project_root / ".gitmodules"
            if not gitmodules_path.exists():
                logger.info("📝 没有找到.gitmodules文件")
                return []
            
            # 使用git config读取子模块配置
            result = subprocess.run(
                [self.git_executable, "config", "--file", ".gitmodules", "--list"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                config_lines = result.stdout.strip().split('\n')
                submodule_configs = {}
                
                for line in config_lines:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key.startswith('submodule.'):
                            parts = key.split('.')
                            if len(parts) >= 3:
                                submodule_name = parts[1]
                                config_key = parts[2]
                                
                                if submodule_name not in submodule_configs:
                                    submodule_configs[submodule_name] = {}
                                
                                submodule_configs[submodule_name][config_key] = value
                
                # 获取子模块状态
                status_info = self.get_submodule_status()
                
                # 合并信息
                for name, config in submodule_configs.items():
                    path = config.get('path', '')
                    url = config.get('url', '')
                    
                    submodule_info = {
                        'name': name,
                        'path': path,
                        'url': url,
                        'status': 'unknown',
                        'commit': ''
                    }
                    
                    if path in status_info:
                        submodule_info.update(status_info[path])
                    
                    submodules.append(submodule_info)
        
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 获取子模块信息失败: {e}")
        
        return submodules
    
    def cleanup_submodules(self) -> bool:
        """
        清理子模块（重置到干净状态）
        
        Returns:
            清理是否成功
        """
        try:
            logger.info("🧹 清理子模块...")
            
            # 首先同步
            if not self.sync_submodules():
                return False
            
            # 然后更新
            if not self.update_submodules():
                return False
            
            logger.info("✅ 子模块清理完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 子模块清理失败: {e}")
            return False
