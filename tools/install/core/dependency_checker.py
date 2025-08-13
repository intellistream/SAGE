"""
SAGE依赖检查器
负责检查系统依赖、版本兼容性和环境准备状态
"""

import os
import sys
import subprocess
import platform
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class DependencyChecker:
    """系统依赖检查器"""
    
    def __init__(self, project_root: str):
        """
        初始化依赖检查器
        
        Args:
            project_root: SAGE项目根目录
        """
        self.project_root = Path(project_root)
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable
        }
    
    def check_python_version(self, min_version: str = "3.8", max_version: str = "3.14") -> Tuple[bool, str]:
        """
        检查Python版本
        
        Args:
            min_version: 最小支持版本
            max_version: 最大支持版本
            
        Returns:
            (是否符合要求, 详细信息)
        """
        current_version = platform.python_version()
        
        try:
            from packaging import version
        except ImportError:
            # 如果packaging不可用，使用简单的版本比较
            current_parts = current_version.split('.')
            min_parts = min_version.split('.')
            max_parts = max_version.split('.')

            # 简单的版本比较
            current_tuple = tuple(int(x) for x in current_parts[:2])
            min_tuple = tuple(int(x) for x in min_parts[:2])
            max_tuple = tuple(int(x) for x in max_parts[:2])
            
            is_valid = min_tuple <= current_tuple <= max_tuple
        else:
            current_ver = version.parse(current_version)
            min_ver = version.parse(min_version)
            max_ver = version.parse(max_version)
            
            is_valid = min_ver <= current_ver <= max_ver
            
        if is_valid:
            return True, f"✅ Python版本 {current_version} 符合要求 ({min_version}-{max_version})"
        else:
            return False, f"❌ Python版本 {current_version} 不符合要求，需要 {min_version}-{max_version}"
    
    def check_conda_installation(self) -> Tuple[bool, str]:
        """
        检查conda安装
        
        Returns:
            (是否安装, 详细信息)
        """
        conda_commands = ["conda", "mamba", "micromamba"]
        
        for cmd in conda_commands:
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                    return True, f"✅ 找到 {cmd}: {version_info}"
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return False, "❌ 未找到conda/mamba/micromamba，请先安装Anaconda或Miniconda"
    
    def check_git_installation(self) -> Tuple[bool, str]:
        """
        检查Git安装
        
        Returns:
            (是否安装, 详细信息)
        """
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                return True, f"✅ {version_info}"
            else:
                return False, "❌ Git命令执行失败"
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "❌ 未找到Git，请先安装Git"
    
    def check_disk_space(self, required_gb: float = 5.0) -> Tuple[bool, str]:
        """
        检查磁盘空间
        
        Args:
            required_gb: 所需磁盘空间（GB）
            
        Returns:
            (是否足够, 详细信息)
        """
        try:
            if platform.system() == "Windows":
                import shutil
                free_bytes = shutil.disk_usage(self.project_root).free
            else:
                statvfs = os.statvfs(self.project_root)
                free_bytes = statvfs.f_frsize * statvfs.f_bavail
            
            free_gb = free_bytes / (1024 ** 3)
            
            if free_gb >= required_gb:
                return True, f"✅ 可用磁盘空间: {free_gb:.1f}GB (需要: {required_gb}GB)"
            else:
                return False, f"❌ 磁盘空间不足: {free_gb:.1f}GB (需要: {required_gb}GB)"
                
        except Exception as e:
            return False, f"❌ 无法检查磁盘空间: {e}"
    
    def check_network_connectivity(self) -> Tuple[bool, str]:
        """
        检查网络连接
        
        Returns:
            (是否连通, 详细信息)
        """
        import urllib.request
        import socket
        
        test_urls = [
            "https://pypi.org",
            "https://anaconda.org",
            "https://github.com"
        ]
        
        results = []
        for url in test_urls:
            try:
                urllib.request.urlopen(url, timeout=10)
                results.append(f"✅ {url}")
            except Exception as e:
                results.append(f"❌ {url}: {str(e)[:50]}")
        
        success_count = sum(1 for r in results if r.startswith("✅"))
        
        if success_count >= 2:
            return True, f"网络连接正常 ({success_count}/{len(test_urls)} 连接成功)"
        else:
            return False, f"网络连接问题 ({success_count}/{len(test_urls)} 连接成功)"
    
    def check_project_structure(self) -> Tuple[bool, str]:
        """
        检查项目结构完整性
        
        Returns:
            (是否完整, 详细信息)
        """
        required_files = [
            "pyproject.toml",
            "quickstart.sh",
            "packages/sage",
            "scripts"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if not missing_files:
            return True, "✅ 项目结构完整"
        else:
            return False, f"❌ 缺少文件: {', '.join(missing_files)}"
    
    def check_system_commands(self) -> Dict[str, Tuple[bool, str]]:
        """
        检查系统必需命令
        
        Returns:
            命令检查结果字典
        """
        required_commands = {
            "python": ["python", "--version"],
            "pip": ["pip", "--version"],
            "git": ["git", "--version"]
        }
        
        results = {}
        
        for name, cmd in required_commands.items():
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                    results[name] = (True, f"✅ {version_info}")
                else:
                    results[name] = (False, f"❌ 命令执行失败")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                results[name] = (False, f"❌ 命令未找到: {' '.join(cmd)}")
        
        return results
    
    def run_comprehensive_check(self) -> Dict[str, Tuple[bool, str]]:
        """
        运行全面的依赖检查
        
        Returns:
            检查结果字典
        """
        logger.info("🔍 开始系统依赖检查...")
        
        checks = {
            "python_version": self.check_python_version(),
            "conda_installation": self.check_conda_installation(),
            "git_installation": self.check_git_installation(),
            "disk_space": self.check_disk_space(),
            "network_connectivity": self.check_network_connectivity(),
            "project_structure": self.check_project_structure()
        }
        
        # 添加系统命令检查
        system_commands = self.check_system_commands()
        checks.update(system_commands)
        
        # 统计结果
        passed = sum(1 for success, _ in checks.values() if success)
        total = len(checks)
        
        logger.info(f"📊 依赖检查完成: {passed}/{total} 项通过")
        
        return checks
    
    def generate_check_report(self, checks: Dict[str, Tuple[bool, str]]) -> str:
        """
        生成检查报告
        
        Args:
            checks: 检查结果字典
            
        Returns:
            格式化的报告字符串
        """
        report_lines = ["🔍 SAGE系统依赖检查报告", "=" * 50, ""]
        
        # 系统信息
        report_lines.append("📋 系统信息:")
        for key, value in self.system_info.items():
            report_lines.append(f"  {key}: {value}")
        report_lines.append("")
        
        # 检查结果
        report_lines.append("🧪 依赖检查结果:")
        
        passed_checks = []
        failed_checks = []
        
        for check_name, (success, message) in checks.items():
            if success:
                passed_checks.append(f"  {message}")
            else:
                failed_checks.append(f"  {message}")
        
        if passed_checks:
            report_lines.append("✅ 通过的检查:")
            report_lines.extend(passed_checks)
            report_lines.append("")
        
        if failed_checks:
            report_lines.append("❌ 失败的检查:")
            report_lines.extend(failed_checks)
            report_lines.append("")
        
        # 总结
        total = len(checks)
        passed = len(passed_checks)
        
        if passed == total:
            report_lines.append("🎉 所有依赖检查通过，可以开始安装SAGE！")
        else:
            report_lines.append(f"⚠️ {total - passed} 项检查失败，请先解决这些问题")
        
        return "\n".join(report_lines)
