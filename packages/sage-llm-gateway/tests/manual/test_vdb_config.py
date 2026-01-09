#!/usr/bin/env python
"""Test VDB backend configuration from config.yaml

NOTE: This test requires NeuroMem (isage-neuromem) to be installed.
Skip if not available.
"""

import sys
from pathlib import Path

import pytest

# Add SAGE to path
sage_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(sage_root / "packages/sage-llm-gateway/src"))

# Check if NeuroMem is available
try:
    from sage.middleware.components.sage_mem.neuromem import MemoryManager  # noqa: F401

    HAS_NEUROMEM = True
except ImportError:
    HAS_NEUROMEM = False

NEUROMEM_SKIP_REASON = "NeuroMem (isage-neuromem) not installed"


@pytest.mark.skipif(not HAS_NEUROMEM, reason=NEUROMEM_SKIP_REASON)
def test_config_loading():
    """测试配置加载"""
    from sage.llm.gateway.session.manager import _load_gateway_config

    print("📝 Testing config.yaml loading...")
    config = _load_gateway_config()

    print(f"\nGateway config: {config}")

    if "memory" in config:
        memory_config = config["memory"]
        print("\n✅ Memory config found:")
        print(f"  - Backend: {memory_config.get('backend', 'short_term')}")
        print(f"  - Max dialogs: {memory_config.get('max_memory_dialogs', 10)}")

        if "vdb" in memory_config:
            vdb_config = memory_config["vdb"]
            print("\n  VDB config:")
            print(f"    - Backend type: {vdb_config.get('backend_type', 'FAISS')}")
            print(f"    - Embedding dim: {vdb_config.get('embedding_dim', 384)}")
            print(f"    - Embedding model: {vdb_config.get('embedding_model', 'hash')}")
    else:
        print("\n⚠️  No memory config found, using defaults")


@pytest.mark.skipif(not HAS_NEUROMEM, reason=NEUROMEM_SKIP_REASON)
def test_session_manager_creation():
    """测试 SessionManager 创建"""
    from sage.llm.gateway.session.manager import get_session_manager

    print("\n\n📝 Testing SessionManager creation...")
    manager = get_session_manager()

    print("✅ SessionManager created:")
    print(f"  - Memory backend: {manager._memory_backend}")
    print(f"  - Max memory dialogs: {manager._max_memory_dialogs}")
    print(f"  - Memory config: {manager._memory_config}")


def test_vdb_backend_selection():
    """测试 VDB 后端选择"""
    from pathlib import Path

    import yaml

    print("\n\n📝 Testing VDB backend selection...")

    # 读取 config.yaml
    config_path = Path.cwd() / "config" / "config.yaml"
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    gateway_config = config.get("gateway", {})
    memory_config = gateway_config.get("memory", {})
    vdb_config = memory_config.get("vdb", {})

    backend_type = vdb_config.get("backend_type", "FAISS")

    print(f"✅ VDB backend from config.yaml: {backend_type}")

    if backend_type == "SageVDB":
        print("  ✅ SageVDB is selected (C++ optimized)")
    else:
        print("  ✅ FAISS is selected (Python)")

    return backend_type


if __name__ == "__main__":
    print("=" * 60)
    print("Testing VDB Backend Configuration")
    print("=" * 60)

    try:
        test_config_loading()
        test_session_manager_creation()
        backend_type = test_vdb_backend_selection()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

        if backend_type == "SageVDB":
            print("\n🚀 Current configuration uses SageVDB (C++ optimized)")
        else:
            print("\n📝 Current configuration uses FAISS")
            print("💡 To use SageVDB, set gateway.memory.vdb.backend_type: SageVDB in config.yaml")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
