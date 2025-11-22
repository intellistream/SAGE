"""
Tests for HuggingFace integration module

Basic test to verify module can be imported
"""

import pytest


@pytest.mark.unit
class TestHFClientImport:
    """Test HuggingFace client can be imported"""

    def test_import(self):
        """测试能够导入HFClient"""
        from sage.libs.integrations.huggingface import HFClient

        assert HFClient is not None
        assert hasattr(HFClient, "__init__")
        assert hasattr(HFClient, "generate")
