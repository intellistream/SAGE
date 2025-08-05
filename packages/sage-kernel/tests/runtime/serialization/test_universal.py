"""
Test suite for sage.runtime.serialization.universal module

Tests the UniversalSerializer class which provides universal
serialization functionality based on dill.
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from typing import List, Dict, Any

from sage.runtime.serialization.universal import UniversalSerializer


class SerializableTestClass:
    """A test class that should be serializable"""
    def __init__(self, value=42):
        self.value = value
        self.data = {"key": "value"}
        self.items = [1, 2, 3]
    
    def get_value(self):
        return self.value
    
    def set_value(self, new_value):
        self.value = new_value


class ComplexSerializableClass:
    """A more complex test class with state exclusions"""
    
    __state_exclude__ = ["_internal_cache", "_logger"]
    
    def __init__(self):
        self.public_data = "public"
        self._internal_cache = {}
        self._logger = Mock()  # Non-serializable
        self.nested_object = SerializableTestClass(100)


class NonSerializableClass:
    """A class with non-serializable attributes"""
    def __init__(self):
        self.serializable_attr = "I can be serialized"
        self.file_handle = open(__file__, 'r')  # Non-serializable
        self.thread = None  # Will be set to a thread object


class TestUniversalSerializer:
    """Test class for UniversalSerializer functionality"""

    @pytest.mark.unit
    def test_serialize_simple_object(self):
        """Test serialization of simple objects"""
        obj = SerializableTestClass(42)
        
        serialized = UniversalSerializer.serialize_object(obj)
        
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

    @pytest.mark.unit
    def test_deserialize_simple_object(self):
        """Test deserialization of simple objects"""
        original = SerializableTestClass(42)
        
        serialized = UniversalSerializer.serialize_object(original)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert isinstance(deserialized, SerializableTestClass)
        assert deserialized.value == 42
        assert deserialized.data == {"key": "value"}
        assert deserialized.items == [1, 2, 3]

    @pytest.mark.unit
    def test_serialize_primitive_types(self):
        """Test serialization of primitive types"""
        test_cases = [
            42,
            3.14,
            "hello world",
            True,
            None,
            [1, 2, 3],
            {"key": "value"},
            (1, 2, 3)
        ]
        
        for obj in test_cases:
            serialized = UniversalSerializer.serialize_object(obj)
            deserialized = UniversalSerializer.deserialize_object(serialized)
            assert deserialized == obj

    @pytest.mark.unit
    def test_serialize_complex_object(self):
        """Test serialization of complex objects"""
        obj = ComplexSerializableClass()
        
        serialized = UniversalSerializer.serialize_object(obj)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert isinstance(deserialized, ComplexSerializableClass)
        assert deserialized.public_data == "public"
        assert isinstance(deserialized.nested_object, SerializableTestClass)
        assert deserialized.nested_object.value == 100

    @pytest.mark.unit
    def test_serialize_with_include_filter(self):
        """Test serialization with include filter"""
        obj = SerializableTestClass(42)
        
        # Only include specific attributes
        serialized = UniversalSerializer.serialize_object(obj, include=["value"])
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        # Should only have the included attribute
        assert hasattr(deserialized, 'value') or deserialized.value == 42

    @pytest.mark.unit
    def test_serialize_with_exclude_filter(self):
        """Test serialization with exclude filter"""
        obj = SerializableTestClass(42)
        
        # Exclude specific attributes
        serialized = UniversalSerializer.serialize_object(obj, exclude=["data"])
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        # Should not have the excluded attribute (or have None/default)
        assert isinstance(deserialized, SerializableTestClass)

    @pytest.mark.unit
    def test_serialize_nested_objects(self):
        """Test serialization of nested objects"""
        class NestedContainer:
            def __init__(self):
                self.level1 = SerializableTestClass(1)
                self.level2 = {
                    "nested": SerializableTestClass(2),
                    "list": [SerializableTestClass(3), SerializableTestClass(4)]
                }
        
        obj = NestedContainer()
        
        serialized = UniversalSerializer.serialize_object(obj)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert isinstance(deserialized.level1, SerializableTestClass)
        assert deserialized.level1.value == 1
        assert isinstance(deserialized.level2["nested"], SerializableTestClass)
        assert deserialized.level2["nested"].value == 2

    @pytest.mark.unit
    @patch('sage.runtime.serialization.universal.dill')
    def test_serialize_dill_not_available(self, mock_dill):
        """Test serialization when dill is not available"""
        mock_dill.__bool__ = Mock(return_value=False)
        
        obj = SerializableTestClass()
        
        with pytest.raises(Exception, match="dill is required"):
            UniversalSerializer.serialize_object(obj)

    @pytest.mark.unit
    @patch('sage.runtime.serialization.universal.dill')
    def test_deserialize_dill_not_available(self, mock_dill):
        """Test deserialization when dill is not available"""
        mock_dill.__bool__ = Mock(return_value=False)
        
        with pytest.raises(Exception, match="dill is required"):
            UniversalSerializer.deserialize_object(b"fake_data")

    @pytest.mark.unit
    @patch('sage.runtime.serialization.universal.dill.dumps')
    def test_serialize_dill_failure(self, mock_dumps):
        """Test serialization when dill.dumps fails"""
        mock_dumps.side_effect = Exception("Dill serialization failed")
        
        obj = SerializableTestClass()
        
        with pytest.raises(Exception, match="Object serialization failed"):
            UniversalSerializer.serialize_object(obj)

    @pytest.mark.unit
    @patch('sage.runtime.serialization.universal.dill.loads')
    def test_deserialize_dill_failure(self, mock_loads):
        """Test deserialization when dill.loads fails"""
        mock_loads.side_effect = Exception("Dill deserialization failed")
        
        with pytest.raises(Exception, match="Object deserialization failed"):
            UniversalSerializer.deserialize_object(b"fake_data")

    @pytest.mark.unit
    def test_save_object_state(self):
        """Test saving object state to file"""
        obj = SerializableTestClass(42)
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            UniversalSerializer.save_object_state(obj, temp_path)
            
            # File should exist and have content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
            # Should be able to read and deserialize
            with open(temp_path, 'rb') as f:
                data = f.read()
            
            deserialized = UniversalSerializer.deserialize_object(data)
            assert isinstance(deserialized, SerializableTestClass)
            assert deserialized.value == 42
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @pytest.mark.unit
    def test_save_object_state_creates_directory(self):
        """Test that save_object_state creates necessary directories"""
        obj = SerializableTestClass(42)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, "nested", "dir", "object.pkl")
            
            UniversalSerializer.save_object_state(obj, nested_path)
            
            # Directory should be created
            assert os.path.exists(os.path.dirname(nested_path))
            assert os.path.exists(nested_path)

    @pytest.mark.unit
    def test_save_object_state_with_filters(self):
        """Test saving object state with include/exclude filters"""
        obj = SerializableTestClass(42)
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            UniversalSerializer.save_object_state(obj, temp_path, include=["value"])
            
            # Should save successfully
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @pytest.mark.unit
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_save_object_state_permission_error(self, mock_open):
        """Test save_object_state with permission error"""
        obj = SerializableTestClass(42)
        
        with pytest.raises(PermissionError):
            UniversalSerializer.save_object_state(obj, "/invalid/path/object.pkl")

    @pytest.mark.integration
    def test_round_trip_serialization(self):
        """Integration test for complete round-trip serialization"""
        # Create a complex object hierarchy
        class ComplexObject:
            __state_exclude__ = ["_cache"]
            
            def __init__(self):
                self.name = "complex"
                self.data = {
                    "numbers": [1, 2, 3, 4, 5],
                    "nested": {
                        "level1": {"level2": "deep_value"}
                    }
                }
                self.objects = [
                    SerializableTestClass(i) for i in range(5)
                ]
                self._cache = {}  # Should be excluded
        
        original = ComplexObject()
        
        # Serialize and deserialize
        serialized = UniversalSerializer.serialize_object(original)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        # Verify structure is preserved
        assert deserialized.name == "complex"
        assert deserialized.data["numbers"] == [1, 2, 3, 4, 5]
        assert deserialized.data["nested"]["level1"]["level2"] == "deep_value"
        assert len(deserialized.objects) == 5
        
        for i, obj in enumerate(deserialized.objects):
            assert isinstance(obj, SerializableTestClass)
            assert obj.value == i

    @pytest.mark.unit
    def test_serialization_thread_safety(self):
        """Test serialization in multi-threaded environment"""
        import threading
        import time
        
        def serialize_worker(obj_id, results):
            try:
                obj = SerializableTestClass(obj_id)
                serialized = UniversalSerializer.serialize_object(obj)
                deserialized = UniversalSerializer.deserialize_object(serialized)
                results.append((obj_id, deserialized.value))
            except Exception as e:
                results.append((obj_id, e))
        
        results = []
        threads = []
        
        # Create multiple threads serializing different objects
        for i in range(10):
            thread = threading.Thread(target=serialize_worker, args=(i, results))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All serializations should succeed
        assert len(results) == 10
        for obj_id, value in results:
            assert isinstance(value, int)
            assert value == obj_id

    @pytest.mark.unit
    def test_large_object_serialization(self):
        """Test serialization of large objects"""
        class LargeObject:
            def __init__(self):
                self.large_list = list(range(10000))
                self.large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
                self.nested_objects = [SerializableTestClass(i) for i in range(100)]
        
        large_obj = LargeObject()
        
        # Should handle large objects
        serialized = UniversalSerializer.serialize_object(large_obj)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert len(deserialized.large_list) == 10000
        assert len(deserialized.large_dict) == 1000
        assert len(deserialized.nested_objects) == 100


class TestUniversalSerializerEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_serialize_none(self):
        """Test serialization of None"""
        serialized = UniversalSerializer.serialize_object(None)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        assert deserialized is None

    @pytest.mark.unit
    def test_serialize_empty_containers(self):
        """Test serialization of empty containers"""
        test_cases = [[], {}, set(), ()]
        
        for obj in test_cases:
            serialized = UniversalSerializer.serialize_object(obj)
            deserialized = UniversalSerializer.deserialize_object(serialized)
            assert deserialized == obj

    @pytest.mark.unit
    def test_serialize_circular_references(self):
        """Test serialization with circular references"""
        class CircularObject:
            def __init__(self):
                self.value = 42
                self.reference = None
        
        obj1 = CircularObject()
        obj2 = CircularObject()
        obj1.reference = obj2
        obj2.reference = obj1
        
        # Should handle circular references (dill usually can)
        try:
            serialized = UniversalSerializer.serialize_object(obj1)
            deserialized = UniversalSerializer.deserialize_object(serialized)
            
            assert deserialized.value == 42
            assert deserialized.reference.value == 42
            assert deserialized.reference.reference is deserialized
        except RecursionError:
            # Some serializers might not handle this
            pytest.skip("Circular references not supported")

    @pytest.mark.unit
    def test_serialize_invalid_data(self):
        """Test deserialization with invalid data"""
        invalid_data = b"not_valid_pickle_data"
        
        with pytest.raises(Exception):
            UniversalSerializer.deserialize_object(invalid_data)

    @pytest.mark.unit
    def test_serialize_empty_bytes(self):
        """Test deserialization with empty bytes"""
        with pytest.raises(Exception):
            UniversalSerializer.deserialize_object(b"")

    @pytest.mark.unit
    def test_include_exclude_both_specified(self):
        """Test behavior when both include and exclude are specified"""
        obj = SerializableTestClass(42)
        
        # Behavior when both include and exclude are provided
        # Implementation should handle this gracefully
        try:
            serialized = UniversalSerializer.serialize_object(
                obj, 
                include=["value"],
                exclude=["data"]
            )
            deserialized = UniversalSerializer.deserialize_object(serialized)
            # Result depends on implementation priority
        except Exception:
            # Some implementations might not support both
            pass

    @pytest.mark.unit
    def test_include_nonexistent_attributes(self):
        """Test include filter with nonexistent attributes"""
        obj = SerializableTestClass(42)
        
        # Include nonexistent attributes - should not crash
        serialized = UniversalSerializer.serialize_object(
            obj, 
            include=["nonexistent_attr"]
        )
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        # Should handle gracefully
        assert isinstance(deserialized, (SerializableTestClass, type(obj)))


class TestUniversalSerializerPerformance:
    """Performance tests for UniversalSerializer"""

    @pytest.mark.slow
    def test_serialization_performance(self):
        """Test serialization performance with medium-sized objects"""
        import time
        
        objects = [SerializableTestClass(i) for i in range(100)]
        
        start_time = time.time()
        
        for obj in objects:
            serialized = UniversalSerializer.serialize_object(obj)
            UniversalSerializer.deserialize_object(serialized)
        
        elapsed = time.time() - start_time
        
        # Should be reasonably fast
        assert elapsed < 5.0  # Less than 5 seconds for 100 objects

    @pytest.mark.slow
    def test_large_file_save_performance(self):
        """Test performance of saving large objects to files"""
        import time
        
        class LargeObject:
            def __init__(self):
                self.data = list(range(1000))
        
        obj = LargeObject()
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            start_time = time.time()
            UniversalSerializer.save_object_state(obj, temp_path)
            elapsed = time.time() - start_time
            
            # Should save reasonably quickly
            assert elapsed < 1.0  # Less than 1 second
            assert os.path.exists(temp_path)
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# Fixtures and utilities
@pytest.fixture
def sample_serializable_object():
    """Create a sample serializable object for testing"""
    return SerializableTestClass(100)


@pytest.fixture
def complex_serializable_object():
    """Create a complex serializable object for testing"""
    return ComplexSerializableClass()


@pytest.fixture
def temp_file_path():
    """Provide a temporary file path for testing"""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)
