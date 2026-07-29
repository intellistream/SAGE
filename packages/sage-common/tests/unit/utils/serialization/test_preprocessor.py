"""
Tests for serialization preprocessor functions.

Tests the preprocessing functions used for dill serialization.
"""


class TestGatherAttrs:
    """Test gather_attrs function"""

    def test_gather_simple_object_attrs(self):
        """Test gathering attributes from simple object"""
        from sage.common.utils.serialization.preprocessor import gather_attrs

        class SimpleObj:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        obj = SimpleObj()
        attrs = gather_attrs(obj)

        assert "attr1" in attrs
        assert attrs["attr1"] == "value1"
        assert "attr2" in attrs
        assert attrs["attr2"] == 42

    def test_gather_attrs_with_property(self):
        """Test gathering @property attributes"""
        from sage.common.utils.serialization.preprocessor import gather_attrs

        class ObjWithProperty:
            def __init__(self):
                self._value = 100

            @property
            def computed(self):
                return self._value * 2

        obj = ObjWithProperty()
        attrs = gather_attrs(obj)

        assert "_value" in attrs
        assert "computed" in attrs
        assert attrs["computed"] == 200

    def test_gather_attrs_property_exception(self):
        """Test handling property that raises exception"""
        from sage.common.utils.serialization.preprocessor import gather_attrs

        class ObjWithFailingProperty:
            @property
            def failing(self):
                raise ValueError("Property error")

        obj = ObjWithFailingProperty()
        attrs = gather_attrs(obj)

        # Should not raise, property just won't be included
        assert "failing" not in attrs or attrs.get("failing") is None


class TestFilterAttrs:
    """Test filter_attrs function"""

    def test_filter_with_include(self):
        """Test filtering with include list"""
        from sage.common.utils.serialization.preprocessor import filter_attrs

        attrs = {"a": 1, "b": 2, "c": 3, "_private": 4}
        filtered = filter_attrs(attrs, include=["a", "c"], exclude=None)

        assert filtered == {"a": 1, "c": 3}

    def test_filter_with_exclude(self):
        """Test filtering with exclude list"""
        from sage.common.utils.serialization.preprocessor import filter_attrs

        attrs = {"a": 1, "b": 2, "c": 3}
        filtered = filter_attrs(attrs, include=None, exclude=["b"])

        assert "a" in filtered
        assert "b" not in filtered
        assert "c" in filtered

    def test_filter_removes_weakref(self):
        """Test that __weakref__ is always filtered out"""
        from sage.common.utils.serialization.preprocessor import filter_attrs

        attrs = {"a": 1, "__weakref__": "something"}
        filtered = filter_attrs(attrs, include=None, exclude=None)

        assert "__weakref__" not in filtered
        assert "a" in filtered

    def test_filter_removes_dict_and_class(self):
        """Test that __dict__ and __class__ are filtered"""
        from sage.common.utils.serialization.preprocessor import filter_attrs

        attrs = {"a": 1, "__dict__": {}, "__class__": object}
        filtered = filter_attrs(attrs, include=None, exclude=None)

        assert "__dict__" not in filtered
        assert "__class__" not in filtered


class TestShouldSkip:
    """Test should_skip function"""

    def test_skip_basic_types(self):
        """Test that basic types are not skipped"""
        from sage.common.utils.serialization.preprocessor import should_skip

        assert not should_skip(42)
        assert not should_skip("string")
        assert not should_skip(3.14)
        assert not should_skip(True)
        assert not should_skip(None)

    def test_skip_module(self):
        """Test that modules are skipped"""
        import os

        from sage.common.utils.serialization.preprocessor import should_skip

        assert should_skip(os)

    def test_skip_lock_types(self):
        """Test that lock types are skipped"""
        import threading

        from sage.common.utils.serialization.preprocessor import should_skip

        lock = threading.Lock()
        assert should_skip(lock)


class TestHasCircularReference:
    """Test has_circular_reference function"""

    def test_no_circular_ref_basic_types(self):
        """Test basic types have no circular reference"""
        from sage.common.utils.serialization.preprocessor import has_circular_reference

        assert not has_circular_reference(42)
        assert not has_circular_reference("string")
        assert not has_circular_reference([1, 2, 3])
        assert not has_circular_reference({"a": 1, "b": 2})

    def test_detect_simple_circular_ref(self):
        """Test detection of simple circular reference"""
        from sage.common.utils.serialization.preprocessor import has_circular_reference

        obj = {}
        obj["self"] = obj

        assert has_circular_reference(obj)

    def test_detect_nested_circular_ref(self):
        """Test detection of nested circular reference"""
        from sage.common.utils.serialization.preprocessor import has_circular_reference

        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2

        assert has_circular_reference(obj1)

    def test_max_depth_prevents_deep_recursion(self):
        """Test that max_depth prevents excessive recursion"""
        from sage.common.utils.serialization.preprocessor import has_circular_reference

        # Create deeply nested structure without circular ref
        obj = {"level": 0}
        current = obj
        for i in range(20):
            current["next"] = {"level": i + 1}
            current = current["next"]

        # Should return False with default max_depth=10
        result = has_circular_reference(obj, max_depth=5)
        assert isinstance(result, bool)  # Should not crash


