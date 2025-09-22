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
    
    def __init__(self, project_root: str, ui=None):
        """
        初始化依赖检查器
        
        Args:
            project_root: SAGE项目根目录
            ui: 用户界面对象，用于显示详细检查信息
        """
        self.project_root = Path(project_root)
        self.ui = ui
        self.system_info = None  # 延迟获取系统信息
        
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
        
    def _get_system_info(self, show_info: bool = True) -> Dict[str, str]:
        """获取系统信息
        
        Args:
            show_info: 是否显示系统信息到UI
        """
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable
        }
        
        # 只在明确要求时才显示系统信息到UI
        if show_info:
            self._show_info("🖥️ 检测到系统信息:")
            for key, value in info.items():
                self._show_info(f"   {key}: {value}")
            
        return info
    
    def check_python_version(self, min_version: str = "3.8", max_version: str = "3.14") -> Tuple[bool, str]:
        """
        检查Python版本
        
        Args:
            min_version: 最小支持版本
            max_version: 最大支持版本
            
        Returns:
            (是否符合要求, 详细信息)
        """
        self._show_info("🐍 检查Python版本兼容性...")
        current_version = platform.python_version()
        self._show_info(f"   当前Python版本: {current_version}")
        self._show_info(f"   要求版本范围: {min_version} - {max_version}")
        
        try:
            from packaging import version
        except ImportError:
            self._show_warning("   ⚠️ packaging模块不可用，使用简单版本比较")
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
            self._show_info("   ✓ 使用packaging模块进行精确版本比较")
            current_ver = version.parse(current_version)
            min_ver = version.parse(min_version)
            max_ver = version.parse(max_version)
            
            is_valid = min_ver <= current_ver <= max_ver
            
        if is_valid:
            self._show_success(f"   ✅ Python版本 {current_version} 符合要求")
            return True, f"✅ Python版本 {current_version} 符合要求 ({min_version}-{max_version})"
        else:
            self._show_error(f"   ❌ Python版本 {current_version} 不符合要求")
            return False, f"❌ Python版本 {current_version} 不符合要求，需要 {min_version}-{max_version}"
    
    def check_conda_installation(self) -> Tuple[bool, str]:
        """
        检查conda安装
        
        Returns:
            (是否安装, 详细信息)
        """
        self._show_info("📦 检查conda包管理器...")
        conda_commands = ["conda", "mamba", "micromamba"]
        
        for cmd in conda_commands:
            self._show_info(f"   尝试检测: {cmd}")
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                    self._show_success(f"   ✅ 找到 {cmd}: {version_info}")
                    return True, f"✅ 找到 {cmd}: {version_info}"
                else:
                    self._show_info(f"   ❌ {cmd} 命令执行失败")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._show_info(f"   ❌ {cmd} 未找到")
                continue
        
        self._show_error("   ❌ 未找到任何conda变体")
        return False, "❌ 未找到conda/mamba/micromamba，请先安装Anaconda或Miniconda"
    
    def check_git_installation(self) -> Tuple[bool, str]:
        """
        检查Git安装
        
        Returns:
            (是否安装, 详细信息)
        """
        self._show_info("� 检查Git可执行文件...")
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                self._show_success(f"✅ 找到Git: {version_info}")
                return True, f"✅ 找到Git: {version_info}"
            else:
                self._show_error("❌ Git命令执行失败")
                return False, "❌ Git命令执行失败"
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._show_error("❌ 未找到Git")
            return False, "❌ 未找到Git，请先安装Git"
    
    def check_disk_space(self, required_gb: float = 5.0) -> Tuple[bool, str]:
        """
        检查磁盘空间
        
        Args:
            required_gb: 所需磁盘空间（GB）
            
        Returns:
            (是否足够, 详细信息)
        """
        self._show_info("💾 检查磁盘空间...")
        try:
            if platform.system() == "Windows":
                import shutil
                free_bytes = shutil.disk_usage(self.project_root).free
            else:
                statvfs = os.statvfs(self.project_root)
                free_bytes = statvfs.f_frsize * statvfs.f_bavail
            
            free_gb = free_bytes / (1024 ** 3)
            
            self._show_info(f"   项目路径: {self.project_root}")
            self._show_info(f"   可用空间: {free_gb:.1f} GB")
            self._show_info(f"   所需空间: {required_gb} GB")
            
            if free_gb >= required_gb:
                self._show_success(f"   ✅ 磁盘空间充足")
                return True, f"✅ 可用磁盘空间: {free_gb:.1f}GB (需要: {required_gb}GB)"
            else:
                self._show_error(f"   ❌ 磁盘空间不足")
                return False, f"❌ 磁盘空间不足: {free_gb:.1f}GB (需要: {required_gb}GB)"
                
        except Exception as e:
            self._show_error(f"   ❌ 检查磁盘空间时出错: {e}")
            return False, f"❌ 无法检查磁盘空间: {e}"
    
    def check_network_connectivity(self) -> Tuple[bool, str]:
        """
        检查网络连接
        
        Returns:
            (是否连通, 详细信息)
        """
        self._show_info("🌐 检查网络连接...")
        import urllib.request
        import socket
        
        # 按重要性排序的测试URL
        test_urls = [
            ("https://pypi.org", "PyPI (Python包安装)", True),  # 最重要
            ("https://anaconda.org", "Anaconda (conda包)", False),  # 可选
            ("https://github.com", "GitHub (代码仓库)", False)  # 可选
        ]
        
        results = []
        critical_success = True
        
        for url, description, is_critical in test_urls:
            self._show_info(f"   测试连接: {url}")
            try:
                # 设置User-Agent以避免403错误
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
                urllib.request.urlopen(req, timeout=10)
                self._show_success(f"   ✅ {description} 连接成功")
                results.append(f"✅ {description}")
            except Exception as e:
                error_msg = str(e)[:50]
                self._show_warning(f"   ❌ {description} 连接失败: {error_msg}")
                results.append(f"❌ {description}: {error_msg}")
                if is_critical:
                    critical_success = False
        
        success_count = sum(1 for r in results if r.startswith("✅"))
        
        # 只要关键连接(PyPI)成功，就认为网络检查通过
        if critical_success:
            self._show_success(f"   网络连接检查通过 ({success_count}/{len(test_urls)} 成功)")
            return True, f"网络连接可用 ({success_count}/{len(test_urls)} 连接成功，PyPI可访问)"
        else:
            self._show_error(f"   关键网络连接失败")
            return False, f"关键网络连接失败 ({success_count}/{len(test_urls)} 连接成功，PyPI不可访问)"
    
    def check_project_structure(self) -> Tuple[bool, str]:
        """
        检查项目结构完整性
        
        Returns:
            (是否完整, 详细信息)
        """
        self._show_info("📁 检查SAGE项目结构...")
        required_files = [
            "pyproject.toml",
            "quickstart.sh",
            "packages/sage",
            "scripts"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            self._show_info(f"   检查: {file_path}")
            if not full_path.exists():
                self._show_error(f"   ❌ 缺少: {file_path}")
                missing_files.append(file_path)
            else:
                self._show_success(f"   ✅ 存在: {file_path}")
        
        if not missing_files:
            self._show_success("   项目结构完整")
            return True, "✅ 项目结构完整"
        else:
            self._show_error(f"   项目结构不完整，缺少 {len(missing_files)} 个文件")
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
            self._show_info(f"   检查命令: {name}")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                    self._show_success(f"   ✅ {name}: {version_info}")
                    results[name] = (True, f"✅ {version_info}")
                else:
                    self._show_error(f"   ❌ {name} 命令执行失败")
                    results[name] = (False, f"❌ 命令执行失败")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._show_error(f"   ❌ {name} 命令未找到")
                results[name] = (False, f"❌ 命令未找到: {' '.join(cmd)}")
        
        return results
    
    def run_comprehensive_check(self) -> Dict[str, Tuple[bool, str]]:
        """
        运行全面的依赖检查
        
        Returns:
            检查结果字典
        """
        self._show_info("🔍 开始SAGE系统依赖全面检查...")
        self._show_info("=" * 50)
        
        # 获取并显示系统信息
        if self.system_info is None:
            self.system_info = self._get_system_info(show_info=True)
        
        checks = {
            "python_version": self.check_python_version(),
            "conda_installation": self.check_conda_installation(),
            "git_installation": self.check_git_installation(),
            "disk_space": self.check_disk_space(),
            "network_connectivity": self.check_network_connectivity(),
            "project_structure": self.check_project_structure()
        }
        
        # 添加系统命令检查
        self._show_info("")
        self._show_info("🛠️ 检查系统命令可用性...")
        system_commands = self.check_system_commands()
        checks.update(system_commands)
        
        # 统计结果
        passed = sum(1 for success, _ in checks.values() if success)
        total = len(checks)
        
        self._show_info("")
        self._show_info("📊 依赖检查统计:")
        self._show_info(f"   总检查项: {total}")
        self._show_info(f"   ✅ 通过: {passed}")
        self._show_info(f"   ❌ 失败: {total - passed}")
        self._show_info(f"   📈 成功率: {passed/total*100:.1f}%")
        
        if passed == total:
            self._show_success("🎉 所有依赖检查通过！系统环境满足SAGE安装要求")
        else:
            self._show_warning(f"⚠️ {total - passed} 项检查失败，可能影响安装过程")
        
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
        # 确保系统信息已经获取
        if self.system_info is None:
            self.system_info = self._get_system_info(show_info=False)
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
