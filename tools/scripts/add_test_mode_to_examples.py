#!/usr/bin/env python3
"""
add_test_mode_to_examples.py

为 SAGE examples 添加测试模式支持的辅助脚本。

Usage:
    python tools/scripts/add_test_mode_to_examples.py [--dry-run] [--file <path>]

Examples:
    # 扫描所有 examples
    python tools/scripts/add_test_mode_to_examples.py --dry-run

    # 为特定文件添加测试模式
    python tools/scripts/add_test_mode_to_examples.py --file packages/sage-libs/examples/some_example.py
"""

import argparse
import sys
from pathlib import Path


def has_test_mode_support(file_path: Path) -> bool:
    """检查文件是否已支持测试模式。"""
    content = file_path.read_text(encoding="utf-8")
    return "SAGE_TEST_MODE" in content or "SAGE_EXAMPLES_MODE" in content


def has_main_block(file_path: Path) -> bool:
    """检查文件是否有 if __name__ == "__main__" 块。"""
    content = file_path.read_text(encoding="utf-8")
    return 'if __name__ == "__main__"' in content


def analyze_example(file_path: Path) -> dict:
    """分析 example 文件，返回建议。"""
    result = {
        "path": str(file_path),
        "has_test_mode": has_test_mode_support(file_path),
        "has_main_block": has_main_block(file_path),
        "needs_test_mode": False,
        "difficulty": "unknown",
        "suggestion": "",
    }

    content = file_path.read_text(encoding="utf-8")

    # 如果已有测试模式支持
    if result["has_test_mode"]:
        result["suggestion"] = "✅ Already has test mode support"
        return result

    # 检查是否需要 API keys
    needs_api = any(
        keyword in content
        for keyword in [
            "openai",
            "OpenAI",
            "api_key",
            "API_KEY",
            "llm",
            "LLM",
            "embeddings",
        ]
    )

    # 检查是否有复杂的外部依赖
    complex_deps = any(
        keyword in content
        for keyword in [
            "ray.init",
            "redis",
            "docker",
            "kubernetes",
            "spark",
        ]
    )

    # 判断难度
    if not result["has_main_block"]:
        result["difficulty"] = "hard"
        result["suggestion"] = "⚠️  No main block - needs major refactoring"
    elif complex_deps:
        result["difficulty"] = "hard"
        result["suggestion"] = "⚠️  Complex dependencies - needs careful handling"
    elif needs_api:
        result["difficulty"] = "medium"
        result["suggestion"] = "💡 Needs API key handling in test mode"
        result["needs_test_mode"] = True
    else:
        result["difficulty"] = "easy"
        result["suggestion"] = "✨ Easy - just add test mode check"
        result["needs_test_mode"] = True

    return result


def generate_test_mode_template(file_path: Path) -> str:
    """生成测试模式代码模板。"""
    return '''
# Add this near the top of the file, after imports
def is_test_mode() -> bool:
    """Check if running in test mode."""
    return (
        os.getenv("SAGE_TEST_MODE") == "true"
        or os.getenv("SAGE_EXAMPLES_MODE") == "test"
    )


# Modify your main function or main block:
def main():
    # Check test mode
    if is_test_mode():
        print("🧪 Test mode: Validating configuration and imports...")
        # Add validation logic here:
        # - Load config files
        # - Import required modules
        # - Check dependencies
        print("✅ Test mode: Validation passed")
        return

    # Normal execution
    # ... your existing code ...


if __name__ == "__main__":
    # Add test mode wrapper
    if is_test_mode():
        try:
            main()
            print("\\n✅ Test passed: Example structure validated")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            sys.exit(1)
    else:
        main()
'''


def scan_examples(root_dir: Path) -> list[tuple[Path, dict]]:
    """扫描所有 examples 文件。"""
    examples = []

    for pkg_dir in root_dir.glob("packages/*/examples"):
        if not pkg_dir.is_dir():
            continue

        for py_file in pkg_dir.rglob("*.py"):
            # 跳过 __pycache__ 和测试文件
            if "__pycache__" in str(py_file) or py_file.name.startswith("test_"):
                continue

            analysis = analyze_example(py_file)
            examples.append((py_file, analysis))

    return examples


