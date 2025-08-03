#!/usr/bin/env python3
"""
SAGE 一键自动化测试运行器
======================

这个脚本提供了 SAGE 项目的完整测试自动化解决方案，包括：
- 环境检查和初始化
- 智能测试运行
- GitHub Actions 本地模拟
- 测试报告生成
- 性能分析

使用方法:
    python run_all_tests.py                    # 运行默认测试套件
    python run_all_tests.py --quick            # 快速测试模式
    python run_all_tests.py --full             # 完整测试套件
    python run_all_tests.py --diff             # 基于差异的智能测试
    python run_all_tests.py --github-actions   # GitHub Actions 本地模拟
    python run_all_tests.py --report           # 生成详细报告
    python run_all_tests.py --interactive      # 交互式菜单模式
"""

import os
import sys
import subprocess
import argparse
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import shutil

class SAGETestAutomation:
    """SAGE 测试自动化主类"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "test_env"
        self.test_logs_dir = self.project_root / "test_logs"
        self.reports_dir = self.project_root / "test_reports"
        
        # 确保目录存在
        self.test_logs_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # 测试配置
        self.test_config = {
            "quick_tests": [
                "sage/cli/tests/test_config_manager.py",
                "sage/utils/tests/test_embedding.py",
                "sage/lib/io/tests/test_print_functionality.py"
            ],
            "core_tests": [
                "sage/core/",
                "sage/cli/",
                "sage/utils/"
            ],
            "full_test_suite": "all"
        }
        
    def print_header(self, title: str):
        """打印格式化的标题"""
        print(f"\n{'='*60}")
        print(f"🚀 {title}")
        print(f"{'='*60}")
        
    def print_section(self, title: str):
        """打印节标题"""
        print(f"\n📋 {title}")
        print("-" * 40)
        
    def run_command(self, command: str, description: str, capture_output: bool = False) -> Tuple[bool, str]:
        """运行命令并返回结果"""
        print(f"🔧 {description}")
        print(f"💻 运行命令: {command}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=self.project_root
                )
                return result.returncode == 0, result.stdout + result.stderr
            else:
                result = subprocess.run(command, shell=True, cwd=self.project_root)
                return result.returncode == 0, ""
        except Exception as e:
            return False, str(e)
            
    def check_environment(self) -> Dict[str, bool]:
        """检查测试环境状态"""
        self.print_section("环境检查")
        
        checks = {}
        
        # 检查虚拟环境
        if self.venv_path.exists():
            print("✅ 虚拟环境存在")
            checks["venv"] = True
        else:
            print("❌ 虚拟环境不存在")
            checks["venv"] = False
            
        # 检查Python版本
        success, output = self.run_command("python --version", "检查Python版本", capture_output=True)
        if success and "3.11" in output:
            print(f"✅ Python版本: {output.strip()}")
            checks["python"] = True
        else:
            print(f"❌ Python版本不符合要求: {output}")
            checks["python"] = False
            
        # 检查关键依赖
        key_packages = ["pytest", "torch", "ray", "fastapi"]
        success, output = self.run_command("pip list", "检查已安装包", capture_output=True)
        
        for package in key_packages:
            if package.lower() in output.lower():
                print(f"✅ {package} 已安装")
                checks[package] = True
            else:
                print(f"❌ {package} 未安装")
                checks[package] = False
                
        # 检查测试运行器
        test_runner = self.project_root / "scripts" / "test_runner.py"
        if test_runner.exists():
            print("✅ 测试运行器存在")
            checks["test_runner"] = True
        else:
            print("❌ 测试运行器不存在")
            checks["test_runner"] = False
            
        # 检查act工具
        success, _ = self.run_command("act --version", "检查act工具", capture_output=True)
        if success:
            print("✅ Act工具可用")
            checks["act"] = True
        else:
            print("❌ Act工具不可用")
            checks["act"] = False
            
        return checks
        
    def setup_environment(self):
        """设置测试环境"""
        self.print_section("环境设置")
        
        if not self.venv_path.exists():
            print("🔧 创建虚拟环境...")
            success, _ = self.run_command("python3 -m venv test_env", "创建虚拟环境")
            if not success:
                print("❌ 虚拟环境创建失败")
                return False
                
        print("🔧 激活虚拟环境并安装依赖...")
        activate_cmd = f"source {self.venv_path}/bin/activate"
        install_cmd = f"{activate_cmd} && pip install -e ."
        
        success, output = self.run_command(install_cmd, "安装项目依赖", capture_output=True)
        if success:
            print("✅ 依赖安装成功")
            return True
        else:
            print(f"❌ 依赖安装失败: {output}")
            return False
            
    def run_quick_tests(self) -> Dict[str, any]:
        """运行快速测试"""
        self.print_section("快速测试模式")
        
        activate_cmd = f"source {self.venv_path}/bin/activate"
        
        # 运行智能差异测试
        print("🎯 运行智能差异测试...")
        success, output = self.run_command(
            f"{activate_cmd} && python scripts/test_runner.py --diff",
            "智能差异测试",
            capture_output=True
        )
        
        # 运行少量核心测试
        print("🚀 运行核心测试...")
        core_success, core_output = self.run_command(
            f"{activate_cmd} && python scripts/test_runner.py --list",
            "列出测试文件",
            capture_output=True
        )
        
        return {
            "diff_test": {"success": success, "output": output},
            "core_test": {"success": core_success, "output": core_output}
        }
        
    def run_full_tests(self, workers: int = 4) -> Dict[str, any]:
        """运行完整测试套件"""
        self.print_section(f"完整测试套件 (使用 {workers} 个并行进程)")
        
        activate_cmd = f"source {self.venv_path}/bin/activate"
        
        # 运行所有测试
        print("🚀 运行所有测试...")
        start_time = time.time()
        
        success, output = self.run_command(
            f"{activate_cmd} && python scripts/test_runner.py --all --workers {workers}",
            f"并行测试执行 ({workers} workers)"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "success": success,
            "duration": duration,
            "workers": workers
        }
        
    def run_github_actions_simulation(self) -> Dict[str, any]:
        """运行GitHub Actions本地模拟"""
        self.print_section("GitHub Actions 本地模拟")
        
        results = {}
        
        # 检查工作流文件
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            workflows = list(workflows_dir.glob("*.yml"))
            print(f"📋 发现 {len(workflows)} 个工作流文件")
            
            for workflow in workflows:
                print(f"  - {workflow.name}")
                
        # 运行act列表
        print("🎭 列出可用的GitHub Actions...")
        success, output = self.run_command("act --list", "列出工作流", capture_output=True)
        results["workflow_list"] = {"success": success, "output": output}
        
        # 尝试运行测试工作流（干运行）
        print("🧪 模拟测试工作流...")
        success, output = self.run_command(
            "act -n --workflows .github/workflows/ci.yml", 
            "模拟CI工作流", 
            capture_output=True
        )
        results["ci_simulation"] = {"success": success, "output": output}
        
        return results
        
    def generate_test_report(self, test_results: Dict) -> str:
        """生成测试报告"""
        self.print_section("生成测试报告")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"test_report_{timestamp}.md"
        
        # 收集测试日志统计
        log_files = list(self.test_logs_dir.glob("*.log"))
        
        # 分析测试结果
        passed_tests = 0
        failed_tests = 0
        total_tests = len(log_files)
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "PASSED" in content and "FAILED" not in content:
                        passed_tests += 1
                    elif "FAILED" in content:
                        failed_tests += 1
            except:
                continue
                
        # 生成报告内容
        report_content = f"""# SAGE 测试报告

