"""
中间结果放置检查工具

此模块提供统一的API来检查项目中间结果文件和目录的放置情况，
确保所有中间结果都放置在 .sage/ 目录下，保持项目根目录整洁。
"""

import fnmatch
import glob
from pathlib import Path


class IntermediateResultsChecker:
    """检查中间结果放置的工具类"""

    def __init__(self, project_root: str):
        """
        初始化检查器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root)

        # 定义不应该在根目录出现的中间结果模式
        self.forbidden_patterns = [
            # ".benchmarks",  # Now configured to use .sage/benchmarks via pytest-benchmark
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            ".coverage",
            "htmlcov",
            ".mypy_cache",
            "logs",
            "outputs",
            "temp",
            "cache",
            "reports",
            "test_results_*.json",
            "benchmark_report_*.json",
            "coverage.xml",
            ".nox",
            ".tox",
            "session_*",  # Ray 临时会话目录
            "tmp_*",  # 临时目录
        ]

        # 定义允许在根目录存在的文件和目录
        self.allowed_items = {
            ".sage",
            ".git",
            ".github",
            ".gitignore",
            ".gitmodules",
            "packages",
            "docs",
            "docs-public",
            "examples",
            "tools",
            "scripts",
            "experiments",
            "data",
            "test_env",
            "README.md",
            "LICENSE",
            "_version.py",
            "quickstart.sh",
            "pytest.ini",
            ".flake8",
            ".pypirc",
            ".github_token",
        }

        # 定义 /tmp 下项目相关的临时文件模式
        self.tmp_project_patterns = [
            "ray/session_*",  # Ray 会话目录
            "sage_*",  # SAGE 相关临时文件
            "pytest_*",  # pytest 临时文件
        ]

    def check_placement(self) -> dict:
        """
        检查项目中间结果放置情况

        Returns:
            Dict: 包含检查结果的字典，格式：
            {
                'violations': List[Dict],  # 违规项列表
                'clean': bool,             # 是否通过检查
                'total_violations': int,   # 违规总数
                'suggestion': str          # 建议信息
            }
        """
        violations = []

        # 检查项目根目录
        root_violations = self._check_project_root()
        violations.extend(root_violations)

        # 检查 /tmp 目录
        tmp_violations = self._check_tmp_directory()
        violations.extend(tmp_violations)

        return {
            "violations": violations,
            "clean": len(violations) == 0,
            "total_violations": len(violations),
            "suggestion": "所有中间结果应该放置在 .sage/ 目录下以保持项目根目录整洁",
        }

    def _check_project_root(self) -> list[dict]:
        """检查项目根目录下的文件和目录"""
        violations = []

        for item in self.project_root.iterdir():
            # 跳过允许的目录和文件
            if item.name in self.allowed_items:
                continue

            # 检查是否匹配禁止模式
            for pattern in self.forbidden_patterns:
                if self._matches_pattern(item.name, pattern):
                    violations.append(
                        {
                            "path": str(item.relative_to(self.project_root)),
                            "type": "directory" if item.is_dir() else "file",
                            "pattern": pattern,
                            "message": "应移动到 .sage/ 目录中",
                            "location": "project_root",
                        }
                    )
                    break

        return violations

    def _check_tmp_directory(self) -> list[dict]:
        """检查 /tmp 目录下是否有项目相关的临时文件"""
        violations: list[dict] = []
        tmp_path = Path("/tmp")

        if not tmp_path.exists():
            return violations

        try:
            for pattern in self.tmp_project_patterns:
                try:
                    matches = glob.glob(str(tmp_path / pattern))
                    for match in matches:
                        violations.append(
                            {
                                "path": match,
                                "type": "temporary",
                                "pattern": pattern,
                                "message": "项目相关临时文件应使用 .sage/temp 目录",
                                "location": "tmp",
                            }
                        )
                except Exception:
                    # 忽略权限错误等
                    pass

        except Exception:
            # 忽略 /tmp 访问错误
            pass

        return violations

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """检查文件名是否匹配模式"""
        return fnmatch.fnmatch(name, pattern)

    def print_check_result(self, check_result: dict | None = None) -> bool:
        """
        打印检查结果

        Args:
            check_result: 检查结果字典，如果为None则重新执行检查

        Returns:
            bool: 是否通过检查
        """
        if check_result is None:
            check_result = self.check_placement()

        if check_result["clean"]:
            print("✅ 中间结果放置检查通过 - 项目根目录整洁")
            return True
        else:
            print(f"⚠️  发现 {check_result['total_violations']} 个中间结果放置问题:")
            for violation in check_result["violations"]:
                print(f"  - {violation['path']} ({violation['type']}): {violation['message']}")
            print(f"\n💡 {check_result['suggestion']}")
            return False

    def get_summary(self) -> str:
        """
        获取检查结果摘要

        Returns:
            str: 检查结果摘要文本
        """
        check_result = self.check_placement()

        if check_result["clean"]:
            return "✅ 中间结果放置检查通过 - 项目根目录整洁"
        else:
            violations_by_location = {}
            for violation in check_result["violations"]:
                location = violation.get("location", "unknown")
                if location not in violations_by_location:
                    violations_by_location[location] = 0
                violations_by_location[location] += 1

            summary_parts = [f"⚠️  发现 {check_result['total_violations']} 个中间结果放置问题"]
            for location, count in violations_by_location.items():
                location_name = "项目根目录" if location == "project_root" else "/tmp目录"
                summary_parts.append(f"  - {location_name}: {count}个")

            return "\n".join(summary_parts)


def check_intermediate_results_placement(project_root: str) -> dict:
    """
    便捷函数：检查中间结果放置情况

    Args:
        project_root: 项目根目录路径

    Returns:
        Dict: 检查结果
    """
    checker = IntermediateResultsChecker(project_root)
    return checker.check_placement()


def print_intermediate_results_check(project_root: str) -> bool:
    """
    便捷函数：打印中间结果检查结果

    Args:
        project_root: 项目根目录路径

    Returns:
        bool: 是否通过检查
    """
    checker = IntermediateResultsChecker(project_root)
    return checker.print_check_result()
