#!/usr/bin/env python3
"""
生成各安装模式的去重依赖文件
一次性预处理，避免每次安装时重复去重
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


def extract_optional_deps(pyproject_path: Path, extra_name: str) -> list[str]:
    """从 pyproject.toml 的 [project.optional-dependencies] 中提取指定 extra 的依赖"""
    if not pyproject_path.exists():
        return []

    content = pyproject_path.read_text(encoding="utf-8")

    # 匹配 extra_name = [...] 块
    pattern = re.compile(rf"\b{re.escape(extra_name)}\s*=\s*\[(.*?)\]", re.DOTALL)
    match = pattern.search(content)

    if not match:
        return []

    deps_block = match.group(1)
    deps = []

    for raw_line in deps_block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # 移除行内注释
        if "#" in line:
            line = line.split("#")[0].strip()

        # 移除尾部逗号
        if line.endswith(","):
            line = line[:-1].strip()

        # 移除引号
        if line.startswith(('"', "'")) and line.endswith(('"', "'")):
            line = line[1:-1]

        if line:
            deps.append(line)

    return deps


def extract_deps(package_dirs: list[str], include_vllm: bool = False) -> list[str]:
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

    # 如果需要，从 sage-common 提取 vLLM 可选依赖
    if include_vllm:
        sage_common_pyproject = Path("packages/sage-common/pyproject.toml")
        vllm_deps = extract_optional_deps(sage_common_pyproject, "vllm")
        if vllm_deps:
            print(f"  提取了 {len(vllm_deps)} 个 vLLM 可选依赖", file=sys.stderr)
            for dep in vllm_deps:
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

        # dev/full 模式默认包含 vLLM 可选依赖
        include_vllm = mode in ("dev", "full")
        deps = extract_deps(pkg_dirs, include_vllm=include_vllm)

        output_file = output_dir / f"external-deps-{mode}.txt"
        with open(output_file, "w") as f:
            for dep in deps:
                f.write(f"{dep}\n")

        print(f"  ✓ 已保存到: {output_file}", file=sys.stderr)

    print("\n✅ 完成！依赖文件已生成到 .sage/ 目录", file=sys.stderr)
    print("💡 提示：修改 pyproject.toml 后需要重新运行此脚本", file=sys.stderr)
    if "dev" in modes or "full" in modes:
        print(
            "💡 dev/full 模式已自动包含 vLLM 可选依赖，将在外部依赖安装时一次性安装",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