class TestPreprocessForDill:
    """Test preprocess_for_dill function"""

    def test_preprocess_basic_types(self):
        """Test preprocessing basic types"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        assert preprocess_for_dill(42) == 42
        assert preprocess_for_dill("test") == "test"
        assert preprocess_for_dill(3.14) == 3.14
        assert preprocess_for_dill(True) is True
        assert preprocess_for_dill(None) is None

    def test_preprocess_list(self):
        """Test preprocessing lists"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        result = preprocess_for_dill([1, 2, 3, "test"])
        assert result == [1, 2, 3, "test"]

    def test_preprocess_dict(self):
        """Test preprocessing dictionaries"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        data = {"a": 1, "b": "test", "c": [1, 2, 3]}
        result = preprocess_for_dill(data)

        assert result["a"] == 1
        assert result["b"] == "test"
        assert result["c"] == [1, 2, 3]

    def test_preprocess_nested_structure(self):
        """Test preprocessing nested structures"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        data = {"level1": {"level2": {"level3": {"value": 42}}}}

        result = preprocess_for_dill(data)
        assert result["level1"]["level2"]["level3"]["value"] == 42

    def test_preprocess_tuple(self):
        """Test that tuples are preserved"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        data = (1, 2, 3)
        result = preprocess_for_dill(data)

        assert isinstance(result, tuple)
        assert result == (1, 2, 3)

    def test_preprocess_set(self):
        """Test preprocessing sets"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        data = {1, 2, 3}
        result = preprocess_for_dill(data)

        assert isinstance(result, set)
        assert result == {1, 2, 3}

    def test_preprocess_custom_object(self):
        """Test preprocessing custom objects"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        class CustomObj:
            def __init__(self):
                self.value = 42
                self.name = "test"

        obj = CustomObj()
        result = preprocess_for_dill(obj)

        assert isinstance(result, CustomObj)
        assert result.value == 42
        assert result.name == "test"

    def test_preprocess_object_with_custom_exclude(self):
        """Test preprocessing with __state_exclude__"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        class ObjWithExclude:
            __state_exclude__ = ["_private"]

            def __init__(self):
                self.public = "visible"
                self._private = "hidden"

        obj = ObjWithExclude()
        result = preprocess_for_dill(obj)

        assert hasattr(result, "public")
        assert result.public == "visible"
        # _private should be excluded
        assert not hasattr(result, "_private") or result._private != "hidden"

    def test_preprocess_function(self):
        """Test that functions pass through"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        def test_func():
            return 42

        result = preprocess_for_dill(test_func)
        assert result is test_func

    def test_preprocess_class(self):
        """Test that classes pass through"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        class TestClass:
            pass

        result = preprocess_for_dill(TestClass)
        assert result is TestClass

    def test_preprocess_circular_ref_returns_original(self):
        """Test that objects with circular refs return original"""
        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        class CircularObj:
            def __init__(self):
                self.ref = self

        obj = CircularObj()
        result = preprocess_for_dill(obj)

        # Should return original object (let dill handle it)
        assert result is obj

    def test_preprocess_skips_blacklisted_values(self):
        """Test that blacklisted values are skipped"""
        import threading

        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        data = {"valid": 42, "lock": threading.Lock()}

        result = preprocess_for_dill(data)

        assert "valid" in result
        assert result["valid"] == 42
        # Lock should be skipped
        assert "lock" not in result

    def test_preprocess_list_with_skipped_items(self):
        """Test list preprocessing with items to skip"""
        import threading

        from sage.common.utils.serialization.preprocessor import preprocess_for_dill

        data = [1, 2, threading.Lock(), 3]
        result = preprocess_for_dill(data)

        # Should have 1, 2, 3 but not the lock
        assert 1 in result
        assert 2 in result
        assert 3 in result
        assert len(result) == 3  # Lock was removed


class TestPostprocessFromDill:
    """Test postprocess_from_dill function"""

    def test_postprocess_basic_types(self):
        """Test postprocessing basic types"""
        from sage.common.utils.serialization.preprocessor import postprocess_from_dill

        assert postprocess_from_dill(42) == 42
        assert postprocess_from_dill("test") == "test"
        assert postprocess_from_dill([1, 2, 3]) == [1, 2, 3]

    def test_postprocess_dict(self):
        """Test postprocessing dictionaries"""
        from sage.common.utils.serialization.preprocessor import postprocess_from_dill

        data = {"a": 1, "b": 2}
        result = postprocess_from_dill(data)

        assert result == {"a": 1, "b": 2}

    def test_postprocess_nested(self):
        """Test postprocessing nested structures"""
        from sage.common.utils.serialization.preprocessor import postprocess_from_dill

        data = {"outer": {"inner": [1, 2, 3]}}

        result = postprocess_from_dill(data)
        assert result["outer"]["inner"] == [1, 2, 3]
