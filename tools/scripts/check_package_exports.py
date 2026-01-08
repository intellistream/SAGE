#!/usr/bin/env python3
"""
check_package_exports.py

检查 SAGE 各包的 __init__.py 导出是否正确。

Usage:
    python tools/scripts/check_package_exports.py
"""

import sys
from pathlib import Path


def check_package_init(pkg_name: str, pkg_path: Path) -> dict[str, any]:
    """检查单个包的 __init__.py 文件。"""
    init_file = pkg_path / "src" / "sage" / pkg_name / "__init__.py"

    result = {
        "name": pkg_name,
        "path": str(pkg_path),
        "init_exists": init_file.exists(),
        "has_version": False,
        "has_all": False,
        "has_layer": False,
        "exports": [],
        "issues": [],
    }

    if not result["init_exists"]:
        result["issues"].append("❌ __init__.py 文件不存在")
        return result

    # 读取文件内容
    try:
        content = init_file.read_text(encoding="utf-8")
    except Exception as e:
        result["issues"].append(f"❌ 无法读取文件: {e}")
        return result

    # 检查 __version__
    if "__version__" in content:
        result["has_version"] = True
        # 提取版本导入方式
        if "from ._version import __version__" in content:
            result["version_source"] = "_version.py"
        elif "from sage." in content and "__version__" in content:
            result["version_source"] = "re-export"
        else:
            result["version_source"] = "hardcoded"
    else:
        result["issues"].append("⚠️  缺少 __version__ 声明")

    # 检查 __all__
    if "__all__" in content:
        result["has_all"] = True
        # 尝试提取 __all__ 列表
        import re

        match = re.search(r"__all__\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            exports_str = match.group(1)
            # 简单解析（去除引号和逗号）
            exports = [e.strip().strip("\"'") for e in exports_str.split(",") if e.strip()]
            result["exports"] = exports
    else:
        result["issues"].append("⚠️  缺少 __all__ 声明")

    # 检查 __layer__
    if "__layer__" in content:
        result["has_layer"] = True
        match = re.search(r'__layer__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            result["layer"] = match.group(1)
    else:
        result["issues"].append("ℹ️  缺少 __layer__ 声明（非必需）")

    # 检查是否有导入语句
    import_count = content.count("from ") + content.count("import ")
    result["import_count"] = import_count

    if import_count == 0:
        result["issues"].append("⚠️  没有任何导入语句")

    # 检查是否有文档字符串
    if '"""' in content or "'''" in content:
        result["has_docstring"] = True
    else:
        result["issues"].append("⚠️  缺少模块文档字符串")

    return result


def print_package_report(results: list[dict[str, any]]):
    """打印检查报告。"""
    print("=" * 80)
    print("📊 SAGE Packages Export Check Report")
    print("=" * 80)
    print()

    # 统计
    total = len(results)
    with_issues = sum(1 for r in results if r["issues"])

    print(f"📦 总计: {total} 个包")
    print(f"✅ 正常: {total - with_issues} 个")
    print(f"⚠️  有问题: {with_issues} 个")
    print()

    # 详细报告
    for result in results:
        print("━" * 80)
        print(f"📦 {result['name']}")
        print("━" * 80)

        if not result["init_exists"]:
            print("  ❌ __init__.py 不存在")
            print()
            continue

        # 基本信息
        print(f"  路径: {result['path']}")
        if result.get("layer"):
            print(f"  层级: {result['layer']}")

        # 版本信息
        if result["has_version"]:
            source = result.get("version_source", "unknown")
            print(f"  ✅ 版本: {source}")
        else:
            print("  ❌ 版本: 未声明")

        # 导出信息
        if result["has_all"]:
            exports = result.get("exports", [])
            if exports:
                print(f"  ✅ __all__: {len(exports)} 项")
                # 显示前5项
                for exp in exports[:5]:
                    print(f"     - {exp}")
                if len(exports) > 5:
                    print(f"     ... 还有 {len(exports) - 5} 项")
            else:
                print("  ⚠️  __all__: 已声明但为空")
        else:
            print("  ❌ __all__: 未声明")

        # 导入统计
        import_count = result.get("import_count", 0)
        print(f"  📥 导入语句: {import_count} 个")

        # 问题列表
        if result["issues"]:
            print()
            print("  ⚠️  发现问题:")
            for issue in result["issues"]:
                print(f"     {issue}")

        print()

    # 建议
    print("━" * 80)
    print("💡 建议")
    print("━" * 80)
    print()

    issues_found = False
    for result in results:
        if not result["has_version"]:
            issues_found = True
            print(f"  • {result['name']}: 添加 __version__ 声明")
        if not result["has_all"]:
            issues_found = True
            print(f"  • {result['name']}: 添加 __all__ 列表")

    if not issues_found:
        print("  ✅ 所有包的导出配置都正常！")

    print()


def main():
    root_dir = Path.cwd()
    packages_dir = root_dir / "packages"

    # 核心包列表（按层级排序）
    packages = [
        # L1
        ("common", "sage-common"),
        ("llm", "sage-llm-core"),
        # L2
        ("platform", "sage-platform"),
        # L3
        ("kernel", "sage-kernel"),
        ("libs", "sage-libs"),
        # L4
        ("middleware", "sage-middleware"),
        # L5
        ("apps", "sage-apps"),
        # L6
        ("cli", "sage-cli"),
        ("tools", "sage-tools"),
    ]

    # 检查 sage-llm-gateway（独立命名空间）
    gateway_pkg = packages_dir / "sage-llm-gateway"
    gateway_init = gateway_pkg / "src" / "sage" / "llm" / "gateway" / "__init__.py"

    results = []

    # 检查核心包
    for pkg_name, pkg_dirname in packages:
        pkg_path = packages_dir / pkg_dirname
        if pkg_path.exists():
            result = check_package_init(pkg_name, pkg_path)
            results.append(result)
        else:
            print(f"⚠️  包目录不存在: {pkg_path}")

    # 特别检查 gateway
    if gateway_init.exists():
        gateway_result = {
            "name": "llm.gateway",
            "path": str(gateway_pkg),
            "init_exists": True,
            "has_version": False,
            "has_all": False,
            "has_layer": False,
            "exports": [],
            "issues": [],
        }

        content = gateway_init.read_text(encoding="utf-8")
        if "__version__" in content:
            gateway_result["has_version"] = True
        else:
            gateway_result["issues"].append("⚠️  缺少 __version__")

        if "__all__" in content:
            gateway_result["has_all"] = True
        else:
            gateway_result["issues"].append("⚠️  缺少 __all__")

        results.append(gateway_result)

    # 打印报告
    print_package_report(results)

    # 返回值：有问题的包数量
    return sum(1 for r in results if r["issues"])


if __name__ == "__main__":
    sys.exit(main())
