"""
Tests for sage.common.core.functions.keyby_function

Tests the KeyByFunction class for partition key extraction.
"""

from unittest.mock import Mock

import pytest

from sage.common.core.functions.keyby_function import KeyByFunction


class SimpleKeyByFunction(KeyByFunction):
    """Simple KeyBy implementation for testing"""

    def execute(self, data):
        return data.get("id") if isinstance(data, dict) else data


class UserIdExtractor(KeyByFunction):
    """Extract user_id from data"""

    def execute(self, data):
        if isinstance(data, dict):
            return data.get("user_id")
        return getattr(data, "user_id", None)


class CompositeKeyExtractor(KeyByFunction):
    """Extract composite key"""

    def execute(self, data):
        if isinstance(data, dict):
            return f"{data.get('user_id', '')}_{data.get('session_id', '')}"
        return None


class TestKeyByFunction:
    """Tests for KeyByFunction class"""

    def test_simple_key_extraction(self):
        """Test simple key extraction"""
        func = SimpleKeyByFunction()

        data = {"id": 123, "name": "test"}
        key = func.execute(data)

        assert key == 123

    def test_user_id_extraction(self):
        """Test user ID extraction"""
        func = UserIdExtractor()

        data = {"user_id": "user_001", "name": "Alice"}
        key = func.execute(data)

        assert key == "user_001"

    def test_composite_key_extraction(self):
        """Test composite key extraction"""
        func = CompositeKeyExtractor()

        data = {"user_id": "user_001", "session_id": "session_123"}
        key = func.execute(data)

        assert key == "user_001_session_123"

    def test_validate_key_with_hashable(self):
        """Test validate_key with hashable values"""
        func = SimpleKeyByFunction()

        # Test various hashable types
        assert func.validate_key(123) is True
        assert func.validate_key("string") is True
        assert func.validate_key((1, 2, 3)) is True
        assert func.validate_key(None) is True

    def test_validate_key_with_unhashable(self):
        """Test validate_key with unhashable values"""
        func = SimpleKeyByFunction()

        # Lists are not hashable
        assert func.validate_key([1, 2, 3]) is False

        # Dicts are not hashable
        assert func.validate_key({"key": "value"}) is False

    def test_extract_with_validation_success(self):
        """Test extract_with_validation with valid key"""
        func = SimpleKeyByFunction()

        data = {"id": 456, "name": "test"}
        key = func.extract_with_validation(data)

        assert key == 456

    def test_extract_with_validation_failure(self):
        """Test extract_with_validation with invalid key"""

        class UnhashableKeyExtractor(KeyByFunction):
            def execute(self, data):
                return [1, 2, 3]  # Return unhashable list

        func = UnhashableKeyExtractor()

        with pytest.raises((TypeError, ValueError)):  # Could be either
            func.extract_with_validation({"data": "test"})

    def test_none_key_is_valid(self):
        """Test that None is a valid (hashable) key"""
        func = SimpleKeyByFunction()

        assert func.validate_key(None) is True

    def test_integer_key(self):
        """Test integer key extraction"""
        func = SimpleKeyByFunction()

        data = {"id": 12345}
        key = func.execute(data)

        assert key == 12345
        assert isinstance(key, int)

    def test_string_key(self):
        """Test string key extraction"""
        func = UserIdExtractor()

        data = {"user_id": "abc123"}
        key = func.execute(data)

        assert key == "abc123"
        assert isinstance(key, str)

    def test_tuple_key(self):
        """Test tuple as composite key"""

        class TupleKeyExtractor(KeyByFunction):
            def execute(self, data):
                return (data.get("category"), data.get("region"))

        func = TupleKeyExtractor()

        data = {"category": "electronics", "region": "US"}
        key = func.execute(data)

        assert key == ("electronics", "US")
        assert func.validate_key(key) is True

    def test_missing_field_returns_none(self):
        """Test extraction when field is missing"""
        func = UserIdExtractor()

        data = {"name": "test"}  # No user_id
        key = func.execute(data)

        assert key is None

    def test_key_extraction_from_object(self):
        """Test key extraction from object with attributes"""

        class DataObject:
            def __init__(self, user_id):
                self.user_id = user_id

        func = UserIdExtractor()
        obj = DataObject("user_789")

        key = func.execute(obj)

        assert key == "user_789"

    def test_case_sensitive_key(self):
        """Test that keys are case-sensitive"""

        class CaseSensitiveExtractor(KeyByFunction):
            def execute(self, data):
                return data.get("Category")  # Note capital C

        func = CaseSensitiveExtractor()

        data1 = {"Category": "A"}
        data2 = {"category": "A"}  # lowercase

        key1 = func.execute(data1)
        key2 = func.execute(data2)

        assert key1 == "A"
        assert key2 is None

    def test_numeric_string_key(self):
        """Test numeric string as key"""
        func = SimpleKeyByFunction()

        data = {"id": "12345"}  # String, not int
        key = func.execute(data)

        assert key == "12345"
        assert isinstance(key, str)

    def test_empty_string_key(self):
        """Test empty string as valid key"""
        func = SimpleKeyByFunction()

        data = {"id": ""}
        key = func.execute(data)

        assert key == ""
        assert func.validate_key(key) is True

    def test_zero_as_key(self):
        """Test zero as valid key"""
        func = SimpleKeyByFunction()

        data = {"id": 0}
        key = func.execute(data)

        assert key == 0
        assert func.validate_key(key) is True

    def test_negative_number_key(self):
        """Test negative number as key"""
        func = SimpleKeyByFunction()

        data = {"id": -999}
        key = func.execute(data)

        assert key == -999
        assert func.validate_key(key) is True


class TestKeyByFunctionAdvanced:
    """Advanced tests for KeyByFunction"""

    def test_custom_validation_logic(self):
        """Test custom validation logic override"""

        class CustomValidationKeyBy(KeyByFunction):
            def execute(self, data):
                return data.get("id")

            def validate_key(self, key):
                # Custom: only accept positive integers
                return isinstance(key, int) and key > 0

        func = CustomValidationKeyBy()

        assert func.validate_key(5) is True
        assert func.validate_key(0) is False
        assert func.validate_key(-1) is False
        assert func.validate_key("string") is False

    def test_key_normalization(self):
        """Test key normalization in extractor"""

        class NormalizingKeyExtractor(KeyByFunction):
            def execute(self, data):
                # Normalize to lowercase
                key = data.get("category", "")
                return key.lower() if isinstance(key, str) else key

        func = NormalizingKeyExtractor()

        data1 = {"category": "Electronics"}
        data2 = {"category": "ELECTRONICS"}
        data3 = {"category": "electronics"}

        assert func.execute(data1) == "electronics"
        assert func.execute(data2) == "electronics"
        assert func.execute(data3) == "electronics"

    def test_frozen_set_as_key(self):
        """Test frozenset as key (hashable set)"""

        class FrozenSetKeyExtractor(KeyByFunction):
            def execute(self, data):
                tags = data.get("tags", [])
                return frozenset(tags)

        func = FrozenSetKeyExtractor()

        data = {"tags": ["python", "testing", "sage"]}
        key = func.execute(data)

        assert isinstance(key, frozenset)
        assert func.validate_key(key) is True

    def test_extract_with_logging(self):
        """Test that validation logs warnings"""
        func = SimpleKeyByFunction()

        # Mock logger
        func._logger = Mock()

        # Try to validate unhashable
        result = func.validate_key([1, 2, 3])

        assert result is False
        # Logger should have been called with warning
        assert func._logger.warning.called
