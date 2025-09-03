"""
SAGE包安装管理器
负责Python包的安装、更新和管理
"""

import subprocess
import logging
import time
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class PackageInstaller:
    """Python包安装管理器"""
    
    def __init__(self, project_root: str, env_vars: Dict[str, str] = None, ui=None):
        """
        初始化包安装器
        
        Args:
            project_root: SAGE项目根目录
            env_vars: 环境变量字典（用于激活特定conda环境）
            ui: 用户界面对象，用于显示详细安装信息
        """
        self.project_root = Path(project_root)
        self.env_vars = env_vars or {}
        self.ui = ui
        
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
        
    def _get_pip_executable(self) -> str:
        """获取正确的pip可执行文件路径"""
        # 如果设置了CONDA_PREFIX环境变量，优先使用conda环境中的pip
        if "CONDA_PREFIX" in self.env_vars:
            conda_prefix = self.env_vars["CONDA_PREFIX"]
            if os.name == "nt":  # Windows
                pip_path = Path(conda_prefix) / "Scripts" / "pip.exe"
            else:  # Unix/Linux/macOS
                pip_path = Path(conda_prefix) / "bin" / "pip"
            
            if pip_path.exists():
                return str(pip_path)
        
        # 回退到系统pip
        return "pip"
        
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
            
            self._show_info(f"📦 开始安装包: {package}")
            
            # 首先检查包是否已安装
            if self.is_package_installed(package.split('=')[0].split('>')[0].split('<')[0].strip()):
                self._show_info(f"   ✓ 包 {package} 已安装，跳过")
                return True
            
            # 尝试conda安装
            if use_conda:
                self._show_info(f"   🔄 尝试使用conda安装: {package}")
                if self._try_conda_install(package):
                    self._show_success(f"   ✅ 通过conda成功安装: {package}")
                    return True
                else:
                    self._show_warning(f"   ⚠️ conda安装失败，回退到pip")
            
            # 回退到pip安装
            self._show_info(f"   🔄 使用pip安装: {package}")
            if self._try_pip_install(package):
                self._show_success(f"   ✅ 通过pip成功安装: {package}")
                return True
            
            self._show_error(f"   ❌ 包安装失败: {package}")
            return False
            
        except Exception as e:
            self._show_error(f"   ❌ 安装包时发生错误 {package}: {e}")
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
        
        self._show_info(f"📋 开始批量安装 {total} 个包...")
        
        for i, package in enumerate(packages, 1):
            if progress_callback:
                progress_callback(f"正在安装 ({i}/{total}): {package}")
            
            self._show_info(f"进度 [{i}/{total}] 安装包: {package}")
            results[package] = self.install_package(
                package, use_conda, progress_callback
            )
            
            # 简短暂停，避免过快安装导致的问题
            time.sleep(0.1)
        
        # 显示安装总结
        successful = sum(1 for success in results.values() if success)
        failed = total - successful
        
        if failed == 0:
            self._show_success(f"🎉 所有 {total} 个包安装成功！")
        else:
            self._show_warning(f"⚠️ {successful} 个包成功，{failed} 个包失败")
            failed_packages = [pkg for pkg, success in results.items() if not success]
            self._show_error(f"   失败的包: {', '.join(failed_packages)}")
        
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
            self._show_error(f"❌ Requirements文件不存在: {requirements_file}")
            return False
        
        try:
            if progress_callback:
                progress_callback(f"安装requirements: {requirements_file}")
            
            self._show_info(f"📋 开始从requirements文件安装: {req_path.name}")
            
            # 读取requirements文件内容并显示
            try:
                with open(req_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
                    self._show_info(f"   📝 发现 {len(lines)} 个包依赖:")
                    for line in lines:
                        self._show_info(f"      - {line}")
            except Exception as e:
                self._show_warning(f"   ⚠️ 无法读取requirements内容: {e}")
            
            # 使用conda环境中的pip
            pip_executable = self._get_pip_executable()
            cmd = [pip_executable, "install", "-r", str(req_path), "-v"]  # 添加-v获取详细输出
            
            self._show_info(f"   🔄 执行命令: {' '.join(cmd)}")
            
            # 实时显示pip安装输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env_vars,
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
                        # 过滤并显示有用的pip输出
                        if any(keyword in line.lower() for keyword in ['collecting', 'downloading', 'installing', 'successfully installed', 'requirement already satisfied']):
                            self._show_info(f"   pip: {line}")
                        elif 'error' in line.lower() or 'failed' in line.lower():
                            self._show_error(f"   pip错误: {line}")
            
            return_code = process.poll()
            
            if return_code == 0:
                self._show_success(f"   ✅ Requirements文件安装成功")
                return True
            else:
                self._show_error(
                    f"   ❌ Requirements安装失败，退出码: {return_code}\n"
                    f"   💡 这通常是由于包依赖问题或网络连接问题导致的\n"
                    f"   📋 详细错误信息已记录到install.log文件\n"
                    f"   🔧 建议检查网络连接或尝试手动安装依赖包"
                )
                return False
            
        except Exception as e:
            self._show_error(f"❌ Requirements安装过程中发生异常: {e}")
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
            self._show_error(f"❌ 本地包路径不存在: {package_path}")
            return False
        
        try:
            if progress_callback:
                progress_callback(f"安装本地包: {package_path}")
            
            package_name = pkg_path.name
            self._show_info(f"🔧 开始安装本地包: {package_name}")
            self._show_info(f"   📁 路径: {package_path}")
            self._show_info(f"   🔄 可编辑模式: {'是' if editable else '否'}")
            
            pip_executable = self._get_pip_executable()
            cmd = [pip_executable, "install"]
            if editable:
                cmd.append("-e")
            cmd.append(str(pkg_path))
            cmd.append("-v")  # 详细输出
            
            self._show_info(f"   🔄 执行命令: {' '.join(cmd)}")
            
            # 实时显示pip安装输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env_vars,
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
                        # 过滤并显示有用的pip输出
                        if any(keyword in line.lower() for keyword in ['processing', 'preparing', 'building', 'installing', 'successfully installed']):
                            self._show_info(f"   pip: {line}")
                        elif 'error' in line.lower() or 'failed' in line.lower():
                            self._show_error(f"   pip错误: {line}")
            
            return_code = process.poll()
            
            if return_code == 0:
                self._show_success(f"   ✅ 本地包 {package_name} 安装成功")
                return True
            else:
                self._show_error(f"   ❌ 本地包安装失败，退出码: {return_code}")
                return False
            
        except Exception as e:
            self._show_error(f"❌ 本地包安装过程中发生异常: {e}")
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
                self._show_warning(f"   ⚠️ 未找到conda可执行文件")
                return False
            
            self._show_info(f"   🔄 使用 {conda_executable} 安装包...")
            
            # 构建conda安装命令
            cmd = [conda_executable, "install", package, "-y", "-v"]
            
            # 实时显示conda输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env_vars,
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
            return return_code == 0
            
        except Exception as e:
            self._show_warning(f"   ⚠️ conda安装异常: {e}")
            return False
    
    def _try_pip_install(self, package: str) -> bool:
        """尝试使用pip安装包"""
        try:
            pip_executable = self._get_pip_executable()
            cmd = [pip_executable, "install", package, "-v"]
            
            self._show_info(f"   🔄 使用pip安装包: {package}")
            
            # 实时显示pip输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env_vars,
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
                        # 过滤并显示有用的pip输出
                        if any(keyword in line.lower() for keyword in ['collecting', 'downloading', 'installing', 'successfully installed', 'requirement already satisfied']):
                            self._show_info(f"   pip: {line}")
                        elif 'error' in line.lower() or 'failed' in line.lower():
                            self._show_error(f"   pip错误: {line}")
            
            return_code = process.poll()
            return return_code == 0
            
        except Exception as e:
            self._show_warning(f"   ⚠️ pip安装异常: {e}")
            return False
    
    def get_installed_packages(self) -> List[Dict[str, str]]:
        """
        获取已安装包列表
        
        Returns:
            包信息列表 [{"name": "package_name", "version": "1.0.0"}, ...]
        """
        try:
            pip_executable = self._get_pip_executable()
            result = subprocess.run(
                [pip_executable, "list", "--format=json"],
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
            pip_executable = self._get_pip_executable()
            result = subprocess.run(
                [pip_executable, "show", package_name],
                capture_output=True,
                text=True,
                env=self.env_vars
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def resolve_dependencies(self, packages: List[str] = None) -> bool:
        """
        解析和安装缺失的依赖
        
        Args:
            packages: 要检查的包列表，如果为None则检查所有已安装的包
            
        Returns:
            解析是否成功
        """
        try:
            self._show_info("🔍 开始解析包依赖...")
            
            # 获取当前环境中的包依赖冲突
            pip_executable = self._get_pip_executable()
            
            # 使用pip check检查依赖冲突
            result = subprocess.run(
                [pip_executable, "check"],
                capture_output=True,
                text=True,
                env=self.env_vars
            )
            
            if result.returncode == 0:
                self._show_success("✅ 所有依赖都已满足")
                return True
            
            # 解析依赖冲突信息
            conflicts = result.stdout.strip().split('\n') if result.stdout else []
            conflicts.extend(result.stderr.strip().split('\n') if result.stderr else [])
            
            missing_packages = set()
            
            for conflict in conflicts:
                if not conflict.strip():
                    continue
                    
                self._show_warning(f"⚠️ 依赖冲突: {conflict}")
                
                # 解析缺失的包名
                # 格式通常是: "package_name X.X.X requires missing_package, which is not installed."
                if "requires" in conflict and "which is not installed" in conflict:
                    # 提取缺失的包名
                    parts = conflict.split("requires")
                    if len(parts) > 1:
                        missing_part = parts[1].split(",")[0].strip()
                        # 移除版本约束，只保留包名
                        missing_pkg = missing_part.split()[0].strip()
                        if missing_pkg and missing_pkg not in ['which', 'is', 'not']:
                            missing_packages.add(missing_pkg)
            
            if not missing_packages:
                self._show_info("ℹ️ 未发现明确的缺失包，尝试升级pip和setuptools")
                # 如果没有明确的缺失包，尝试升级基础包
                base_packages = ["pip", "setuptools", "wheel"]
                for pkg in base_packages:
                    self._try_pip_install(f"{pkg} --upgrade")
                return True
            
            # 安装缺失的包
            self._show_info(f"📦 发现 {len(missing_packages)} 个缺失的依赖包: {', '.join(missing_packages)}")
            
            success_count = 0
            for missing_pkg in missing_packages:
                self._show_info(f"   🔄 安装缺失依赖: {missing_pkg}")
                if self._try_pip_install(missing_pkg):
                    self._show_success(f"   ✅ 成功安装: {missing_pkg}")
                    success_count += 1
                else:
                    self._show_error(f"   ❌ 安装失败: {missing_pkg}")
            
            # 再次检查依赖
            self._show_info("🔄 重新检查依赖...")
            final_check = subprocess.run(
                [pip_executable, "check"],
                capture_output=True,
                text=True,
                env=self.env_vars
            )
            
            if final_check.returncode == 0:
                self._show_success(f"✅ 依赖解析完成，成功安装 {success_count} 个缺失包")
                return True
            else:
                self._show_warning(f"⚠️ 部分依赖问题仍然存在，但已安装 {success_count} 个包")
                # 显示剩余的冲突
                remaining_conflicts = final_check.stdout.strip().split('\n') if final_check.stdout else []
                for conflict in remaining_conflicts:
                    if conflict.strip():
                        self._show_warning(f"   剩余冲突: {conflict}")
                return success_count > 0
                
        except Exception as e:
            self._show_error(f"❌ 依赖解析过程中发生错误: {e}")
            return False
