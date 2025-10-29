#!/usr/bin/env python3
"""
Dev-notes Documentation Compliance Checker

检查 dev-notes 文档是否符合规范：
1. 必须放在正确的分类目录下
2. 必须包含日期和作者信息
3. 文件名必须符合命名规范

Author: SAGE Team
Date: 2025-10-23
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# 允许的 dev-notes 分类目录
# 按照 SAGE 系统架构设计：L1-L6 分层 + 跨层主题
ALLOWED_CATEGORIES = {
    # === 架构层次分类 (L1-L6) ===
    "l1-common": "L1 基础层 - sage-common 包相关开发笔记",
    "l2-platform": "L2 平台层 - sage-platform 包相关开发笔记",
    "l3-kernel": "L3 核心层 - sage-kernel 包相关开发笔记",
    "l3-libs": "L3 核心层 - sage-libs 包相关开发笔记",
    "l4-middleware": "L4 中间件层 - sage-middleware 包相关开发笔记",
    "l5-apps": "L5 应用层 - sage-apps 包相关开发笔记",
    "l5-benchmark": "L5 应用层 - sage-benchmark 包相关开发笔记",
    "l6-studio": "L6 工具层 - sage-studio 包相关开发笔记",
    "l6-tools": "L6 工具层 - sage-tools 包相关开发笔记",
    # === 跨层主题分类 (在 cross-layer/ 下) ===
    "cross-layer/architecture": "系统架构设计与演进",
    "cross-layer/ci-cd": "CI/CD 流程、构建系统、自动化",
    "cross-layer/performance": "性能优化、基准测试、调优",
    "cross-layer/security": "安全机制、权限控制、加密",
    "cross-layer/testing": "测试策略、测试框架、质量保证",
    "cross-layer/deployment": "部署方案、运维配置、发布流程",
    "cross-layer/migration": "数据迁移、代码重构、升级指南",
    "cross-layer/documentation": "文档规范、API 文档、用户指南",
    "cross-layer/research": "研究实验、算法探索、原型验证",
    # === 特殊分类 ===
    "archive": "已归档文档（历史记录，只读）",
}

# 特殊文件（不受规则限制）
SPECIAL_FILES = {
    "README.md",
    "TEMPLATE.md",
}

# 必需的元数据字段
REQUIRED_METADATA = ["Date", "Author", "Summary"]


class DevNotesChecker:
    """Dev-notes 文档规范检查器"""

    def __init__(self, root_dir: Path | str, strict: bool = False):
        self.root_dir = Path(root_dir) if isinstance(root_dir, str) else root_dir
        self.devnotes_dir = self.root_dir / "docs" / "dev-notes"
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def check_file(self, file_path: Path) -> bool:
        """检查单个文件是否符合规范"""
        if not file_path.exists():
            return True

        # 获取相对路径
        try:
            rel_path = file_path.relative_to(self.devnotes_dir)
        except ValueError:
            # 文件不在 dev-notes 目录下
            return True

        # 检查是否是特殊文件
        if rel_path.name in SPECIAL_FILES:
            return True

        # 检查是否在根目录（不允许）
        if len(rel_path.parts) == 1:
            self.errors.append(
                f"❌ {rel_path}: 文档必须放在分类目录下，不能直接放在 dev-notes 根目录\n"
                f"   建议: 根据内容移动到合适的分类目录"
            )
            return False

        # 检查分类目录（支持一级或二级分类）
        # 例如: l3-kernel/xxx.md 或 cross-layer/architecture/xxx.md
        if rel_path.parts[0] == "cross-layer":
            # 跨层主题：需要二级分类
            if len(rel_path.parts) < 3:
                self.errors.append(
                    f"❌ {rel_path}: cross-layer 目录下的文档必须放在具体的子分类中\n"
                    f"   例如: cross-layer/architecture/, cross-layer/ci-cd/ 等"
                )
                return False
            category = f"{rel_path.parts[0]}/{rel_path.parts[1]}"
        else:
            # 层次分类或归档：一级分类
            category = rel_path.parts[0]

        if category not in ALLOWED_CATEGORIES:
            allowed_list = "\n   ".join(sorted(ALLOWED_CATEGORIES.keys()))
            self.errors.append(
                f"❌ {rel_path}: 未知的分类目录 '{category}'\n   允许的分类:\n   {allowed_list}"
            )
            return False

        # 检查文件名（不能包含日期，日期应该在元数据中）
        if re.search(r"\d{4}[-_]\d{2}[-_]\d{2}", rel_path.name):
            self.warnings.append(f"⚠️  {rel_path}: 文件名不应包含日期，请在文档元数据中标注日期")

        # 检查元数据
        if not self._check_metadata(file_path, rel_path):
            return False

        return True

    def _check_metadata(self, file_path: Path, rel_path: Path) -> bool:
        """检查文档元数据"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.errors.append(f"❌ {rel_path}: 无法读取文件 - {e}")
            return False

        # 检查是否有元数据区域（前几行）
        lines = content.split("\n")
        metadata = {}

        # 支持两种格式：
        # 1. 元数据在文档开头（第一行开始）
        # 2. 元数据在第一个 # 标题之后
        for i, line in enumerate(lines[:30]):  # 只检查前30行
            # 跳过空行和分隔线
            if not line.strip() or line.strip() == "---":
                continue

            # 跳过标题行
            if line.startswith("#"):
                continue

            # 尝试匹配元数据格式
            # 支持格式：**Key**: Value 或 **Key:** Value 或 Key: Value
            match = re.match(
                r"^\*?\*?(Date|Author|Summary|Related)\*?\*?\s*[:：]\s*(.+)$",
                line.strip(),
                re.IGNORECASE,
            )
            if match:
                key, value = match.groups()
                metadata[key.title()] = value.strip()
            elif metadata:
                # 已经读取到元数据，遇到非元数据行则停止
                break

        # 检查必需字段
        missing_fields = [field for field in REQUIRED_METADATA if field not in metadata]
        if missing_fields:
            self.errors.append(
                f"❌ {rel_path}: 缺少必需的元数据字段: {', '.join(missing_fields)}\n"
                f"   请在文档开头添加:\n"
                f"   **Date**: YYYY-MM-DD\n"
                f"   **Author**: Your Name\n"
                f"   **Summary**: Brief description"
            )
            return False

        # 检查日期格式
        if "Date" in metadata:
            date_str = metadata["Date"]
            if not re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                self.errors.append(f"❌ {rel_path}: 日期格式错误 '{date_str}'，应为 YYYY-MM-DD")
                return False

            # 检查日期是否合理（不能是未来日期）
            try:
                doc_date = datetime.strptime(date_str, "%Y-%m-%d")
                if doc_date > datetime.now():
                    self.warnings.append(f"⚠️  {rel_path}: 日期是未来日期 '{date_str}'")
            except ValueError:
                self.errors.append(f"❌ {rel_path}: 无效的日期 '{date_str}'")
                return False

        return True

    def check_directory_structure(self) -> bool:
        """检查 dev-notes 目录结构"""
        issues_found = False

        if not self.devnotes_dir.exists():
            self.errors.append(f"❌ dev-notes 目录不存在: {self.devnotes_dir}")
            return False

        # 1. 检查是否存在 dev-notes 根目录下的文件（除了特殊文件）
        devnotes_root_files = [
            f for f in self.devnotes_dir.glob("*.md") if f.name not in SPECIAL_FILES
        ]
        if devnotes_root_files:
            self.errors.append(
                f"❌ dev-notes 根目录下有 {len(devnotes_root_files)} 个文件需要整理:\n"
                + "\n".join(f"   - {f.name}" for f in devnotes_root_files[:10])
            )
            if len(devnotes_root_files) > 10:
                self.errors.append(f"   ... 还有 {len(devnotes_root_files) - 10} 个文件")
            issues_found = True

        # 2. 检查项目根目录是否有应该在 dev-notes 的 markdown 文件
        # 允许的根目录文件（用户文档、贡献指南等）
        allowed_root_md = {
            "README.md",
            "CONTRIBUTING.md",
            "DEVELOPER.md",
            "LICENSE.md",
            "CHANGELOG.md",
            "CODE_OF_CONDUCT.md",
        }

        project_root_files = [
            f for f in self.root_dir.glob("*.md") if f.name not in allowed_root_md
        ]

        if project_root_files:
            self.errors.append(
                f"❌ 项目根目录下有 {len(project_root_files)} 个 markdown 文件应该移到 docs/dev-notes/ 下:\n"
                + "\n".join(
                    f"   - {f.name} → 建议移到 docs/dev-notes/<category>/"
                    for f in project_root_files[:10]
                )
            )
            if len(project_root_files) > 10:
                self.errors.append(f"   ... 还有 {len(project_root_files) - 10} 个文件")
            issues_found = True

        return not issues_found

    def check_changed_files(self, changed_files: list[str]) -> tuple[int, int]:
        """检查变更的文件"""
        devnotes_files = [
            f for f in changed_files if f.startswith("docs/dev-notes/") and f.endswith(".md")
        ]

        if not devnotes_files:
            return 0, 0

        print(f"\n📝 检查 {len(devnotes_files)} 个 dev-notes 文档...\n")

        passed = 0
        failed = 0

        for file_str in devnotes_files:
            file_path = self.root_dir / file_str
            if self.check_file(file_path):
                passed += 1
            else:
                failed += 1

        return passed, failed

    def check_all_files(self) -> tuple[int, int]:
        """检查所有 dev-notes 文件"""
        all_files = list(self.devnotes_dir.rglob("*.md"))
        all_files = [f for f in all_files if f.name not in SPECIAL_FILES]

        if not all_files:
            print("ℹ️  没有 dev-notes 文档需要检查")
            return 0, 0

        print(f"\n📝 检查 {len(all_files)} 个 dev-notes 文档...\n")

        passed = 0
        failed = 0

        for file_path in all_files:
            if self.check_file(file_path):
                passed += 1
            else:
                failed += 1

        return passed, failed

    def check_all(self) -> dict:
        """检查所有文件（返回字典格式，用于 CLI）"""
        # 先检查目录结构
        structure_ok = self.check_directory_structure()

        # 再检查文件内容
        passed, failed = self.check_all_files()

        # 如果目录结构有问题，也算失败
        if not structure_ok:
            failed += 1

        return {
            "passed": failed == 0 and (not self.strict or len(self.warnings) == 0),
            "total": passed + failed,
            "passed_count": passed,
            "failed_count": failed,
            "warnings": len(self.warnings),
            "issues": [{"file": "devnotes", "message": err} for err in self.errors]
            + [{"file": "devnotes", "message": warn} for warn in self.warnings],
        }

    def check_changed(self, diff_target: str = "HEAD") -> dict:
        """检查变更的文件（返回字典格式，用于 CLI）"""
        # 先检查目录结构（根目录文件检查）
        structure_ok = self.check_directory_structure()

        # 再检查变更的文件
        changed_files = get_changed_files(self.root_dir, diff_target)
        passed, failed = self.check_changed_files(changed_files)

        # 如果目录结构有问题，也算失败
        if not structure_ok:
            failed += 1

        return {
            "passed": failed == 0 and (not self.strict or len(self.warnings) == 0),
            "total": passed + failed,
            "passed_count": passed,
            "failed_count": failed,
            "warnings": len(self.warnings),
            "issues": [{"file": "devnotes", "message": err} for err in self.errors]
            + [{"file": "devnotes", "message": warn} for warn in self.warnings],
        }

    def print_results(self, passed: int, failed: int) -> bool:
        """打印检查结果"""
        # 打印警告
        if self.warnings:
            print("\n" + "=" * 80)
            print("⚠️  警告信息:")
            print("=" * 80)
            for warning in self.warnings:
                print(warning)

        # 打印错误
        if self.errors:
            print("\n" + "=" * 80)
            print("❌ 错误信息:")
            print("=" * 80)
            for error in self.errors:
                print(error)

        # 打印统计
        print("\n" + "=" * 80)
        print("📊 检查结果:")
        print("=" * 80)
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  警告: {len(self.warnings)}")

        if failed == 0:
            print("\n🎉 所有文档都符合规范！")
            if self.warnings and self.strict:
                print("⚠️  但有警告信息（严格模式已开启）")
                return False
            return True
        else:
            print(f"\n❌ 发现 {failed} 个不符合规范的文档")
            print("\n💡 规范说明:")
            print("1. 文档必须放在分类目录下（architecture, kernel, middleware 等）")
            print("2. 文档开头必须包含元数据:")
            print("   **Date**: YYYY-MM-DD")
            print("   **Author**: Your Name")
            print("   **Summary**: Brief description")
            print("3. 文件名不应包含日期（日期在元数据中标注）")
            print("\n📖 详细规范请参考: docs/dev-notes/TEMPLATE.md")
            return False


