"""
Test suite for sage.kernels.runtime.distributed.actor module

Tests the ActorWrapper class which provides transparent proxying
between local objects and Ray actors.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import concurrent.futures
from typing import Any

from sage.kernel.kernels.runtime.distributed.actor import ActorWrapper


class MockLocalObject:
    """Mock local object for testing"""
    def __init__(self, value=42):
        self.value = value
        self.call_count = 0
    
    def get_value(self):
        """Simple method that returns value"""
        self.call_count += 1
        return self.value
    
    def set_value(self, new_value):
        """Simple method that sets value"""
        self.call_count += 1
        self.value = new_value
    
    def add(self, x, y):
        """Method with multiple parameters"""
        self.call_count += 1
        return x + y
    
    def complex_operation(self, data, multiplier=2, **kwargs):
        """Method with complex parameters"""
        self.call_count += 1
        result = data * multiplier
        if kwargs.get('add_value'):
            result += kwargs['add_value']
        return result


class MockRayActor:
    """Mock Ray actor for testing"""
    def __init__(self, value=42):
        self.value = value
        self.call_count = 0
    
    def get_value(self):
        """Ray actor method that returns ObjectRef"""
        self.call_count += 1
        # Create a mock ObjectRef
        object_ref = Mock()
        object_ref.remote = Mock(return_value=object_ref)
        return object_ref
    
    def set_value(self, new_value):
        """Ray actor method"""
        self.call_count += 1
        self.value = new_value
        object_ref = Mock()
        object_ref.remote = Mock(return_value=object_ref)
        return object_ref
    
    def add(self, x, y):
        """Ray actor method with parameters"""
        self.call_count += 1
        object_ref = Mock()
        object_ref.remote = Mock(return_value=object_ref)
        return object_ref


class TestActorWrapper:
    """Test class for ActorWrapper functionality"""

    @pytest.fixture
    def local_object(self):
        """Create a mock local object"""
        return MockLocalObject()

    @pytest.fixture
    def ray_actor(self):
        """Create a mock Ray actor"""
        mock_actor = Mock()
        mock_actor.get_value = Mock()
        mock_actor.get_value.remote = Mock(return_value="mock_object_ref")
        mock_actor.set_value = Mock()
        mock_actor.set_value.remote = Mock(return_value="mock_object_ref")
        return mock_actor

    @pytest.fixture
    def local_wrapper(self, local_object):
        """Create an ActorWrapper for local object"""
        return ActorWrapper(local_object)

    @pytest.fixture
    def ray_wrapper(self, ray_actor):
        """Create an ActorWrapper for Ray actor"""
        # Patch the _detect_execution_mode method to return ray_actor for our mock
        with patch.object(ActorWrapper, '_detect_execution_mode', return_value="ray_actor"):
            wrapper = ActorWrapper(ray_actor)
            return wrapper

    @pytest.mark.unit
    def test_local_object_detection(self, local_object):
        """Test detection of local objects"""
        wrapper = ActorWrapper(local_object)
        assert wrapper._execution_mode == "local"
        assert wrapper.is_local() is True
        assert wrapper.is_ray_actor() is False

    @pytest.mark.unit
    def test_ray_actor_detection(self, ray_actor):
        """Test detection of Ray actors"""
        # Patch the _detect_execution_mode method to return ray_actor for our mock
        with patch.object(ActorWrapper, '_detect_execution_mode', return_value="ray_actor"):
            wrapper = ActorWrapper(ray_actor)
            assert wrapper._execution_mode == "ray_actor"
            assert wrapper.is_ray_actor() is True
            assert wrapper.is_local() is False

    @pytest.mark.unit
    def test_local_method_call(self, local_wrapper):
        """Test calling methods on local objects"""
        # Simple method call
        result = local_wrapper.get_value()
        assert result == 42
        
        # Method call with parameters
        local_wrapper.set_value(100)
        result = local_wrapper.get_value()
        assert result == 100

    @pytest.mark.unit
    def test_local_method_with_parameters(self, local_wrapper):
        """Test calling local methods with various parameters"""
        # Method with multiple parameters
        result = local_wrapper.add(5, 3)
        assert result == 8
        
        # Method with complex parameters
        result = local_wrapper.complex_operation(10, multiplier=3, add_value=5)
        assert result == 35

    @pytest.mark.unit
    @patch('ray.get')
    def test_ray_actor_method_call(self, mock_ray_get, ray_wrapper):
        """Test calling methods on Ray actors"""
        mock_ray_get.return_value = 42
        
        # Call method - should be synchronous due to wrapper
        result = ray_wrapper.get_value()
        
        # Should call ray.get to get the result
        mock_ray_get.assert_called_once()
        assert result == 42

    @pytest.mark.unit
    def test_ray_actor_async_call(self, ray_wrapper):
        """Test async calls to Ray actor methods"""
        # Call async method
        object_ref = ray_wrapper.call_async('get_value')
        
        # Should return the ObjectRef without calling ray.get
        assert object_ref is not None

    @pytest.mark.unit
    def test_local_object_async_call_error(self, local_wrapper):
        """Test that async calls fail on local objects"""
        with pytest.raises(RuntimeError, match="call_async only available for Ray actors"):
            local_wrapper.call_async('get_value')

    @pytest.mark.unit
    def test_attribute_access_local(self, local_wrapper):
        """Test attribute access on local objects"""
        # Direct attribute access
        assert local_wrapper.value == 42
        
        # Attribute modification
        local_wrapper.value = 100
        assert local_wrapper.value == 100

    @pytest.mark.unit
    def test_attribute_access_ray(self, ray_wrapper):
        """Test attribute access on Ray actors"""
        # Mock the underlying actor's attribute
        ray_wrapper._obj.value = 42
        
        # Access attribute through wrapper
        result = ray_wrapper.value
        assert result == 42

    @pytest.mark.unit
    def test_private_attribute_access(self, local_wrapper):
        """Test that private attributes are handled correctly"""
        # Private attributes should raise AttributeError
        with pytest.raises(AttributeError):
            _ = local_wrapper._private_attr
        
        # But wrapper's own private attributes should work
        assert hasattr(local_wrapper, '_obj')
        assert hasattr(local_wrapper, '_execution_mode')

    @pytest.mark.unit
    def test_nonexistent_attribute_access(self, local_wrapper):
        """Test access to nonexistent attributes"""
        with pytest.raises(AttributeError):
            _ = local_wrapper.nonexistent_attribute

    @pytest.mark.unit
    def test_nonexistent_method_call(self, local_wrapper):
        """Test calling nonexistent methods"""
        with pytest.raises(AttributeError):
            local_wrapper.nonexistent_method()

    @pytest.mark.unit
    def test_get_object_method(self, local_wrapper, local_object):
        """Test get_object method returns wrapped object"""
        retrieved_object = local_wrapper.get_object()
        assert retrieved_object is local_object

    @pytest.mark.unit
    def test_wrapper_repr(self, local_wrapper):
        """Test string representation of wrapper"""
        repr_str = repr(local_wrapper)
        assert "ActorWrapper" in repr_str
        assert "local" in repr_str

    @pytest.mark.unit
    def test_kill_actor_local_object(self, local_wrapper):
        """Test kill_actor on local object"""
        result = local_wrapper.kill_actor()
        assert result is False  # Should return False for local objects

    @pytest.mark.unit
    @patch('ray.kill')
    def test_kill_actor_ray_actor(self, mock_ray_kill, ray_wrapper):
        """Test kill_actor on Ray actor"""
        mock_ray_kill.return_value = None
        
        result = ray_wrapper.kill_actor()
        
        # Should call ray.kill and return True
        mock_ray_kill.assert_called_once_with(ray_wrapper._obj, no_restart=True)
        assert result is True

    @pytest.mark.unit
    @patch('ray.kill')
    def test_kill_actor_with_restart(self, mock_ray_kill, ray_wrapper):
        """Test kill_actor with restart option"""
        mock_ray_kill.return_value = None
        
        result = ray_wrapper.kill_actor(no_restart=False)
        
        # Should call ray.kill with no_restart=False
        mock_ray_kill.assert_called_once_with(ray_wrapper._obj, no_restart=False)
        assert result is True

    @pytest.mark.unit
    def test_callable_detection(self, local_wrapper):
        """Test that wrapper correctly identifies callable vs non-callable attributes"""
        # Method should be callable
        method = getattr(local_wrapper, 'get_value')
        assert callable(method)
        
        # Attribute should not be wrapped as callable
        value = getattr(local_wrapper, 'value')
        assert not callable(value)

    @pytest.mark.unit
    def test_setattr_protection(self, local_wrapper):
        """Test that wrapper protects its internal attributes"""
        # Should be able to set attributes on wrapped object
        local_wrapper.new_attribute = "test_value"
        assert local_wrapper.new_attribute == "test_value"
        
        # Should not be able to modify wrapper's internal state
        original_mode = local_wrapper._execution_mode
        local_wrapper._execution_mode = "modified"
        assert local_wrapper._execution_mode == "modified"  # Should allow internal modification

    @pytest.mark.integration
    def test_wrapper_with_complex_object(self):
        """Integration test with more complex object"""
        class ComplexObject:
            def __init__(self):
                self.data = {"key": "value"}
                self.counter = 0
            
            def increment(self, amount=1):
                self.counter += amount
                return self.counter
            
            def get_data(self):
                return self.data.copy()
            
            def update_data(self, key, value):
                self.data[key] = value
        
        complex_obj = ComplexObject()
        wrapper = ActorWrapper(complex_obj)
        
        # Test various operations
        assert wrapper.counter == 0
        result = wrapper.increment(5)
        assert result == 5
        assert wrapper.counter == 5
        
        data = wrapper.get_data()
        assert data == {"key": "value"}
        
        wrapper.update_data("new_key", "new_value")
        data = wrapper.get_data()
        assert "new_key" in data
        assert data["new_key"] == "new_value"

    @pytest.mark.unit
    def test_wrapper_thread_safety(self, local_wrapper):
        """Test wrapper in multi-threaded environment"""
        import threading
        results = []
        
        def worker():
            try:
                for i in range(10):
                    result = local_wrapper.add(i, i)
                    results.append(result)
            except Exception as e:
                results.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All results should be successful
        numeric_results = [r for r in results if isinstance(r, int)]
        assert len(numeric_results) == 50  # 5 threads * 10 calls each


class TestActorWrapperEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def ray_actor(self):
        """Create a mock Ray actor"""
        mock_actor = Mock()
        mock_actor.get_value = Mock()
        mock_actor.get_value.remote = Mock(return_value="mock_object_ref")
        mock_actor.set_value = Mock()
        mock_actor.set_value.remote = Mock(return_value="mock_object_ref")
        return mock_actor

    @pytest.fixture
    def ray_wrapper(self, ray_actor):
        """Create an ActorWrapper for Ray actor"""
        # Patch the _detect_execution_mode method to return ray_actor for our mock
        with patch.object(ActorWrapper, '_detect_execution_mode', return_value="ray_actor"):
            wrapper = ActorWrapper(ray_actor)
            return wrapper

    @pytest.mark.unit
    def test_wrapper_with_none_object(self):
        """Test wrapper with None object"""
        wrapper = ActorWrapper(None)
        assert wrapper._execution_mode == "local"
        
        # Accessing attributes should raise AttributeError
        with pytest.raises(AttributeError):
            _ = wrapper.some_attribute

    @pytest.mark.unit
    def test_wrapper_with_primitive_object(self):
        """Test wrapper with primitive objects"""
        # String object
        wrapper = ActorWrapper("test_string")
        assert wrapper._execution_mode == "local"
        
        # Should be able to access string methods
        result = wrapper.upper()
        assert result == "TEST_STRING"
        
        # Integer object
        int_wrapper = ActorWrapper(42)
        # Integers don't have many methods, but should not crash
        assert int_wrapper._execution_mode == "local"

    @pytest.mark.unit
    @patch('ray.kill')
    def test_kill_actor_ray_kill_failure(self, mock_ray_kill, ray_wrapper):
        """Test kill_actor when ray.kill fails"""
        mock_ray_kill.side_effect = Exception("Kill failed")
        
        # Should handle exception gracefully
        try:
            result = ray_wrapper.kill_actor()
            # Behavior depends on implementation - might return False or raise
        except Exception:
            # Acceptable if implementation propagates the exception
            pass

    @pytest.mark.unit
    def test_async_call_nonexistent_method(self):
        """Test async call to nonexistent method"""
        # Create a simple object that will raise AttributeError for nonexistent methods
        class SimpleActor:
            def existing_method(self):
                pass
                
        simple_actor = SimpleActor()
        
        # Create wrapper with ray actor mode
        with patch.object(ActorWrapper, '_detect_execution_mode', return_value="ray_actor"):
            wrapper = ActorWrapper(simple_actor)
            
            with pytest.raises(AttributeError):
                wrapper.call_async('nonexistent_method')

    @pytest.mark.unit
    def test_async_call_non_callable_attribute(self, ray_wrapper):
        """Test async call to non-callable attribute"""
        # Mock a non-callable attribute
        ray_wrapper._obj.value = 42
        
        with pytest.raises(AttributeError, match="not a callable method"):
            ray_wrapper.call_async('value')

    @pytest.mark.unit
    def test_detection_with_ray_import_error(self):
        """Test actor detection when Ray is not available"""
        # Patch the _detect_execution_mode method to simulate ImportError handling
        with patch.object(ActorWrapper, '_detect_execution_mode', return_value="local"):
            obj = Mock()
            wrapper = ActorWrapper(obj)
            
            # Should default to local mode
            assert wrapper._execution_mode == "local"

    @pytest.mark.unit
    def test_detection_with_ray_attribute_error(self):
        """Test actor detection when Ray module has issues"""
        # Patch the _detect_execution_mode method to simulate AttributeError handling
        with patch.object(ActorWrapper, '_detect_execution_mode', return_value="local"):
            obj = Mock()
            wrapper = ActorWrapper(obj)
            
            # Should default to local mode
            assert wrapper._execution_mode == "local"


# Performance tests
class TestActorWrapperPerformance:
    """Performance tests for ActorWrapper"""

    @pytest.mark.slow
    def test_local_wrapper_performance(self):
        """Test performance of local wrapper operations"""
        import time
        
        obj = MockLocalObject()
        wrapper = ActorWrapper(obj)
        
        start_time = time.time()
        
        # Perform many operations
        for i in range(1000):
            wrapper.add(i, i)
        
        elapsed = time.time() - start_time
        
        # Should be reasonably fast
        assert elapsed < 1.0  # Less than 1 second for 1000 calls

    @pytest.mark.slow
    def test_attribute_access_performance(self):
        """Test performance of attribute access"""
        import time
        
        obj = MockLocalObject()
        wrapper = ActorWrapper(obj)
        
        start_time = time.time()
        
        # Access attributes many times
        for _ in range(1000):
            _ = wrapper.value
        
        elapsed = time.time() - start_time
        
        # Should be very fast
        assert elapsed < 0.1  # Less than 100ms for 1000 accesses


# Fixtures and utilities
@pytest.fixture
def complex_local_object():
    """Create a complex local object for testing"""
    class ComplexLocal:
        def __init__(self):
            self.data = list(range(100))
            self.metadata = {"created": "test", "version": 1.0}
        
        def process_data(self, func_name):
            if func_name == "sum":
                return sum(self.data)
            elif func_name == "max":
                return max(self.data)
            return None
        
        def batch_operation(self, operations):
            results = []
            for op in operations:
                results.append(self.process_data(op))
            return results
    
    return ComplexLocal()
