#!/usr/bin/env python3
"""测试 Studio 自动 ingest 功能"""

import sys
from pathlib import Path

# Add SAGE to path
sage_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(sage_root / "packages/sage-studio/src"))

# ruff: noqa: E402 - imports after path setup
from sage.studio.studio_manager import StudioManager


def test_ensure_rag_index():
    """测试 _ensure_rag_index 方法"""
    manager = StudioManager()

    print("=" * 60)
    print("测试自动 RAG 索引构建")
    print("=" * 60)

    # 删除现有索引
    index_root = Path.home() / ".sage" / "cache" / "chat"
    if index_root.exists():
        print(f"清理现有索引: {index_root}")
        import shutil

        shutil.rmtree(index_root)

    # 调用 _ensure_rag_index
    print("\n调用 _ensure_rag_index()...")
    success = manager._ensure_rag_index()

    print(f"\n结果: {'成功' if success else '失败'}")

    # 检查索引文件
    manifest_file = index_root / "docs-public_manifest.json"
    db_file = index_root / "docs-public.sagedb"

    print("\n索引文件检查:")
    print(f"  Manifest: {manifest_file.exists()} - {manifest_file}")
    print(f"  Database: {db_file.exists()} - {db_file}")

    if manifest_file.exists():
        import json

        with open(manifest_file) as f:
            manifest = json.load(f)
        print("\n索引统计:")
        print(f"  文档数: {manifest.get('num_documents', 0)}")
        print(f"  片段数: {manifest.get('num_chunks', 0)}")
        print(f"  创建时间: {manifest.get('created_at', 'N/A')}")

    return success


if __name__ == "__main__":
    try:
        success = test_ensure_rag_index()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
