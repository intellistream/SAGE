#!/usr/bin/env python3
"""
SAGE模块化安装系统
主入口点 - 替代复杂的quickstart.sh脚本

使用方法:
    python3 install.py                    # 交互式安装
    python3 install.py --dev             # 开发模式
    python3 install.py --profile quick   # 使用快速安装配置
    python3 install.py --env-name my-env # 指定环境名称
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# 添加当前目录到Python路径，以便导入模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from core import EnvironmentManager, PackageInstaller, DependencyChecker, SubmoduleManager
from utils import ProgressTracker, UserInterface, Validator
from config import get_profile, list_profiles, get_profile_recommendations


class SAGEInstaller:
    """SAGE安装系统主类"""
    
    def __init__(self, project_root: str = None):
        """
        初始化安装器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root or self._find_project_root())
        self.ui = UserInterface()
        self.progress = ProgressTracker()
        
        # 初始化各种管理器
        self.env_manager = EnvironmentManager(str(self.project_root))
        self.dependency_checker = DependencyChecker(str(self.project_root))
        self.submodule_manager = SubmoduleManager(str(self.project_root))
        
        # 安装配置
        self.config = {
            "profile": None,
            "env_name": None,
            "python_version": "3.11",
            "force_reinstall": False,
            "quiet_mode": False,
            "skip_validation": False
        }
        
        # 设置日志
        self._setup_logging()
    
    def _find_project_root(self) -> str:
        """查找项目根目录"""
        current = Path(__file__).parent
        
        # 向上查找包含pyproject.toml的目录
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return str(current)
            current = current.parent
        
        # 如果没找到，使用当前目录的上级目录
        return str(Path(__file__).parent.parent.parent)
    
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.project_root / "install.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def parse_arguments(self) -> argparse.Namespace:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="SAGE模块化安装系统",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  python3 install.py                      # 交互式安装
  python3 install.py --dev               # 开发模式安装
  python3 install.py --profile quick     # 快速安装
  python3 install.py --env-name my-sage  # 指定环境名称
  python3 install.py --quiet             # 静默模式
            """
        )
        
        parser.add_argument(
            "--profile", "-p",
            choices=list_profiles(),
            help="选择安装配置文件"
        )
        
        parser.add_argument(
            "--env-name", "-e",
            help="conda环境名称"
        )
        
        parser.add_argument(
            "--python-version",
            default="3.11",
            help="Python版本 (默认: 3.11)"
        )
        
        parser.add_argument(
            "--dev", "--development",
            action="store_true",
            help="开发模式安装（等同于 --profile development）"
        )
        
        parser.add_argument(
            "--prod", "--production", 
            action="store_true",
            help="生产模式安装（等同于 --profile production）"
        )
        
        parser.add_argument(
            "--minimal",
            action="store_true",
            help="最小化安装（等同于 --profile minimal）"
        )
        
        parser.add_argument(
            "--force",
            action="store_true",
            help="强制重新安装，即使环境已存在"
        )
        
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="静默模式，减少输出"
        )
        
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="跳过安装后验证"
        )
        
        parser.add_argument(
            "--list-profiles",
            action="store_true",
            help="列出所有可用的安装配置文件"
        )
        
        return parser.parse_args()
    
    def show_profile_list(self):
        """显示可用的安装配置文件"""
        profiles = list_profiles()
        
        print("🎯 可用的安装配置文件:")
        print("=" * 50)
        
        for profile_name in profiles:
            profile = get_profile(profile_name)
            if profile:
                print(f"\n📋 {profile_name}")
                print(f"   名称: {profile.name}")
                print(f"   描述: {profile.description}")
                print(f"   包数量: {len(profile.packages)}")
                print(f"   子模块: {'是' if profile.install_submodules else '否'}")
    
    def configure_from_args(self, args: argparse.Namespace):
        """根据命令行参数配置安装器"""
        # 设置配置文件
        if args.dev:
            self.config["profile"] = "development"
        elif args.prod:
            self.config["profile"] = "production"
        elif args.minimal:
            self.config["profile"] = "minimal"
        elif args.profile:
            self.config["profile"] = args.profile
        
        # 其他配置
        self.config.update({
            "env_name": args.env_name,
            "python_version": args.python_version,
            "force_reinstall": args.force,
            "quiet_mode": args.quiet,
            "skip_validation": args.skip_validation
        })
        
        # 更新UI静默模式
        self.ui.quiet_mode = args.quiet
    
    def interactive_setup(self):
        """交互式设置"""
        self.ui.show_welcome("SAGE安装向导")
        
        # 选择安装配置文件
        if not self.config["profile"]:
            self.ui.show_section("选择安装模式")
            
            profiles = list_profiles()
            profile_descriptions = []
            
            for profile_name in profiles:
                profile = get_profile(profile_name)
                if profile:
                    profile_descriptions.append(f"{profile.name} - {profile.description}")
            
            choice = self.ui.show_menu(
                "请选择安装模式:",
                profile_descriptions,
                default=2  # 默认选择standard
            )
            
            self.config["profile"] = profiles[choice]
        
        # 获取环境名称
        if not self.config["env_name"]:
            profile_suffix = get_profile(self.config["profile"]).environment_suffix
            default_name = f"sage-{profile_suffix}"
            
            self.config["env_name"] = self.ui.get_input(
                "输入conda环境名称",
                default=default_name,
                validator=lambda x: len(x.strip()) > 0,
                error_message="环境名称不能为空"
            )
    
    def run_dependency_check(self) -> bool:
        """运行依赖检查"""
        self.ui.show_section("系统依赖检查")
        self.progress.start_step("dependency_check", "检查系统依赖...")
        
        try:
            checks = self.dependency_checker.run_comprehensive_check()
            
            # 显示检查结果
            passed = sum(1 for success, _ in checks.values() if success)
            total = len(checks)
            
            if passed == total:
                self.progress.complete_step("dependency_check", "所有依赖检查通过")
                return True
            else:
                self.progress.fail_step(
                    "dependency_check", 
                    f"{total - passed} 项检查失败"
                )
                
                # 显示详细报告
                if not self.config["quiet_mode"]:
                    report = self.dependency_checker.generate_check_report(checks)
                    print("\n" + report)
                
                # 询问是否继续
                if not self.ui.get_yes_no("是否继续安装？", default=False):
                    return False
                
                return True
                
        except Exception as e:
            self.progress.fail_step("dependency_check", str(e))
            return False
    
    def setup_environment(self) -> bool:
        """设置conda环境"""
        env_name = self.config["env_name"]
        python_version = self.config["python_version"]
        
        self.ui.show_section(f"设置环境: {env_name}")
        
        # 检查环境是否已存在
        if self.env_manager.environment_exists(env_name):
            if self.config["force_reinstall"]:
                self.progress.start_step("delete_env", f"删除现有环境: {env_name}")
                if self.env_manager.delete_environment(env_name):
                    self.progress.complete_step("delete_env")
                else:
                    self.progress.fail_step("delete_env", "删除环境失败")
                    return False
            else:
                self.ui.show_info(f"环境 {env_name} 已存在，将使用现有环境")
                self.progress.complete_step("create_env", f"使用现有环境: {env_name}")
                return True
        
        # 创建新环境
        self.progress.start_step("create_env", f"创建conda环境: {env_name}")
        if self.env_manager.create_environment(env_name, python_version):
            self.progress.complete_step("create_env")
            return True
        else:
            self.progress.fail_step("create_env", "创建环境失败")
            return False
    
    def install_packages(self) -> bool:
        """安装Python包"""
        profile = get_profile(self.config["profile"])
        env_name = self.config["env_name"]
        
        self.ui.show_section("安装Python包")
        
        # 获取环境变量
        env_vars = self.env_manager.activate_environment(env_name)
        package_installer = PackageInstaller(str(self.project_root), env_vars)
        
        # Check if requirements file is used
        if "use_requirements" in profile.additional_config:
            requirements_file = profile.additional_config["use_requirements"]
            requirements_path = self.project_root / "scripts" / "requirements" / requirements_file
            
            self.progress.start_step("requirements_install", f"安装requirements: {requirements_file}")
            
            if requirements_path.exists():
                if package_installer.install_requirements_file(str(requirements_path)):
                    self.progress.complete_step("requirements_install")
                    # requirements文件已经包含了所有SAGE包的开发安装，直接返回成功
                    return True
                else:
                    self.progress.fail_step("requirements_install", "Requirements安装失败")
                    return False
            else:
                self.progress.fail_step("requirements_install", f"Requirements文件不存在: {requirements_path}")
                return False
        
        # 如果没有使用requirements文件，则继续传统的安装方式
        
        # 安装conda包
        if profile.conda_packages:
            self.progress.start_step("conda_packages", "安装conda包...")
            conda_success = True
            for package in profile.conda_packages:
                if not package_installer.install_package(package, use_conda=True):
                    conda_success = False
                    break
            
            if conda_success:
                self.progress.complete_step("conda_packages")
            else:
                self.progress.fail_step("conda_packages", "部分conda包安装失败")
        
        # 分离本地SAGE包和外部依赖包
        local_sage_packages = {"sage", "sage-common", "sage-kernel", "sage-middleware"}
        pip_packages = [pkg for pkg in profile.packages 
                       if pkg not in profile.conda_packages and pkg not in local_sage_packages]
        
        # 安装外部依赖包（pip）
        if pip_packages:
            self.progress.start_step("pip_packages", "安装外部依赖包...")
            results = package_installer.install_packages(pip_packages, use_conda=False)
            failed_packages = [pkg for pkg, success in results.items() if not success]
            
            if not failed_packages:
                self.progress.complete_step("pip_packages")
            else:
                self.progress.fail_step("pip_packages", f"{len(failed_packages)} 个包安装失败")
                self.ui.show_warning(f"失败的包: {', '.join(failed_packages)}")
        
        # 安装本地SAGE包（从源代码）
        self.progress.start_step("sage_packages", "安装SAGE本地包...")
        sage_packages_success = True
        
        for package_name in ["sage-common", "sage-kernel", "sage-middleware", "sage"]:
            package_path = self.project_root / "packages" / package_name
            if package_path.exists():
                if not package_installer.install_local_package(str(package_path)):
                    sage_packages_success = False
        
        if sage_packages_success:
            self.progress.complete_step("sage_packages")
        else:
            self.progress.fail_step("sage_packages", "SAGE包安装失败")
            return False
        
        return True
    
    def setup_submodules(self) -> bool:
        """设置Git子模块"""
        profile = get_profile(self.config["profile"])
        
        if not profile.install_submodules:
            return True
        
        self.ui.show_section("设置Git子模块")
        self.progress.start_step("submodules", "初始化和更新子模块...")
        
        try:
            if self.submodule_manager.initialize_submodules():
                self.progress.complete_step("submodules")
                return True
            else:
                self.progress.fail_step("submodules", "子模块设置失败")
                return False
        except Exception as e:
            self.progress.fail_step("submodules", str(e))
            return False
    
    def run_validation(self) -> bool:
        """运行安装验证"""
        if self.config["skip_validation"]:
            return True
        
        self.ui.show_section("验证安装")
        self.progress.start_step("validation", "验证安装结果...")
        
        try:
            env_name = self.config["env_name"]
            env_vars = self.env_manager.activate_environment(env_name)
            validator = Validator(str(self.project_root))
            
            validation_results = validator.run_comprehensive_validation(env_name, env_vars)
            
            if validation_results.get("overall_success", False):
                self.progress.complete_step("validation", "验证通过")
                return True
            else:
                self.progress.fail_step("validation", "验证发现问题")
                
                if not self.config["quiet_mode"]:
                    report = validator.generate_validation_report(validation_results)
                    print("\n" + report)
                
                return False
                
        except Exception as e:
            self.progress.fail_step("validation", str(e))
            return False
    
    def show_completion_info(self):
        """显示安装完成信息"""
        env_name = self.config["env_name"]
        profile = get_profile(self.config["profile"])
        
        self.ui.show_section("安装完成")
        self.ui.show_success("🎉 SAGE安装成功完成！")
        
        # 显示环境信息
        info_data = {
            "conda环境": env_name,
            "安装模式": profile.name,
            "Python版本": self.config["python_version"],
            "包数量": len(profile.packages),
            "项目根目录": str(self.project_root)
        }
        
        self.ui.show_key_value(info_data, "环境信息")
        
        # 显示使用说明
        activation_cmd = f"conda activate {env_name}"
        self.ui.show_info(f"激活环境: {activation_cmd}")
        self.ui.show_info("测试安装: python -c 'import sage; print(\"SAGE安装成功!\")'")
        
        # 显示进度摘要
        summary = self.progress.get_summary()
        self.ui.show_progress_summary(summary)
    
    def run(self, args: argparse.Namespace = None) -> bool:
        """运行安装流程"""
        try:
            if not args:
                args = self.parse_arguments()
            
            # 处理特殊命令
            if args.list_profiles:
                self.show_profile_list()
                return True
            
            # 配置安装器
            self.configure_from_args(args)
            
            # 交互式设置（如果需要）
            if not self.config["profile"] or not self.config["env_name"]:
                self.interactive_setup()
            
            # 初始化进度跟踪
            steps = [
                ("dependency_check", "系统依赖检查"),
                ("create_env", "创建conda环境"),
                ("requirements_install", "安装requirements文件"),
                ("conda_packages", "安装conda包"),
                ("pip_packages", "安装外部依赖"),
                ("sage_packages", "安装SAGE源代码包"),
                ("submodules", "设置Git子模块"),
                ("validation", "验证安装")
            ]
            
            for step_name, description in steps:
                self.progress.add_step(step_name, description)
            
            # 执行安装步骤
            self.logger.info(f"开始SAGE安装 - 配置: {self.config['profile']}, 环境: {self.config['env_name']}")
            
            if not self.run_dependency_check():
                return False
            
            if not self.setup_environment():
                return False
            
            if not self.install_packages():
                return False
            
            if not self.setup_submodules():
                return False
            
            if not self.run_validation():
                return False
            
            # 显示完成信息
            self.show_completion_info()
            
            self.logger.info("SAGE安装成功完成")
            return True
            
        except KeyboardInterrupt:
            self.ui.show_warning("\n安装被用户取消")
            return False
        except Exception as e:
            self.logger.error(f"安装过程中发生错误: {e}")
            self.ui.show_error(f"安装失败: {e}")
            return False
        finally:
            self.progress.print_summary()


def main():
    """主函数"""
    installer = SAGEInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
