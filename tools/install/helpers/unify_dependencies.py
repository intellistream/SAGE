#!/usr/bin/env python3
"""统一 SAGE 所有包的依赖版本冲突

扫描所有 pyproject.toml，识别版本不一致的依赖，自动选择最严格的版本。
支持 extras（如 passlib[argon2]）的合并。
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"


def parse_dependency(dep: str) -> tuple:
    """解析依赖，返回 (包名, extras, 版本约束, 原始字符串)

    Examples:
        'numpy>=1.24.0' -> ('numpy', '', '>=1.24.0', 'numpy>=1.24.0')
        'passlib[argon2]>=1.7.4' -> ('passlib', '[argon2]', '>=1.7.4', 'passlib[argon2]>=1.7.4')
    """
    match = re.match(r"^([a-zA-Z0-9_-]+)(\[[a-zA-Z0-9,_-]+\])?(.*)", dep)
    if match:
        pkg_name = match.group(1).lower()
        extras = match.group(2) or ""
        constraint = match.group(3).strip()
        return pkg_name, extras, constraint, dep
    return None, None, None, dep


def merge_versions(versions: dict) -> str:
    """合并多个版本，选择最严格的约束 + 合并所有 extras

    Args:
        versions: {原始依赖字符串: [使用该版本的包列表]}

    Returns:
        统一后的依赖字符串
    """
    all_extras = set()
    best_constraint = ""
    pkg_name = None

    for dep in versions.keys():
        name, extras, constraint, _ = parse_dependency(dep)
        if name:
            pkg_name = name

            # 收集所有 extras
            if extras:
                extras_list = extras[1:-1].split(",")  # 移除 [] 并分割
                all_extras.update(extras_list)

            # 选择最严格的约束
            if is_stricter(constraint, best_constraint):
                best_constraint = constraint

    # 构建最终版本
    if pkg_name:
        result = pkg_name
        if all_extras:
            result += "[" + ",".join(sorted(all_extras)) + "]"
        result += best_constraint
        return result

    return list(versions.keys())[0]


def is_stricter(ver1: str, ver2: str) -> bool:
    """判断 ver1 是否比 ver2 更严格

    规则：
    1. 有上限比没上限严格
    2. 都有或都没有上限，比较下限（字符串比较，不完美但够用）
    """
    if not ver1:
        return False
    if not ver2:
        return True

    has_upper1 = "<" in ver1
    has_upper2 = "<" in ver2

    if has_upper1 and not has_upper2:
        return True
    if not has_upper1 and has_upper2:
        return False

    # 都有或都没有上限，比较下限
    return ver1 >= ver2


def analyze_conflicts() -> dict:
    """分析所有包的依赖冲突

    Returns:
        {包名: {依赖字符串: [使用该版本的包列表]}}
    """
    conflicts = defaultdict(lambda: defaultdict(list))

    for pkg_dir in PACKAGES_DIR.glob("sage-*"):
        pyproject_file = pkg_dir / "pyproject.toml"
        if not pyproject_file.exists():
            continue

        content = pyproject_file.read_text()
        in_deps = False

        for line in content.splitlines():
            line_stripped = line.strip()
            if "dependencies" in line_stripped and "=" in line_stripped:
                in_deps = True
                continue
            if in_deps:
                if line_stripped == "]":
                    break
                match = re.search(r'"([^"]+)"', line_stripped)
                if match:
                    dep = match.group(1)
                    pkg_name, extras, constraint, _ = parse_dependency(dep)
                    if pkg_name:
                        conflicts[pkg_name][dep].append(pkg_dir.name)

    # 只保留有冲突的包（忽略 extras 差异，只看版本约束）
    actual_conflicts = {}
    for pkg_name, versions in conflicts.items():
        # 提取所有唯一的版本约束
        unique_constraints = set()
        for dep in versions.keys():
            _, _, constraint, _ = parse_dependency(dep)
            unique_constraints.add(constraint)

        # 只有版本约束不同才算冲突
        if len(unique_constraints) > 1:
            actual_conflicts[pkg_name] = dict(versions)

    return actual_conflicts


def apply_unification(dry_run: bool = True) -> None:
    """应用依赖统一

    Args:
        dry_run: True 只显示变更，False 实际修改文件
    """
    conflicts = analyze_conflicts()

    if not conflicts:
        print("✅ 没有发现依赖冲突")
        return

    print(f"📊 发现 {len(conflicts)} 个依赖包有版本冲突\n")

    # 为每个冲突选择统一版本
    unified = {}
    for pkg_name, versions in sorted(conflicts.items()):
        unified_version = merge_versions(versions)
        unified[pkg_name] = unified_version

        print(f"📦 {pkg_name}: 选择 {unified_version}")
        for old_ver, packages in versions.items():
            if old_ver != unified_version:
                print(f"   替换 {old_ver} (用于 {', '.join(packages)})")
        print()

    if dry_run:
        print("ℹ️  这是 dry-run 模式，没有实际修改文件")
        print("   运行 python3 tools/install/helpers/unify_dependencies.py --apply 应用修改")
        return

    # 实际修改文件
    print("🔧 开始修改 pyproject.toml 文件...\n")
    modified_count = 0

    for pkg_dir in PACKAGES_DIR.glob("sage-*"):
        pyproject_file = pkg_dir / "pyproject.toml"
        if not pyproject_file.exists():
            continue

        content = pyproject_file.read_text()
        original_content = content

        # 替换依赖
        for pkg_name, unified_version in unified.items():
            if pkg_name in conflicts:
                for old_version in conflicts[pkg_name].keys():
                    if old_version != unified_version:
                        # 精确匹配 "old_version" 避免误替换
                        pattern = f'"{re.escape(old_version)}"'
                        replacement = f'"{unified_version}"'
                        content = re.sub(pattern, replacement, content)

        if content != original_content:
            pyproject_file.write_text(content)
            print(f"✅ 修改 {pkg_dir.name}/pyproject.toml")
            modified_count += 1

    print(f"\n🎉 完成! 修改了 {modified_count} 个文件")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="统一 SAGE 依赖版本")
    parser.add_argument("--apply", action="store_true", help="实际修改文件（默认是 dry-run）")
    parser.add_argument("--dry-run", action="store_true", default=True, help="只显示变更（默认）")
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查是否有冲突（用于 pre-commit，有冲突时退出码非零）",
    )

    args = parser.parse_args()

    # --check 模式：用于 pre-commit hook
    if args.check:
        conflicts = analyze_conflicts()
        if conflicts:
            print("❌ 发现依赖版本冲突！请运行以下命令修复:", file=sys.stderr)
            print(
                "   python3 tools/install/helpers/unify_dependencies.py --apply",
                file=sys.stderr,
            )
            print(f"\n冲突详情（{len(conflicts)} 个）:", file=sys.stderr)
            for pkg_name, versions in sorted(conflicts.items()):
                print(f"  • {pkg_name}: {len(versions)} 个不同版本", file=sys.stderr)
                for ver in sorted(versions.keys()):
                    print(f"    - {ver}", file=sys.stderr)
            sys.exit(1)
        else:
            print("✅ 依赖版本检查通过，无冲突", file=sys.stderr)
            sys.exit(0)

    # --apply 覆盖 --dry-run
    dry_run = not args.apply

    apply_unification(dry_run=dry_run)


if __name__ == "__main__":
    main()
