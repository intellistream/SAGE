#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Examples 测试框架
用于自动化测试 examples 目录下的所有示例代码
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, track
from rich.table import Table

console = Console()


def find_project_root() -> Path:
    """查找项目根目录，使用统一的路径管理"""
    try:
        # 尝试导入统一的路径管理
        import os
        import sys

        # 添加sage-common到路径
        current_dir = Path(__file__).parent
        sage_common_path = (
            current_dir.parent.parent / "packages" / "sage-common" / "src"
        )
        if sage_common_path.exists():
            sys.path.insert(0, str(sage_common_path))

        from sage.common.config.output_paths import \
            find_project_root as find_sage_root

        return find_sage_root()
    except ImportError:
        # 回退到原来的查找逻辑
        return _fallback_find_project_root()


def _fallback_find_project_root() -> Path:
    """备用的项目根目录查找逻辑"""
    # 从当前文件开始向上查找
    current = Path(__file__).parent
    while current != current.parent:
        examples_path = current / "examples"
        if examples_path.exists() and examples_path.is_dir():
            return current
        current = current.parent

    # 如果没找到，尝试从当前工作目录查找
    current = Path.cwd()
    while current != current.parent:
        examples_path = current / "examples"
        if examples_path.exists() and examples_path.is_dir():
            return current
        current = current.parent

    # 尝试通过环境变量获取SAGE根目录
    sage_root = os.environ.get("SAGE_ROOT")
    if sage_root:
        sage_root_path = Path(sage_root)
        if (sage_root_path / "examples").exists():
            return sage_root_path

    # 最后的备用方案 - 尝试从sys.path中找到sage包的位置
    import sys

    for path in sys.path:
        path_obj = Path(path)
        # 查找包含sage包的目录
        if path_obj.name == "src" and "sage" in str(path_obj):
            # 从packages/sage/src向上找到项目根目录
            potential_root = path_obj.parent.parent.parent
            if (potential_root / "examples").exists():
                return potential_root

    # 如果都找不到，抛出详细的错误信息
    raise FileNotFoundError(
        "Cannot find SAGE project root directory. "
        "Please ensure you are running tests from within the SAGE project directory, "
        "or set the SAGE_ROOT environment variable to point to your SAGE installation directory. "
        f"Current working directory: {Path.cwd()}, "
        f"Script directory: {Path(__file__).parent}"
    )


@dataclass
class ExampleTestResult:
    """示例测试结果"""

    file_path: str
    test_name: str
    status: str  # "passed", "failed", "skipped", "timeout"
    execution_time: float
    output: str
    error: Optional[str] = None
    dependencies_met: bool = True
    requires_user_input: bool = False


@dataclass
class ExampleInfo:
    """示例文件信息"""

    file_path: str
    category: str  # tutorials, rag, memory, etc.
    imports: List[str]
    has_main: bool
    requires_config: bool
    requires_data: bool
    estimated_runtime: str  # "quick", "medium", "slow"
    dependencies: List[str]
    test_tags: List[str]  # 测试标记，从文件注释中提取


