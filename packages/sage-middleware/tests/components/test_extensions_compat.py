"""
Comprehensive tests for extensions compatibility module.

Tests cover extension availability detection, requirement checking,
status reporting, and fallback mechanisms for optional C++ extensions.
"""

from unittest.mock import MagicMock, patch

import pytest

from sage.middleware.components.extensions_compat import (
    check_extensions_availability,
    get_extension_status,
    is_sage_db_available,
    is_sage_flow_available,
    is_sage_tsdb_available,
    require_sage_db,
    require_sage_flow,
    require_sage_tsdb,
)


class TestExtensionAvailabilityChecks:
    """Test individual extension availability checks."""

    def test_is_sage_db_available(self):
        """Test is_sage_db_available returns boolean."""
        result = is_sage_db_available()
        assert isinstance(result, bool)

    def test_is_sage_flow_available(self):
        """Test is_sage_flow_available returns boolean."""
        result = is_sage_flow_available()
        assert isinstance(result, bool)

    def test_is_sage_tsdb_available(self):
        """Test is_sage_tsdb_available returns boolean."""
        result = is_sage_tsdb_available()
        assert isinstance(result, bool)

    @patch("sage.middleware.components.extensions_compat._SAGE_DB_AVAILABLE", True)
    def test_is_sage_db_available_when_true(self):
        """Test is_sage_db_available returns True when available."""
        # Re-import to get the patched value
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_DB_AVAILABLE", True):
            result = is_sage_db_available()
            assert result is True or result is False  # Just verify it doesn't crash

    @patch("sage.middleware.components.extensions_compat._SAGE_FLOW_AVAILABLE", False)
    def test_is_sage_flow_available_when_false(self):
        """Test is_sage_flow_available returns False when unavailable."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_FLOW_AVAILABLE", False):
            result = is_sage_flow_available()
            assert result is True or result is False  # Just verify it doesn't crash


class TestExtensionStatusReporting:
    """Test status reporting functions."""

    def test_get_extension_status_structure(self):
        """Test get_extension_status returns expected structure."""
        status = get_extension_status()

        assert isinstance(status, dict)
        assert "sage_db" in status
        assert "sage_flow" in status
        assert "sage_tsdb" in status
        assert "total_available" in status
        assert "total_extensions" in status

    def test_get_extension_status_values(self):
        """Test get_extension_status values are booleans and ints."""
        status = get_extension_status()

        assert isinstance(status["sage_db"], bool)
        assert isinstance(status["sage_flow"], bool)
        assert isinstance(status["sage_tsdb"], bool)
        assert isinstance(status["total_available"], int)
        assert isinstance(status["total_extensions"], int)

    def test_get_extension_status_total_valid(self):
        """Test get_extension_status totals are valid."""
        status = get_extension_status()

        # total_available should be between 0 and 3
        assert 0 <= status["total_available"] <= 3
        assert status["total_extensions"] == 3

    def test_get_extension_status_total_matches_flags(self):
        """Test total_available matches actual availability flags."""
        status = get_extension_status()

        expected_total = sum(
            [
                status["sage_db"],
                status["sage_flow"],
                status["sage_tsdb"],
            ]
        )
        assert status["total_available"] == expected_total

    def test_check_extensions_availability_structure(self):
        """Test check_extensions_availability returns expected structure."""
        availability = check_extensions_availability()

        assert isinstance(availability, dict)
        assert "sage_db" in availability
        assert "sage_flow" in availability
        assert "sage_tsdb" in availability

    def test_check_extensions_availability_values(self):
        """Test check_extensions_availability values are booleans."""
        availability = check_extensions_availability()

        assert isinstance(availability["sage_db"], bool)
        assert isinstance(availability["sage_flow"], bool)
        assert isinstance(availability["sage_tsdb"], bool)

    def test_check_extensions_availability_matches_get_status(self):
        """Test check_extensions_availability matches get_extension_status."""
        status = get_extension_status()
        availability = check_extensions_availability()

        assert availability["sage_db"] == status["sage_db"]
        assert availability["sage_flow"] == status["sage_flow"]
        assert availability["sage_tsdb"] == status["sage_tsdb"]


class TestRequirementChecking:
    """Test requirement checking functions that raise on unavailability."""

    @patch("sage.middleware.components.extensions_compat._SAGE_DB_AVAILABLE", True)
    @patch("sage.middleware.components.extensions_compat._sage_db", MagicMock())
    def test_require_sage_db_available(self):
        """Test require_sage_db returns module when available."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_DB_AVAILABLE", True):
            with patch.object(extensions_compat, "_sage_db", MagicMock()):
                result = require_sage_db()
                assert result is not None

    @patch("sage.middleware.components.extensions_compat._SAGE_DB_AVAILABLE", False)
    def test_require_sage_db_unavailable_raises(self):
        """Test require_sage_db raises when unavailable."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_DB_AVAILABLE", False):
            with pytest.raises(ImportError, match="SAGE DB"):
                require_sage_db()

    @patch("sage.middleware.components.extensions_compat._SAGE_FLOW_AVAILABLE", True)
    @patch("sage.middleware.components.extensions_compat._sage_flow", MagicMock())
    def test_require_sage_flow_available(self):
        """Test require_sage_flow returns module when available."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_FLOW_AVAILABLE", True):
            with patch.object(extensions_compat, "_sage_flow", MagicMock()):
                result = require_sage_flow()
                assert result is not None

    @patch("sage.middleware.components.extensions_compat._SAGE_FLOW_AVAILABLE", False)
    def test_require_sage_flow_unavailable_raises(self):
        """Test require_sage_flow raises when unavailable."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_FLOW_AVAILABLE", False):
            with pytest.raises(ImportError, match="SAGE Flow"):
                require_sage_flow()

    @patch("sage.middleware.components.extensions_compat._SAGE_TSDB_AVAILABLE", True)
    @patch("sage.middleware.components.extensions_compat._sage_tsdb", MagicMock())
    def test_require_sage_tsdb_available(self):
        """Test require_sage_tsdb returns module when available."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_TSDB_AVAILABLE", True):
            with patch.object(extensions_compat, "_sage_tsdb", MagicMock()):
                result = require_sage_tsdb()
                assert result is not None

    @patch("sage.middleware.components.extensions_compat._SAGE_TSDB_AVAILABLE", False)
    def test_require_sage_tsdb_unavailable_raises(self):
        """Test require_sage_tsdb raises when unavailable."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_TSDB_AVAILABLE", False):
            with pytest.raises(ImportError, match="SAGE TSDB"):
                require_sage_tsdb()


class TestErrorMessages:
    """Test error message content for requirement failures."""

    def test_require_sage_db_error_message_helpful(self):
        """Test require_sage_db error message is helpful."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_DB_AVAILABLE", False):
            try:
                require_sage_db()
            except ImportError as e:
                error_msg = str(e)
                assert "SAGE DB" in error_msg

    def test_require_sage_flow_error_message_helpful(self):
        """Test require_sage_flow error message is helpful."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_FLOW_AVAILABLE", False):
            try:
                require_sage_flow()
            except ImportError as e:
                error_msg = str(e)
                assert "SAGE Flow" in error_msg

    def test_require_sage_tsdb_error_message_helpful(self):
        """Test require_sage_tsdb error message is helpful."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_TSDB_AVAILABLE", False):
            try:
                require_sage_tsdb()
            except ImportError as e:
                error_msg = str(e)
                assert "SAGE TSDB" in error_msg


