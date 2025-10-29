#!/usr/bin/env python3
"""
同步 pytest 配置到所有子包

这个脚本确保所有子包的 pytest 配置保持一致，同时允许每个包自定义特定的 markers。

使用方法：
    python tools/sync_pytest_config.py [--check]

    --check: 仅检查配置是否一致，不进行修改
"""

import argparse
import sys
from pathlib import Path

try:
    import tomli
    import tomli_w
except ImportError:
    print("❌ 需要安装 tomli 和 tomli_w:")
    print("   pip install tomli tomli-w")
    sys.exit(1)


# 标准 pytest 配置模板（所有包共享的基础配置）
STANDARD_PYTEST_CONFIG = {
    "testpaths": ["tests", "src"],
    "python_files": ["test_*.py", "*_test.py"],
    "python_classes": ["Test*"],
    "python_functions": ["test_*"],
    "addopts": [
        "--benchmark-storage=../../.sage/benchmarks",
        "-o",
        "cache_dir=../../.sage/cache/pytest",
        "--strict-markers",
        "--strict-config",
        "--verbose",
        "-ra",
    ],
}

# 包特定的 filterwarnings（可选）
PACKAGE_FILTERWARNINGS = {
    "sage-kernel": [
        "ignore::DeprecationWarning:ray._private.client_mode_hook",
        "ignore:.*local mode is an experimental feature.*:DeprecationWarning",
        "ignore::DeprecationWarning:pkg_resources",
        "ignore:.*SWIG.*:DeprecationWarning",
        "ignore:.*SwigPyPacked.*:DeprecationWarning",
        "ignore:.*SwigPyObject.*:DeprecationWarning",
        "ignore:.*swigvarlink.*:DeprecationWarning",
        "ignore:.*pkg_resources is deprecated.*:UserWarning",
        "ignore::pytest.PytestReturnNotNoneWarning",
    ],
    "sage-tools": [
        "ignore::DeprecationWarning:pkg_resources",
        "ignore:.*pkg_resources is deprecated.*:UserWarning",
        "ignore:.*SWIG.*:DeprecationWarning",
        "ignore:.*SwigPyPacked.*:DeprecationWarning",
        "ignore:.*SwigPyObject.*:DeprecationWarning",
        "ignore:.*swigvarlink.*:DeprecationWarning",
    ],
    "sage-studio": [
        "ignore::DeprecationWarning:pkg_resources",
        "ignore:.*pkg_resources is deprecated.*:UserWarning",
    ],
}

# 各包特定的 markers（可以自定义）
PACKAGE_MARKERS = {
    "sage": None,  # 元包不需要测试
    "sage-common": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "core: marks tests as core functionality tests",
        "smoke: marks tests as smoke tests (quick validation)",
    ],
    "sage-platform": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "network: marks tests as network tests",
        "queue: marks tests as queue tests",
        "storage: marks tests as storage tests",
    ],
    "sage-kernel": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "network: marks tests as network tests",
        "system: marks tests as system tests",
        "core: marks tests as core functionality tests",
        "smoke: marks tests as smoke tests (quick validation)",
        "cli: marks tests as CLI tests",
        "ray: marks tests requiring Ray framework (may be slow)",
        "distributed: marks tests requiring distributed setup",
    ],
    "sage-libs": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "network: marks tests as network tests",
        "system: marks tests as system tests",
        "core: marks tests as core functionality tests",
        "smoke: marks tests as smoke tests (quick validation)",
        "cli: marks tests as CLI tests",
        "external: marks tests requiring external services/APIs",
    ],
    "sage-middleware": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "network: marks tests as network tests",
        "system: marks tests as system tests",
        "core: marks tests as core functionality tests",
        "smoke: marks tests as smoke tests (quick validation)",
        "cli: marks tests as CLI tests",
    ],
    "sage-apps": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "video: marks tests as video intelligence tests",
        "medical: marks tests as medical diagnosis tests",
    ],
    "sage-benchmark": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "benchmark: marks tests as benchmark tests",
        "rag: marks tests as RAG benchmark tests",
    ],
    "sage-cli": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "cli: marks tests as CLI tests",
    ],
    "sage-tools": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "network: marks tests as network tests",
        "system: marks tests as system tests",
        "core: marks tests as core functionality tests",
        "smoke: marks tests as smoke tests (quick validation)",
        "cli: marks tests as CLI tests",
    ],
    "sage-studio": [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
        "unit: marks tests as unit tests",
        "network: marks tests as network tests",
        "system: marks tests as system tests",
        "core: marks tests as core functionality tests",
        "smoke: marks tests as smoke tests (quick validation)",
        "frontend: marks tests as frontend tests",
    ],
}


