"""
Example Test Suite Module

This module provides the main test suite for running and managing
example tests, including result collection and reporting.
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import ExampleAnalyzer
from .models import ExampleInfo, ExampleTestResult
from .runner import ExampleRunner

console = Console()


class ExampleTestSuite:
    """示例测试套件"""

    def __init__(self):
        """初始化 ExampleTestSuite

        Raises:
            RuntimeError: 如果开发环境不可用
        """
        self.analyzer = ExampleAnalyzer()
        self.runner = ExampleRunner()
        self.results: list[ExampleTestResult] = []

    def _show_examples_summary(self, examples: list[ExampleInfo]):
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
            runtime_summary = (
                f"快速: {runtimes.count('quick')}, "
                f"中等: {runtimes.count('medium')}, "
                f"慢速: {runtimes.count('slow')}"
            )

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

    def _get_statistics(self) -> dict[str, int]:
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
        """保存测试结果

        Args:
            output_file: 输出文件路径
        """
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

    def run_all_tests(
        self, categories: list[str] | None = None, quick_only: bool = False
    ) -> dict[str, int]:
        """运行所有测试

        Args:
            categories: 要测试的类别列表，None表示所有类别
            quick_only: 是否只运行快速测试

        Returns:
            测试统计字典
        """
        console.print("🚀 [bold blue]开始运行 SAGE Examples 测试[/bold blue]")

        # 发现所有示例
        examples = self.analyzer.discover_examples()

        if not examples:
            console.print("[yellow]没有发现任何示例文件[/yellow]")
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "timeout": 0}

        # 过滤示例
        filtered_examples = self._filter_examples(examples, categories, quick_only)

        if not filtered_examples:
            console.print("[yellow]没有符合条件的示例文件[/yellow]")
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "timeout": 0}

        # 显示摘要
        self._show_examples_summary(filtered_examples)

        # 运行测试
        console.print(f"\n🧪 开始测试 {len(filtered_examples)} 个示例文件...")

        self.results = []
        for i, example in enumerate(filtered_examples, 1):
            console.print(f"[{i}/{len(filtered_examples)}] 测试 {Path(example.file_path).name}...")

            result = self.runner.run_example(example)
            self.results.append(result)

            # 显示结果
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "timeout": "⏰",
            }.get(result.status, "❓")

            console.print(
                f"  {status_emoji} {result.status.upper()} ({result.execution_time:.2f}s)"
            )
            if result.error:
                console.print(f"    错误: {result.error}")

        # 显示结果和统计
        console.print("\n" + "=" * 50)
        self._show_results()
        stats = self._get_statistics()

        return stats

    def _filter_examples(
        self,
        examples: list[ExampleInfo],
        categories: list[str] | None = None,
        quick_only: bool = False,
    ) -> list[ExampleInfo]:
        """过滤示例

        Args:
            examples: 所有示例列表
            categories: 要包含的类别
            quick_only: 是否只包含快速测试

        Returns:
            过滤后的示例列表
        """
        filtered = examples

        # 按类别过滤
        if categories:
            filtered = [e for e in filtered if e.category in categories]

        # 按运行时间过滤
        if quick_only:
            filtered = [e for e in filtered if e.estimated_runtime == "quick"]

        # 检查测试标记
        filtered = [e for e in filtered if "skip" not in e.test_tags]

        return filtered