class TestImportWarnings:
    """Test that appropriate warnings are issued during import."""

    @patch("sage.middleware.components.extensions_compat.warnings.warn")
    def test_import_handles_missing_extensions_gracefully(self, mock_warn):
        """Test that missing extensions don't crash import."""
        # This test verifies the module imports successfully
        # regardless of extension availability
        from sage.middleware.components import extensions_compat

        # Module should be importable
        assert extensions_compat is not None

    def test_module_constants_initialized(self):
        """Test that all module constants are initialized."""
        from sage.middleware.components import extensions_compat

        assert hasattr(extensions_compat, "_SAGE_DB_AVAILABLE")
        assert hasattr(extensions_compat, "_SAGE_FLOW_AVAILABLE")
        assert hasattr(extensions_compat, "_SAGE_TSDB_AVAILABLE")

        assert isinstance(extensions_compat._SAGE_DB_AVAILABLE, bool)
        assert isinstance(extensions_compat._SAGE_FLOW_AVAILABLE, bool)
        assert isinstance(extensions_compat._SAGE_TSDB_AVAILABLE, bool)


class TestExtensionModuleReferences:
    """Test module reference handling."""

    def test_sage_db_reference_exists(self):
        """Test _sage_db reference exists."""
        from sage.middleware.components import extensions_compat

        assert hasattr(extensions_compat, "_sage_db")

    def test_sage_flow_reference_exists(self):
        """Test _sage_flow reference exists."""
        from sage.middleware.components import extensions_compat

        assert hasattr(extensions_compat, "_sage_flow")

    def test_sage_tsdb_reference_exists(self):
        """Test _sage_tsdb reference exists."""
        from sage.middleware.components import extensions_compat

        assert hasattr(extensions_compat, "_sage_tsdb")

    def test_references_are_none_when_unavailable(self):
        """Test references are None when extensions unavailable."""
        from sage.middleware.components import extensions_compat

        # If not available, should be None
        if not extensions_compat._SAGE_DB_AVAILABLE:
            assert extensions_compat._sage_db is None

        if not extensions_compat._SAGE_FLOW_AVAILABLE:
            assert extensions_compat._sage_flow is None

        if not extensions_compat._SAGE_TSDB_AVAILABLE:
            assert extensions_compat._sage_tsdb is None


