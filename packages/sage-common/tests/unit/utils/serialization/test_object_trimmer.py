"""
Tests for object trimmer functionality.

Tests the trim_object_for_remote function and ObjectTrimmer class.
"""

from unittest.mock import Mock


class TestTrimObjectForRemote:
    """Test trim_object_for_remote function"""

    def test_trim_simple_object(self):
        """Test trimming simple object"""
        from sage.common.utils.serialization.object_trimmer import trim_object_for_remote

        class SimpleObj:
            def __init__(self):
                self.value = 42
                self.name = "test"

        obj = SimpleObj()
        result = trim_object_for_remote(obj)

        assert hasattr(result, "value")
        assert hasattr(result, "name")

    def test_trim_with_exclude(self):
        """Test trimming with exclude list"""
        from sage.common.utils.serialization.object_trimmer import trim_object_for_remote

        class ObjWithPrivate:
            def __init__(self):
                self.public = "visible"
                self._private = "hidden"
                self.logger = "should_exclude"

        obj = ObjWithPrivate()
        result = trim_object_for_remote(obj, exclude=["logger", "_private"])

        assert hasattr(result, "public")
        # Excluded attributes should not be present
        assert not hasattr(result, "logger") or result.logger != "should_exclude"

    def test_trim_with_include(self):
        """Test trimming with include list"""
        from sage.common.utils.serialization.object_trimmer import trim_object_for_remote

        class ObjWithMany:
            def __init__(self):
                self.a = 1
                self.b = 2
                self.c = 3

        obj = ObjWithMany()
        result = trim_object_for_remote(obj, include=["a", "c"])

        assert hasattr(result, "a")
        assert hasattr(result, "c")
        # b should not be included
        assert not hasattr(result, "b") or result.b != 2

    def test_trim_nested_objects(self):
        """Test trimming nested objects"""
        from sage.common.utils.serialization.object_trimmer import trim_object_for_remote

        class Inner:
            def __init__(self):
                self.value = 100

        class Outer:
            def __init__(self):
                self.inner = Inner()
                self.name = "outer"

        obj = Outer()
        result = trim_object_for_remote(obj)

        assert hasattr(result, "name")
        assert hasattr(result, "inner")

    def test_trim_basic_types_unchanged(self):
        """Test that basic types pass through unchanged"""
        from sage.common.utils.serialization.object_trimmer import trim_object_for_remote

        assert trim_object_for_remote(42) == 42
        assert trim_object_for_remote("test") == "test"
        assert trim_object_for_remote([1, 2, 3]) == [1, 2, 3]
        assert trim_object_for_remote({"a": 1}) == {"a": 1}


class TestObjectTrimmer:
    """Test ObjectTrimmer class"""

    def test_trim_for_remote_call_basic(self):
        """Test basic trimming for remote call"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class SimpleObj:
            def __init__(self):
                self.value = 42

        obj = SimpleObj()
        result = ObjectTrimmer.trim_for_remote_call(obj)

        assert hasattr(result, "value")
        assert result.value == 42

    def test_trim_for_remote_call_with_exclude(self):
        """Test remote call trimming with exclusions"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class ObjWithLogger:
            def __init__(self):
                self.data = "important"
                self.logger = Mock()
                self._cache = {}

        obj = ObjWithLogger()
        result = ObjectTrimmer.trim_for_remote_call(obj, exclude=["logger", "_cache"])

        assert hasattr(result, "data")
        assert not hasattr(result, "logger") or result.logger != obj.logger

    def test_trim_for_remote_call_shallow(self):
        """Test shallow trimming (deep_clean=False)"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class Nested:
            def __init__(self):
                self.inner_value = 100

        class Outer:
            def __init__(self):
                self.value = 42
                self.nested = Nested()

        obj = Outer()
        result = ObjectTrimmer.trim_for_remote_call(obj, deep_clean=False)

        assert hasattr(result, "value")

    def test_trim_for_remote_call_deep(self):
        """Test deep trimming (deep_clean=True)"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class Inner:
            def __init__(self):
                self.inner_data = "deep"

        class Outer:
            def __init__(self):
                self.outer_data = "shallow"
                self.inner = Inner()

        obj = Outer()
        result = ObjectTrimmer.trim_for_remote_call(obj, deep_clean=True)

        assert hasattr(result, "outer_data")
        assert hasattr(result, "inner")

    def test_trim_handles_lists(self):
        """Test trimming objects containing lists"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class ObjWithList:
            def __init__(self):
                self.items = [1, 2, 3, 4, 5]

        obj = ObjWithList()
        result = ObjectTrimmer.trim_for_remote_call(obj)

        assert hasattr(result, "items")
        assert len(result.items) == 5

    def test_trim_handles_dicts(self):
        """Test trimming objects containing dicts"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class ObjWithDict:
            def __init__(self):
                self.config = {"key1": "value1", "key2": "value2"}

        obj = ObjWithDict()
        result = ObjectTrimmer.trim_for_remote_call(obj)

        assert hasattr(result, "config")
        assert isinstance(result.config, dict)

    def test_trim_preserves_basic_types(self):
        """Test that basic types are preserved"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        assert ObjectTrimmer.trim_for_remote_call(42) == 42
        assert ObjectTrimmer.trim_for_remote_call("text") == "text"
        assert ObjectTrimmer.trim_for_remote_call(3.14) == 3.14
        assert ObjectTrimmer.trim_for_remote_call(True) is True

    def test_trim_with_state_exclude_annotation(self):
        """Test trimming with __state_exclude__ class annotation"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class ObjWithAnnotation:
            __state_exclude__ = ["_internal"]

            def __init__(self):
                self.public = "visible"
                self._internal = "hidden"

        obj = ObjWithAnnotation()
        result = ObjectTrimmer.trim_for_remote_call(obj)

        assert hasattr(result, "public")
        # _internal should be excluded per __state_exclude__
        assert not hasattr(result, "_internal") or result._internal != "hidden"

    def test_trim_complex_nested_structure(self):
        """Test trimming complex nested structures"""
        from sage.common.utils.serialization.object_trimmer import ObjectTrimmer

        class Level3:
            def __init__(self):
                self.value = "level3"

        class Level2:
            def __init__(self):
                self.value = "level2"
                self.level3 = Level3()

        class Level1:
            def __init__(self):
                self.value = "level1"
                self.level2 = Level2()

        obj = Level1()
        result = ObjectTrimmer.trim_for_remote_call(obj, deep_clean=True)

        assert hasattr(result, "value")
        assert result.value == "level1"
        assert hasattr(result, "level2")
