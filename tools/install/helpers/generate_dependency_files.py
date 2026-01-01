#!/usr/bin/env python3
"""
生成各安装模式的去重依赖文件
一次性预处理，避免每次安装时重复去重
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


def extract_deps(package_dirs: list[str]) -> list[str]:
    """提取并去重依赖"""
    dep_versions = defaultdict(list)

    for pkg_dir in package_dirs:
        pyproject = Path(pkg_dir) / "pyproject.toml"
        if not pyproject.exists():
            continue

        content = pyproject.read_text()
        in_deps = False

        for line in content.splitlines():
            line = line.strip()
            if "dependencies" in line and "=" in line:
                in_deps = True
                continue
            if in_deps:
                if line == "]":
                    in_deps = False
                    continue
                match = re.search(r'"([^"]+)"', line)
                if match:
                    dep = match.group(1)
                    if not dep.startswith("isage-"):
                        # 提取包名
                        pkg_match = re.match(r"^([a-zA-Z0-9_-]+[a-zA-Z0-9_\[\]-]*)", dep)
                        if pkg_match:
                            pkg_name = pkg_match.group(1)
                            dep_versions[pkg_name].append(dep)

    # 去重并选择最严格的版本约束
    external_deps = []
    dedup_count = 0

    for pkg_name, versions in sorted(dep_versions.items()):
        if len(versions) == 1:
            external_deps.append(versions[0])
        else:
            # 选择最新的（最严格的）版本约束
            best_dep = max(versions, key=lambda v: (">=" in v, v))
            external_deps.append(best_dep)
            dedup_count += len(versions) - 1

    print(f"  提取了 {len(external_deps)} 个依赖（去重 {dedup_count} 个）", file=sys.stderr)
    return external_deps


def main():
    # 定义各模式的包列表
    modes = {
        "core": [
            "packages/sage-common",
            "packages/sage-platform",
            "packages/sage-kernel",
            "packages/sage-libs",
            "packages/sage-middleware",
        ],
        "standard": None,  # 将自动包含 core + cli + benchmark
        "full": None,  # 将自动包含 standard + apps + studio
        "dev": None,  # 将自动包含 full + tools + gateway
    }

    # 构建完整包列表
    modes["standard"] = modes["core"] + [
        "packages/sage-cli",
        "packages/sage-benchmark",
        "packages/sage-llm-gateway",
        "packages/sage-llm-core",
    ]

    modes["full"] = modes["standard"] + ["packages/sage-apps"]

    modes["dev"] = modes["full"] + ["packages/sage-tools", "packages/sage-studio"]

    # 生成依赖文件
    output_dir = Path(".sage")
    output_dir.mkdir(exist_ok=True)

    print("🔧 生成去重依赖文件...")

    for mode, pkg_dirs in modes.items():
        print(f"\n📦 {mode.upper()} 模式:", file=sys.stderr)
        deps = extract_deps(pkg_dirs)

        output_file = output_dir / f"external-deps-{mode}.txt"
        with open(output_file, "w") as f:
            for dep in deps:
                f.write(f"{dep}\n")

        print(f"  ✓ 已保存到: {output_file}", file=sys.stderr)

    print("\n✅ 完成！依赖文件已生成到 .sage/ 目录", file=sys.stderr)
    print("💡 提示：修改 pyproject.toml 后需要重新运行此脚本", file=sys.stderr)


if __name__ == "__main__":
    main()
