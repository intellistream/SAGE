"""
Core模块测试覆盖率报告生成器
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class TestCoverageReporter:
    """测试覆盖率报告器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or self._find_project_root()
        self.core_src_path = self.project_root / "src" / "sage" / "core"
        self.core_tests_path = self.project_root / "tests" / "core"

    def _find_project_root(self) -> Path:
        """查找项目根目录"""
        current_dir = Path(__file__).parent
        while current_dir.parent != current_dir:
            if (current_dir / "pyproject.toml").exists():
                return current_dir
            current_dir = current_dir.parent
        return Path(__file__).parent

    def get_source_files(self) -> list[Path]:
        """获取所有源文件"""
        source_files = []
        for pattern in ["*.py"]:
            source_files.extend(self.core_src_path.rglob(pattern))
        return [f for f in source_files if not f.name.startswith("__")]

    def get_test_files(self) -> list[Path]:
        """获取所有测试文件"""
        test_files = []
        for pattern in ["test_*.py", "*_test.py"]:
            test_files.extend(self.core_tests_path.rglob(pattern))
        return test_files

    def map_source_to_test(self) -> dict[str, str]:
        """映射源文件到测试文件"""
        source_files = self.get_source_files()
        self.get_test_files()

        mapping = {}

        for src_file in source_files:
            # 计算相对路径
            rel_path = src_file.relative_to(self.core_src_path)

            # 查找对应的测试文件
            expected_test_name = f"test_{src_file.stem}.py"

            # 在对应的测试目录中查找
            test_dir = self.core_tests_path / rel_path.parent
            expected_test_path = test_dir / expected_test_name

            if expected_test_path.exists():
                mapping[str(rel_path)] = str(expected_test_path.relative_to(self.core_tests_path))
            else:
                mapping[str(rel_path)] = None

        return mapping

    def analyze_test_compliance(self) -> dict[str, Any]:
        """分析测试合规性"""
        source_to_test = self.map_source_to_test()

        total_files = len(source_to_test)
        covered_files = sum(1 for test_path in source_to_test.values() if test_path is not None)
        uncovered_files = total_files - covered_files

        compliance_rate = (covered_files / total_files * 100) if total_files > 0 else 0

        return {
            "total_source_files": total_files,
            "covered_files": covered_files,
            "uncovered_files": uncovered_files,
            "compliance_rate": compliance_rate,
            "source_to_test_mapping": source_to_test,
            "uncovered_source_files": [src for src, test in source_to_test.items() if test is None],
        }

    def run_coverage_analysis(self) -> dict[str, Any]:
        """运行覆盖率分析"""
        os.chdir(self.project_root)

        # 运行pytest with coverage
        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/core/",
            "--cov=src/sage/core",
            "--cov-report=json:coverage-core.json",
            "--cov-report=term-missing",
            "-q",  # quiet mode
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            # 读取覆盖率JSON报告
            coverage_file = self.project_root / "coverage-core.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                return {
                    "success": True,
                    "coverage_data": coverage_data,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            else:
                return {
                    "success": False,
                    "error": "Coverage file not generated",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        compliance = self.analyze_test_compliance()
        coverage = self.run_coverage_analysis()

        report = []
        report.append("# SAGE Core模块测试覆盖率报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 测试合规性部分
        report.append("## 1. 测试合规性分析")
        report.append("")
        report.append(f"- **总源文件数**: {compliance['total_source_files']}")
        report.append(f"- **已覆盖文件数**: {compliance['covered_files']}")
        report.append(f"- **未覆盖文件数**: {compliance['uncovered_files']}")
        report.append(f"- **合规率**: {compliance['compliance_rate']:.2f}%")
        report.append("")

        # 合规性状态
        if compliance["compliance_rate"] >= 80:
            status = "✅ 优秀"
        elif compliance["compliance_rate"] >= 60:
            status = "⚠️ 良好"
        else:
            status = "❌ 需要改进"

        report.append(f"**合规性状态**: {status}")
        report.append("")

        # 文件映射表
        report.append("## 2. 源文件到测试文件映射")
        report.append("")
        report.append("| 源文件 | 测试文件 | 状态 |")
        report.append("|--------|----------|------|")

        for src_file, test_file in compliance["source_to_test_mapping"].items():
            if test_file:
                status = "✅"
                test_display = test_file
            else:
                status = "❌"
                test_display = "缺失"
            report.append(f"| `{src_file}` | `{test_display}` | {status} |")

        report.append("")

        # 未覆盖文件列表
        if compliance["uncovered_source_files"]:
            report.append("## 3. 未覆盖的源文件")
            report.append("")
            for src_file in compliance["uncovered_source_files"]:
                report.append(f"- `{src_file}`")
            report.append("")

        # 代码覆盖率部分
        if coverage["success"] and "coverage_data" in coverage:
            cov_data = coverage["coverage_data"]
            report.append("## 4. 代码覆盖率分析")
            report.append("")

            if "totals" in cov_data:
                totals = cov_data["totals"]
                line_rate = totals.get("percent_covered", 0)
                report.append(f"- **行覆盖率**: {line_rate:.2f}%")
                report.append(f"- **总行数**: {totals.get('num_statements', 0)}")
                report.append(f"- **覆盖行数**: {totals.get('covered_lines', 0)}")
                report.append(f"- **缺失行数**: {totals.get('missing_lines', 0)}")
                report.append("")

            # 按文件的覆盖率
            if "files" in cov_data:
                report.append("### 4.1 按文件覆盖率详情")
                report.append("")
                report.append("| 文件 | 覆盖率 | 总行数 | 覆盖行数 | 缺失行数 |")
                report.append("|------|--------|--------|----------|----------|")

                for file_path, file_data in cov_data["files"].items():
                    if "src/sage/core" in file_path:
                        # 只显示core模块的文件
                        rel_path = file_path.replace("src/sage/core/", "")
                        coverage_pct = file_data.get("summary", {}).get("percent_covered", 0)
                        num_statements = file_data.get("summary", {}).get("num_statements", 0)
                        covered = file_data.get("summary", {}).get("covered_lines", 0)
                        missing = file_data.get("summary", {}).get("missing_lines", 0)

                        report.append(
                            f"| `{rel_path}` | {coverage_pct:.1f}% | {num_statements} | {covered} | {missing} |"
                        )

                report.append("")
        else:
            report.append("## 4. 代码覆盖率分析")
            report.append("")
            report.append("❌ 覆盖率分析失败")
            if "error" in coverage:
                report.append(f"错误信息: {coverage['error']}")
            report.append("")

        # 建议和改进
        report.append("## 5. 建议和改进")
        report.append("")

        if compliance["compliance_rate"] < 100:
            report.append("### 5.1 测试覆盖建议")
            report.append("")
            for src_file in compliance["uncovered_source_files"]:
                # 生成测试文件建议路径
                src_path = Path(src_file)
                suggested_test = f"tests/core/{src_path.parent}/test_{src_path.stem}.py"
                report.append(f"- 为 `{src_file}` 创建测试文件: `{suggested_test}`")
            report.append("")

        if coverage["success"] and "coverage_data" in coverage:
            cov_data = coverage["coverage_data"]
            if "totals" in cov_data:
                line_rate = cov_data["totals"].get("percent_covered", 0)
                if line_rate < 80:
                    report.append("### 5.2 代码覆盖率改进")
                    report.append("")
                    report.append("- 当前行覆盖率低于80%，建议增加更多测试用例")
                    report.append("- 特别关注分支覆盖和边界情况测试")
                    report.append("- 考虑添加集成测试以提高整体覆盖率")
                    report.append("")

        # Issue要求对比
        report.append("## 6. Issue要求对比")
        report.append("")
        report.append("根据 Issue 要求，检查测试组织架构完成情况：")
        report.append("")

        required_structure = {
            "test_pipeline.py": "Pipeline核心测试",
            "function/test_base_function.py": "BaseFunction测试",
            "function/test_comap_function.py": "CoMapFunction测试",
            "function/test_sink_function.py": "SinkFunction测试",
            "function/test_source_function.py": "SourceFunction测试",
            "operator/test_base_operator.py": "BaseOperator测试",
            "service/test_base_service.py": "BaseService测试",
        }

        report.append("| 要求的测试文件 | 描述 | 状态 |")
        report.append("|----------------|------|------|")

        for test_file, description in required_structure.items():
            test_path = self.core_tests_path / test_file
            status = "✅ 已完成" if test_path.exists() else "❌ 缺失"
            report.append(f"| `{test_file}` | {description} | {status} |")

        report.append("")

        # 总结
        completed_count = sum(
            1
            for test_file in required_structure.keys()
            if (self.core_tests_path / test_file).exists()
        )
        total_required = len(required_structure)
        completion_rate = (completed_count / total_required * 100) if total_required > 0 else 0

        report.append("## 7. 总结")
        report.append("")
        report.append(
            f"- **Issue要求完成度**: {completion_rate:.1f}% ({completed_count}/{total_required})"
        )
        report.append(f"- **测试文件合规率**: {compliance['compliance_rate']:.1f}%")

        if coverage["success"] and "coverage_data" in coverage:
            line_rate = coverage["coverage_data"]["totals"].get("percent_covered", 0)
            report.append(f"- **代码行覆盖率**: {line_rate:.1f}%")

        report.append("")

        if completion_rate >= 100 and compliance["compliance_rate"] >= 80:
            report.append("🎉 **恭喜！测试组织架构已按照Issue要求完成，质量良好！**")
        elif completion_rate >= 80:
            report.append("👍 **测试架构基本完成，还有少量工作需要完善**")
        else:
            report.append("⚠️ **测试架构需要继续完善以满足Issue要求**")

        return "\n".join(report)

    def save_report(self, filename: str = None) -> Path:
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_coverage_report_{timestamp}.md"

        report_path = self.project_root / filename
        report_content = self.generate_markdown_report()

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return report_path


def main():
    """主函数"""
    reporter = TestCoverageReporter()

    print("生成SAGE Core模块测试覆盖率报告...")
    print("=" * 50)

    # 生成并保存报告
    report_path = reporter.save_report()
    print(f"报告已保存到: {report_path}")

    # 显示简要摘要
    compliance = reporter.analyze_test_compliance()
    print("\n快速摘要:")
    print(f"- 测试合规率: {compliance['compliance_rate']:.1f}%")
    print(f"- 源文件总数: {compliance['total_source_files']}")
    print(f"- 已覆盖文件: {compliance['covered_files']}")
    print(f"- 未覆盖文件: {compliance['uncovered_files']}")

    if compliance["uncovered_source_files"]:
        print("\n需要创建测试的文件:")
        for src_file in compliance["uncovered_source_files"][:5]:  # 只显示前5个
            print(f"  - {src_file}")
        if len(compliance["uncovered_source_files"]) > 5:
            print(f"  ... 还有{len(compliance['uncovered_source_files']) - 5}个文件")


if __name__ == "__main__":
    main()
