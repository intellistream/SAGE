"""
Tests for Architecture Compliance Checker

测试架构检查器的各种场景
"""

import shutil
import sys
import tempfile
from pathlib import Path

# 添加工具目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from architecture_checker import ArchitectureChecker


def create_test_structure():
    """创建测试用的临时项目结构"""
    temp_dir = Path(tempfile.mkdtemp())

    # 创建包结构
    packages = [
        "sage-common",
        "sage-platform",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
    ]

    for pkg in packages:
        pkg_path = temp_dir / "packages" / pkg / "src" / "sage" / pkg.replace("sage-", "")
        pkg_path.mkdir(parents=True, exist_ok=True)

        # 创建 __init__.py
        init_file = pkg_path / "__init__.py"
        layer = {
            "sage-common": "L1",
            "sage-platform": "L2",
            "sage-kernel": "L3",
            "sage-libs": "L3",
            "sage-middleware": "L4",
        }
        init_file.write_text(f'"""Package {pkg}"""\n__layer__ = "{layer[pkg]}"\n')

    return temp_dir


def test_legal_dependency():
    """测试合法的依赖"""
    print("🧪 测试合法依赖...")

    temp_dir = create_test_structure()

    try:
        # 创建合法的导入
        test_file = temp_dir / "packages/sage-kernel/src/sage/kernel/test.py"
        test_file.write_text(
            """
from sage.common import utils
from sage.platform import service

def test():
    pass
"""
        )

        checker = ArchitectureChecker(temp_dir)
        result = checker.run_checks([test_file])

        # 应该没有违规
        illegal_deps = [v for v in result.violations if v.type == "ILLEGAL_DEPENDENCY"]
        assert len(illegal_deps) == 0, f"发现非法依赖: {illegal_deps}"

        print("  ✅ 合法依赖测试通过")

    finally:
        shutil.rmtree(temp_dir)


def test_illegal_upward_dependency():
    """测试非法的向上依赖"""
    print("🧪 测试非法向上依赖...")

    temp_dir = create_test_structure()

    try:
        # 创建非法的向上依赖
        test_file = temp_dir / "packages/sage-common/src/sage/common/test.py"
        test_file.write_text(
            """
from sage.kernel import api  # L1 -> L3 非法

def test():
    pass
"""
        )

        checker = ArchitectureChecker(temp_dir)
        result = checker.run_checks([test_file])

        # 应该发现违规
        illegal_deps = [v for v in result.violations if v.type == "ILLEGAL_DEPENDENCY"]
        assert len(illegal_deps) > 0, "应该检测到非法依赖"

        violation = illegal_deps[0]
        assert "sage-common" in violation.message
        assert "sage-kernel" in violation.message

        print("  ✅ 非法向上依赖检测通过")

    finally:
        shutil.rmtree(temp_dir)


def test_illegal_same_layer_dependency():
    """测试非法的同层依赖"""
    print("🧪 测试非法同层依赖...")

    temp_dir = create_test_structure()

    try:
        # sage-libs 可以依赖 sage-kernel（明确允许）
        # 但 sage-kernel 不能依赖 sage-libs
        test_file = temp_dir / "packages/sage-kernel/src/sage/kernel/test.py"
        test_file.write_text(
            """
from sage.libs import agents  # L3 -> L3 但未授权

def test():
    pass
"""
        )

        checker = ArchitectureChecker(temp_dir)
        result = checker.run_checks([test_file])

        # 应该发现违规
        illegal_deps = [v for v in result.violations if v.type == "ILLEGAL_DEPENDENCY"]
        assert len(illegal_deps) > 0, "应该检测到非法同层依赖"

        print("  ✅ 非法同层依赖检测通过")

    finally:
        shutil.rmtree(temp_dir)


def test_internal_import_warning():
    """测试内部导入警告"""
    print("🧪 测试内部导入警告...")

    temp_dir = create_test_structure()

    try:
        # 创建直接导入内部模块的代码
        test_file = temp_dir / "packages/sage-middleware/src/sage/middleware/test.py"
        test_file.write_text(
            """
from sage.kernel.runtime.dispatcher import Dispatcher  # 内部模块

def test():
    pass
"""
        )

        checker = ArchitectureChecker(temp_dir)
        result = checker.run_checks([test_file])

        # 应该产生警告
        internal_imports = [w for w in result.warnings if w.type == "INTERNAL_IMPORT"]
        assert len(internal_imports) > 0, "应该检测到内部导入"

        print("  ✅ 内部导入警告测试通过")

    finally:
        shutil.rmtree(temp_dir)


def test_missing_layer_marker():
    """测试缺少 Layer 标记"""
    print("🧪 测试缺少 Layer 标记...")

    temp_dir = create_test_structure()

    try:
        # 删除一个包的 Layer 标记
        init_file = temp_dir / "packages/sage-kernel/src/sage/kernel/__init__.py"
        init_file.write_text('"""Package sage-kernel"""\n')  # 没有 __layer__

        checker = ArchitectureChecker(temp_dir)
        result = checker.run_checks()

        # 应该产生警告
        missing_markers = [w for w in result.warnings if w.type == "MISSING_LAYER_MARKER"]
        assert len(missing_markers) > 0, "应该检测到缺少 Layer 标记"

        print("  ✅ Layer 标记检测通过")

    finally:
        shutil.rmtree(temp_dir)


def test_extract_package_name():
    """测试从路径提取包名"""
    print("🧪 测试包名提取...")

    temp_dir = create_test_structure()
    checker = ArchitectureChecker(temp_dir)

    test_cases = [
        (
            temp_dir / "packages/sage-kernel/src/sage/kernel/api.py",
            "sage-kernel",
        ),
        (
            temp_dir / "packages/sage-common/src/sage/common/utils.py",
            "sage-common",
        ),
        (temp_dir / "other/path/file.py", None),
    ]

    for path, expected in test_cases:
        result = checker.extract_package_name(path)
        assert result == expected, f"期望 {expected}，得到 {result}"

    print("  ✅ 包名提取测试通过")

    shutil.rmtree(temp_dir)


def test_get_imported_package():
    """测试从导入语句提取包名"""
    print("🧪 测试导入包名提取...")

    checker = ArchitectureChecker(Path("."))

    test_cases = [
        ("sage.common.utils", "sage-common"),
        ("sage.kernel.api", "sage-kernel"),
        ("sage.libs.agents", "sage-libs"),
        ("os.path", None),
        ("numpy", None),
    ]

    for module, expected in test_cases:
        result = checker.get_imported_package(module)
        assert result == expected, f"模块 {module}: 期望 {expected}，得到 {result}"

    print("  ✅ 导入包名提取测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("🧪 开始测试架构检查器")
    print("=" * 70)
    print()

    tests = [
        test_extract_package_name,
        test_get_imported_package,
        test_legal_dependency,
        test_illegal_upward_dependency,
        test_illegal_same_layer_dependency,
        test_internal_import_warning,
        test_missing_layer_marker,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ 测试错误: {e}")
            failed += 1
        print()

    print("=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
