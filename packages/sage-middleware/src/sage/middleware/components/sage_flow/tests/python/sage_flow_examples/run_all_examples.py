#!/usr/bin/env python3
"""
SAGE Flow 示例测试运行器

批量运行所有示例并收集测试结果和问题

作者: Kilo Code
日期: 2025-09-04
"""

import sys
import os
import subprocess
import time
from typing import List, Dict, Any
from datetime import datetime

class ExampleTestRunner:
    """示例测试运行器"""

    def __init__(self):
        self.examples_dir = os.path.dirname(__file__)
        self.test_results = []
        self.issues_found = []

    def get_example_files(self) -> List[str]:
        """获取所有示例文件"""
        example_files = []
        for file in os.listdir(self.examples_dir):
            if file.endswith('.py') and file != 'run_all_examples.py' and not file.startswith('__'):
                example_files.append(file)
        return sorted(example_files)

    def run_example(self, example_file: str) -> Dict[str, Any]:
        """运行单个示例"""
        print(f"\n{'='*60}")
        print(f"运行示例: {example_file}")
        print('='*60)

        start_time = time.time()
        result = {
            "example": example_file,
            "start_time": datetime.now().isoformat(),
            "exit_code": None,
            "duration": None,
            "output": "",
            "errors": [],
            "warnings": [],
            "success": False
        }

        try:
            # 运行示例
            cmd = [sys.executable, os.path.join(self.examples_dir, example_file)]
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                cwd=self.examples_dir
            )

            end_time = time.time()
            result["exit_code"] = process.returncode
            result["duration"] = end_time - start_time
            result["output"] = process.stdout
            result["success"] = process.returncode == 0

            # 分析输出
            if process.stderr:
                errors = self.parse_errors(process.stderr)
                result["errors"] = errors

            # 检查输出中的警告
            warnings = self.parse_warnings(process.stdout + process.stderr)
            result["warnings"] = warnings

            # 打印结果摘要
            status = "✓ 成功" if result["success"] else "✗ 失败"
            print(f"{status} - 运行时间: {result['duration']:.2f}秒")
            print(f"退出代码: {result['exit_code']}")

            if result["errors"]:
                print(f"发现 {len(result['errors'])} 个错误")
            if result["warnings"]:
                print(f"发现 {len(result['warnings'])} 个警告")

        except subprocess.TimeoutExpired:
            result["errors"].append("执行超时 (5分钟)")
            result["success"] = False
            print("✗ 执行超时")
        except Exception as e:
            result["errors"].append(f"执行异常: {str(e)}")
            result["success"] = False
            print(f"✗ 执行异常: {e}")

        return result

    def parse_errors(self, stderr: str) -> List[str]:
        """解析错误信息"""
        errors = []
        for line in stderr.split('\n'):
            line = line.strip()
            if line and ('error' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower()):
                errors.append(line)
        return errors

    def parse_warnings(self, output: str) -> List[str]:
        """解析警告信息"""
        warnings = []
        for line in output.split('\n'):
            line = line.strip()
            if line and ('warning' in line.lower() or 'warn' in line.lower()):
                warnings.append(line)
        return warnings

    def analyze_results(self):
        """分析测试结果"""
        print(f"\n{'='*80}")
        print("测试结果分析")
        print('='*80)

        total_examples = len(self.test_results)
        successful_examples = sum(1 for r in self.test_results if r["success"])
        failed_examples = total_examples - successful_examples

        print(f"总示例数: {total_examples}")
        print(f"成功示例: {successful_examples}")
        print(f"失败示例: {failed_examples}")
        print(".1f")

        # 统计问题
        total_errors = sum(len(r["errors"]) for r in self.test_results)
        total_warnings = sum(len(r["warnings"]) for r in self.test_results)

        print(f"总错误数: {total_errors}")
        print(f"总警告数: {total_warnings}")

        # 详细结果
        print("\n详细结果:")
        for result in self.test_results:
            status = "✓" if result["success"] else "✗"
            duration = ".2f" if result["duration"] else "N/A"
            print(f"  {status} {result['example']}: {duration}秒")

            if result["errors"]:
                print(f"    错误: {len(result['errors'])} 个")
                for error in result["errors"][:2]:  # 只显示前2个错误
                    print(f"      - {error}")

            if result["warnings"]:
                print(f"    警告: {len(result['warnings'])} 个")
                for warning in result["warnings"][:2]:  # 只显示前2个警告
                    print(f"      - {warning}")

    def collect_common_issues(self):
        """收集常见问题"""
        print(f"\n{'='*80}")
        print("常见问题分析")
        print('='*80)

        all_errors = []
        all_warnings = []

        for result in self.test_results:
            all_errors.extend(result["errors"])
            all_warnings.extend(result["warnings"])

        # 统计常见错误
        error_patterns = {}
        for error in all_errors:
            # 简化错误模式匹配
            if "No module named 'sage_flow_datastream'" in error:
                pattern = "SAGE Flow 模块未安装"
            elif "psutil" in error.lower():
                pattern = "psutil 模块缺失"
            elif "syntax" in error.lower():
                pattern = "语法错误"
            elif "import" in error.lower():
                pattern = "导入错误"
            else:
                pattern = "其他错误"

            error_patterns[pattern] = error_patterns.get(pattern, 0) + 1

        # 统计常见警告
        warning_patterns = {}
        for warning in all_warnings:
            if "模拟模式" in warning:
                pattern = "运行在模拟模式"
            elif "deprecated" in warning.lower():
                pattern = "弃用警告"
            elif "performance" in warning.lower():
                pattern = "性能警告"
            else:
                pattern = "其他警告"

            warning_patterns[pattern] = warning_patterns.get(pattern, 0) + 1

        print("常见错误模式:")
        for pattern, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"  {pattern}: {count} 次")

        print("\n常见警告模式:")
        for pattern, count in sorted(warning_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"  {pattern}: {count} 次")

    def generate_report(self):
        """生成测试报告"""
        report_file = os.path.join(self.examples_dir, "test_report.md")

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# SAGE Flow 示例测试报告\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n\n")

            f.write("## 测试概览\n\n")
            total = len(self.test_results)
            successful = sum(1 for r in self.test_results if r["success"])
            f.write(f"- 总示例数: {total}\n")
            f.write(f"- 成功示例: {successful}\n")
            f.write(f"- 失败示例: {total - successful}\n")
            f.write(".1f")

            f.write("\n## 详细结果\n\n")
            for result in self.test_results:
                status = "✅ 成功" if result["success"] else "❌ 失败"
                f.write(f"### {result['example']}\n\n")
                f.write(f"- 状态: {status}\n")
                f.write(".2f")
                f.write(f"- 退出代码: {result['exit_code']}\n")

                if result["errors"]:
                    f.write("\n**错误:**\n")
                    for error in result["errors"]:
                        f.write(f"- {error}\n")

                if result["warnings"]:
                    f.write("\n**警告:**\n")
                    for warning in result["warnings"]:
                        f.write(f"- {warning}\n")

                f.write("\n")

            f.write("## 建议\n\n")
            f.write("1. **安装依赖**: 确保安装了所有必需的 Python 包\n")
            f.write("2. **编译模块**: 编译并安装 SAGE Flow Python 模块\n")
            f.write("3. **检查环境**: 验证 Python 环境配置正确\n")
            f.write("4. **更新依赖**: 考虑更新过时的依赖包\n")

        print(f"\n✓ 测试报告已生成: {report_file}")

def main():
    """主函数"""
    print("SAGE Flow 示例测试运行器")
    print("=" * 60)

    runner = ExampleTestRunner()

    # 获取示例文件
    example_files = runner.get_example_files()
    print(f"发现 {len(example_files)} 个示例文件:")
    for i, file in enumerate(example_files, 1):
        print(f"  {i}. {file}")

    # 运行所有示例
    print("\n开始运行示例测试...")
    for example_file in example_files:
        result = runner.run_example(example_file)
        runner.test_results.append(result)

    # 分析结果
    runner.analyze_results()
    runner.collect_common_issues()
    runner.generate_report()

    print("\n✓ 所有示例测试完成")

if __name__ == "__main__":
    main()