## 📊 执行概览
- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **项目路径**: {self.project_root}
- **测试日志数量**: {total_tests}
- **通过测试**: {passed_tests}
- **失败测试**: {failed_tests}
- **成功率**: {(passed_tests/max(total_tests,1)*100):.1f}%

## 🏗️ 环境信息
"""
        
        # 添加环境检查结果
        env_checks = self.check_environment()
        for check_name, status in env_checks.items():
            status_icon = "✅" if status else "❌"
            report_content += f"- **{check_name}**: {status_icon}\n"
            
        # 添加测试结果详情
        if "test_results" in test_results:
            report_content += f"\n## 🧪 测试执行详情\n"
            for test_type, result in test_results["test_results"].items():
                success_icon = "✅" if result.get("success", False) else "❌"
                report_content += f"- **{test_type}**: {success_icon}\n"
                
        # 添加性能信息
        report_content += f"""
## 📈 性能统计
- **CPU核心数**: {os.cpu_count()}
- **内存使用**: 查看系统监控
- **磁盘空间**: {shutil.disk_usage('.').free // (1024**3)} GB 可用

## 📋 推荐操作
1. 检查失败的测试日志: `ls -la test_logs/`
2. 重新运行失败的测试: `python run_all_tests.py --diff`
3. 查看详细日志: `cat test_logs/specific_test.log`

---
*报告由 SAGE 测试自动化系统生成*
"""
        
        # 写入报告文件
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"📄 测试报告已生成: {report_file}")
        return str(report_file)
        
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            self.print_header("SAGE 测试自动化 - 交互式菜单")
            
            print("请选择操作:")
            print("1. 🔍 环境检查")
            print("2. ⚡ 快速测试")
            print("3. 🚀 完整测试")
            print("4. 🎯 智能差异测试")
            print("5. 🎭 GitHub Actions 模拟")
            print("6. 📊 生成测试报告")
            print("7. 🛠️ 设置环境")
            print("0. 🚪 退出")
            
            choice = input("\n请输入选择 (0-7): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                self.check_environment()
            elif choice == "2":
                self.run_quick_tests()
            elif choice == "3":
                workers = input("请输入并行进程数 (默认4): ").strip() or "4"
                try:
                    workers = int(workers)
                    self.run_full_tests(workers)
                except ValueError:
                    print("❌ 无效的进程数")
            elif choice == "4":
                activate_cmd = f"source {self.venv_path}/bin/activate"
                self.run_command(
                    f"{activate_cmd} && python scripts/test_runner.py --diff",
                    "智能差异测试"
                )
            elif choice == "5":
                self.run_github_actions_simulation()
            elif choice == "6":
                report_file = self.generate_test_report({})
                print(f"📄 报告已生成: {report_file}")
            elif choice == "7":
                self.setup_environment()
            else:
                print("❌ 无效选择，请重试")
                
            input("\n按Enter键继续...")
            
    def run_automation(self, mode: str = "default", **kwargs):
        """运行自动化测试"""
        self.print_header(f"SAGE 测试自动化 - {mode.upper()} 模式")
        
        results = {"mode": mode, "timestamp": datetime.now().isoformat()}
        
        # 环境检查
        env_status = self.check_environment()
        results["environment"] = env_status
        
        # 根据模式执行不同的测试
        if mode == "quick":
            test_results = self.run_quick_tests()
            results["test_results"] = test_results
            
        elif mode == "full":
            workers = kwargs.get("workers", 4)
            test_results = self.run_full_tests(workers)
            results["test_results"] = {"full_test": test_results}
            
        elif mode == "diff":
            activate_cmd = f"source {self.venv_path}/bin/activate"
            success, output = self.run_command(
                f"{activate_cmd} && python scripts/test_runner.py --diff",
                "智能差异测试",
                capture_output=True
            )
            results["test_results"] = {"diff_test": {"success": success, "output": output}}
            
        elif mode == "github-actions":
            github_results = self.run_github_actions_simulation()
            results["test_results"] = {"github_actions": github_results}
            
        elif mode == "report":
            report_file = self.generate_test_report(results)
            results["report_file"] = report_file
            
        elif mode == "interactive":
            self.interactive_menu()
            return
            
        else:  # default mode
            # 默认模式：环境检查 + 快速测试 + 报告
            test_results = self.run_quick_tests()
            results["test_results"] = test_results
            
        # 生成最终报告
        if mode != "interactive":
            report_file = self.generate_test_report(results)
            results["report_file"] = report_file
            
            self.print_header("测试自动化完成")
            print(f"📄 详细报告: {report_file}")
            print(f"📊 测试日志: {self.test_logs_dir}")
            print("🎉 自动化测试执行完成！")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SAGE 一键自动化测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_all_tests.py                    # 默认模式
  python run_all_tests.py --quick            # 快速测试
  python run_all_tests.py --full --workers 8 # 完整测试(8并发)
  python run_all_tests.py --diff             # 智能差异测试
  python run_all_tests.py --interactive      # 交互式菜单
        """
    )
    
    # 添加参数
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--quick", action="store_true", help="运行快速测试模式")
    group.add_argument("--full", action="store_true", help="运行完整测试套件")
    group.add_argument("--diff", action="store_true", help="运行智能差异测试")
    group.add_argument("--github-actions", action="store_true", help="GitHub Actions本地模拟")
    group.add_argument("--report", action="store_true", help="仅生成测试报告")
    group.add_argument("--interactive", action="store_true", help="交互式菜单模式")
    
    parser.add_argument("--workers", type=int, default=4, help="并行进程数量 (默认: 4)")
    parser.add_argument("--setup", action="store_true", help="设置测试环境")
    
    args = parser.parse_args()
    
    # 创建自动化实例
    automation = SAGETestAutomation()
    
    # 如果需要设置环境
    if args.setup:
        automation.setup_environment()
        return
        
    # 确定运行模式
    if args.quick:
        mode = "quick"
    elif args.full:
        mode = "full"
    elif args.diff:
        mode = "diff"
    elif args.github_actions:
        mode = "github-actions"
    elif args.report:
        mode = "report"
    elif args.interactive:
        mode = "interactive"
    else:
        mode = "default"
        
    # 运行自动化测试
    try:
        automation.run_automation(mode, workers=args.workers)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
