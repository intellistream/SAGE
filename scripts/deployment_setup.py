#!/usr/bin/env python3
"""
SAGE 项目一键部署脚本
提供简单的命令来初始化和管理 SAGE 项目及其文档仓库
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
from typing import List, Optional


class Colors:
    """终端颜色输出"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SAGESetup:
    """SAGE 项目部署管理器"""
    
    def __init__(self):
        # 获取脚本的绝对路径，然后找到项目根目录
        script_path = Path(__file__).resolve()
        self.repo_root = script_path.parent
        
        # 确保我们在正确的SAGE项目目录
        while not (self.repo_root / "pyproject.toml").exists() and self.repo_root.parent != self.repo_root:
            self.repo_root = self.repo_root.parent
            
        if not (self.repo_root / "pyproject.toml").exists():
            self.print_colored("❌ 错误: 无法找到SAGE项目根目录", Colors.FAIL)
            sys.exit(1)
            
        self.docs_public_path = self.repo_root / "docs-public"
        self.requirements_files = [
            "scripts/requirements/requirements.txt",
            "scripts/requirements/requirements-dev.txt"
        ]
        
    def print_colored(self, message: str, color: str = Colors.OKGREEN):
        """打印彩色消息"""
        print(f"{color}{message}{Colors.ENDC}")
        
    def print_header(self, message: str):
        """打印标题"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{message.center(60)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
        """执行命令"""
        if cwd is None:
            cwd = self.repo_root
            
        self.print_colored(f"🔧 执行命令: {' '.join(cmd)}", Colors.OKCYAN)
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                check=check, 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            self.print_colored(f"❌ 命令执行失败: {e}", Colors.FAIL)
            if e.stderr:
                print(f"错误输出: {e.stderr}")
            if check:
                sys.exit(1)
            return e
    
    def check_git_installed(self) -> bool:
        """检查Git是否安装"""
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_python_installed(self) -> bool:
        """检查Python是否安装"""
        try:
            subprocess.run([sys.executable, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def init_submodules(self) -> bool:
        """初始化Git submodules"""
        self.print_header("初始化 Git Submodules")
        
        if not self.check_git_installed():
            self.print_colored("❌ 错误: 未找到Git，请先安装Git", Colors.FAIL)
            return False
        
        # 检查是否在Git仓库中
        if not (self.repo_root / ".git").exists():
            self.print_colored("❌ 错误: 当前目录不是Git仓库", Colors.FAIL)
            return False
        
        try:
            # 初始化submodule
            self.print_colored("📥 初始化submodules...", Colors.OKBLUE)
            self.run_command(["git", "submodule", "init"])
            
            # 更新submodule
            self.print_colored("🔄 更新submodules...", Colors.OKBLUE)
            self.run_command(["git", "submodule", "update"])
            
            # 如果docs-public不存在，尝试添加
            if not self.docs_public_path.exists():
                self.print_colored("📁 添加SAGE-Pub文档仓库...", Colors.OKBLUE)
                self.run_command([
                    "git", "submodule", "add", 
                    "https://github.com/intellistream/SAGE-Pub.git", 
                    "docs-public"
                ])
            
            self.print_colored("✅ Submodules初始化完成", Colors.OKGREEN)
            return True
            
        except Exception as e:
            self.print_colored(f"❌ Submodule初始化失败: {e}", Colors.FAIL)
            return False
    
    def install_dependencies(self, dev: bool = False) -> bool:
        """安装Python依赖"""
        self.print_header("安装Python依赖")
        
        if not self.check_python_installed():
            self.print_colored("❌ 错误: 未找到Python，请先安装Python", Colors.FAIL)
            return False
        
        try:
            # 升级pip
            self.print_colored("⬆️ 升级pip...", Colors.OKBLUE)
            self.run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            
            # 安装主要依赖
            for req_file in self.requirements_files:
                req_path = self.repo_root / req_file
                if req_path.exists():
                    self.print_colored(f"📦 安装 {req_file}...", Colors.OKBLUE)
                    self.run_command([sys.executable, "-m", "pip", "install", "-r", str(req_path)])
            
            # 如果是开发模式，安装额外的开发依赖
            if dev:
                dev_packages = [
                    "pytest>=7.0",
                    "black>=22.0",
                    "flake8>=4.0",
                    "mypy>=0.910",
                    "pre-commit>=2.15"
                ]
                self.print_colored("🛠️ 安装开发工具...", Colors.OKBLUE)
                self.run_command([sys.executable, "-m", "pip", "install"] + dev_packages)
                
                # 安装pre-commit hooks
                if shutil.which("pre-commit"):
                    self.print_colored("🪝 安装pre-commit hooks...", Colors.OKBLUE)
                    self.run_command(["pre-commit", "install"])
            
            # 安装SAGE包（开发模式）
            self.print_colored("🔧 安装SAGE包（开发模式）...", Colors.OKBLUE)
            sage_packages = [
                "packages/sage",
                "packages/sage-kernel", 
                "packages/sage-middleware",
                "packages/sage-userspace",
                "packages/sage-tools/sage-dev-toolkit",
                "packages/sage-tools/sage-frontend"
            ]
            
            for package_dir in sage_packages:
                package_path = self.repo_root / package_dir
                if package_path.exists() and (package_path / "pyproject.toml").exists():
                    self.print_colored(f"📦 安装 {package_dir}...", Colors.OKBLUE)
                    self.run_command([sys.executable, "-m", "pip", "install", "-e", str(package_path)])
            
            # 安装文档依赖
            docs_req = self.docs_public_path / "requirements.txt"
            if docs_req.exists():
                self.print_colored("📚 安装文档依赖...", Colors.OKBLUE)
                self.run_command([sys.executable, "-m", "pip", "install", "-r", str(docs_req)])
            
            self.print_colored("✅ 依赖安装完成", Colors.OKGREEN)
            return True
            
        except Exception as e:
            self.print_colored(f"❌ 依赖安装失败: {e}", Colors.FAIL)
            return False
    
    def build_project(self) -> bool:
        """构建项目"""
        self.print_header("构建SAGE项目")
        
        try:
            # 检查是否有构建脚本
            build_script = self.repo_root / "scripts" / "build.sh"
            if build_script.exists():
                self.print_colored("🔨 执行构建脚本...", Colors.OKBLUE)
                self.run_command(["bash", str(build_script)])
            
            # 构建文档
            if self.docs_public_path.exists():
                self.print_colored("📖 构建文档...", Colors.OKBLUE)
                self.run_command(["mkdocs", "build"], cwd=self.docs_public_path)
            
            self.print_colored("✅ 项目构建完成", Colors.OKGREEN)
            return True
            
        except Exception as e:
            self.print_colored(f"❌ 项目构建失败: {e}", Colors.FAIL)
            return False
    
    def run_tests(self) -> bool:
        """运行测试"""
        self.print_header("运行测试") # TODO:让它调用sage-dev里边的测试方法
        
        try:
            # 查找并运行pytest
            test_dirs = ["tests", "packages/*/tests"]
            for test_pattern in test_dirs:
                test_paths = list(self.repo_root.glob(test_pattern))
                for test_path in test_paths:
                    if test_path.is_dir():
                        self.print_colored(f"🧪 运行测试: {test_path.relative_to(self.repo_root)}", Colors.OKBLUE)
                        self.run_command([sys.executable, "-m", "pytest", str(test_path), "-v"])
            
            self.print_colored("✅ 测试完成", Colors.OKGREEN)
            return True
            
        except Exception as e:
            self.print_colored(f"❌ 测试失败: {e}", Colors.FAIL)
            return False
    
    def status_check(self) -> None:
        """检查项目状态"""
        self.print_header("SAGE项目状态检查")
        
        # 检查Git状态
        try:
            result = self.run_command(["git", "status", "--porcelain"], check=False)
            if result.returncode == 0:
                if result.stdout.strip():
                    self.print_colored("📝 Git工作区有未提交的更改", Colors.WARNING)
                else:
                    self.print_colored("✅ Git工作区干净", Colors.OKGREEN)
            else:
                self.print_colored("❌ 无法获取Git状态", Colors.FAIL)
        except:
            self.print_colored("❌ Git状态检查失败", Colors.FAIL)
        
        # 检查submodule状态
        if self.docs_public_path.exists():
            self.print_colored("✅ docs-public submodule 存在", Colors.OKGREEN)
        else:
            self.print_colored("❌ docs-public submodule 缺失", Colors.FAIL)
        
        # 检查Python包
        sage_packages = [
            ("sage", "sage"),
            ("sage.kernel", "sage-kernel"),
            ("sage.middleware", "sage-middleware"),
            ("sage.apps", "sage-apps"),
            ("sage_dev_toolkit", "sage-dev-toolkit"),
            ("sage_frontend", "sage-frontend")
        ]
        for import_name, display_name in sage_packages:
            try:
                result = self.run_command([sys.executable, "-c", f"import {import_name}"], check=False)
                if result.returncode == 0:
                    self.print_colored(f"✅ {display_name} 包可导入", Colors.OKGREEN)
                else:
                    self.print_colored(f"❌ {display_name} 包无法导入", Colors.WARNING)
            except:
                self.print_colored(f"❌ {display_name} 包检查失败", Colors.FAIL)
        
        # 检查关键命令
        commands = ["git", "python", "pip", "mkdocs"]
        for cmd in commands:
            if shutil.which(cmd):
                self.print_colored(f"✅ {cmd} 可用", Colors.OKGREEN)
            else:
                self.print_colored(f"❌ {cmd} 不可用", Colors.FAIL)
    
    def full_setup(self, dev: bool = False) -> bool:
        """完整项目部署"""
        self.print_header("SAGE项目完整部署")
        
        steps = [
            ("初始化Submodules", self.init_submodules),
            ("安装依赖", lambda: self.install_dependencies(dev)),
            ("构建项目", self.build_project),
        ]
        
        # if dev:
        #     steps.append(("运行测试", self.run_tests))
        
        failed_steps = []
        
        for step_name, step_func in steps:
            self.print_colored(f"\n🚀 开始: {step_name}", Colors.OKBLUE)
            if not step_func():
                failed_steps.append(step_name)
                self.print_colored(f"❌ {step_name} 失败", Colors.FAIL)
            else:
                self.print_colored(f"✅ {step_name} 完成", Colors.OKGREEN)
        
        if failed_steps:
            self.print_colored(f"\n❌ 部署完成，但以下步骤失败: {', '.join(failed_steps)}", Colors.WARNING)
            return False
        else:
            self.print_colored(f"\n🎉 SAGE项目部署完全成功！", Colors.OKGREEN)
            self.print_colored("📖 查看文档: http://127.0.0.1:8000 (运行 'cd docs-public && mkdocs serve')", Colors.OKCYAN)
            return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SAGE项目一键部署脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python setup.py init           # 只初始化submodules
  python setup.py install        # 安装依赖
  python setup.py install --dev  # 安装开发依赖
  python setup.py build          # 构建项目
  python setup.py test           # 运行测试
  python setup.py status         # 检查状态
  python setup.py full           # 完整部署
  python setup.py full --dev     # 完整部署（开发模式）
        """
    )
    
    parser.add_argument(
        "action",
        choices=["init", "install", "build", "test", "status", "full"],
        help="要执行的操作"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式（安装开发依赖和工具）"
    )
    
    args = parser.parse_args()
    
    setup = SAGESetup()
    
    # 显示欢迎信息
    setup.print_colored("""
🌟 欢迎使用SAGE项目部署脚本！
📂 项目目录: {}
🐍 Python版本: {}
    """.format(setup.repo_root, sys.version.split()[0]), Colors.HEADER)
    
    # 执行对应操作
    success = True
    
    if args.action == "init":
        success = setup.init_submodules()
    elif args.action == "install":
        success = setup.install_dependencies(args.dev)
    elif args.action == "build":
        success = setup.build_project()
    elif args.action == "test":
        success = setup.run_tests()
    elif args.action == "status":
        setup.status_check()
    elif args.action == "full":
        success = setup.full_setup(args.dev)
    
    # 显示最终状态
    if args.action != "status":
        if success:
            setup.print_colored("\n🎯 操作成功完成！", Colors.OKGREEN)
        else:
            setup.print_colored("\n💥 操作失败，请检查错误信息", Colors.FAIL)
            sys.exit(1)


if __name__ == "__main__":
    main()
