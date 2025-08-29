"""
Test command implementation - Universal test runner for any Python project.

Integrated with enhanced test runner functionality for comprehensive testing.
"""

import os
import sys
import subprocess
import typer
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .common import console, handle_command_error
from ..core.base import BaseCommand
from ...core.exceptions import SAGEDevToolkitError
from ...utils.sage_home import get_logs_dir


class TestCommand(BaseCommand):
    """统一测试命令 - 支持任何 Python 项目，集成增强功能"""
    
    def __init__(self):
        super().__init__()
        self.app = typer.Typer(
            name="test", 
            help="🧪 Universal test runner for Python projects",
            invoke_without_command=True,
            no_args_is_help=False
        )
        self._register_commands()
    
    def _get_package_from_test_file(self, test_file: Path, project_root: Path) -> str:
        """确定测试文件所属的包"""
        try:
            relative_path = test_file.relative_to(project_root)
            path_parts = relative_path.parts
            
            if len(path_parts) >= 1:
                # 检查是否在packages目录下
                if path_parts[0] == 'packages' and len(path_parts) >= 2:
                    package_part = path_parts[1]
                    # 映射包目录名到标准日志目录名
                    package_mapping = {
                        'sage-kernel': 'kernel',
                        'sage-middleware': 'middleware', 
                        'sage-common': 'common',
                        'sage-libs': 'libs'
                    }
                    return package_mapping.get(package_part, 'common')
        except ValueError:
            pass
        
        return 'common'  # 默认回退
    
    def _create_testlogs_dir(self, project_path: Path) -> Path:
        """创建测试日志目录 - 使用统一的.sage/logs目录"""
        # 找到项目根目录
        root_path = project_path
        while root_path.parent != root_path:
            if (root_path / '.sage').exists() or (root_path / 'packages').exists():
                break
            root_path = root_path.parent
        
        # 使用统一的.sage/logs目录
        sage_dir = root_path / '.sage'
        sage_dir.mkdir(exist_ok=True)
        
        testlogs_dir = sage_dir / 'logs'
        testlogs_dir.mkdir(exist_ok=True)
        
        # 如果是packages下的子项目，创建对应子目录
        try:
            relative_path = project_path.relative_to(root_path)
            if relative_path.parts and relative_path.parts[0] == 'packages':
                # 提取包名，如 packages/sage-kernel -> kernel
                if len(relative_path.parts) >= 2:
                    package_name = relative_path.parts[1].replace('sage-', '')
                    package_logs_dir = testlogs_dir / package_name
                    package_logs_dir.mkdir(exist_ok=True)
                    return package_logs_dir
        except ValueError:
            pass
        
        return testlogs_dir
    
    def _find_tests_directory(self, project_path) -> Optional[Path]:
        """查找测试目录"""
        if isinstance(project_path, str):
            project_path = Path(project_path)
        
        possible_test_dirs = ["tests", "test", "Tests", "Test"]
        
        for test_dir_name in possible_test_dirs:
            test_dir = project_path / test_dir_name
            if test_dir.exists() and test_dir.is_dir():
                return test_dir
        
        return None
    
    def _discover_test_files(self, test_dir: Path, pattern: str = "test_*.py") -> List[Path]:
        """发现测试文件"""
        test_files = []
        
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
    
    def _run_single_test_file(self, test_file: Path, timeout: int, testlogs_dir: Path, 
                             project_root: Path, verbose: bool = False) -> Dict:
        """运行单个测试文件"""
        try:
            # 确定包名并创建对应的日志文件路径
            package_name = self._get_package_from_test_file(test_file, project_root)
            package_log_dir = testlogs_dir.parent / package_name
            package_log_dir.mkdir(parents=True, exist_ok=True)
            log_file = package_log_dir / f"{test_file.name}.log"
            
            # 准备命令
            cmd = [sys.executable, '-m', 'pytest', str(test_file), '-v']
            
            # 禁用覆盖率，避免 pyproject.toml 覆盖率设置
            cmd.extend(['--cov=', '--no-cov'])
            
            # 在详细模式下显示开始信息
            if verbose:
                console.print(f"  🧪 Starting {test_file.name}...", style="dim blue")
            
            # 创建环境变量
            env = os.environ.copy()
            
            # 运行测试
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root),
                env=env
            )
            duration = time.time() - start_time
            
            # 写入日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Duration: {duration:.2f}s\n")
                f.write(f"=== STDOUT ===\n{result.stdout}\n")
                f.write(f"=== STDERR ===\n{result.stderr}\n")
            
            return {
                'test_file': str(test_file),
                'passed': result.returncode == 0,
                'duration': duration,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None,
                'log_file': str(log_file)
            }
            
        except subprocess.TimeoutExpired:
            return {
                'test_file': str(test_file),
                'passed': False,
                'duration': timeout,
                'output': '',
                'error': f'Test timed out after {timeout} seconds',
                'log_file': str(log_file) if 'log_file' in locals() else None
            }
        except Exception as e:
            return {
                'test_file': str(test_file),
                'passed': False,
                'duration': 0,
                'output': '',
                'error': f'Error: {str(e)}',
                'log_file': str(log_file) if 'log_file' in locals() else None
            }
    
    def _run_tests_parallel(self, test_files: List[Path], project_root: Path, 
                           testlogs_dir: Path, timeout: int = 300, 
                           max_workers: int = None, verbose: bool = False) -> dict:
        """并行运行测试"""
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'failed_tests': [],
            'output': ''
        }
        
        # 如果没有指定并行数，使用 CPU 核心数或测试文件数的较小值
        if max_workers is None:
            max_workers = min(len(test_files), os.cpu_count() or 1, 4)  # 最多4个并行
        
        console.print(f"🚀 Running {len(test_files)} test files with {max_workers} parallel workers...", style="blue")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self._run_single_test_file, test_file, timeout, testlogs_dir, project_root, verbose): test_file 
                for test_file in test_files
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                test_file = future_to_file[future]
                try:
                    result = future.result()
                    
                    if result['passed']:
                        results['passed'] += 1
                        console.print(f"✅ {test_file.name} PASSED", style="green")
                    else:
                        results['failed'] += 1
                        results['failed_tests'].append(str(test_file))
                        console.print(f"❌ {test_file.name} FAILED", style="red")
                        if verbose and result.get('error'):
                            console.print(f"   Error: {result['error']}", style="dim red")
                    
                    results['total'] += 1
                    results['output'] += f"\n=== {test_file.name} ===\n" + (result['output'] or '') + "\n"
                    
                except Exception as e:
                    console.print(f"💥 {test_file.name} EXCEPTION: {e}", style="red")
                    results['errors'] += 1
                    results['failed_tests'].append(str(test_file))
                    results['total'] += 1
                    results['output'] += f"\n=== {test_file.name} ===\nException: {str(e)}\n"
        
        return results
    
    def _run_tests(
        self, 
        project_path: Path, 
        failed_only: bool = False,
        pattern: str = "test_*.py",
        verbose: bool = False,
        timeout: int = 300,
        max_workers: int = None
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
                try:
                    rel_path = test_file.relative_to(project_path)
                    console.print(f"   - {rel_path}", style="dim")
                except ValueError:
                    console.print(f"   - {test_file.name}", style="dim")
        
        # 找到项目根目录
        project_root = project_path
        while project_root.parent != project_root:
            if (project_root / '.sage').exists() or (project_root / 'packages').exists():
                break
            project_root = project_root.parent
        
        # 运行测试
        results = self._run_tests_parallel(
            test_files, project_root, testlogs_dir, timeout, max_workers, verbose
        )
        
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
            ),
            jobs: int = typer.Option(
                None,
                "-j",
                "--jobs",
                help="Number of parallel test jobs (default: auto-detect)"
            )
        ):
            """🧪 Universal test runner for Python projects
            
            Run tests in any Python project. Automatically discovers test directory
            and runs tests using pytest with enhanced logging and progress display.
            
            Test results and logs are saved to .sage/logs/{package}/ directory.
            
            Examples:
              sage-dev test                        # Run all tests in current directory
              sage-dev test /path/to/project       # Run tests in specific project
              sage-dev test --failed               # Run only previously failed tests
              sage-dev test --pattern "*_test.py"  # Use custom test file pattern
              sage-dev test --timeout 600          # Set 10-minute timeout
              sage-dev test -j 8                   # Use 8 parallel workers
              sage-dev test -j 1                   # Disable parallel execution
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
                    timeout=timeout,
                    max_workers=jobs
                )
                
                # 显示结果摘要
                if results['total'] > 0:
                    if results['failed'] == 0 and results['errors'] == 0:
                        console.print(f"✅ All tests passed! ({results['passed']}/{results['total']})", style="green")
                    else:
                        console.print(f"❌ Tests failed: {results['failed']} failed, {results['errors']} errors, {results['passed']} passed", style="red")
                        
                        if results['failed_tests']:
                            console.print(f"📝 Failed tests logged to .sage/logs/ directory", style="dim")
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
            """Manage test failure cache"""
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
                try:
                    rel_path = test_file.relative_to(project_path)
                    console.print(f"  🧪 {rel_path}", style="green")
                except ValueError:
                    console.print(f"  🧪 {test_file.name}", style="green")


# 创建命令实例
command = TestCommand()
app = command.app
