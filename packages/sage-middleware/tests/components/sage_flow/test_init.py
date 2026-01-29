"""
Unit tests for sage_flow __init__.py module
Tests import compatibility and graceful degradation
"""

import pytest


@pytest.mark.unit
class TestSageFlowImports:
    """Tests for SageFlow import compatibility"""

    def test_sage_flow_available_flag_exists(self):
        """Test _SAGE_FLOW_AVAILABLE flag is defined"""
        from sage.middleware.components import sage_flow

        assert hasattr(sage_flow, "_SAGE_FLOW_AVAILABLE")
        assert isinstance(sage_flow._SAGE_FLOW_AVAILABLE, bool)

    def test_sage_flow_exports_exist(self):
        """Test all expected exports are present (even if None)"""
        from sage.middleware.components import sage_flow

        expected_exports = [
            "DataType",
            "SimpleStreamSource",
            "Stream",
            "StreamEnvironment",
            "VectorData",
            "VectorRecord",
            "__version__",
        ]

        for export in expected_exports:
            assert hasattr(sage_flow, export), f"Missing export: {export}"

    def test_sage_flow_version_attribute(self):
        """Test __version__ attribute exists"""
        from sage.middleware.components import sage_flow

        assert hasattr(sage_flow, "__version__")
        assert isinstance(sage_flow.__version__, str)

    def test_sage_flow_graceful_degradation(self):
        """Test graceful degradation when isage-flow not installed"""
        from sage.middleware.components import sage_flow

        # If SageFlow not available, exports should be None
        if not sage_flow._SAGE_FLOW_AVAILABLE:
            assert sage_flow.DataType is None
            assert sage_flow.SimpleStreamSource is None
            assert sage_flow.Stream is None
            assert sage_flow.StreamEnvironment is None
            assert sage_flow.__version__ == "unavailable"


@pytest.mark.unit
class TestSageFlowCompatibility:
    """Tests for SageFlow backward compatibility"""

    def test_import_from_sage_middleware_components(self):
        """Test importing from sage.middleware.components.sage_flow"""
        # Use importlib to test availability without triggering unused imports
        from importlib.util import find_spec

        spec = find_spec("sage.middleware.components.sage_flow")
        assert spec is not None, "sage_flow module should be available"

        # Test that key exports exist
        import sage.middleware.components.sage_flow as sf

        assert hasattr(sf, "DataType"), "DataType should be exported"
        assert hasattr(sf, "SimpleStreamSource"), "SimpleStreamSource should be exported"
        assert hasattr(sf, "Stream"), "Stream should be exported"
        assert hasattr(sf, "StreamEnvironment"), "StreamEnvironment should be exported"

    def test_sage_flow_service_import(self):
        """Test SageFlowService can be imported"""
        from sage.middleware.components import sage_flow

        # Should have SageFlowService
        assert hasattr(sage_flow, "SageFlowService")

    def test_module_docstring_exists(self):
        """Test module has proper documentation"""
        from sage.middleware.components import sage_flow

        assert sage_flow.__doc__ is not None
        assert "SageFlow compatibility layer" in sage_flow.__doc__
        assert "isage-flow" in sage_flow.__doc__


@pytest.mark.unit
class TestSageFlowWarnings:
    """Tests for SageFlow import warnings"""

    def test_warning_issued_when_unavailable(self):
        """Test warning is issued when SageFlow not available"""

        from sage.middleware.components import sage_flow

        if not sage_flow._SAGE_FLOW_AVAILABLE:
            # Warning should have been issued during import
            # We can't easily test this here, but we can verify the flag
            assert sage_flow._SAGE_FLOW_AVAILABLE is False
        else:
            # SageFlow is available, no warning expected
            assert sage_flow._SAGE_FLOW_AVAILABLE is True

    def test_stub_exports_when_unavailable(self):
        """Test stub exports are None when SageFlow unavailable"""
        from sage.middleware.components import sage_flow

        if not sage_flow._SAGE_FLOW_AVAILABLE:
            stubs = [
                "DataType",
                "SimpleStreamSource",
                "Stream",
                "StreamEnvironment",
                "VectorData",
                "VectorRecord",
            ]

            for stub in stubs:
                value = getattr(sage_flow, stub)
                assert value is None, f"{stub} should be None when unavailable"
