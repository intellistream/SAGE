#!/usr/bin/env python3
"""
Quick test for RAG Index Builder code sharing

Tests the new IndexBuilder architecture without requiring full package reinstall.
"""

import sys
from pathlib import Path

# Add source paths for dev testing
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "packages/sage-common/src"))
sys.path.insert(0, str(repo_root / "packages/sage-middleware/src"))
sys.path.insert(0, str(repo_root / "packages/sage-libs/src"))


def test_document_processing():
    """Test L1 document processing utilities"""
    print("\n[L1] Testing sage.common.utils.document_processing")
    print("-" * 70)

    from sage.common.utils.document_processing import (
        chunk_text,
        parse_markdown_sections,
        sanitize_metadata_value,
        slugify,
        truncate_text,
    )

    # Test chunk_text
    text = "First paragraph.\n\nSecond paragraph with more content here."
    chunks = chunk_text(text, chunk_size=30, chunk_overlap=10)
    assert len(chunks) > 0, "chunk_text should produce chunks"
    print(f"✓ chunk_text: {len(chunks)} chunks from {len(text)} chars")

    # Test parse_markdown_sections
    md = "# Title\nIntro\n## Section\nContent"
    sections = parse_markdown_sections(md)
    assert len(sections) == 2, "Should parse 2 sections"
    assert sections[0]["heading"] == "Title"
    assert sections[1]["heading"] == "Section"
    print(f"✓ parse_markdown_sections: {[s['heading'] for s in sections]}")

    # Test sanitize_metadata_value
    sanitized = sanitize_metadata_value("Line 1\nLine 2")
    assert "\n" not in sanitized
    print(f"✓ sanitize_metadata_value: '{sanitized}'")

    # Test slugify
    slug = slugify("Hello World!")
    assert slug == "hello-world"
    print(f"✓ slugify: 'Hello World!' → '{slug}'")

    # Test truncate_text
    long_text = "x" * 100
    truncated = truncate_text(long_text, limit=20)
    assert len(truncated) == 20
    assert truncated.endswith("...")
    print(f"✓ truncate_text: {len(long_text)} chars → {len(truncated)} chars")


def test_index_builder():
    """Test L4 IndexBuilder components"""
    print("\n[L4] Testing sage.middleware.operators.rag.index_builder")
    print("-" * 70)

    from datetime import datetime
    from pathlib import Path

    from sage.middleware.operators.rag.index_builder import (
        IndexBuilder,
        IndexManifest,
        VectorStore,
    )

    # Test IndexManifest
    manifest = IndexManifest(
        index_name="test",
        backend_type="SageDB",
        persist_path=Path("/tmp/test"),
        source_dir="/tmp/docs",
        embedding_config={"method": "hash", "dim": 384},
        chunk_size=800,
        chunk_overlap=160,
        num_documents=10,
        num_chunks=100,
        created_at=datetime.utcnow().isoformat(),
    )
    assert manifest.num_documents == 10
    assert manifest.num_chunks == 100
    manifest_dict = manifest.to_dict()
    assert manifest_dict["index_name"] == "test"
    print(f"✓ IndexManifest: {manifest.num_documents} docs, {manifest.num_chunks} chunks")

    # Test IndexBuilder initialization
    def mock_factory(path, dim):
        class MockStore:
            def add(self, vector, metadata):
                pass

            def build_index(self):
                pass

            def save(self, path):
                pass

            def load(self, path):
                pass

            def search(self, query, top_k=5, filter_dict=None):
                return []

            def get_dim(self):
                return dim

            def count(self):
                return 0

        return MockStore()

    builder = IndexBuilder(backend_factory=mock_factory)
    assert builder.backend_factory == mock_factory
    print("✓ IndexBuilder initialized with factory")

    # Test VectorStore Protocol
    print(f"✓ VectorStore Protocol: {VectorStore}")


def test_backends():
    """Test L4 SageDBBackend"""
    print("\n[L4] Testing sage.middleware.components.sage_db.backend")
    print("-" * 70)

    from sage.middleware.components.sage_db.backend import SageDBBackend

    print(f"✓ SageDBBackend class available: {SageDBBackend}")

    # Note: Can't instantiate without actual SageDB C++ extension
    # Just check that the class exists and has required methods
    required_methods = [
        "add",
        "build_index",
        "save",
        "load",
        "search",
        "get_dim",
        "count",
    ]
    for method in required_methods:
        assert hasattr(SageDBBackend, method), f"SageDBBackend missing {method}"
    print(f"✓ SageDBBackend has all required methods: {required_methods}")


def test_chroma_adapter():
    """Test L3 ChromaVectorStoreAdapter"""
    print("\n[L3] Testing sage.libs.integrations.chroma_adapter")
    print("-" * 70)

    try:
        from sage.libs.integrations.chroma_adapter import ChromaVectorStoreAdapter

        print(f"✓ ChromaVectorStoreAdapter class: {ChromaVectorStoreAdapter}")
    except ImportError as e:
        print(f"⚠  ChromaVectorStoreAdapter: {e}")
        print("   (Needs package reinstall with './quickstart.sh --dev --yes')")


def main():
    """Run all tests"""
    print("=" * 70)
    print("SAGE IndexBuilder Code Sharing - Quick Test")
    print("=" * 70)

    try:
        test_document_processing()
        test_index_builder()
        test_backends()
        test_chroma_adapter()

        print("\n" + "=" * 70)
        print("✅ All tests PASSED")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Run './quickstart.sh --dev --yes' to reinstall packages")
        print("  2. Test sage chat: sage chat ingest --source docs-public/docs_src")
        print("  3. Test gateway: sage-gateway start && curl localhost:8000/admin/index/status")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