def get_changed_files(root_dir: Path, diff_target: str | None = None) -> list[str]:
    """获取变更的文件列表"""
    import subprocess

    try:
        if diff_target:
            # 比较指定的 diff target
            result = subprocess.run(
                ["git", "diff", "--name-only", diff_target],
                cwd=root_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            # 获取暂存区的文件
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=root_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"⚠️  警告: 无法获取 Git 变更文件: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Dev-notes 文档规范检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查所有 dev-notes 文档
  python devnotes_checker.py --all

  # 检查暂存的文件
  python devnotes_checker.py --changed-only

  # 检查与指定提交的差异
  python devnotes_checker.py --changed-only --diff HEAD~5

  # 严格模式（警告也会失败）
  python devnotes_checker.py --all --strict

允许的分类目录:
"""
        + "\n".join(f"  {k}: {v}" for k, v in ALLOWED_CATEGORIES.items()),
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="项目根目录（默认: 当前目录）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="检查所有 dev-notes 文档",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="仅检查变更的文档",
    )
    parser.add_argument(
        "--diff",
        type=str,
        help="比较差异的目标（如 HEAD, HEAD~5, origin/main）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：警告也会导致失败",
    )
    parser.add_argument(
        "--check-structure",
        action="store_true",
        help="检查目录结构（是否有文件在根目录）",
    )

    args = parser.parse_args()

    # 检查是否在 Git 仓库中
    if not (args.root / ".git").exists():
        print("❌ 错误: 不在 Git 仓库中")
        sys.exit(1)

    checker = DevNotesChecker(args.root, strict=args.strict)

    # 打印检查模式
    print("=" * 80)
    print("📚 Dev-notes 文档规范检查")
    print("=" * 80)

    # 检查目录结构
    structure_ok = True
    if args.check_structure:
        print("\n🔍 检查目录结构...")
        if not checker.check_directory_structure():
            structure_ok = False
            print("\n❌ 目录结构检查失败")
        else:
            print("\n✅ 目录结构检查通过")

        # 如果只检查结构，不检查文件内容
        if not args.all and not args.changed_only:
            if not structure_ok:
                checker.print_results(0, 0)
                sys.exit(1)
            sys.exit(0)

    # 执行检查
    if args.all:
        print("\n🔍 检查模式: 全部文档")
        passed, failed = checker.check_all_files()
    elif args.changed_only:
        print("\n🔍 检查模式: 仅变更的文档")
        if args.diff:
            print(f"   差异目标: {args.diff}")
        else:
            print("   差异目标: 暂存区")
        changed_files = get_changed_files(args.root, args.diff)
        passed, failed = checker.check_changed_files(changed_files)
    else:
        parser.print_help()
        sys.exit(0)

    # 打印结果
    success = checker.print_results(passed, failed) and structure_ok

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