def get_pytest_config(package_name: str) -> dict:
    """获取指定包的完整 pytest 配置"""
    # 元包不需要 pytest 配置
    if package_name == "sage":
        return None

    config = STANDARD_PYTEST_CONFIG.copy()
    config["markers"] = PACKAGE_MARKERS.get(package_name, [])

    # 添加包特定的 filterwarnings（如果有）
    filterwarnings = PACKAGE_FILTERWARNINGS.get(package_name)
    if filterwarnings:
        config["filterwarnings"] = filterwarnings

    return config


def sync_package_pytest_config(package_path: Path, check_only: bool = False) -> bool:
    """
    同步单个包的 pytest 配置

    Returns:
        bool: True 如果配置一致或已更新，False 如果存在差异（仅在 check_only 模式）
    """
    package_name = package_path.name
    pyproject_path = package_path / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"⚠️  {package_name}: pyproject.toml 不存在")
        return True

    # 元包不需要 pytest 配置
    if package_name == "sage":
        print(f"⏭️  {package_name}: 元包跳过 pytest 配置")
        return True

    # 验证目录结构
    tests_dir = package_path / "tests"
    src_dir = package_path / "src"
    if not tests_dir.exists():
        print(f"⚠️  {package_name}: tests/ 目录不存在，请创建")
        if not check_only:
            tests_dir.mkdir(exist_ok=True)
            (tests_dir / "__init__.py").touch()
            print("   ✅ 已创建 tests/ 目录")
    if not src_dir.exists():
        print(f"⚠️  {package_name}: src/ 目录不存在，请检查包结构")
        return True

    # 读取现有配置
    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)

    # 获取标准配置
    expected_config = get_pytest_config(package_name)
    current_config = data.get("tool", {}).get("pytest", {}).get("ini_options", {})

    # 比较配置
    if current_config == expected_config:
        print(f"✅ {package_name}: pytest 配置已是最新")
        return True

    if check_only:
        print(f"❌ {package_name}: pytest 配置需要更新")
        print(f"   期望: {expected_config}")
        print(f"   当前: {current_config}")
        return False

    # 更新配置
    if "tool" not in data:
        data["tool"] = {}
    if "pytest" not in data["tool"]:
        data["tool"]["pytest"] = {}

    data["tool"]["pytest"]["ini_options"] = expected_config

    # 写回文件
    with open(pyproject_path, "wb") as f:
        tomli_w.dump(data, f)

    print(f"✅ {package_name}: pytest 配置已更新")
    return True


def main():
    parser = argparse.ArgumentParser(description="同步 pytest 配置到所有子包")
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅检查配置是否一致，不进行修改",
    )
    args = parser.parse_args()

    # 获取项目根目录
    root = Path(__file__).parent.parent
    packages_dir = root / "packages"

    if not packages_dir.exists():
        print(f"❌ 找不到 packages 目录: {packages_dir}")
        sys.exit(1)

    print(f"🔍 扫描 {packages_dir}")
    print(f"{'检查模式' if args.check else '同步模式'}")
    print()

    all_good = True
    package_dirs = sorted([p for p in packages_dir.iterdir() if p.is_dir()])

    for package_path in package_dirs:
        if package_path.name.startswith("."):
            continue

        success = sync_package_pytest_config(package_path, check_only=args.check)
        all_good = all_good and success

    print()
    if args.check:
        if all_good:
            print("✅ 所有包的 pytest 配置都是最新的")
            sys.exit(0)
        else:
            print("❌ 部分包的 pytest 配置需要更新")
            print("   运行 'python tools/sync_pytest_config.py' 进行同步")
            sys.exit(1)
    else:
        print("✅ pytest 配置同步完成")
        sys.exit(0)


if __name__ == "__main__":
    main()