def print_report(examples: list[tuple[Path, dict]]):
    """打印分析报告。"""
    print("=" * 80)
    print("📊 SAGE Examples Test Mode Support Analysis")
    print("=" * 80)
    print()

    # 统计
    total = len(examples)
    with_test_mode = sum(1 for _, a in examples if a["has_test_mode"])
    needs_test_mode = sum(1 for _, a in examples if a["needs_test_mode"])

    print(f"📁 总计: {total} 个 examples")
    print(f"✅ 已支持测试模式: {with_test_mode} ({with_test_mode * 100 // total}%)")
    print(f"💡 建议添加测试模式: {needs_test_mode}")
    print()

    # 按难度分组
    by_difficulty = {"easy": [], "medium": [], "hard": [], "unknown": []}
    for file_path, analysis in examples:
        if not analysis["has_test_mode"]:
            by_difficulty[analysis["difficulty"]].append((file_path, analysis))

    print("━" * 80)
    print("🎯 推荐优先级")
    print("━" * 80)
    print()

    # Easy
    if by_difficulty["easy"]:
        print(f"✨ Easy ({len(by_difficulty['easy'])} 个) - 推荐立即添加:")
        for file_path, analysis in by_difficulty["easy"][:10]:
            rel_path = file_path.relative_to(Path.cwd())
            print(f"  • {rel_path}")
            print(f"    {analysis['suggestion']}")
        if len(by_difficulty["easy"]) > 10:
            print(f"  ... 还有 {len(by_difficulty['easy']) - 10} 个")
        print()

    # Medium
    if by_difficulty["medium"]:
        print(f"💡 Medium ({len(by_difficulty['medium'])} 个) - 需要 API 处理:")
        for file_path, analysis in by_difficulty["medium"][:5]:
            rel_path = file_path.relative_to(Path.cwd())
            print(f"  • {rel_path}")
            print(f"    {analysis['suggestion']}")
        if len(by_difficulty["medium"]) > 5:
            print(f"  ... 还有 {len(by_difficulty['medium']) - 5} 个")
        print()

    # Hard
    if by_difficulty["hard"]:
        print(f"⚠️  Hard ({len(by_difficulty['hard'])} 个) - 需要重构:")
        for file_path, analysis in by_difficulty["hard"][:5]:
            rel_path = file_path.relative_to(Path.cwd())
            print(f"  • {rel_path}")
            print(f"    {analysis['suggestion']}")
        if len(by_difficulty["hard"]) > 5:
            print(f"  ... 还有 {len(by_difficulty['hard']) - 5} 个")
        print()

    print("━" * 80)
    print("📝 下一步行动")
    print("━" * 80)
    print()
    print("1. 查看具体文件建议:")
    print("   python tools/scripts/add_test_mode_to_examples.py --file <path>")
    print()
    print("2. 使用模板添加测试模式:")
    print("   python tools/scripts/add_test_mode_to_examples.py --template")
    print()
    print("3. 运行 examples 测试:")
    print("   SAGE_TEST_MODE=true python <example_file>")
    print()


def print_file_suggestion(file_path: Path):
    """为特定文件打印详细建议。"""
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return

    analysis = analyze_example(file_path)

    print("=" * 80)
    print(f"📝 {file_path.name}")
    print("=" * 80)
    print()
    print(f"路径: {file_path}")
    print(f"状态: {analysis['suggestion']}")
    print(f"难度: {analysis['difficulty']}")
    print()

    if analysis["has_test_mode"]:
        print("✅ 该文件已支持测试模式")
        print()
        print("验证命令:")
        print(f"  SAGE_TEST_MODE=true python {file_path}")
        return

    print("━" * 80)
    print("💡 添加测试模式支持的步骤")
    print("━" * 80)
    print()

    if not analysis["has_main_block"]:
        print("1. ⚠️  该文件没有 if __name__ == '__main__' 块")
        print("   需要先重构代码，将执行逻辑移到 main() 函数中")
        print()
    else:
        print("1. ✅ 文件已有 main 块")
        print()

    print("2. 添加测试模式检测函数:")
    print()
    print("```python")
    print("import os")
    print()
    print("def is_test_mode() -> bool:")
    print('    """Check if running in test mode."""')
    print("    return (")
    print('        os.getenv("SAGE_TEST_MODE") == "true"')
    print('        or os.getenv("SAGE_EXAMPLES_MODE") == "test"')
    print("    )")
    print("```")
    print()

    print("3. 在 main() 函数开头添加测试模式逻辑:")
    print()
    print("```python")
    print("def main():")
    print("    if is_test_mode():")
    print('        print("🧪 Test mode: Validating configuration...")')
    print("        # 验证配置加载")
    print("        # 验证模块导入")
    print('        print("✅ Test mode: Validation passed")')
    print("        return")
    print()
    print("    # 正常执行逻辑")
    print("    ...")
    print("```")
    print()

    print("4. 修改 if __name__ == '__main__' 块:")
    print()
    print("```python")
    print('if __name__ == "__main__":')
    print("    if is_test_mode():")
    print("        try:")
    print("            main()")
    print('            print("\\n✅ Test passed: Example structure validated")')
    print("        except Exception as e:")
    print('            print(f"❌ Test failed: {e}")')
    print("            sys.exit(1)")
    print("    else:")
    print("        main()")
    print("```")
    print()

    print("5. 测试:")
    print(f"   SAGE_TEST_MODE=true python {file_path}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Add test mode support to SAGE examples")
    parser.add_argument("--dry-run", action="store_true", help="Only analyze, don't modify files")
    parser.add_argument("--file", type=Path, help="Analyze specific file")
    parser.add_argument("--template", action="store_true", help="Show test mode template")

    args = parser.parse_args()

    root_dir = Path.cwd()

    if args.template:
        print(generate_test_mode_template(Path("example.py")))
        return 0

    if args.file:
        print_file_suggestion(args.file)
        return 0

    # 扫描所有 examples
    examples = scan_examples(root_dir)

    if not examples:
        print("❌ 未找到 examples 文件")
        return 1

    print_report(examples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
