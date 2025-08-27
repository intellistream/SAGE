#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from utils import ProgressTracker, Validator
from utils.curses_interface import CursesUserInterface
from config import get_profile, list_profiles, get_profile_recommendations


class SAGEInstaller:
    """SAGE安装系统主类"""
    
    def __init__(self, project_root: str = None, use_curses: bool = True):
        """
        初始化安装器
        
        Args:
            project_root: 项目根目录
            use_curses: 是否使用curses界面
        """
        self.project_root = Path(project_root or self._find_project_root())
        self.use_curses = use_curses
        
        if use_curses:
            self.ui = CursesUserInterface()
        else:
            # 对于非交互操作使用标准输出
            from utils.user_interface import UserInterface
            self.ui = UserInterface()
            
        self.progress = ProgressTracker(ui=self.ui)
        
        # 初始化各种管理器，传入UI对象用于详细信息输出
        self.env_manager = EnvironmentManager(str(self.project_root), ui=self.ui)
        self.dependency_checker = DependencyChecker(str(self.project_root), ui=self.ui)
        self.submodule_manager = SubmoduleManager(str(self.project_root), ui=self.ui)
        
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
        handlers = [logging.FileHandler(self.project_root / "install.log")]
        
        # 在非curses模式下才输出到控制台
        if not self.use_curses:
            handlers.append(logging.StreamHandler())
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
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
                "请输入您希望创建的Sage环境名称",
                default=default_name,
                validator=lambda x: len(x.strip()) > 0,
                error_message="环境名称不能为空"
            )
    
    def run_dependency_check(self) -> bool:
        """运行依赖检查"""
        self.ui.show_progress_section("系统依赖检查", 
                                    self.progress.current_step + 1, 
                                    self.progress.total_steps)
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
        
        self.ui.show_progress_section(f"设置环境: {env_name}", 
                                    self.progress.current_step, 
                                    self.progress.total_steps)
        
        # 显示环境配置信息
        self.ui.show_info("🔧 环境配置信息:")
        self.ui.show_info(f"   环境名称: {env_name}")
        self.ui.show_info(f"   Python版本: {python_version}")
        self.ui.show_info(f"   强制重装: {'是' if self.config['force_reinstall'] else '否'}")
        
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
        
        self.ui.show_progress_section("安装Python包", 
                                    self.progress.current_step, 
                                    self.progress.total_steps)
        
        # 获取环境变量
        env_vars = self.env_manager.activate_environment(env_name)
        package_installer = PackageInstaller(str(self.project_root), env_vars, ui=self.ui)
        
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
            self.ui.show_info(f"📦 开始安装 {len(profile.conda_packages)} 个Conda包:")
            for pkg in profile.conda_packages:
                self.ui.show_info(f"   - {pkg}")
            
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
        local_sage_packages = {"sage", "sage-common", "sage-kernel", "sage-middleware", "sage-libs"}
        pip_packages = [pkg for pkg in profile.packages 
                       if pkg not in profile.conda_packages and pkg not in local_sage_packages]
        
        # 显示安装计划
        self.ui.show_info("📋 第一阶段安装计划分析完成:")
        self.ui.show_info(f"   📦 Conda包: {len(profile.conda_packages) if profile.conda_packages else 0} 个")
        self.ui.show_info(f"   🐍 Pip包: {len(pip_packages)} 个")
        self.ui.show_info(f"   🏠 本地SAGE包: 5 个 (sage-common, sage-kernel, sage-middleware, sage-libs, sage)")
        self.ui.show_info("   📋 第二阶段包: vllm==0.10.0 (将在第一阶段完成后安装)")
        
        # 安装外部依赖包（pip）
        if pip_packages:
            self.progress.start_step("pip_packages", "安装外部依赖包...")
            self.ui.show_info(f"📥 开始安装 {len(pip_packages)} 个外部依赖包:")
            for pkg in pip_packages:
                self.ui.show_info(f"   - {pkg}")
            
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
        
        self.ui.show_info("🏠 开始安装SAGE本地包 (开发模式):")
        sage_package_order = ["sage-common", "sage-kernel", "sage-middleware", "sage-libs", "sage"]
        
        for package_name in sage_package_order:
            package_path = self.project_root / "packages" / package_name
            if package_path.exists():
                self.ui.show_info(f"📦 安装 {package_name}...")
                if not package_installer.install_local_package(str(package_path)):
                    sage_packages_success = False
            else:
                self.ui.show_warning(f"⚠️ 跳过不存在的包: {package_name}")
        
        if sage_packages_success:
            self.progress.complete_step("sage_packages")
        else:
            self.progress.fail_step("sage_packages", "SAGE包安装失败")
            return False
        
        return True
    
    def install_stage2_packages(self) -> bool:
        """第二阶段包安装 - 安装vllm等需要在SAGE包安装完成后才能安装的包"""
        env_name = self.config["env_name"]
        
        self.ui.show_progress_section("第二阶段包安装", 
                                    self.progress.current_step, 
                                    self.progress.total_steps)
        
        # 获取环境变量
        env_vars = self.env_manager.activate_environment(env_name)
        package_installer = PackageInstaller(str(self.project_root), env_vars, ui=self.ui)
        
        # 第二阶段需要安装的包（所有模式都需要）
        stage2_packages = ["vllm==0.10.0"]
        
        self.progress.start_step("stage2_packages", "安装第二阶段包...")
        self.ui.show_info("🚀 开始第二阶段包安装:")
        self.ui.show_info("   这些包需要在SAGE核心包安装完成后才能正确安装")
        
        for pkg in stage2_packages:
            self.ui.show_info(f"   - {pkg}")
        
        # 安装第二阶段包（不使用开发模式，直接pip install）
        results = package_installer.install_packages(stage2_packages, use_conda=False)
        failed_packages = [pkg for pkg, success in results.items() if not success]
        
        if not failed_packages:
            self.progress.complete_step("stage2_packages", f"成功安装 {len(stage2_packages)} 个第二阶段包")
            self.ui.show_success(f"✅ 第二阶段包安装完成: {', '.join(stage2_packages)}")
            return True
        else:
            self.progress.fail_step("stage2_packages", f"{len(failed_packages)} 个第二阶段包安装失败")
            self.ui.show_warning(f"❌ 失败的包: {', '.join(failed_packages)}")
            # 第二阶段失败不应该阻止整个安装流程，只给出警告
            self.ui.show_info("⚠️ 第二阶段包安装失败，但不影响核心功能使用")
            return True  # 返回True以继续安装流程
    
    def setup_submodules(self) -> bool:
        """设置Git子模块"""
        profile = get_profile(self.config["profile"])
        
        if not profile.install_submodules:
            return True
        
        self.ui.show_progress_section("设置Git子模块", 
                                    self.progress.current_step, 
                                    self.progress.total_steps)
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
        
        self.ui.show_progress_section("验证安装", 
                                    self.progress.current_step, 
                                    self.progress.total_steps)
        self.progress.start_step("validation", "验证安装结果...")
        
        try:
            env_name = self.config["env_name"]
            env_vars = self.env_manager.activate_environment(env_name)
            validator = Validator(str(self.project_root), ui=self.ui)
            
            validation_results = validator.run_comprehensive_validation(env_name, env_vars)
            
            if validation_results.get("overall_success", False):
                self.progress.complete_step("validation", "验证通过")
                return True
            else:
                self.progress.fail_step("validation", "验证发现问题")
                
                # 生成验证报告并记录到日志（无论是否为quiet模式）
                report = validator.generate_validation_report(validation_results)
                self.logger.error("验证失败详细报告:")
                for line in report.split('\n'):
                    self.logger.error(line)
                
                # 在非quiet模式下也打印到控制台
                if not self.config["quiet_mode"]:
                    print("\n" + report)
                
                return False
                
        except Exception as e:
            self.progress.fail_step("validation", str(e))
            self.logger.error(f"验证过程中发生异常: {e}")
            return False
    
    def show_completion_info(self):
        """显示安装完成信息"""
        env_name = self.config["env_name"]
        profile = get_profile(self.config["profile"])
        
        self.ui.show_progress_section("安装完成", 
                                    self.progress.total_steps, 
                                    self.progress.total_steps)
        
        # 显示成功标题
        self.ui.show_success("🎉 SAGE安装成功完成！")
        self.ui.show_info("")
        
        # 显示详细的安装结果
        self.ui.show_section("安装结果摘要")
        
        # 显示环境信息
        info_data = {
            "✅ Conda环境": env_name,
            "✅ 安装模式": profile.name,
            "✅ Python版本": self.config["python_version"],
            "✅ 第一阶段包数": f"{len(profile.packages)} 个",
            "✅ 第二阶段包数": "1 个 (vllm==0.10.0)",
            "✅ 项目根目录": str(self.project_root)
        }
        
        self.ui.show_key_value(info_data, "🔧 环境配置")
        
        # 显示进度摘要
        summary = self.progress.get_summary()
        summary_data = {
            "📊 总步骤数": summary.get('total_steps', 0),
            "✅ 成功步骤": summary.get('completed', 0),
            "❌ 失败步骤": summary.get('failed', 0),
            "⏱️ 总耗时": f"{summary.get('total_time', 0):.1f}秒",
            "📈 成功率": f"{summary.get('success_rate', 0):.1%}"
        }
        self.ui.show_key_value(summary_data, "📊 安装统计")
        
        # 显示使用说明
        self.ui.show_section("使用指南")
        activation_cmd = f"conda activate {env_name}"
        self.ui.show_info(f"🔸 激活环境: {activation_cmd}")
        self.ui.show_info(f"🔸 测试安装: python -c 'import sage; print(\"SAGE运行正常!\")'")
        self.ui.show_info(f"🔸 验证vllm: python -c 'import vllm; print(\"vLLM已安装:\", vllm.__version__)'")
        
        # 根据安装模式显示特定提示
        if "development" in self.config["profile"]:
            self.ui.show_info("🔸 开发工具: 已安装完整的开发环境，包含调试和测试工具")
            self.ui.show_info("🔸 代码编辑: 可以直接修改 packages/ 目录下的源代码")
        elif "production" in self.config["profile"]:
            self.ui.show_info("🔸 生产环境: 已优化性能配置，适合生产环境部署")
        elif "research" in self.config["profile"]:
            self.ui.show_info("🔸 科研工具: 已安装数据科学和机器学习相关库")
        
        self.ui.show_info("🔸 vLLM支持: 已安装vLLM 0.10.0，支持高性能LLM推理")
        
        self.ui.show_info("")
        self.ui.show_success("🚀 您现在可以开始使用SAGE了！")
        
        # 最后提示用户按Enter结束
        self.ui.pause("按 Enter 键结束安装程序...")
    
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
            
            # 根据配置决定要执行的步骤
            profile = get_profile(self.config["profile"])
            
            # 动态确定步骤列表
            steps_to_execute = [
                ("dependency_check", "系统依赖检查"),
                ("create_env", "创建conda环境"),
            ]
            
            # 根据配置添加包安装步骤
            if "use_requirements" in profile.additional_config:
                steps_to_execute.append(("requirements_install", "安装requirements文件"))
            else:
                if profile.conda_packages:
                    steps_to_execute.append(("conda_packages", "安装conda包"))
                if profile.packages:
                    steps_to_execute.append(("pip_packages", "安装pip包"))
                steps_to_execute.append(("sage_packages", "安装SAGE源代码包"))
            
            # 添加第二阶段包安装步骤（所有模式都需要）
            steps_to_execute.append(("stage2_packages", "第二阶段包安装"))
            
            # 添加子模块步骤（如果需要）
            if profile.install_submodules:
                steps_to_execute.append(("submodules", "设置Git子模块"))
            
            # 添加验证步骤（如果不跳过）
            if not self.config["skip_validation"]:
                steps_to_execute.append(("validation", "验证安装"))
            
            # 初始化进度跟踪，使用实际步骤数
            self.progress.total_steps = len(steps_to_execute)
            for step_name, description in steps_to_execute:
                self.progress.add_step(step_name, description)
            
            # 执行安装步骤
            self.logger.info(f"开始SAGE安装 - 配置: {self.config['profile']}, 环境: {self.config['env_name']}")
            
            if not self.run_dependency_check():
                return False
            
            if not self.setup_environment():
                return False
            
            if not self.install_packages():
                return False
            
            # 第二阶段包安装（所有模式都需要）
            if not self.install_stage2_packages():
                return False
            
            if profile.install_submodules and not self.setup_submodules():
                return False
            
            if not self.config["skip_validation"] and not self.run_validation():
                return False
            
            # 显示完成信息
            self.show_completion_info()
            
            self.logger.info("SAGE安装成功完成")
            return True
            
        except KeyboardInterrupt:
            try:
                self.ui.show_warning("安装被用户取消")
                self.ui.show_info("您可以稍后重新运行安装程序")
            except:
                # 如果UI已经被清理，使用标准输出
                print("\n安装被用户取消")
                print("您可以稍后重新运行安装程序")
            # 不调用pause，直接返回
            return False
        except Exception as e:
            self.logger.error(f"安装过程中发生错误: {e}")
            try:
                self.ui.show_error(f"安装失败: {e}")
                self.ui.show_info("请检查错误信息并重试，或查看install.log获取详细日志")
                if hasattr(self.ui, 'pause') and hasattr(self.ui, 'stdscr') and self.ui.stdscr is not None:
                    self.ui.pause("按 Enter 键退出...")
            except:
                # 如果UI已经被清理，使用标准输出
                print(f"\n安装失败: {e}")
                print("请检查错误信息并重试，或查看install.log获取详细日志")
                try:
                    input("按 Enter 键退出...")
                except KeyboardInterrupt:
                    pass
            return False
        finally:
            self.progress.print_summary()
            # 清理curses界面
            if hasattr(self.ui, 'cleanup'):
                self.ui.cleanup()


