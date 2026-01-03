#!/usr/bin/env python3
"""
T2.8 验证脚本

验证 Hierarchical Services 的文档和示例完整性。
"""

import sys
from pathlib import Path

# 项目根目录（从脚本位置向上查找）
SCRIPT_PATH = Path(__file__).resolve()
# 从 packages/sage-middleware/tests/verification/ 向上4层到项目根
ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
HIERARCHICAL_DIR = (
    ROOT
    / "packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/services/hierarchical"
)
EXAMPLES_DIR = ROOT / "examples/services"


def check_file_exists(path: Path, description: str) -> bool:
    """检查文件是否存在"""
    if path.exists():
        print(f"✅ {description}: {path.name}")
        return True
    else:
        print(f"❌ {description} 缺失: {path}")
        return False


def check_documentation():
    """检查文档完整性"""
    print("\n" + "=" * 60)
    print("1. 检查文档文件")
    print("=" * 60)

    checks = [
        (HIERARCHICAL_DIR / "README.md", "完整文档"),
        (HIERARCHICAL_DIR / "QUICKSTART.md", "快速开始"),
        (HIERARCHICAL_DIR / "__init__.py", "模块初始化"),
        (
            HIERARCHICAL_DIR / "linknote_graph_service.py",
            "Linknote 服务实现",
        ),
        (
            HIERARCHICAL_DIR / "property_graph_service.py",
            "PropertyGraph 服务实现",
        ),
    ]

    results = [check_file_exists(path, desc) for path, desc in checks]
    return all(results)


def check_examples():
    """检查示例文件"""
    print("\n" + "=" * 60)
    print("2. 检查示例文件")
    print("=" * 60)

    checks = [
        (EXAMPLES_DIR / "linknote_example.py", "Linknote 完整示例"),
        (EXAMPLES_DIR / "property_graph_example.py", "PropertyGraph 完整示例"),
        (EXAMPLES_DIR / "hybrid_knowledge_base.py", "混合知识库示例"),
    ]

    results = [check_file_exists(path, desc) for path, desc in checks]
    return all(results)


def check_tests():
    """检查测试文件"""
    print("\n" + "=" * 60)
    print("3. 检查测试文件")
    print("=" * 60)

    test_dir = ROOT / "packages/sage-middleware/tests/unit/components/sage_mem/neuromem/services"
    integration_dir = ROOT / "packages/sage-middleware/tests/integration/services"

    checks = [
        (test_dir / "test_linknote_graph.py", "Linknote 单元测试"),
        (test_dir / "test_property_graph.py", "PropertyGraph 单元测试"),
        (
            integration_dir / "test_hierarchical_services_integration.py",
            "集成测试",
        ),
    ]

    results = [check_file_exists(path, desc) for path, desc in checks]
    return all(results)


def run_examples():
    """运行示例验证"""
    print("\n" + "=" * 60)
    print("4. 运行示例验证")
    print("=" * 60)

    import subprocess

    examples = [
        ("Linknote 示例", EXAMPLES_DIR / "linknote_example.py"),
        ("PropertyGraph 示例", EXAMPLES_DIR / "property_graph_example.py"),
        ("混合知识库示例", EXAMPLES_DIR / "hybrid_knowledge_base.py"),
    ]

    results = []
    for name, example_path in examples:
        try:
            result = subprocess.run(
                [sys.executable, str(example_path)],
                cwd=ROOT,
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                print(f"✅ {name} 运行成功")
                results.append(True)
            else:
                print(f"❌ {name} 运行失败 (退出码: {result.returncode})")
                print(f"   错误: {result.stderr.decode()[:200]}")
                results.append(False)
        except Exception as e:
            print(f"❌ {name} 运行异常: {e}")
            results.append(False)

    return all(results)


def check_content():
    """检查文档内容完整性"""
    print("\n" + "=" * 60)
    print("5. 检查文档内容")
    print("=" * 60)

    # 检查 README.md
    readme = HIERARCHICAL_DIR / "README.md"
    if readme.exists():
        content = readme.read_text()
        required_sections = [
            "# Hierarchical Services",
            "## 概述",
            "## 快速开始",
            "## 核心功能",
            "## 高级用法",
            "## API 参考",
        ]

        missing = [s for s in required_sections if s not in content]
        if not missing:
            print("✅ README.md 包含所有必需章节")
        else:
            print(f"❌ README.md 缺少章节: {missing}")
            return False

    # 检查 QUICKSTART.md
    quickstart = HIERARCHICAL_DIR / "QUICKSTART.md"
    if quickstart.exists():
        content = quickstart.read_text()
        required_sections = [
            "# Hierarchical Services 快速开始",
            "## 场景 1: 笔记链接",
            "## 场景 2: 知识图谱",
            "## 核心 API 速查",
        ]

        missing = [s for s in required_sections if s not in content]
        if not missing:
            print("✅ QUICKSTART.md 包含所有必需章节")
        else:
            print(f"❌ QUICKSTART.md 缺少章节: {missing}")
            return False

    return True


def print_statistics():
    """打印统计信息"""
    print("\n" + "=" * 60)
    print("6. 统计信息")
    print("=" * 60)

    # 文档行数
    readme_lines = (
        len((HIERARCHICAL_DIR / "README.md").read_text().split("\n"))
        if (HIERARCHICAL_DIR / "README.md").exists()
        else 0
    )
    quickstart_lines = (
        len((HIERARCHICAL_DIR / "QUICKSTART.md").read_text().split("\n"))
        if (HIERARCHICAL_DIR / "QUICKSTART.md").exists()
        else 0
    )

    print(f"README.md: {readme_lines} 行")
    print(f"QUICKSTART.md: {quickstart_lines} 行")
    print(f"文档总行数: {readme_lines + quickstart_lines} 行")

    # 示例代码行数
    example_files = list(EXAMPLES_DIR.glob("*.py"))
    total_example_lines = sum(len(f.read_text().split("\n")) for f in example_files)
    print(f"\n示例代码总行数: {total_example_lines} 行")
    for f in example_files:
        lines = len(f.read_text().split("\n"))
        print(f"  - {f.name}: {lines} 行")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("T2.8 完善文档和示例 - 验证脚本")
    print("=" * 60)

    results = []

    # 执行所有检查
    results.append(check_documentation())
    results.append(check_examples())
    results.append(check_tests())
    results.append(check_content())
    results.append(run_examples())

    # 统计信息
    print_statistics()

    # 总结
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    if all(results):
        print("✅ 所有检查通过！T2.8 完成。")
        return 0
    else:
        print("❌ 部分检查失败，请修复问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
