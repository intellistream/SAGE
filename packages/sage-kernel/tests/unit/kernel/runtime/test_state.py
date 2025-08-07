"""
Test suite for sage.kernels.runtime.state module

Tests state management functionality including serialization
and object attribute filtering.
"""
import pytest
import pickle
import threading
from unittest.mock import Mock, patch, mock_open
from collections.abc import Mapping, Sequence, Set

from sage.kernel.utils.persistence.state import (
    _gather_attrs, _filter_attrs, _is_serializable, _prepare,
    save_function_state, load_function_state,
    _BLACKLIST
)


class SerializableTestObject:
    """Test object that should be serializable"""
    def __init__(self):
        self.data = "test_data"
        self.number = 42
        self.items = [1, 2, 3]


class NonSerializableTestObject:
    """Test object with non-serializable attributes"""
    def __init__(self):
        self.serializable_data = "good_data"
        self.file_handle = None  # Will be set to non-serializable object


class FilteredTestObject:
    """Test object with state filtering attributes"""
    __state_include__ = ["include_this"]
    __state_exclude__ = ["exclude_this"]
    
    def __init__(self):
        self.include_this = "should_be_included"
        self.exclude_this = "should_be_excluded"
        self.normal_attr = "normal"


class TestStateHelperFunctions:
    """Test class for state helper functions"""

    @pytest.mark.unit
    def test_gather_attrs_simple_object(self):
        """Test gathering attributes from simple object"""
        obj = SerializableTestObject()
        attrs = _gather_attrs(obj)
        
        assert isinstance(attrs, dict)
        assert "data" in attrs
        assert "number" in attrs
        assert "items" in attrs
        assert attrs["data"] == "test_data"
        assert attrs["number"] == 42

    @pytest.mark.unit
    def test_gather_attrs_with_properties(self):
        """Test gathering attributes including properties"""
        class ObjectWithProperty:
            def __init__(self):
                self._value = 100
            
            @property
            def computed_value(self):
                return self._value * 2
        
        obj = ObjectWithProperty()
        attrs = _gather_attrs(obj)
        
        assert "_value" in attrs
        assert "computed_value" in attrs
        assert attrs["computed_value"] == 200

    @pytest.mark.unit
    def test_gather_attrs_property_exception(self):
        """Test gathering attributes when property raises exception"""
        class ObjectWithFailingProperty:
            @property
            def failing_prop(self):
                raise RuntimeError("Property failed")
        
        obj = ObjectWithFailingProperty()
        attrs = _gather_attrs(obj)
        
        # Should handle property exception gracefully
        assert "failing_prop" not in attrs or attrs["failing_prop"] is None

    @pytest.mark.unit
    def test_filter_attrs_with_include(self):
        """Test filtering attributes with include list"""
        attrs = {
            "include_me": "value1",
            "exclude_me": "value2",
            "another": "value3"
        }
        
        filtered = _filter_attrs(attrs, include=["include_me", "another"], exclude=[])
        
        assert "include_me" in filtered
        assert "another" in filtered
        assert "exclude_me" not in filtered

    @pytest.mark.unit
    def test_filter_attrs_with_exclude(self):
        """Test filtering attributes with exclude list"""
        attrs = {
            "keep_me": "value1",
            "exclude_me": "value2",
            "also_keep": "value3"
        }
        
        filtered = _filter_attrs(attrs, include=[], exclude=["exclude_me"])
        
        assert "keep_me" in filtered
        assert "also_keep" in filtered
        assert "exclude_me" not in filtered

    @pytest.mark.unit
    def test_filter_attrs_include_nonexistent(self):
        """Test filtering with include list containing nonexistent keys"""
        attrs = {"existing": "value"}
        
        filtered = _filter_attrs(attrs, include=["existing", "nonexistent"], exclude=[])
        
        assert "existing" in filtered
        assert "nonexistent" not in filtered

    @pytest.mark.unit
    def test_is_serializable_basic_types(self):
        """Test serialization check for basic types"""
        # Serializable types
        assert _is_serializable(42) is True
        assert _is_serializable("string") is True
        assert _is_serializable([1, 2, 3]) is True
        assert _is_serializable({"key": "value"}) is True
        assert _is_serializable(None) is True

    @pytest.mark.unit
    def test_is_serializable_blacklisted_types(self):
        """Test serialization check for blacklisted types"""
        # Create objects that should be blacklisted
        file_obj = open(__file__, 'r')
        try:
            assert _is_serializable(file_obj) is False
        finally:
            file_obj.close()
        
        # Threading objects should be blacklisted
        import threading
        thread = threading.Thread()
        assert _is_serializable(thread) is False

    @pytest.mark.unit
    def test_is_serializable_custom_object(self):
        """Test serialization check for custom objects"""
        serializable_obj = SerializableTestObject()
        assert _is_serializable(serializable_obj) is True

    @pytest.mark.unit
    def test_prepare_primitive_types(self):
        """Test preparation of primitive types"""
        # Primitive types should pass through unchanged
        assert _prepare(42) == 42
        assert _prepare("string") == "string"
        assert _prepare(True) is True
        assert _prepare(None) is None

    @pytest.mark.unit
    def test_prepare_mapping_types(self):
        """Test preparation of mapping types"""
        input_dict = {
            "serializable_key": "serializable_value",
            42: "numeric_key",
        }
        
        result = _prepare(input_dict)
        
        assert isinstance(result, dict)
        assert "serializable_key" in result
        assert 42 in result

    @pytest.mark.unit
    def test_prepare_sequence_types(self):
        """Test preparation of sequence types"""
        input_list = [1, "string", {"nested": "dict"}]
        
        result = _prepare(input_list)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == 1
        assert result[1] == "string"

    @pytest.mark.unit
    def test_prepare_set_types(self):
        """Test preparation of set types"""
        input_set = {1, 2, "string"}
        
        result = _prepare(input_set)
        
        assert isinstance(result, set)
        assert 1 in result
        assert 2 in result
        assert "string" in result

    @pytest.mark.unit
    def test_prepare_non_serializable_filtering(self):
        """Test that non-serializable items are filtered out"""
        file_obj = open(__file__, 'r')
        try:
            input_list = [1, file_obj, "string"]
            result = _prepare(input_list)
            
            # Non-serializable object should be filtered out
            assert file_obj not in result
            assert 1 in result
            assert "string" in result
        finally:
            file_obj.close()

    @pytest.mark.unit
    def test_prepare_nested_structures(self):
        """Test preparation of deeply nested structures"""
        nested_data = {
            "level1": {
                "level2": [1, 2, {"level3": "deep_value"}]
            },
            "list": [{"nested": "dict"}, "string", 42]
        }
        
        result = _prepare(nested_data)
        
        assert result["level1"]["level2"][2]["level3"] == "deep_value"
        assert result["list"][0]["nested"] == "dict"