class ExampleAnalyzer:
    """示例代码分析器"""

    def __init__(self):
        try:
            project_root = find_project_root()
            self.examples_root = project_root / "examples"
        except FileNotFoundError:
            # 如果找不到项目根目录，抛出更有用的错误信息
            raise FileNotFoundError(
                "Cannot find SAGE project root directory. "
                "Please ensure you are running tests from within the SAGE project directory "
                "or that the examples/ directory exists in your current or parent directories."
            )

    def analyze_file(self, file_path: Path) -> ExampleInfo:
        """分析单个示例文件"""
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # 提取导入信息
            imports = self._extract_imports(tree)

            # 检查是否有主函数
            has_main = self._has_main_function(tree)

            # 检查配置和数据依赖
            requires_config = self._requires_config(content)
            requires_data = self._requires_data(content)

            # 估算运行时间
            estimated_runtime = self._estimate_runtime(content)

            # 提取依赖
            dependencies = self._extract_dependencies(imports)

            # 提取测试标记
            test_tags = self._extract_test_tags(content)

            category = self._get_category(file_path)

            return ExampleInfo(
                file_path=str(file_path),
                category=category,
                imports=imports,
                has_main=has_main,
                requires_config=requires_config,
                requires_data=requires_data,
                estimated_runtime=estimated_runtime,
                dependencies=dependencies,
                test_tags=test_tags,
            )

        except Exception as e:
            console.print(f"[red]分析文件失败 {file_path}: {e}[/red]")
            return None

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入语句"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _has_main_function(self, tree: ast.AST) -> bool:
        """检查是否有主函数"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return True
            if isinstance(node, ast.If) and hasattr(node.test, "left"):
                if (
                    hasattr(node.test.left, "id")
                    and node.test.left.id == "__name__"
                    and hasattr(node.test.comparators[0], "s")
                    and node.test.comparators[0].s == "__main__"
                ):
                    return True
        return False

    def _requires_config(self, content: str) -> bool:
        """检查是否需要配置文件"""
        config_indicators = [
            ".yaml",
            ".yml",
            ".json",
            ".toml",
            "config",
            "Config",
            "load_dotenv",
            "os.environ",
            "getenv",
        ]
        return any(indicator in content for indicator in config_indicators)

    def _requires_data(self, content: str) -> bool:
        """检查是否需要数据文件"""
        data_indicators = [
            ".csv",
            ".txt",
            ".pdf",
            ".docx",
            "data/",
            "dataset",
            "corpus",
        ]
        return any(indicator in content for indicator in data_indicators)

    def _estimate_runtime(self, content: str) -> str:
        """估算运行时间"""
        # 检查是否有明显的长时间运行指标
        if any(
            keyword in content
            for keyword in ["time.sleep", "train", "fit", "epochs", "while True"]
        ):
            return "slow"
        # 检查是否是简单的教程示例（优先级高）
        elif any(
            keyword in content
            for keyword in ["Hello, World!", "HelloBatch", "simple", "basic"]
        ):
            return "quick"
        # 检查网络请求等中等时间指标
        elif any(
            keyword in content
            for keyword in ["requests.", "http.", "download", "ray.init"]
        ):
            return "medium"
        # 文件大小作为参考
        elif len(content) < 3000:  # 小于3KB的文件通常是快速示例
            return "quick"
        else:
            return "medium"

    def _extract_dependencies(self, imports: List[str]) -> List[str]:
        """提取外部依赖"""
        sage_modules = {imp for imp in imports if imp.startswith("sage")}
        external_deps = []

        dependency_map = {
            "openai": "openai",
            "transformers": "transformers",
            "torch": "torch",
            "numpy": "numpy",
            "pandas": "pandas",
            "requests": "requests",
            "yaml": "pyyaml",
            "dotenv": "python-dotenv",
            "chromadb": "chromadb",
            "pymilvus": "pymilvus",
            "redis": "redis",
            "kafka": "kafka-python",
        }

        for imp in imports:
            root_module = imp.split(".")[0]
            if root_module in dependency_map:
                external_deps.append(dependency_map[root_module])

        return list(set(external_deps))

    def _extract_test_tags(self, content: str) -> List[str]:
        """从文件内容中提取测试标记

        支持的标记格式:
        # @test:skip - 跳过测试
        # @test:slow - 标记为慢速测试
        # @test:require-api - 需要API密钥
        # @test:interactive - 需要用户交互
        # @test:unstable - 不稳定的测试
        # @test:gpu - 需要GPU
        # @test:timeout=120 - 自定义超时时间
        # @test:category=batch - 自定义类别
        """
        import re

        # 查找所有 @test: 标记，支持注释和文档字符串中的标记
        # 匹配 # @test: 或 @test: (可能在文档字符串中)
        pattern = r"(?:#\s*)?@test:(\w+)(?:=(\w+))?"
        matches = re.findall(pattern, content, re.IGNORECASE)

        tags = []
        for match in matches:
            if len(match) == 2 and match[1]:
                # 带值的标记，如 timeout=120
                tags.append(f"{match[0]}={match[1]}")
            else:
                # 简单标记，如 skip
                tags.append(match[0])

        return list(set(tags))

    def _get_category(self, file_path: Path) -> str:
        """获取示例类别"""
        relative_path = file_path.relative_to(self.examples_root)
        return str(relative_path.parts[0]) if relative_path.parts else "unknown"

    def discover_examples(self) -> List[ExampleInfo]:
        """发现所有示例文件"""
        examples = []

        for py_file in self.examples_root.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            example_info = self.analyze_file(py_file)
            if example_info:
                examples.append(example_info)

        return examples


class ExampleRunner:
    """示例执行器"""

    def __init__(self, timeout: int = None):
        # 优先级：传入参数 > 环境变量 > 默认值（让策略决定）
        if timeout is not None:
            self.timeout = timeout
        else:
            # 如果没有传入timeout，检查环境变量，否则使用默认值让策略决定
            env_timeout = os.environ.get("SAGE_EXAMPLE_TIMEOUT")
            if env_timeout:
                self.timeout = int(env_timeout)
            else:
                # 不设置默认超时，让_get_test_timeout方法从策略中获取
                self.timeout = None
        try:
            project_root = find_project_root()
            self.examples_root = project_root / "examples"
            self.project_root = project_root
        except FileNotFoundError:
            # 如果找不到项目根目录，抛出更有用的错误信息
            raise FileNotFoundError(
                "Cannot find SAGE project root directory. "
                "Please ensure you are running tests from within the SAGE project directory "
                "or that the examples/ directory exists in your current or parent directories."
            )

    def run_example(self, example_info: ExampleInfo) -> ExampleTestResult:
        """运行单个示例"""
        start_time = time.time()

        # 检查依赖
        if not self._check_dependencies(example_info.dependencies):
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="skipped",
                execution_time=0,
                output="",
                error="Missing dependencies",
                dependencies_met=False,
            )

        # 检查是否需要用户输入
        if self._requires_user_input(example_info.file_path):
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="skipped",
                execution_time=0,
                output="",
                error="Requires user input",
                requires_user_input=True,
            )

        # 准备环境
        env = self._prepare_environment(example_info)

        # 确定超时时间
        test_timeout = self._get_test_timeout(example_info)

        try:
            # 执行示例
            result = subprocess.run(
                [sys.executable, example_info.file_path],
                capture_output=True,
                text=True,
                timeout=test_timeout,
                cwd=self.project_root,
                env=env,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                status = "passed"
                error = None
            else:
                status = "failed"
                error = result.stderr

            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status=status,
                execution_time=execution_time,
                output=result.stdout,
                error=error,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="timeout",
                execution_time=execution_time,
                output="",
                error=f"Execution timed out after {test_timeout}s",
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExampleTestResult(
                file_path=example_info.file_path,
                test_name=Path(example_info.file_path).name,
                status="failed",
                execution_time=execution_time,
                output="",
                error=str(e),
            )

    def _get_test_timeout(self, example_info: ExampleInfo) -> int:
        """从测试标记中确定超时时间"""
        # 检查是否有自定义超时标记
        for tag in example_info.test_tags:
            if tag.startswith("timeout="):
                try:
                    return int(tag.split("=")[1])
                except (ValueError, IndexError):
                    pass

        # 从类别策略中获取超时
        category = (
            self._get_category_from_tags(example_info.test_tags)
            or example_info.category
        )

        # 导入策略类
        try:
            from example_strategies import ExampleTestStrategies

            strategies = ExampleTestStrategies.get_strategies()
            if category in strategies:
                return strategies[category].timeout
        except ImportError:
            pass

        # 如果策略不可用，使用默认超时
        if self.timeout is not None:
            return self.timeout
        
        # 最后的默认值
        return 60

    def _get_category_from_tags(self, test_tags: List[str]) -> Optional[str]:
        """从测试标记中提取类别"""
        for tag in test_tags:
            if tag.startswith("category="):
                try:
                    return tag.split("=")[1]
                except IndexError:
                    pass
        return None

    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查依赖是否满足"""
        # 包名到导入名的映射
        import_name_map = {
            "pyyaml": "yaml",
            "python-dotenv": "dotenv",
            "kafka-python": "kafka",
        }

        for dep in dependencies:
            import_name = import_name_map.get(dep, dep)
            try:
                subprocess.run(
                    [sys.executable, "-c", f"import {import_name}"],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                return False
        return True

    def _requires_user_input(self, file_path: str) -> bool:
        """检查是否需要用户输入"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            input_indicators = ["input(", "raw_input(", "getpass."]
            return any(indicator in content for indicator in input_indicators)
        except:
            return False

    def _prepare_environment(self, example_info: ExampleInfo) -> Dict[str, str]:
        """准备执行环境"""
        env = os.environ.copy()

        # 设置 Python 路径 - 使用动态路径而不是硬编码
        python_path = env.get("PYTHONPATH", "")
        sage_paths = [
            str(self.project_root / "packages" / "sage" / "src"),
            str(self.project_root / "packages" / "sage-common" / "src"),
            str(self.project_root / "packages" / "sage-kernel" / "src"),
            str(self.project_root / "packages" / "sage-libs" / "src"),
            str(self.project_root / "packages" / "sage-middleware" / "src"),
            str(self.project_root / "packages" / "sage-tools" / "src"),
        ]

        if python_path:
            env["PYTHONPATH"] = ":".join(sage_paths + [python_path])
        else:
            env["PYTHONPATH"] = ":".join(sage_paths)

        # 设置示例特定的环境变量
        env["SAGE_EXAMPLES_MODE"] = "test"
        env["SAGE_LOG_LEVEL"] = "WARNING"  # 减少日志输出

        # 检查是否需要使用真实API (通过环境变量传递)
        if os.environ.get("SAGE_USE_REAL_API") == "true":
            env["SAGE_USE_REAL_API"] = "true"

        return env


class ExampleTestSuite:
    """示例测试套件"""

    def __init__(self):
        self.analyzer = ExampleAnalyzer()
        self.runner = ExampleRunner()
        self.results: List[ExampleTestResult] = []

    def run_all_tests(
        self, categories: Optional[List[str]] = None, quick_only: bool = False
    ) -> Dict[str, int]:
        """运行所有测试"""
        # 清理之前的测试结果
        self.results.clear()

        console.print("🔍 [bold blue]发现示例文件...[/bold blue]")
        examples = self.analyzer.discover_examples()

        # 过滤示例
        if categories:
            examples = [e for e in examples if e.category in categories]

        if quick_only:
            examples = [e for e in examples if e.estimated_runtime == "quick"]

        console.print(f"📋 找到 {len(examples)} 个示例文件")

        # 按类别分组显示
        self._show_examples_summary(examples)

        # 运行测试
        console.print("🚀 [bold blue]开始运行测试...[/bold blue]")

        with Progress() as progress:
            task = progress.add_task("运行示例测试", total=len(examples))

            for example in examples:
                console.print(f"  测试: {example.file_path}")
                result = self.runner.run_example(example)
                self.results.append(result)
                progress.update(task, advance=1)

        # 显示结果
        self._show_results()

        # 返回统计信息
        return self._get_statistics()

    def _show_examples_summary(self, examples: List[ExampleInfo]):
        """显示示例摘要"""
        categories = {}
        for example in examples:
            if example.category not in categories:
                categories[example.category] = []
            categories[example.category].append(example)

        table = Table(title="示例文件摘要")
        table.add_column("类别", style="cyan")
        table.add_column("文件数", style="magenta")
        table.add_column("运行时间", style="green")
        table.add_column("依赖项", style="yellow")

        for category, cat_examples in categories.items():
            count = len(cat_examples)
            runtimes = [e.estimated_runtime for e in cat_examples]
            runtime_summary = f"快速: {runtimes.count('quick')}, 中等: {runtimes.count('medium')}, 慢速: {runtimes.count('slow')}"

            all_deps = set()
            for e in cat_examples:
                all_deps.update(e.dependencies)
            deps_summary = f"{len(all_deps)} 个外部依赖"

            table.add_row(category, str(count), runtime_summary, deps_summary)

        console.print(table)

    def _show_results(self):
        """显示测试结果"""
        table = Table(title="测试结果")
        table.add_column("示例", style="cyan", width=40)
        table.add_column("状态", style="bold")
        table.add_column("执行时间", style="green")
        table.add_column("错误", style="red", width=50)

        for result in self.results:
            status_style = {
                "passed": "[green]✓ 通过[/green]",
                "failed": "[red]✗ 失败[/red]",
                "skipped": "[yellow]- 跳过[/yellow]",
                "timeout": "[orange]⏱ 超时[/orange]",
            }.get(result.status, result.status)

            error_msg = (
                result.error[:50] + "..."
                if result.error and len(result.error) > 50
                else (result.error or "")
            )

            table.add_row(
                Path(result.file_path).name,
                status_style,
                f"{result.execution_time:.2f}s",
                error_msg,
            )

        console.print(table)

    def _get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.status == "passed"),
            "failed": sum(1 for r in self.results if r.status == "failed"),
            "skipped": sum(1 for r in self.results if r.status == "skipped"),
            "timeout": sum(1 for r in self.results if r.status == "timeout"),
        }

        console.print(
            Panel(
                f"总计: {stats['total']} | "
                f"[green]通过: {stats['passed']}[/green] | "
                f"[red]失败: {stats['failed']}[/red] | "
                f"[yellow]跳过: {stats['skipped']}[/yellow] | "
                f"[orange]超时: {stats['timeout']}[/orange]",
                title="测试统计",
            )
        )

        return stats

    def save_results(self, output_file: str):
        """保存测试结果"""
        results_data = [asdict(result) for result in self.results]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "results": results_data,
                    "statistics": self._get_statistics(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        console.print(f"📄 测试结果已保存到: {output_file}")


# CLI 接口
app = typer.Typer(help="SAGE Examples 测试工具")


@app.command("test")
def test_cmd(
    categories: Optional[List[str]] = typer.Option(
        None, "--category", "-c", help="指定测试类别"
    ),
    quick_only: bool = typer.Option(False, "--quick", help="只运行快速测试"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="结果输出文件"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="单个测试超时时间(秒)"),
):
    """运行 examples 测试"""
    suite = ExampleTestSuite()
    suite.runner.timeout = timeout

    stats = suite.run_all_tests(categories=categories, quick_only=quick_only)

    if output:
        suite.save_results(output)

    # 设置退出码
    if stats["failed"] > 0 or stats["timeout"] > 0:
        sys.exit(1)


def test():
    """pytest 测试函数 - 轻量级测试，只验证框架能正常工作"""
    suite = ExampleTestSuite()

    # 只测试框架的基本功能，不运行所有示例
    analyzer = suite.analyzer
    examples = analyzer.discover_examples()

    # 验证能够发现示例
    assert len(examples) > 0, "应该能发现至少一个示例文件"

    # 验证 run_all_tests 方法能正常调用（但不实际运行测试）
    # 通过传入空的类别列表来避免运行任何测试
    stats = suite.run_all_tests(categories=["non_existent_category"], quick_only=False)

    # 验证返回的统计信息格式正确
    assert isinstance(stats, dict), "统计信息应该是字典格式"
    expected_keys = {"total", "passed", "failed", "timeout", "skipped"}
    assert expected_keys.issubset(stats.keys()), f"统计信息应该包含键: {expected_keys}"


@app.command()
def analyze():
    """分析 examples 目录结构"""
    analyzer = ExampleAnalyzer()
    examples = analyzer.discover_examples()

    console.print(f"📊 [bold blue]Examples 分析报告[/bold blue]")
    console.print(f"总计发现 {len(examples)} 个示例文件\n")

    # 按类别统计
    categories = {}
    for example in examples:
        if example.category not in categories:
            categories[example.category] = []
        categories[example.category].append(example)

    for category, cat_examples in categories.items():
        console.print(
            f"📁 [bold cyan]{category}[/bold cyan] ({len(cat_examples)} 个文件)"
        )
        for example in cat_examples:
            deps = ", ".join(example.dependencies) if example.dependencies else "无"
            console.print(
                f"  • {Path(example.file_path).name} - {example.estimated_runtime} - 依赖: {deps}"
            )
        console.print()


if __name__ == "__main__":
    app()
