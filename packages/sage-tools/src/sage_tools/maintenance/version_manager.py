# Converted from version_manager.sh
# SAGE Framework 版本管理脚本
# Version Management Script for SAGE Framework
#
# 用于批量管理所有包的版本号
# For batch version management of all packages

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import toml
from packaging import version
from packaging.version import Version

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 颜色配置 (使用 ANSI 代码)
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_colored(text: str, color: str = NC):
    print(f"{color}{text}{NC}")

def get_package_versions(packages: List[str]) -> List[Tuple[str, str]]:
    """获取包版本"""
    versions = []
    for package in packages:
        package_path = PROJECT_ROOT / "packages" / package
        pyproject_file = package_path / "pyproject.toml"
        if not pyproject_file.exists():
            versions.append((package, "未知"))
            continue
        try:
            data = toml.load(pyproject_file)
            v = data.get('tool', {}).get('poetry', {}).get('version', '未知')
            versions.append((package, v))
        except Exception:
            versions.append((package, "未知"))
    return versions

def increment_package_version(package: str, increment_type: str = "patch") -> bool:
    """递增单个包版本"""
    package_path = PROJECT_ROOT / "packages" / package
    pyproject_file = package_path / "pyproject.toml"
    if not pyproject_file.exists():
        print_colored(f"❌ {package}: 未找到 pyproject.toml", RED)
        return False

    # 备份
    backup_file = pyproject_file.with_suffix('.pyproject.toml.backup')
    pyproject_file.replace(backup_file)

    try:
        data = toml.load(pyproject_file)
        current_v = data.get('tool', {}).get('poetry', {}).get('version', '0.0.0')
        current_version = Version(current_v)
        if increment_type == "major":
            new_version = Version(f"{current_version.major + 1}.0.0")
        elif increment_type == "minor":
            new_version = Version(f"{current_version.major}.{current_version.minor + 1}.0")
        else:
            new_version = Version(f"{current_version.major}.{current_version.minor}.{current_version.micro + 1}")

        data['tool']['poetry']['version'] = str(new_version)
        with open(pyproject_file, 'w') as f:
            toml.dump(data, f)

        print_colored(f"✅ {package}: {current_v} → {new_version}", GREEN)
        return True
    except Exception as e:
        print_colored(f"❌ {package}: 更新失败 {e}", RED)
        # 恢复备份
        if backup_file.exists():
            backup_file.replace(pyproject_file)
        return False

def main():
    parser = argparse.ArgumentParser(description="SAGE Framework 版本管理")
    subparsers = parser.add_subparsers(dest='action', required=True)

    # list 子命令
    list_parser = subparsers.add_parser('list', help='显示所有包的版本信息')

    # increment 子命令
    increment_parser = subparsers.add_parser('increment', aliases=['bump'], help='递增版本号')
    increment_parser.add_argument('--packages', help='指定包名，用逗号分隔 (默认: 所有包)')
    increment_parser.add_argument('--type', choices=['major', 'minor', 'patch'], default='patch', help='版本递增类型')

    args = parser.parse_args()

    print_colored("🔢 SAGE Framework 版本管理", BOLD)
    print_colored("=================================")

    if args.action == 'list':
        packages = [p.name for p in (PROJECT_ROOT / "packages").glob("sage-*") if p.is_dir()]
        versions = get_package_versions(packages)
        print_colored("📋 包版本信息:", BOLD)
        print()
        for package, v in versions:
            print(f"  {package:25} {v}")

    elif args.action == 'increment':
        packages = args.packages.split(',') if args.packages else [p.name for p in (PROJECT_ROOT / "packages").glob("sage-*") if p.is_dir()]
        print_colored(f"🔄 递增版本号 (类型: {args.type}):", BOLD)
        print()

        success_count = 0
        failed_count = 0
        for package in packages:
            if increment_package_version(package, args.type):
                success_count += 1
            else:
                failed_count += 1

        print()
        print_colored("===== 版本递增摘要 =====", BOLD)
        print_colored(f"成功: {success_count}", GREEN)
        print_colored(f"失败: {failed_count}", RED)

        if failed_count == 0:
            print_colored("\n🎉 所有包版本递增成功！", GREEN)
        else:
            print_colored(f"\n💥 有 {failed_count} 个包版本递增失败", RED)
            sys.exit(1)

if __name__ == "__main__":
    main()