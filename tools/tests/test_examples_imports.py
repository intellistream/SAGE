#!/usr/bin/env python3
"""
测试 examples 目录中关键文件的导入是否正确

这个测试不运行示例，只检查导入是否有错误。
"""

import sys
import importlib.util
from pathlib import Path
from typing import List, Tuple


def test_import_file(file_path: Path) -> Tuple[bool, str]:
    """
    测试一个 Python 文件是否可以成功导入

    Returns:
        (success, error_message)
    """
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec is None or spec.loader is None:
            return False, "Failed to create module spec"

        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module"] = module
        spec.loader.exec_module(module)

        # Clean up
        if "test_module" in sys.modules:
            del sys.modules["test_module"]

        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    """测试关键示例文件的导入"""
    project_root = Path(__file__).resolve().parents[2]
    examples_dir = project_root / "examples"

    # 关键示例文件列表
    key_examples = [
        # Tutorials - 基础教程
        "tutorials/hello_world.py",
        "tutorials/embedding_demo.py",
        "tutorials/pipeline_builder_embedding_demo.py",
        "tutorials/pipeline_builder_llm_demo.py",

        # Apps - 应用示例
        "apps/run_video_intelligence.py",
        "apps/run_medical_diagnosis.py",

        # Unlearning - 隐私遗忘
        "unlearning/usage_1_direct_library.py",
        "unlearning/usage_2_sage_function.py",
        "unlearning/usage_4_complete_rag.py",
    ]

    print("=" * 80)
    print("测试 SAGE Examples 导入")
    print("=" * 80)
    print()

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for example_path in key_examples:
        full_path = examples_dir / example_path

        # 检查文件是否存在
        if not full_path.exists():
            print(f"⚠️  SKIP: {example_path} (file not found)")
            skipped_count += 1
            continue

        # 测试导入
        success, error = test_import_file(full_path)

        if success:
            print(f"✅ PASS: {example_path}")
            success_count += 1
        else:
            print(f"❌ FAIL: {example_path}")
            print(f"   Error: {error}")
            fail_count += 1

    print()
    print("=" * 80)
    print(f"Results: {success_count} passed, {fail_count} failed, {skipped_count} skipped")
    print("=" * 80)

    # 返回适当的退出码
    if fail_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
