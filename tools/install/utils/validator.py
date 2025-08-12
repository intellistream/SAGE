"""
SAGE安装验证器
提供安装结果验证、配置检查和环境健康检查功能
"""

import os
import sys
import subprocess
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


class Validator:
    """安装验证器"""
    
    def __init__(self, project_root: str):
        """
        初始化验证器
        
        Args:
            project_root: SAGE项目根目录
        """
        self.project_root = Path(project_root)
        
    def validate_python_environment(self, env_vars: Dict[str, str] = None) -> Dict[str, Any]:
        """
        验证Python环境
        
        Args:
            env_vars: 环境变量
            
        Returns:
            验证结果字典
        """
        results = {
            "python_executable": {"status": False, "message": "", "details": {}},
            "python_version": {"status": False, "message": "", "details": {}},
            "pip_availability": {"status": False, "message": "", "details": {}}
        }
        
        try:
            # 检查Python可执行文件
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                env=env_vars
            )
            
            if result.returncode == 0:
                python_version = result.stdout.strip()
                results["python_executable"]["status"] = True
                results["python_executable"]["message"] = f"✅ Python可用: {python_version}"
                results["python_executable"]["details"]["version"] = python_version
                results["python_executable"]["details"]["executable"] = sys.executable
                
                # 检查Python版本
                version_parts = python_version.replace("Python ", "").split('.')
                major, minor = int(version_parts[0]), int(version_parts[1])
                
                if major == 3 and 8 <= minor <= 12:
                    results["python_version"]["status"] = True
                    results["python_version"]["message"] = f"✅ Python版本兼容: {python_version}"
                else:
                    results["python_version"]["message"] = f"⚠️ Python版本可能不兼容: {python_version}"
                
                results["python_version"]["details"]["major"] = major
                results["python_version"]["details"]["minor"] = minor
            else:
                results["python_executable"]["message"] = "❌ Python不可用"
            
            # 检查pip
            pip_result = subprocess.run(
                ["pip", "--version"],
                capture_output=True,
                text=True,
                env=env_vars
            )
            
            if pip_result.returncode == 0:
                pip_version = pip_result.stdout.strip()
                results["pip_availability"]["status"] = True
                results["pip_availability"]["message"] = f"✅ pip可用: {pip_version}"
                results["pip_availability"]["details"]["version"] = pip_version
            else:
                results["pip_availability"]["message"] = "❌ pip不可用"
                
        except Exception as e:
            logger.error(f"Python环境验证失败: {e}")
            
        return results
    
    def validate_package_installation(self, 
                                    packages: List[str],
                                    env_vars: Dict[str, str] = None) -> Dict[str, Dict[str, Any]]:
        """
        验证包安装
        
        Args:
            packages: 要验证的包列表
            env_vars: 环境变量
            
        Returns:
            包验证结果字典
        """
        results = {}
        
        for package in packages:
            package_name = package.split('==')[0].split('>=')[0].split('<=')[0]
            
            try:
                # 使用pip show检查包安装
                result = subprocess.run(
                    ["pip", "show", package_name],
                    capture_output=True,
                    text=True,
                    env=env_vars
                )
                
                if result.returncode == 0:
                    # 解析包信息
                    package_info = {}
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            package_info[key.strip().lower()] = value.strip()
                    
                    results[package_name] = {
                        "status": True,
                        "message": f"✅ {package_name} 已安装",
                        "details": package_info
                    }
                else:
                    results[package_name] = {
                        "status": False,
                        "message": f"❌ {package_name} 未安装",
                        "details": {}
                    }
                    
            except Exception as e:
                results[package_name] = {
                    "status": False,
                    "message": f"❌ {package_name} 验证失败: {e}",
                    "details": {}
                }
        
        return results
    
    def validate_sage_packages(self, env_vars: Dict[str, str] = None) -> Dict[str, Any]:
        """
        验证SAGE特定包
        
        Args:
            env_vars: 环境变量
            
        Returns:
            SAGE包验证结果
        """
        sage_packages = [
            "sage",
            "sage-common", 
            "sage-kernel",
            "sage-middleware"
        ]
        
        results = {
            "core_packages": {},
            "import_tests": {},
            "overall_status": False
        }
        
        # 验证包安装
        package_results = self.validate_package_installation(sage_packages, env_vars)
        results["core_packages"] = package_results
        
        # 验证包导入
        for package in sage_packages:
            try:
                # 尝试导入包
                if env_vars:
                    # 在特定环境中运行Python导入测试
                    import_cmd = f"python -c 'import {package.replace('-', '_')}; print(\"OK\")'"
                    result = subprocess.run(
                        import_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        env=env_vars
                    )
                    
                    if result.returncode == 0 and "OK" in result.stdout:
                        results["import_tests"][package] = {
                            "status": True,
                            "message": f"✅ {package} 导入成功"
                        }
                    else:
                        results["import_tests"][package] = {
                            "status": False,
                            "message": f"❌ {package} 导入失败: {result.stderr}"
                        }
                else:
                    # 直接导入测试
                    module_name = package.replace('-', '_')
                    importlib.import_module(module_name)
                    results["import_tests"][package] = {
                        "status": True,
                        "message": f"✅ {package} 导入成功"
                    }
                    
            except Exception as e:
                results["import_tests"][package] = {
                    "status": False,
                    "message": f"❌ {package} 导入失败: {e}"
                }
        
        # 计算总体状态
        all_packages_ok = all(
            result["status"] for result in package_results.values()
        )
        all_imports_ok = all(
            result["status"] for result in results["import_tests"].values()
        )
        
        results["overall_status"] = all_packages_ok and all_imports_ok
        
        return results
    
    def validate_environment_consistency(self, env_name: str) -> Dict[str, Any]:
        """
        验证环境一致性
        
        Args:
            env_name: 环境名称
            
        Returns:
            环境一致性验证结果
        """
        results = {
            "conda_env_exists": {"status": False, "message": ""},
            "conda_env_active": {"status": False, "message": ""},
            "python_path_correct": {"status": False, "message": ""},
            "package_conflicts": {"status": True, "message": "", "conflicts": []}
        }
        
        try:
            # 检查conda环境是否存在
            conda_result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True
            )
            
            if conda_result.returncode == 0:
                env_exists = env_name in conda_result.stdout
                results["conda_env_exists"]["status"] = env_exists
                results["conda_env_exists"]["message"] = (
                    f"✅ 环境 {env_name} 存在" if env_exists 
                    else f"❌ 环境 {env_name} 不存在"
                )
            
            # 检查当前激活的环境
            current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
            if current_env == env_name:
                results["conda_env_active"]["status"] = True
                results["conda_env_active"]["message"] = f"✅ 环境 {env_name} 已激活"
            else:
                results["conda_env_active"]["message"] = f"⚠️ 当前环境: {current_env}, 期望: {env_name}"
            
            # 检查Python路径
            python_executable = sys.executable
            if env_name in python_executable:
                results["python_path_correct"]["status"] = True
                results["python_path_correct"]["message"] = f"✅ Python路径正确: {python_executable}"
            else:
                results["python_path_correct"]["message"] = f"⚠️ Python路径可能不正确: {python_executable}"
            
            # 检查包冲突（简化版）
            pip_result = subprocess.run(
                ["pip", "check"],
                capture_output=True,
                text=True
            )
            
            if pip_result.returncode == 0:
                results["package_conflicts"]["status"] = True
                results["package_conflicts"]["message"] = "✅ 无包依赖冲突"
            else:
                results["package_conflicts"]["status"] = False
                results["package_conflicts"]["message"] = "⚠️ 检测到包依赖冲突"
                results["package_conflicts"]["conflicts"] = pip_result.stdout.split('\n')
                
        except Exception as e:
            logger.error(f"环境一致性验证失败: {e}")
        
        return results
    
    def validate_project_structure(self) -> Dict[str, Any]:
        """
        验证项目结构
        
        Returns:
            项目结构验证结果
        """
        required_paths = {
            "pyproject.toml": "项目配置文件",
            "packages/sage": "SAGE核心包",
            "packages/sage-common": "SAGE通用包",
            "packages/sage-kernel": "SAGE内核包",
            "scripts": "脚本目录",
            "docs": "文档目录"
        }
        
        results = {
            "structure_check": {},
            "permissions_check": {},
            "git_status": {"status": False, "message": ""}
        }
        
        # 检查必需路径
        for path, description in required_paths.items():
            full_path = self.project_root / path
            exists = full_path.exists()
            
            results["structure_check"][path] = {
                "status": exists,
                "message": f"✅ {description}" if exists else f"❌ 缺少 {description}",
                "path": str(full_path)
            }
            
            # 检查权限（如果路径存在）
            if exists:
                readable = os.access(full_path, os.R_OK)
                writable = os.access(full_path, os.W_OK)
                
                results["permissions_check"][path] = {
                    "readable": readable,
                    "writable": writable,
                    "status": readable and writable,
                    "message": "✅ 权限正常" if readable and writable else "⚠️ 权限问题"
                }
        
        # 检查Git状态
        try:
            git_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if git_result.returncode == 0:
                if git_result.stdout.strip():
                    results["git_status"]["message"] = "⚠️ 有未提交的更改"
                else:
                    results["git_status"]["status"] = True
                    results["git_status"]["message"] = "✅ Git工作目录干净"
            else:
                results["git_status"]["message"] = "⚠️ 无法检查Git状态"
                
        except Exception:
            results["git_status"]["message"] = "⚠️ Git不可用"
        
        return results
    
    def run_comprehensive_validation(self, 
                                   env_name: str,
                                   env_vars: Dict[str, str] = None) -> Dict[str, Any]:
        """
        运行全面验证
        
        Args:
            env_name: 环境名称
            env_vars: 环境变量
            
        Returns:
            完整验证结果
        """
        logger.info("🔍 开始全面安装验证...")
        
        validation_results = {
            "python_environment": self.validate_python_environment(env_vars),
            "sage_packages": self.validate_sage_packages(env_vars),
            "environment_consistency": self.validate_environment_consistency(env_name),
            "project_structure": self.validate_project_structure()
        }
        
        # 计算总体状态
        overall_success = True
        for category, results in validation_results.items():
            if isinstance(results, dict):
                if "overall_status" in results:
                    overall_success &= results["overall_status"]
                else:
                    # 检查所有子项状态
                    for item in results.values():
                        if isinstance(item, dict) and "status" in item:
                            overall_success &= item["status"]
        
        validation_results["overall_success"] = overall_success
        
        logger.info(f"📊 验证完成: {'成功' if overall_success else '发现问题'}")
        
        return validation_results
    
    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """
        生成验证报告
        
        Args:
            validation_results: 验证结果
            
        Returns:
            格式化的验证报告
        """
        report_lines = ["🔍 SAGE安装验证报告", "=" * 50, ""]
        
        for category, results in validation_results.items():
            if category == "overall_success":
                continue
                
            report_lines.append(f"📋 {category.replace('_', ' ').title()}")
            report_lines.append("-" * 30)
            
            if isinstance(results, dict):
                for item_name, item_result in results.items():
                    if isinstance(item_result, dict) and "message" in item_result:
                        report_lines.append(f"  {item_result['message']}")
                    elif isinstance(item_result, dict):
                        report_lines.append(f"  {item_name}:")
                        for sub_key, sub_value in item_result.items():
                            if isinstance(sub_value, dict) and "message" in sub_value:
                                report_lines.append(f"    {sub_value['message']}")
            
            report_lines.append("")
        
        # 总结
        overall_success = validation_results.get("overall_success", False)
        if overall_success:
            report_lines.append("🎉 验证通过！SAGE安装成功完成。")
        else:
            report_lines.append("⚠️ 验证发现问题，请检查上述错误并修复。")
        
        return "\n".join(report_lines)
