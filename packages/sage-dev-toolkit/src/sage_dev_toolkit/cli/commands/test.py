"""
Test command implementation - Universal test runner for any Python project.
"""

import os
import sys
import subprocess
import typer
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .common import console, handle_command_error
from ..core.base import BaseCommand


class TestCommand(BaseCommand):
    """通用测试命令 - 支持任何 Python 项目"""
    
    def __init__(self):
        super().__init__()
        self.app = typer.Typer(
            name="test", 
            help="🧪 Universal test runner for Python projects",
            invoke_without_command=True,
            no_args_is_help=False
        )
        self._register_commands()
    
    def _create_testlogs_dir(self, project_path: Path) -> Path:
        """创建测试日志目录"""
        testlogs_dir = project_path / ".testlogs"
        testlogs_dir.mkdir(exist_ok=True)
        return testlogs_dir
    
    def _find_tests_directory(self, project_path: Path) -> Optional[Path]:
        """查找测试目录"""
        possible_test_dirs = ["tests", "test", "Tests", "Test"]
        
        for test_dir_name in possible_test_dirs:
            test_dir = project_path / test_dir_name
            if test_dir.exists() and test_dir.is_dir():
                return test_dir
        
        return None
    
    def _discover_test_files(self, test_dir: Path, pattern: str = "test_*.py") -> List[Path]:
        """发现测试文件"""
        test_files = []
        
        # 简单的通配符匹配
        if pattern.startswith("test_") and pattern.endswith(".py"):
            prefix = pattern[:-3]  # 去掉 .py
            for file_path in test_dir.rglob("*.py"):
                if file_path.stem.startswith(prefix.replace("*", "")):
                    test_files.append(file_path)
        else:
            # 使用 glob 模式
            for file_path in test_dir.glob(pattern):
                if file_path.is_file():
                    test_files.append(file_path)
            # 也搜索子目录
            for file_path in test_dir.rglob(pattern):
                if file_path.is_file():
                    test_files.append(file_path)
        
        return sorted(set(test_files))
    
    def _read_failed_tests(self, testlogs_dir: Path) -> set:
        """读取上次失败的测试"""
        failed_file = testlogs_dir / "failed_tests.txt"
        if not failed_file.exists():
            return set()
        
        failed_tests = set()
        with open(failed_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    failed_tests.add(line)
        return failed_tests
    
    def _write_test_results(self, testlogs_dir: Path, results: dict):
        """写入测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 写入详细日志
        log_file = testlogs_dir / f"test_run_{timestamp}.log"
        with open(log_file, 'w') as f:
            f.write(f"Test Run Results - {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total Tests: {results['total']}\n")
            f.write(f"Passed: {results['passed']}\n")
            f.write(f"Failed: {results['failed']}\n")
            f.write(f"Errors: {results['errors']}\n")
            f.write(f"Skipped: {results['skipped']}\n\n")
            
            if results.get('failed_tests'):
                f.write("Failed Tests:\n")
                for test in results['failed_tests']:
                    f.write(f"  - {test}\n")
        
        # 更新失败测试列表
        failed_file = testlogs_dir / "failed_tests.txt"
        with open(failed_file, 'w') as f:
            for test in results.get('failed_tests', []):
                f.write(f"{test}\n")
        
        # 保持最新状态
        status_file = testlogs_dir / "latest_status.txt"
        with open(status_file, 'w') as f:
            f.write(f"Last run: {datetime.now().isoformat()}\n")
            f.write(f"Status: {'PASSED' if results['failed'] == 0 else 'FAILED'}\n")
            f.write(f"Total: {results['total']}, Passed: {results['passed']}, Failed: {results['failed']}\n")
    
    def _run_tests_with_pytest(self, test_files: List[Path], verbose: bool = False, timeout: int = 300, testlogs_dir: Path = None) -> dict:
        """使用 pytest 运行测试"""
        try:
            cmd = [sys.executable, "-m", "pytest"]
            
            # 总是添加 -s 来捕获所有输出
            cmd.append("-s")
            
            if verbose:
                cmd.extend(["-v", "--tb=short"])
            else:
                cmd.append("-q")
            
            # 添加测试文件
            cmd.extend([str(f) for f in test_files])
            
            # 创建实时输出文件
            if testlogs_dir:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = testlogs_dir / f"pytest_output_{timestamp}.log"
                console.print(f"📝 Test output will be saved to: {output_file}", style="blue")
            else:
                output_file = None
            
            # 运行测试，添加超时控制
            console.print(f"🕐 Running tests with {timeout}s timeout...", style="blue")
            
            if output_file:
                # 使用实时输出重定向
                with open(output_file, 'w', encoding='utf-8') as f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        cwd=test_files[0].parent if test_files else None,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    output_lines = []
                    try:
                        import select
                        import time
                        start_time = time.time()
                        
                        # 实时读取输出并写入文件
                        while True:
                            # 检查超时
                            if time.time() - start_time > timeout:
                                process.kill()
                                process.wait()
                                raise subprocess.TimeoutExpired(cmd, timeout)
                            
                            # 检查进程是否结束
                            if process.poll() is not None:
                                # 读取剩余输出
                                remaining = process.stdout.read()
                                if remaining:
                                    f.write(remaining)
                                    f.flush()
                                    output_lines.extend(remaining.splitlines())
                                break
                            
                            # 读取输出
                            line = process.stdout.readline()
                            if line:
                                f.write(line)
                                f.flush()
                                output_lines.append(line.rstrip())
                                # 如果是详细模式，也打印到控制台
                                if verbose:
                                    console.print(line.rstrip(), style="dim")
                            else:
                                time.sleep(0.1)  # 短暂等待
                                
                    except Exception as e:
                        process.kill()
                        process.wait()
                        raise e
                    
                    output = '\n'.join(output_lines)
                    return_code = process.returncode
                    
            else:
                # 回退到原来的方式
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    timeout=timeout,
                    cwd=test_files[0].parent if test_files else None
                )
                output = result.stdout + result.stderr
                return_code = result.returncode
            
            # 解析结果（简化版本）
            results = {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'skipped': 0,
                'failed_tests': [],
                'output': output
            }
            
            # 简单的输出解析
            lines = output.split('\n')
            for line in lines:
                if "failed" in line.lower() and "passed" in line.lower():
                    # 例如: "2 failed, 3 passed in 1.23s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed":
                            results['failed'] = int(parts[i-1])
                        elif part == "passed":
                            results['passed'] = int(parts[i-1])
                        elif part == "skipped":
                            results['skipped'] = int(parts[i-1])
                        elif part == "error":
                            results['errors'] = int(parts[i-1])
            
            results['total'] = results['passed'] + results['failed'] + results['errors'] + results['skipped']
            
            return results
            
        except subprocess.TimeoutExpired as e:
            console.print(f"⏰ Tests timed out after {timeout} seconds", style="red")
            console.print("💡 Try running with a longer timeout using --timeout option", style="yellow")
            return {
                'total': len(test_files),
                'passed': 0,
                'failed': len(test_files),
                'errors': 0,
                'skipped': 0,
                'failed_tests': [str(f) for f in test_files],
                'output': f'Tests timed out after {timeout} seconds'
            }
        except Exception as e:
            console.print(f"❌ Error running pytest: {e}", style="red")
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'skipped': 0,
                'failed_tests': [],
                'output': str(e)
            }
    
    def _run_tests_with_unittest(self, test_files: List[Path], verbose: bool = False, timeout: int = 300) -> dict:
        """使用 unittest 运行测试"""
        try:
            cmd = [sys.executable, "-m", "unittest"]
            
            # 总是使用 verbose 模式获取详细输出
            cmd.append("-v")
            
            # 转换文件路径为模块路径
            modules = []
            for test_file in test_files:
                # 简化版本：假设测试文件可以直接运行
                modules.append(str(test_file))
            
            cmd.extend(modules)
            
            console.print(f"🕐 Running unittest with {timeout}s timeout...", style="blue")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=test_files[0].parent if test_files else None
            )
            
            output = result.stdout + result.stderr
            
            # 简单的结果解析
            results = {
                'total': len(test_files),
                'passed': len(test_files) if result.returncode == 0 else 0,
                'failed': len(test_files) if result.returncode != 0 else 0,
                'errors': 0,
                'skipped': 0,
                'failed_tests': [str(f) for f in test_files] if result.returncode != 0 else [],
                'output': output
            }
            
            return results
            
        except subprocess.TimeoutExpired as e:
            console.print(f"⏰ Unittest timed out after {timeout} seconds", style="red")
            console.print("💡 Try running with a longer timeout using --timeout option", style="yellow")
            return {
                'total': len(test_files),
                'passed': 0,
                'failed': len(test_files),
                'errors': 0,
                'skipped': 0,
                'failed_tests': [str(f) for f in test_files],
                'output': f'Unittest timed out after {timeout} seconds'
            }
        except Exception as e:
            console.print(f"❌ Error running unittest: {e}", style="red")
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'skipped': 0,
                'failed_tests': [],
                'output': str(e)
            }
    
    def _run_tests(
        self, 
        project_path: Path, 
        failed_only: bool = False,
        pattern: str = "test_*.py",
        verbose: bool = False,
        timeout: int = 300
    ) -> dict:
        """运行测试的主要逻辑"""
        
        # 查找测试目录
        test_dir = self._find_tests_directory(project_path)
        if not test_dir:
            console.print(f"❌ No tests directory found in {project_path}", style="red")
            console.print("   Expected directories: tests, test, Tests, Test", style="dim")
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'skipped': 0,
                'failed_tests': [],
                'output': 'No tests directory found'
            }
        
        console.print(f"📁 Found test directory: {test_dir}", style="blue")
        
        # 创建测试日志目录
        testlogs_dir = self._create_testlogs_dir(project_path)
        console.print(f"📝 Test logs will be saved to: {testlogs_dir}", style="blue")
        
        # 发现测试文件
        test_files = self._discover_test_files(test_dir, pattern)
        if not test_files:
            console.print(f"❌ No test files found matching pattern: {pattern}", style="red")
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'skipped': 0,
                'failed_tests': [],
                'output': f'No test files found matching {pattern}'
            }
        
        # 如果只运行失败的测试
        if failed_only:
            failed_tests = self._read_failed_tests(testlogs_dir)
            if not failed_tests:
                console.print("✅ No previously failed tests found!", style="green")
                return {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'errors': 0,
                    'skipped': 0,
                    'failed_tests': [],
                    'output': 'No failed tests to run'
                }
            
            # 过滤只包含失败的测试文件
            test_files = [f for f in test_files if str(f) in failed_tests]
        
        console.print(f"🧪 Running {len(test_files)} test file(s)...", style="blue")
        if verbose:
            for test_file in test_files:
                console.print(f"   - {test_file.relative_to(project_path)}", style="dim")
        
        # 尝试使用 pytest，如果失败则使用 unittest
        results = self._run_tests_with_pytest(test_files, verbose, timeout, testlogs_dir)
        if results['errors'] > 0 and 'pytest' in results['output']:
            console.print("⚠️  pytest failed, trying unittest...", style="yellow")
            results = self._run_tests_with_unittest(test_files, verbose, timeout)
        
        # 写入测试结果
        self._write_test_results(testlogs_dir, results)
        
        return results
    
    
    def _register_commands(self):
        """注册测试相关命令"""
        
        @self.app.callback()
        def test_main(
            ctx: typer.Context,
            path: str = typer.Argument(
                ".",
                help="Project path to test (default: current directory)"
            ),
            failed: bool = typer.Option(
                False, 
                "--failed", 
                help="Run only previously failed tests"
            ),
            pattern: str = typer.Option(
                "test_*.py", 
                help="Test file pattern"
            ),
            verbose: bool = typer.Option(
                False, 
                "-v", 
                "--verbose", 
                help="Verbose output"
            ),
            timeout: int = typer.Option(
                300,
                "--timeout",
                help="Test execution timeout in seconds (default: 300)"
            )
        ):
            """🧪 Universal test runner for Python projects
            
            Run tests in any Python project. Automatically discovers test directory
            (tests, test, Tests, Test) and runs tests using pytest or unittest.
            
            Test results and logs are saved to .testlogs/ directory in the project root.
            
            Examples:
              sage-dev test                        # Run all tests in current directory
              sage-dev test /path/to/project       # Run tests in specific project
              sage-dev test --failed               # Run only previously failed tests
              sage-dev test --pattern "*_test.py"  # Use custom test file pattern
              sage-dev test --timeout 600          # Set 10-minute timeout
            """
            # 如果有子命令被调用，不执行主命令逻辑
            if ctx.invoked_subcommand is not None:
                return
            
            # 解析项目路径
            project_path = Path(path).resolve()
            if not project_path.exists():
                console.print(f"❌ Path does not exist: {project_path}", style="red")
                raise typer.Exit(1)
            
            if not project_path.is_dir():
                console.print(f"❌ Path is not a directory: {project_path}", style="red")
                raise typer.Exit(1)
            
            console.print(f"🔍 Testing project at: {project_path}", style="blue")
            
            # 运行测试
            try:
                results = self._run_tests(
                    project_path=project_path,
                    failed_only=failed,
                    pattern=pattern,
                    verbose=verbose,
                    timeout=timeout
                )
                
                # 显示结果摘要
                if results['total'] > 0:
                    if results['failed'] == 0 and results['errors'] == 0:
                        console.print(f"✅ All tests passed! ({results['passed']}/{results['total']})", style="green")
                    else:
                        console.print(f"❌ Tests failed: {results['failed']} failed, {results['errors']} errors, {results['passed']} passed", style="red")
                        
                        # 显示测试输出
                        if results.get('output') and results['output'].strip():
                            console.print("\n📋 Test Output:", style="yellow")
                            console.print("=" * 60, style="dim")
                            console.print(results['output'], style="white")
                            console.print("=" * 60, style="dim")
                        
                        if results['failed_tests']:
                            console.print("Failed tests saved to .testlogs/failed_tests.txt", style="dim")
                        raise typer.Exit(1)
                else:
                    console.print("⚠️  No tests were run", style="yellow")
                    
            except Exception as e:
                console.print(f"❌ Test execution failed: {e}", style="red")
                raise typer.Exit(1)
        
        @self.app.command("cache")
        def test_cache(
            path: str = typer.Argument(
                ".",
                help="Project path (default: current directory)"
            ),
            action: str = typer.Argument(
                help="Cache action: clear, list, status"
            ),
            verbose: bool = typer.Option(
                False, 
                "-v", 
                "--verbose", 
                help="Verbose output"
            )
        ):
            """Manage test failure cache
            
            Actions:
              clear  - Clear failed tests cache
              list   - List previously failed tests  
              status - Show cache status
            """
            project_path = Path(path).resolve()
            if not project_path.exists() or not project_path.is_dir():
                console.print(f"❌ Invalid project path: {project_path}", style="red")
                raise typer.Exit(1)
            
            testlogs_dir = self._create_testlogs_dir(project_path)
            failed_file = testlogs_dir / "failed_tests.txt"
            
            if action == "clear":
                if failed_file.exists():
                    failed_file.unlink()
                    console.print("✅ Failed tests cache cleared", style="green")
                else:
                    console.print("ℹ️  No failed tests cache to clear", style="blue")
                    
            elif action == "list":
                failed_tests = self._read_failed_tests(testlogs_dir)
                if failed_tests:
                    console.print(f"📝 Found {len(failed_tests)} previously failed tests:", style="blue")
                    for test in sorted(failed_tests):
                        console.print(f"  - {test}", style="red")
                else:
                    console.print("✅ No previously failed tests found", style="green")
                    
            elif action == "status":
                status_file = testlogs_dir / "latest_status.txt"
                if status_file.exists():
                    with open(status_file, 'r') as f:
                        content = f.read()
                    console.print("📊 Latest test status:", style="blue")
                    console.print(content, style="dim")
                else:
                    console.print("ℹ️  No test status available", style="blue")
                    
            else:
                console.print(f"❌ Unknown action: {action}", style="red")
                console.print("Available actions: clear, list, status", style="dim")
                raise typer.Exit(1)
        
        @self.app.command("list")
        def list_tests(
            path: str = typer.Argument(
                ".",
                help="Project path (default: current directory)"
            ),
            pattern: str = typer.Option(
                "test_*.py",
                help="Test file pattern"
            ),
            verbose: bool = typer.Option(
                False,
                "-v", 
                "--verbose",
                help="Verbose output"
            )
        ):
            """List all available tests in the project"""
            project_path = Path(path).resolve()
            if not project_path.exists() or not project_path.is_dir():
                console.print(f"❌ Invalid project path: {project_path}", style="red")
                raise typer.Exit(1)
            
            test_dir = self._find_tests_directory(project_path)
            if not test_dir:
                console.print(f"❌ No tests directory found in {project_path}", style="red")
                raise typer.Exit(1)
            
            test_files = self._discover_test_files(test_dir, pattern)
            if not test_files:
                console.print(f"❌ No test files found matching pattern: {pattern}", style="red")
                raise typer.Exit(1)
            
            console.print(f"📁 Found {len(test_files)} test file(s) in {test_dir}:", style="blue")
            for test_file in test_files:
                rel_path = test_file.relative_to(project_path)
                console.print(f"  🧪 {rel_path}", style="green")
                
                if verbose:
                    # 尝试提取测试函数/类名称
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        import re
                        # 查找测试函数和类
                        test_functions = re.findall(r'def (test_\w+)', content)
                        test_classes = re.findall(r'class (Test\w+)', content)
                        
                        if test_functions or test_classes:
                            for cls in test_classes:
                                console.print(f"      🏗️  {cls}", style="dim cyan")
                            for func in test_functions:
                                console.print(f"      ⚡ {func}", style="dim yellow")
                                
                    except Exception:
                        # 如果无法解析文件，跳过详细信息
                        pass


# 创建命令实例
command = TestCommand()
app = command.app