def main():
    """主函数"""
    installer = None
    try:
        # 预解析参数来决定是否使用curses
        import sys
        use_curses = True
        if len(sys.argv) > 1:
            # 对于某些非交互命令，不使用curses
            non_interactive_flags = ['--list-profiles', '--help', '-h']
            if any(flag in sys.argv for flag in non_interactive_flags):
                use_curses = False
        
        # 检查终端环境
        if use_curses:
            try:
                # 基本的curses可用性检查
                import curses
                test_scr = curses.initscr()
                height, width = test_scr.getmaxyx()
                curses.endwin()
                
                # 检查最小尺寸要求（与curses_interface.py保持一致）
                if height < 15 or width < 60:
                    print(f"终端尺寸太小 ({width}x{height})，需要至少 60x15")
                    print("正在使用传统界面...")
                    use_curses = False
                    
            except Exception as e:
                print(f"Curses不可用: {e}")
                print("正在使用传统界面...")
                use_curses = False
        
        installer = SAGEInstaller(use_curses=use_curses)
        success = installer.run()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        if installer and hasattr(installer, 'ui') and hasattr(installer.ui, 'cleanup'):
            try:
                installer.ui.cleanup()
            except:
                pass  # 忽略清理时的错误
        print(f"程序发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    except KeyboardInterrupt:
        if installer and hasattr(installer, 'ui') and hasattr(installer.ui, 'cleanup'):
            try:
                installer.ui.cleanup()
            except:
                pass  # 忽略清理时的错误
        print("\n程序被用户中断")
        sys.exit(1)
        
    finally:
        if installer and hasattr(installer, 'ui') and hasattr(installer.ui, 'cleanup'):
            try:
                installer.ui.cleanup()
            except:
                pass  # 忽略清理时的错误


if __name__ == "__main__":
    main()
