#!/usr/bin/env python3
"""
Package README Checker

This tool checks if package README files follow the standard template structure.

Usage:
    python tools/package_readme_checker.py [--fix] [--package PACKAGE_NAME]

Options:
    --fix                  Generate missing sections (interactive mode)
    --package NAME         Check only specific package
    --all                  Check all packages (default)
    --report               Generate detailed report
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class READMESection:
    """Represents a README section."""

    name: str
    pattern: str
    required: bool = True
    found: bool = False


@dataclass
class PackageREADMECheck:
    """Represents a package README check result."""

    package_name: str
    readme_path: Path
    exists: bool = False
    sections: list[READMESection] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    score: float = 0.0

    def calculate_score(self) -> float:
        """Calculate README quality score (0-100)."""
        if not self.exists:
            return 0.0

        required_sections = [s for s in self.sections if s.required]
        optional_sections = [s for s in self.sections if not s.required]

        required_found = sum(1 for s in required_sections if s.found)
        optional_found = sum(1 for s in optional_sections if s.found)

        required_score = (required_found / len(required_sections) * 70) if required_sections else 0
        optional_score = (optional_found / len(optional_sections) * 30) if optional_sections else 0

        base_score = required_score + optional_score

        # Deduct points for issues (each issue -5 points, minimum 0)
        issue_penalty = len(self.issues) * 5
        self.score = max(0.0, base_score - issue_penalty)

        return self.score


class PackageREADMEChecker:
    """Checker for package README files."""

    # Required sections for all package READMEs
    REQUIRED_SECTIONS = [
        READMESection("Title", r"^#\s+", True),
        READMESection("Overview", r"^##\s+(📋\s+)?Overview", True),
        READMESection("Installation", r"^##\s+(🚀\s+)?Installation", True),
        READMESection("Quick Start", r"^##\s+(📖\s+)?Quick Start", True),
        READMESection("License", r"^##\s+(📄\s+)?License", True),
    ]

    # Recommended sections
    RECOMMENDED_SECTIONS = [
        READMESection("Features", r"^##\s+(✨\s+)?(?:Key\s+)?Features", False),
        READMESection("Package Structure", r"^##\s+(📦\s+)?Package Structure", False),
        READMESection("Configuration", r"^##\s+(🔧\s+)?Configuration", False),
        READMESection("Documentation", r"^##\s+(📚\s+)?Documentation", False),
        READMESection("Testing", r"^##\s+(🧪\s+)?Testing", False),
        READMESection("Contributing", r"^##\s+(🤝\s+)?Contributing", False),
    ]

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.packages_dir = workspace_root / "packages"

    def get_packages(self) -> list[str]:
        """Get list of all packages."""
        if not self.packages_dir.exists():
            return []

        return [
            p.name for p in self.packages_dir.iterdir() if p.is_dir() and p.name.startswith("sage-")
        ]

    def check_readme(self, package_name: str) -> PackageREADMECheck:
        """Check README for a specific package."""
        package_path = self.packages_dir / package_name
        readme_path = package_path / "README.md"

        result = PackageREADMECheck(
            package_name=package_name,
            readme_path=readme_path,
            sections=self.REQUIRED_SECTIONS + self.RECOMMENDED_SECTIONS,
        )

        # Check if README exists
        if not readme_path.exists():
            result.issues.append("README.md not found")
            return result

        result.exists = True

        # Read README content
        content = readme_path.read_text(encoding="utf-8")

        # Check each section
        for section in result.sections:
            if re.search(section.pattern, content, re.MULTILINE | re.IGNORECASE):
                section.found = True
            elif section.required:
                result.issues.append(f"Missing required section: {section.name}")

        # Additional checks
        self._check_code_blocks(content, result)
        self._check_links(content, result)
        self._check_badges(content, result)

        result.calculate_score()
        return result

    def _check_code_blocks(self, content: str, result: PackageREADMECheck):
        """Check if README has code examples."""
        code_blocks = re.findall(r"```[\w]*\n", content)
        if not code_blocks:
            result.issues.append("No code examples found (recommended)")

    def _check_links(self, content: str, result: PackageREADMECheck):
        """Check for broken link patterns."""
        # Check for placeholder links
        placeholders = re.findall(r"\{[A-Z_]+\}", content)
        if placeholders:
            result.issues.append(f"Found placeholder text: {', '.join(set(placeholders))}")

    def _check_badges(self, content: str, result: PackageREADMECheck):
        """Check if README has status badges."""
        badges = re.findall(r"!\[.*?\]\(.*?\)", content)
        if not badges:
            result.issues.append("No status badges found (recommended)")

    def check_all_packages(self) -> dict[str, PackageREADMECheck]:
        """Check all packages."""
        packages = self.get_packages()
        results = {}

        for package in packages:
            results[package] = self.check_readme(package)

        return results

    def print_summary(self, results: dict[str, PackageREADMECheck]):
        """Print summary of all checks."""
        print("=" * 70)
        print("📦 Package README Quality Report")
        print("=" * 70)
        print()

        total_packages = len(results)
        packages_with_readme = sum(1 for r in results.values() if r.exists)
        avg_score = sum(r.score for r in results.values()) / total_packages if total_packages else 0

        print("📊 Overall Statistics:")
        print(f"  - Total packages: {total_packages}")
        print(f"  - Packages with README: {packages_with_readme}")
        print(f"  - Average quality score: {avg_score:.1f}/100")
        print()

        # Sort by score
        sorted_results = sorted(results.items(), key=lambda x: x[1].score, reverse=True)

        print("📋 Individual Package Scores:")
        print()

        for package_name, result in sorted_results:
            status = "✅" if result.score >= 80 else "⚠️" if result.score >= 60 else "❌"
            print(f"{status} {package_name:25} Score: {result.score:5.1f}/100")

            if result.issues:
                for issue in result.issues[:3]:  # Show first 3 issues
                    print(f"     - {issue}")
                if len(result.issues) > 3:
                    print(f"     ... and {len(result.issues) - 3} more issues")
            print()

    def generate_detailed_report(self, results: dict[str, PackageREADMECheck]) -> str:
        """Generate detailed markdown report."""
        lines = ["# Package README Quality Report", ""]
        lines.append(f"**Generated**: {self._get_timestamp()}")
        lines.append("")

        # Summary
        total = len(results)
        avg_score = sum(r.score for r in results.values()) / total if total else 0

        lines.extend(
            [
                "## Summary",
                "",
                f"- **Total Packages**: {total}",
                f"- **Average Score**: {avg_score:.1f}/100",
                "",
            ]
        )

        # Detailed results
        lines.extend(["## Detailed Results", ""])

        for package_name, result in sorted(results.items()):
            lines.append(f"### {package_name}")
            lines.append("")
            lines.append(f"**Score**: {result.score:.1f}/100")
            lines.append("")

            if not result.exists:
                lines.append("❌ **README.md not found**")
                lines.append("")
                continue

            # Section checklist
            lines.append("#### Sections")
            lines.append("")

            for section in result.sections:
                status = "✅" if section.found else "❌" if section.required else "⚠️"
                req_label = " (required)" if section.required else " (recommended)"
                lines.append(f"- {status} {section.name}{req_label}")

            lines.append("")

            # Issues
            if result.issues:
                lines.append("#### Issues")
                lines.append("")
                for issue in result.issues:
                    lines.append(f"- {issue}")
                lines.append("")

        return "\n".join(lines)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check package README quality")
    parser.add_argument("--package", help="Check specific package")
    parser.add_argument("--all", action="store_true", help="Check all packages")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    # Find workspace root
    workspace_root = Path(__file__).parent.parent

    checker = PackageREADMEChecker(workspace_root)

    # Check packages
    if args.package:
        results = {args.package: checker.check_readme(args.package)}
    else:
        results = checker.check_all_packages()

    # Print summary
    checker.print_summary(results)

    # Generate report if requested
    if args.report:
        report = checker.generate_detailed_report(results)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding="utf-8")
            print(f"\n✅ Report saved to: {output_path}")
        else:
            print("\n" + "=" * 70)
            print(report)

    # Exit with error if any package has low score
    avg_score = sum(r.score for r in results.values()) / len(results) if results else 0
    failing_packages = [name for name, r in results.items() if r.score < 80 or r.issues]

    if failing_packages:
        print(f"\n❌ {len(failing_packages)} package(s) have README quality issues:")
        for pkg in failing_packages:
            print(f"   - {pkg}: {results[pkg].score:.1f}/100")

        # 如果平均分高于 90，只显示警告而不失败
        if avg_score >= 90:
            print(f"\n⚠️  虽然有 {len(failing_packages)} 个包需要改进，")
            print(f"    但平均分 {avg_score:.1f}/100 >= 90，仅作为警告")
            print("    建议修复以上问题以达到更高质量标准")
            return 0
        else:
            print(f"\n💡 平均分 {avg_score:.1f}/100 < 90，需要改进")
            return 1

    print("\n✅ All package READMEs meet quality standards!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
