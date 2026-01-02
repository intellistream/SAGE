#!/usr/bin/env python3
"""
SAGE 依赖版本同步工具

根据 dependencies-spec.yaml 统一所有包的依赖版本
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ 需要安装 PyYAML: pip install pyyaml")
    sys.exit(1)


class DependencySynchronizer:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.spec_file = root_dir / "dependencies-spec.yaml"
        self.packages_dir = root_dir / "packages"

        # 加载规范
        with open(self.spec_file) as f:
            self.spec = yaml.safe_load(f)

        # 提取核心依赖
        self.core_deps = self.spec.get("core", {})

    def parse_dependency_line(self, line: str) -> tuple[str, str]:
        """解析依赖行，返回 (包名, 完整约束)"""
        line = line.strip().strip('"').strip("'")
        # 处理 package[extra]>=version 格式
        match = re.match(r"^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9,]+\])?)(.*)", line)
        if match:
            pkg_name = match.group(1)
            # version_spec is intentionally not used, only for parsing structure
            return pkg_name.split("[")[0], line
        return "", line

    def check_package_deps(self, pkg_path: Path) -> dict[str, list[str]]:
        """检查包的依赖是否符合规范"""
        pyproject = pkg_path / "pyproject.toml"
        if not pyproject.exists():
            return {}

        issues = {}

        with open(pyproject) as f:
            content = f.read()

        # 简单解析 dependencies 列表
        in_deps = False
        for line in content.split("\n"):
            if "dependencies = [" in line:
                in_deps = True
                continue
            if in_deps and "]" in line:
                in_deps = False
                continue

            if in_deps and line.strip().startswith('"'):
                pkg_name, full_dep = self.parse_dependency_line(line)

                # 检查是否在核心依赖中
                if pkg_name in self.core_deps:
                    expected = self.core_deps[pkg_name]
                    # 标准化比较（移除空格）
                    line_normalized = line.replace(" ", "")
                    expected_normalized = f'"{pkg_name}{expected}"'.replace(" ", "")

                    if expected_normalized not in line_normalized:
                        if pkg_name not in issues:
                            issues[pkg_name] = []
                        issues[pkg_name].append(
                            {
                                "found": full_dep.strip(),
                                "expected": f"{pkg_name}{expected}",
                                "package": pkg_path.name,
                            }
                        )

        return issues

    def scan_all_packages(self) -> dict[str, list[dict]]:
        """扫描所有包"""
        all_issues = {}

        for pkg_dir in self.packages_dir.iterdir():
            if not pkg_dir.is_dir() or pkg_dir.name.startswith("."):
                continue

            issues = self.check_package_deps(pkg_dir)
            for pkg_name, problems in issues.items():
                if pkg_name not in all_issues:
                    all_issues[pkg_name] = []
                all_issues[pkg_name].extend(problems)

        return all_issues

    def report(self):
        """生成报告"""
        print("🔍 扫描 SAGE 依赖版本一致性...")
        print()

        issues = self.scan_all_packages()

        if not issues:
            print("✅ 所有包的依赖版本都符合规范！")
            return 0

        print(f"⚠️  发现 {len(issues)} 个包的版本不一致：")
        print()

        for pkg_name, problems in sorted(issues.items()):
            print(f"📦 {pkg_name}")
            print(f"   期望版本: {self.core_deps.get(pkg_name, '(未定义)')}")
            print()

            # 按包分组
            by_package = {}
            for problem in problems:
                pkg = problem["package"]
                if pkg not in by_package:
                    by_package[pkg] = []
                by_package[pkg].append(problem["found"])

            for pkg, versions in sorted(by_package.items()):
                print(f"   ❌ {pkg}:")
                for ver in versions:
                    print(f"      {ver}")
            print()

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("💡 建议:")
        print("  1. 根据上述输出手动修改各包的 pyproject.toml")
        print("  2. 或运行: python tools/scripts/sync_dependencies.py --fix")
        print()

        return len(issues)


def main():
    root = Path(__file__).parent.parent.parent
    syncer = DependencySynchronizer(root)
    exit_code = syncer.report()
    sys.exit(exit_code if exit_code > 0 else 0)


if __name__ == "__main__":
    main()