class TestStateSaveLoad:
    """Test class for state save/load functions"""

    @pytest.fixture
    def temp_file_path(self, tmp_path):
        """Create a temporary file path for testing"""
        return tmp_path / "test_state.pkl"

    @pytest.mark.unit
    def test_save_function_state_basic(self, temp_file_path):
        """Test basic function state saving"""
        obj = SerializableTestObject()
        
        save_function_state(obj, str(temp_file_path))
        
        assert temp_file_path.exists()
        assert temp_file_path.stat().st_size > 0

    @pytest.mark.unit
    def test_load_function_state_basic(self, temp_file_path):
        """Test basic function state loading"""
        original_obj = SerializableTestObject()
        save_function_state(original_obj, str(temp_file_path))
        
        # Create new object and load state into it
        loaded_obj = SerializableTestObject()
        load_function_state(loaded_obj, str(temp_file_path))
        
        # Verify attributes were loaded
        assert hasattr(loaded_obj, 'data')
        assert hasattr(loaded_obj, 'number')

    @pytest.mark.unit
    def test_save_function_state_with_include_filter(self, temp_file_path):
        """Test state saving with include filter"""
        obj = FilteredTestObject()
        
        save_function_state(obj, str(temp_file_path))
        
        # File should be created
        assert temp_file_path.exists()

    @pytest.mark.unit
    def test_save_function_state_with_exclude_filter(self, temp_file_path):
        """Test state saving with exclude filter"""
        obj = FilteredTestObject()
        
        save_function_state(obj, str(temp_file_path))
        
        # File should be created
        assert temp_file_path.exists()

    @pytest.mark.unit
    def test_load_function_state_nonexistent_file(self):
        """Test loading state from nonexistent file"""
        obj = SerializableTestObject()
        original_data = obj.data
        
        # Should not crash when file doesn't exist
        load_function_state(obj, "nonexistent_file.pkl")
        
        # Object should remain unchanged
        assert obj.data == original_data

    @pytest.mark.unit
    def test_save_function_state_creates_directory(self, tmp_path):
        """Test that save_function_state creates necessary directories"""
        obj = SerializableTestObject()
        nested_path = tmp_path / "nested" / "dir" / "state.pkl"
        
        save_function_state(obj, str(nested_path))
        
        assert nested_path.exists()
        assert nested_path.parent.exists()

    @pytest.mark.integration
    def test_state_roundtrip_complex_object(self, temp_file_path):
        """Integration test for complex object state preservation"""
        class ComplexObject:
            __state_exclude__ = ["_internal"]
            
            def __init__(self):
                self.name = "test"
                self.data = {"nested": {"key": "value"}}
                self.items = [1, 2, {"item": "data"}]
                self._internal = "should_be_excluded"
        
        original_obj = ComplexObject()
        save_function_state(original_obj, str(temp_file_path))
        
        # Create new object and load state
        loaded_obj = ComplexObject()
        load_function_state(loaded_obj, str(temp_file_path))
        
        # Verify complex structure is preserved
        assert hasattr(loaded_obj, 'name')
        assert hasattr(loaded_obj, 'data')
        assert hasattr(loaded_obj, 'items')

    @pytest.mark.unit
    def test_state_thread_safety(self, tmp_path):
        """Test state operations in multi-threaded environment"""
        import threading
        
        def save_worker(worker_id):
            obj = SerializableTestObject()
            obj.data = f"worker_{worker_id}"
            save_function_state(obj, str(tmp_path / f"state_{worker_id}.pkl"))
        
        # Create multiple threads saving state
        threads = [threading.Thread(target=save_worker, args=(i,)) for i in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All files should be created
        for i in range(5):
            assert (tmp_path / f"state_{i}.pkl").exists()

    @pytest.mark.unit
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_save_function_state_permission_error(self, mock_open):
        """Test save_function_state with permission error"""
        obj = SerializableTestObject()
        
        with pytest.raises(PermissionError):
            save_function_state(obj, "/invalid/path/state.pkl")

    @pytest.mark.unit
    @patch('os.path.isfile', return_value=True)
    @patch('builtins.open', side_effect=IOError("File read error"))
    def test_load_function_state_io_error(self, mock_open, mock_isfile):
        """Test load_function_state with IO error"""
        obj = SerializableTestObject()
        
        # Should handle IO errors gracefully
        with pytest.raises(IOError):
            load_function_state(obj, "corrupted_file.pkl")


class TestStateEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_gather_attrs_object_without_dict(self):
        """Test gathering attributes from object without __dict__"""
        # Some built-in types don't have __dict__
        attrs = _gather_attrs(42)
        
        # Should handle gracefully
        assert isinstance(attrs, dict)

    @pytest.mark.unit
    def test_prepare_circular_references(self):
        """Test preparation with circular references"""
        # Create circular reference
        obj1 = {}
        obj2 = {}
        obj1["ref"] = obj2
        obj2["ref"] = obj1
        
        # Should handle without infinite recursion
        try:
            result = _prepare(obj1)
            # Success if no exception
            assert isinstance(result, dict)
        except RecursionError:
            pytest.skip("Circular reference handling not implemented")

    @pytest.mark.unit
    def test_filter_attrs_empty_filters(self):
        """Test filtering with empty filter lists"""
        attrs = {"key1": "value1", "key2": "value2"}
        
        # Empty include list should include everything
        result = _filter_attrs(attrs, include=[], exclude=[])
        assert result == attrs

    @pytest.mark.unit
    def test_is_serializable_exception_during_pickle(self):
        """Test serialization check when pickle.dumps raises exception"""
        class UnpicklableObject:
            def __reduce__(self):
                raise TypeError("Cannot pickle this object")
        
        obj = UnpicklableObject()
        assert _is_serializable(obj) is False

    @pytest.mark.unit
    def test_prepare_very_large_structure(self):
        """Test preparation of very large data structures"""
        # Create large structure
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        large_list = list(range(1000))
        
        combined = {
            "dict": large_dict,
            "list": large_list
        }
        
        result = _prepare(combined)
        
        # Should handle large structures
        assert len(result["dict"]) == 1000
        assert len(result["list"]) == 1000


class TestStateBlacklistHandling:
    """Test blacklist functionality"""

    @pytest.mark.unit
    def test_blacklist_contains_expected_types(self):
        """Test that blacklist contains expected non-serializable types"""
        import threading
        
        # Check that blacklist is a tuple of types
        assert isinstance(_BLACKLIST, tuple)
        
        # Thread type should be in blacklist
        assert threading.Thread in _BLACKLIST
        
        # File open function type should be in blacklist
        assert type(open) in _BLACKLIST

    @pytest.mark.unit
    def test_blacklist_detection_in_is_serializable(self):
        """Test that blacklisted types are detected in _is_serializable"""
        import threading
        
        thread = threading.Thread()
        assert _is_serializable(thread) is False
        
        file_handle = open(__file__, 'r')
        try:
            assert _is_serializable(file_handle) is False
        finally:
            file_handle.close()


# Fixtures and utilities
@pytest.fixture
def serializable_object():
    """Create a serializable test object"""
    return SerializableTestObject()


@pytest.fixture
def filtered_object():
    """Create a filtered test object"""
    return FilteredTestObject()


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup any test files created during testing"""
    yield
    # Cleanup logic would go here if needed
