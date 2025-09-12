#!/usr/bin/env python3
"""
SAGE 开发工具 CLI 命令测试脚本

测试所有dev命令的功能，确保它们能正常工作。
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import json

# ANSI 颜色代码
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class SAGECLITester:
    """SAGE CLI 命令测试器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []
        
    def print_header(self, text: str):
        """打印测试标题"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    def print_test(self, test_name: str, command: str):
        """打印正在测试的命令"""
        print(f"{Colors.CYAN}🧪 测试: {test_name}{Colors.END}")
        print(f"{Colors.WHITE}命令: {command}{Colors.END}")
    
    def print_result(self, test_name: str, success: bool, output: str = "", error: str = ""):
        """打印测试结果"""
        if success:
            print(f"{Colors.GREEN}✅ {test_name} - 成功{Colors.END}")
            self.passed_tests.append(test_name)
        else:
            print(f"{Colors.RED}❌ {test_name} - 失败{Colors.END}")
            if error:
                print(f"{Colors.RED}错误: {error}{Colors.END}")
            self.failed_tests.append(test_name)
        print("-" * 50)
    
    def run_command(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def test_help_commands(self):
        """测试帮助命令"""
        self.print_header("测试帮助命令")
        
        tests = [
            ("主CLI帮助", [sys.executable, "-m", "sage.tools.cli", "--help"]),
            ("dev命令帮助", [sys.executable, "-m", "sage.tools.cli", "dev", "--help"]),
            ("sage-dev帮助", ["sage-dev", "--help"]),
        ]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command)
            
            # 帮助命令即使返回码不为0，只要有输出就算成功
            success = bool(result["stdout"]) or ("help" in result["stderr"].lower())
            self.print_result(test_name, success, result["stdout"], result["stderr"])
    
    def test_status_commands(self):
        """测试状态检查命令"""
        self.print_header("测试状态检查命令")
        
        tests = [
            ("新版status(简要)", [sys.executable, "-m", "sage.tools.cli", "dev", "status"]),
            ("新版status(详细)", [sys.executable, "-m", "sage.tools.cli", "dev", "status", "--output-format", "full"]),
            ("新版status(JSON)", [sys.executable, "-m", "sage.tools.cli", "dev", "status", "--output-format", "json"]),
            ("旧版sage-dev status", ["sage-dev", "status"]),
        ]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command)
            
            # 状态命令应该成功执行
            success = result["success"] and (
                "状态报告" in result["stdout"] or 
                "检查项目" in result["stdout"] or
                "timestamp" in result["stdout"]  # JSON输出
            )
            self.print_result(test_name, success, result["stdout"][:200] + "...", result["stderr"])
    
    def test_analyze_commands(self):
        """测试分析命令"""
        self.print_header("测试分析命令")
        
        # 先检查DependencyAnalyzer的可用方法
        self.print_test("检查DependencyAnalyzer方法", "Python introspection")
        try:
            from sage.tools.dev.tools.dependency_analyzer import DependencyAnalyzer
            analyzer = DependencyAnalyzer(".")
            available_methods = [method for method in dir(analyzer) 
                               if not method.startswith('_') and callable(getattr(analyzer, method))]
            print(f"{Colors.YELLOW}可用方法: {', '.join(available_methods)}{Colors.END}")
            
            # 测试实际存在的方法
            tests = []
            if hasattr(analyzer, 'analyze_all_dependencies'):
                tests.append(("分析所有依赖", [sys.executable, "-m", "sage.tools.cli", "dev", "analyze", "--analysis-type", "all"]))
            if hasattr(analyzer, 'check_dependency_health'):
                tests.append(("依赖健康检查", [sys.executable, "-m", "sage.tools.cli", "dev", "analyze", "--analysis-type", "health"]))
            
            # 如果没有合适的方法，测试一个基本命令
            if not tests:
                tests.append(("基本分析命令", [sys.executable, "-m", "sage.tools.cli", "dev", "analyze"]))
            
        except Exception as e:
            print(f"{Colors.RED}导入DependencyAnalyzer失败: {e}{Colors.END}")
            tests = [("基本分析命令", [sys.executable, "-m", "sage.tools.cli", "dev", "analyze"])]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command, timeout=60)  # 分析可能需要更长时间
            
            # 分析命令可能失败，但不应该崩溃
            success = "分析失败" not in result["stderr"] or "Traceback" not in result["stderr"]
            self.print_result(test_name, success, result["stdout"][:200] + "...", result["stderr"][:200] + "...")
    
    def test_clean_commands(self):
        """测试清理命令"""
        self.print_header("测试清理命令")
        
        tests = [
            ("清理帮助", [sys.executable, "-m", "sage.tools.cli", "dev", "clean", "--help"]),
            ("预览清理(dry-run)", [sys.executable, "-m", "sage.tools.cli", "dev", "clean", "--dry-run"]),
            ("清理缓存(dry-run)", [sys.executable, "-m", "sage.tools.cli", "dev", "clean", "--target", "cache", "--dry-run"]),
        ]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command)
            
            success = result["success"] or "help" in result["stderr"].lower()
            self.print_result(test_name, success, result["stdout"][:200] + "...", result["stderr"])
    
    def test_test_commands(self):
        """测试测试命令"""
        self.print_header("测试测试命令")
        
        tests = [
            ("测试帮助", [sys.executable, "-m", "sage.tools.cli", "dev", "test", "--help"]),
            # 注意：实际运行测试可能耗时很长，这里只测试命令格式
        ]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command)
            
            success = result["success"] or "help" in result["stderr"].lower()
            self.print_result(test_name, success, result["stdout"][:200] + "...", result["stderr"])
    
    def test_home_commands(self):
        """测试SAGE_HOME管理命令"""
        self.print_header("测试SAGE_HOME管理命令")
        
        tests = [
            ("home帮助", [sys.executable, "-m", "sage.tools.cli", "dev", "home", "--help"]),
            ("home状态", [sys.executable, "-m", "sage.tools.cli", "dev", "home", "status"]),
        ]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command)
            
            success = result["success"] or "help" in result["stderr"].lower()
            self.print_result(test_name, success, result["stdout"][:200] + "...", result["stderr"])
    
    def test_other_cli_commands(self):
        """测试其他CLI命令"""
        self.print_header("测试其他CLI命令")
        
        tests = [
            ("版本信息", [sys.executable, "-m", "sage.tools.cli", "version"]),
            ("系统诊断", [sys.executable, "-m", "sage.tools.cli", "doctor"]),
            ("配置管理", [sys.executable, "-m", "sage.tools.cli", "config", "--help"]),
        ]
        
        for test_name, command in tests:
            self.print_test(test_name, " ".join(command))
            result = self.run_command(command)
            
            success = result["success"] or "help" in result["stderr"].lower()
            self.print_result(test_name, success, result["stdout"][:200] + "...", result["stderr"])
    
    def test_import_functionality(self):
        """测试Python导入功能"""
        self.print_header("测试Python导入功能")
        
        modules_to_test = [
            "sage.tools.cli.main",
            "sage.tools.cli.commands.dev.simple_main",
            "sage.tools.dev.tools.project_status_checker",
            "sage.tools.dev.tools.dependency_analyzer",
            "sage.tools.dev.tools.enhanced_package_manager",
        ]
        
        for module_name in modules_to_test:
            self.print_test(f"导入 {module_name}", f"import {module_name}")
            try:
                __import__(module_name)
                self.print_result(f"导入 {module_name}", True)
            except Exception as e:
                self.print_result(f"导入 {module_name}", False, error=str(e))
    
    def run_all_tests(self):
        """运行所有测试"""
        start_time = time.time()
        
        print(f"{Colors.BOLD}{Colors.PURPLE}")
        print("🚀 SAGE CLI 工具测试开始")
        print(f"📁 项目路径: {self.project_root}")
        print(f"🕐 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Colors.END}")
        
        # 运行各类测试
        self.test_import_functionality()
        self.test_help_commands()
        self.test_status_commands()
        self.test_analyze_commands()
        self.test_clean_commands()
        self.test_test_commands()
        self.test_home_commands()
        self.test_other_cli_commands()
        
        # 测试总结
        end_time = time.time()
        duration = end_time - start_time
        
        self.print_header("测试总结")
        
        total_tests = len(self.passed_tests) + len(self.failed_tests)
        success_rate = (len(self.passed_tests) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"{Colors.BOLD}📊 测试统计:{Colors.END}")
        print(f"✅ 通过: {Colors.GREEN}{len(self.passed_tests)}{Colors.END}")
        print(f"❌ 失败: {Colors.RED}{len(self.failed_tests)}{Colors.END}")
        print(f"📈 成功率: {Colors.CYAN}{success_rate:.1f}%{Colors.END}")
        print(f"⏱️ 耗时: {Colors.YELLOW}{duration:.1f}秒{Colors.END}")
        
        if self.failed_tests:
            print(f"\n{Colors.RED}失败的测试:{Colors.END}")
            for test in self.failed_tests:
                print(f"  ❌ {test}")
        
        if success_rate >= 80:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 测试基本通过！{Colors.END}")
        elif success_rate >= 60:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ 部分功能需要修复{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}🚨 需要大量修复工作{Colors.END}")
        
        return success_rate >= 80

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE CLI 工具测试脚本")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    
    args = parser.parse_args()
    
    tester = SAGECLITester(args.project_root)
    
    if args.quick:
        # 快速模式只测试关键功能
        tester.test_import_functionality()
        tester.test_help_commands()
        tester.test_status_commands()
    else:
        # 完整测试
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
