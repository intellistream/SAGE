"""
Check dependency command implementation - Check import dependencies for Python packages.
"""

import os
import sys
import re
import typer
import importlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .common import console, handle_command_error
from ..core.base import BaseCommand


def extract_imports_from_text(content: str) -> Set[str]:
    """从Python代码文本中提取导入语句"""
    imports = set()
    
    # 使用正则表达式匹配导入语句
    lines = content.split('\n')
    
    for line in lines:
        # 去除注释和多余空格
        line = line.split('#')[0].strip()
        if not line:
            continue
            
        # 匹配 import xxx
        import_match = re.match(r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', line)
        if import_match:
            imports.add(import_match.group(1))
            continue
            
        # 匹配 from xxx import yyy
        from_match = re.match(r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import', line)
        if from_match:
            imports.add(from_match.group(1))
            continue
            
        # 匹配 import xxx, yyy, zzz
        multi_import_match = re.match(r'^import\s+(.+)', line)
        if multi_import_match:
            modules = multi_import_match.group(1).split(',')
            for module in modules:
                module = module.strip()
                # 处理 as 别名
                if ' as ' in module:
                    module = module.split(' as ')[0].strip()
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$', module):
                    imports.add(module)
    
    return imports


class CheckDependencyCommand(BaseCommand):
    """依赖检查命令 - 检查 Python 包的导入依赖"""
    
    def __init__(self):
        super().__init__()
        # 创建单个命令而不是子命令组
        self._create_command()
        
    def _create_command(self):
        """创建单个命令"""
        def check_dependency_main(
            path: str = typer.Argument(..., help="Path to the package directory"),
            max_workers: int = typer.Option(10, "--max-workers", "-w", help="Maximum number of concurrent import checks"),
            verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output during processing")
        ):
            """
            🔍 Check import dependencies for a Python package.
            
            This command analyzes all Python source files in the package's src directory,
            extracts all import statements, and tests whether they can be imported successfully.
            Results are saved to package/.testlogs/import_checks.log.
            
            Examples:
                sage-dev check-dependency /path/to/package
                sage-dev check-dependency packages/sage-kernel --verbose
                sage-dev check-dependency packages/sage-core --max-workers 20
            """
            try:
                self._run_dependency_check(path, max_workers, verbose)
            except SystemExit as e:
                # 捕获 sys.exit() 调用，这可能来自被分析的模块
                console.print(f"⚠️  A module called sys.exit() during analysis (exit code: {e.code})", style="yellow")
                console.print("💡 This usually indicates missing dependencies in the analyzed package", style="dim yellow")
                console.print("📝 Dependency check may be incomplete", style="yellow")
            except Exception as e:
                handle_command_error(e, "Dependency check failed")
        
        # 保存为单个命令而不是应用
        self.command = check_dependency_main
    
    def _create_testlogs_dir(self, project_path: Path) -> Path:
        """创建测试日志目录"""
        testlogs_dir = project_path / ".testlogs"
        testlogs_dir.mkdir(exist_ok=True)
        return testlogs_dir
    
    def _find_source_files(self, src_dir: Path) -> List[Path]:
        """查找所有 Python 源文件"""
        python_files = []
        if not src_dir.exists():
            return python_files
            
        for file_path in src_dir.rglob("*.py"):
            if file_path.is_file():
                # 跳过 __pycache__ 和测试文件
                if "__pycache__" not in str(file_path) and not file_path.name.startswith("test_"):
                    python_files.append(file_path)
        
        return sorted(python_files)
    
    def _extract_imports_from_file(self, file_path: Path) -> Set[str]:
        """从 Python 文件中提取所有导入语句"""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 使用简单的文本解析而不是AST
            imports = extract_imports_from_text(content)
            
        except UnicodeDecodeError as e:
            console.print(f"⚠️  Encoding error in {file_path.name}: {e}", style="yellow")
        except Exception as e:
            console.print(f"⚠️  Error reading {file_path.name}: {e}", style="yellow")
        
        return imports
    
    def _test_import(self, import_name: str) -> Tuple[str, bool, Optional[str]]:
        """测试单个导入是否成功"""
        try:
            # 直接尝试导入模块名
            importlib.import_module(import_name)
            return import_name, True, None
        except Exception as e:
            return import_name, False, str(e)
    
    def _check_imports_batch(self, imports: Set[str], max_workers: int = 10) -> List[Tuple[str, bool, Optional[str]]]:
        """批量检查导入"""
        results = []
        
        # 先尝试非并发方式，避免并发导入的问题
        if max_workers == 1:
            for import_name in imports:
                try:
                    result = self._test_import(import_name)
                    results.append(result)
                except Exception as e:
                    console.print(f"❌ Unexpected error testing {import_name}: {e}", style="red")
                    results.append((import_name, False, str(e)))
        else:
            # 使用线程池并发检查导入
            try:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交所有任务
                    future_to_import = {
                        executor.submit(self._test_import, import_name): import_name 
                        for import_name in imports
                    }
                    
                    # 收集结果
                    for future in as_completed(future_to_import):
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            import_name = future_to_import[future]
                            console.print(f"❌ Unexpected error in thread for {import_name}: {e}", style="red")
                            results.append((import_name, False, str(e)))
            except Exception as e:
                console.print(f"❌ Error in concurrent import testing: {e}", style="red")
                # 回退到非并发模式
                return self._check_imports_batch(imports, 1)
        
        return sorted(results, key=lambda x: x[0])
    
    def _write_import_check_log(self, testlogs_dir: Path, results: List[Tuple[str, bool, Optional[str]]], source_files: List[Path]):
        """写入导入检查日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = testlogs_dir / "import_checks.log"
        
        # 统计结果
        total_imports = len(results)
        successful_imports = sum(1 for _, success, _ in results if success)
        failed_imports = total_imports - successful_imports
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Import Dependency Check Report - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"📊 Summary:\n")
            f.write(f"  Total imports checked: {total_imports}\n")
            f.write(f"  Successful imports: {successful_imports}\n")
            f.write(f"  Failed imports: {failed_imports}\n")
            f.write(f"  Success rate: {(successful_imports/total_imports*100):.1f}%\n\n")
            
            f.write(f"📁 Source files analyzed ({len(source_files)}):\n")
            for file_path in source_files:
                f.write(f"  - {file_path}\n")
            f.write("\n")
            
            if failed_imports > 0:
                f.write("❌ Failed Imports:\n")
                f.write("-" * 40 + "\n")
                for import_name, success, error in results:
                    if not success:
                        f.write(f"  {import_name}\n")
                        if error:
                            f.write(f"    Error: {error}\n")
                f.write("\n")
            
            f.write("✅ Successful Imports:\n")
            f.write("-" * 40 + "\n")
            for import_name, success, _ in results:
                if success:
                    f.write(f"  {import_name}\n")
            
            f.write(f"\n📝 Log generated at: {timestamp}\n")
        
        return log_file, failed_imports, successful_imports
    
    def _run_dependency_check(self, path: str, max_workers: int, verbose: bool):
        """执行依赖检查"""
        project_path = Path(path).resolve()
        
        if not project_path.exists():
            console.print(f"❌ Path does not exist: {project_path}", style="red")
            raise typer.Exit(1)
        
        console.print(f"🔍 Checking dependencies for: {project_path}")
        
        # 查找 src 目录
        src_dir = project_path / "src"
        if not src_dir.exists():
            console.print(f"❌ Source directory not found: {src_dir}", style="red")
            console.print("💡 Expected structure: package_name/src/", style="yellow")
            raise typer.Exit(1)
        
        # 创建日志目录
        testlogs_dir = self._create_testlogs_dir(project_path)
        console.print(f"📝 Import check logs will be saved to: {testlogs_dir}")
        
        # 查找所有 Python 源文件
        console.print("📁 Scanning source files...")
        source_files = self._find_source_files(src_dir)
        
        if not source_files:
            console.print(f"⚠️  No Python source files found in {src_dir}", style="yellow")
            return
        
        console.print(f"📄 Found {len(source_files)} Python source file(s)")
        
        if verbose:
            for file_path in source_files[:10]:  # Show first 10 files
                console.print(f"  • {file_path.relative_to(project_path)}")
            if len(source_files) > 10:
                console.print(f"  ... and {len(source_files) - 10} more files")
        
        # 提取所有导入语句
        console.print("🔎 Extracting import statements...")
        all_imports = set()
        
        for file_path in source_files:
            if verbose:
                console.print(f"  Analyzing {file_path.relative_to(project_path)}...")
            
            file_imports = self._extract_imports_from_file(file_path)
            all_imports.update(file_imports)
        
        if not all_imports:
            console.print("⚠️  No import statements found", style="yellow")
            return
        
        console.print(f"📦 Found {len(all_imports)} unique import(s)")
        
        # 测试导入
        console.print(f"🧪 Testing imports (using {max_workers} workers)...")
        
        with console.status("Checking imports..."):
            results = self._check_imports_batch(all_imports, max_workers)
        
        # 写入日志并显示结果
        log_file, failed_count, success_count = self._write_import_check_log(
            testlogs_dir, results, source_files
        )
        
        # 显示结果摘要
        total = len(results)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        console.print(f"\n📊 [bold]Import Check Results:[/bold]")
        console.print(f"  Total imports: {total}")
        console.print(f"  ✅ Successful: {success_count}")
        console.print(f"  ❌ Failed: {failed_count}")
        console.print(f"  📈 Success rate: {success_rate:.1f}%")
        
        if failed_count > 0:
            console.print(f"\n❌ [red]Failed imports ({failed_count}):[/red]")
            for import_name, success, error in results:
                if not success:
                    console.print(f"  • {import_name}")
                    if verbose and error:
                        console.print(f"    {error}", style="dim")
        
        console.print(f"\n📝 Detailed report saved to: {log_file}")
        
        if failed_count > 0:
            console.print("💡 Install missing dependencies or check import paths", style="yellow")


# 创建命令实例
command = CheckDependencyCommand()
# 为了兼容get_apps()函数，创建一个虚拟的app属性
app = command