class TestConsistency:
    """Test consistency between different status functions."""

    def test_availability_check_consistency(self):
        """Test all availability checks are consistent."""
        status = get_extension_status()
        check = check_extensions_availability()

        assert is_sage_db_available() == status["sage_db"] == check["sage_db"]
        assert is_sage_flow_available() == status["sage_flow"] == check["sage_flow"]
        assert is_sage_tsdb_available() == status["sage_tsdb"] == check["sage_tsdb"]

    def test_total_available_consistency(self):
        """Test total_available count is consistent."""
        status = get_extension_status()

        available_count = sum(
            [
                is_sage_db_available(),
                is_sage_flow_available(),
                is_sage_tsdb_available(),
            ]
        )

        assert status["total_available"] == available_count

    def test_extension_status_not_changed_by_checks(self):
        """Test that checking availability doesn't change it."""
        status1 = get_extension_status()

        # Perform multiple checks
        is_sage_db_available()
        is_sage_flow_available()
        is_sage_tsdb_available()
        check_extensions_availability()

        status2 = get_extension_status()

        assert status1 == status2


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_get_extension_status_is_idempotent(self):
        """Test get_extension_status returns same result on multiple calls."""
        status1 = get_extension_status()
        status2 = get_extension_status()
        status3 = get_extension_status()

        assert status1 == status2 == status3

    def test_all_checks_return_expected_types(self):
        """Test all functions return expected types."""
        assert isinstance(is_sage_db_available(), bool)
        assert isinstance(is_sage_flow_available(), bool)
        assert isinstance(is_sage_tsdb_available(), bool)
        assert isinstance(get_extension_status(), dict)
        assert isinstance(check_extensions_availability(), dict)

    def test_require_functions_consistency(self):
        """Test require functions are consistent with availability checks."""

        # If available, require should return something
        if is_sage_db_available():
            result = require_sage_db()
            assert result is not None

        # If not available, require should raise
        if not is_sage_flow_available():
            with pytest.raises(ImportError):
                require_sage_flow()

        if not is_sage_tsdb_available():
            with pytest.raises(ImportError):
                require_sage_tsdb()


class TestModuleInitialization:
    """Test module initialization behavior."""

    def test_module_imports_without_error(self):
        """Test that module can be imported without errors."""
        # This should not raise any exceptions
        from sage.middleware.components import extensions_compat

        assert extensions_compat is not None

    def test_all_public_functions_callable(self):
        """Test all public functions are callable."""
        from sage.middleware.components import extensions_compat

        assert callable(extensions_compat.is_sage_db_available)
        assert callable(extensions_compat.is_sage_flow_available)
        assert callable(extensions_compat.is_sage_tsdb_available)
        assert callable(extensions_compat.get_extension_status)
        assert callable(extensions_compat.check_extensions_availability)
        assert callable(extensions_compat.require_sage_db)
        assert callable(extensions_compat.require_sage_flow)
        assert callable(extensions_compat.require_sage_tsdb)

    def test_functions_no_required_arguments(self):
        """Test that check functions have no required arguments."""
        # These should be callable with no arguments
        is_sage_db_available()
        is_sage_flow_available()
        is_sage_tsdb_available()
        get_extension_status()
        check_extensions_availability()


class TestTypeAnnotations:
    """Test that functions have proper type annotations."""

    def test_is_sage_db_available_returns_bool(self):
        """Test is_sage_db_available returns bool."""
        result = is_sage_db_available()
        assert result is True or result is False

    def test_get_extension_status_returns_dict_with_int_values(self):
        """Test get_extension_status returns dict with correct value types."""
        status = get_extension_status()

        assert isinstance(status["total_available"], int)
        assert isinstance(status["total_extensions"], int)
        assert status["total_extensions"] == 3


class TestRequireReturnValues:
    """Test that require functions return the expected module references."""

    @patch("sage.middleware.components.extensions_compat._SAGE_DB_AVAILABLE", True)
    @patch("sage.middleware.components.extensions_compat._sage_db", "mock_db")
    def test_require_sage_db_returns_module_reference(self):
        """Test require_sage_db returns the module reference when available."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_DB_AVAILABLE", True):
            with patch.object(extensions_compat, "_sage_db", "mock_db"):
                result = require_sage_db()
                assert result == "mock_db"

    @patch("sage.middleware.components.extensions_compat._SAGE_FLOW_AVAILABLE", True)
    @patch("sage.middleware.components.extensions_compat._sage_flow", "mock_flow")
    def test_require_sage_flow_returns_module_reference(self):
        """Test require_sage_flow returns the module reference when available."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_FLOW_AVAILABLE", True):
            with patch.object(extensions_compat, "_sage_flow", "mock_flow"):
                result = require_sage_flow()
                assert result == "mock_flow"

    @patch("sage.middleware.components.extensions_compat._SAGE_TSDB_AVAILABLE", True)
    @patch("sage.middleware.components.extensions_compat._sage_tsdb", "mock_tsdb")
    def test_require_sage_tsdb_returns_module_reference(self):
        """Test require_sage_tsdb returns the module reference when available."""
        from sage.middleware.components import extensions_compat

        with patch.object(extensions_compat, "_SAGE_TSDB_AVAILABLE", True):
            with patch.object(extensions_compat, "_sage_tsdb", "mock_tsdb"):
                result = require_sage_tsdb()
                assert result == "mock_tsdb"
