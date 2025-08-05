"""
测试 sage.utils.serialization.preprocessor 模块
"""
import pytest
import sys
import os
import threading
import inspect
from unittest.mock import Mock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sage.utils.serialization.preprocessor import (
    gather_attrs,
    filter_attrs,
    should_skip,
    preprocess_for_dill,
    postprocess_from_dill
)
from sage.utils.serialization.config import SKIP_VALUE, ATTRIBUTE_BLACKLIST


class TestGatherAttrs:
    """测试 gather_attrs 函数"""
    
    def test_gather_simple_attrs(self):
        """测试收集简单属性"""
        class SimpleClass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42
        
        obj = SimpleClass()
        attrs = gather_attrs(obj)
        
        assert 'attr1' in attrs
        assert 'attr2' in attrs
        assert attrs['attr1'] == "value1"
        assert attrs['attr2'] == 42
    
    def test_gather_property_attrs(self):
        """测试收集 property 属性"""
        class PropertyClass:
            def __init__(self):
                self._value = "hidden"
            
            @property
            def computed_value(self):
                return self._value.upper()
        
        obj = PropertyClass()
        attrs = gather_attrs(obj)
        
        assert '_value' in attrs
        assert 'computed_value' in attrs
        assert attrs['computed_value'] == "HIDDEN"
    
    def test_gather_attrs_with_failing_property(self):
        """测试收集有异常的 property 属性"""
        class FailingPropertyClass:
            @property
            def failing_prop(self):
                raise ValueError("Property failed")
            
            def __init__(self):
                self.safe_attr = "safe"
        
        obj = FailingPropertyClass()
        attrs = gather_attrs(obj)
        
        # 失败的 property 应该被忽略
        assert 'failing_prop' not in attrs
        assert 'safe_attr' in attrs
    
    def test_gather_attrs_no_dict(self):
        """测试没有 __dict__ 的对象"""
        # 使用内置类型，它们没有 __dict__
        attrs = gather_attrs(42)
        assert attrs == {}
        
        attrs = gather_attrs("string")
        assert attrs == {}
    
    def test_gather_attrs_empty_dict(self):
        """测试空 __dict__ 的对象"""
        class EmptyClass:
            pass
        
        obj = EmptyClass()
        attrs = gather_attrs(obj)
        assert attrs == {}


class TestFilterAttrs:
    """测试 filter_attrs 函数"""
    
    def test_filter_with_include_list(self):
        """测试使用 include 列表过滤"""
        attrs = {
            'keep1': 'value1',
            'keep2': 'value2',
            'remove': 'value3'
        }
        
        filtered = filter_attrs(attrs, include=['keep1', 'keep2'], exclude=None)
        
        assert 'keep1' in filtered
        assert 'keep2' in filtered
        assert 'remove' not in filtered
    
    def test_filter_with_exclude_list(self):
        """测试使用 exclude 列表过滤"""
        attrs = {
            'keep1': 'value1',
            'keep2': 'value2',
            'logger': 'should_be_removed',
            'custom_exclude': 'also_removed'
        }
        
        filtered = filter_attrs(attrs, include=None, exclude=['custom_exclude'])
        
        assert 'keep1' in filtered
        assert 'keep2' in filtered
        assert 'logger' not in filtered  # 系统默认排除
        assert 'custom_exclude' not in filtered  # 用户自定义排除
    
    def test_filter_include_overrides_exclude(self):
        """测试 include 覆盖 exclude"""
        attrs = {
            'keep': 'value1',
            'logger': 'normally_excluded',
            'remove': 'value3'
        }
        
        # 当指定 include 时，只保留 include 中的属性
        filtered = filter_attrs(attrs, include=['keep', 'logger'], exclude=None)
        
        assert 'keep' in filtered
        assert 'logger' in filtered  # 即使在黑名单中，也被 include
        assert 'remove' not in filtered
    
    def test_filter_with_default_blacklist(self):
        """测试默认黑名单过滤"""
        attrs = {}
        for attr in ATTRIBUTE_BLACKLIST:
            attrs[attr] = f"value_for_{attr}"
        attrs['safe_attr'] = 'safe_value'
        
        filtered = filter_attrs(attrs, include=None, exclude=None)
        
        # 所有黑名单属性都应该被过滤掉
        for attr in ATTRIBUTE_BLACKLIST:
            assert attr not in filtered
        
        # 安全属性应该保留
        assert 'safe_attr' in filtered
    
    def test_filter_empty_attrs(self):
        """测试空属性字典"""
        filtered = filter_attrs({}, include=None, exclude=None)
        assert filtered == {}
    
    def test_filter_nonexistent_include(self):
        """测试包含不存在的属性"""
        attrs = {'existing': 'value'}
        filtered = filter_attrs(attrs, include=['existing', 'nonexistent'], exclude=None)
        
        assert 'existing' in filtered
        assert 'nonexistent' not in filtered
        assert len(filtered) == 1


class TestShouldSkip:
    """测试 should_skip 函数"""
    
    def test_skip_blacklisted_types(self):
        """测试跳过黑名单类型"""
        # 测试线程对象
        thread = threading.Thread(target=lambda: None)
        assert should_skip(thread) is True
        
        # 测试事件对象
        event = threading.Event()
        assert should_skip(event) is True
        
        # 测试锁对象
        lock = threading.Lock()
        assert should_skip(lock) is True
    
    def test_skip_modules(self):
        """测试跳过模块"""
        import math
        assert should_skip(math) is True
        
        import os
        assert should_skip(os) is True
    
    def test_dont_skip_safe_types(self):
        """测试不跳过安全类型"""
        # 基本类型
        assert should_skip(42) is False
        assert should_skip("string") is False
        assert should_skip([1, 2, 3]) is False
        assert should_skip({"key": "value"}) is False
        assert should_skip(None) is False
        assert should_skip(True) is False
        
        # 用户定义的类
        class SafeClass:
            pass
        
        obj = SafeClass()
        assert should_skip(obj) is False
    
    def test_skip_file_handles(self):
        """测试跳过文件句柄"""
        import tempfile
        
        with tempfile.NamedTemporaryFile() as tmp_file:
            assert should_skip(tmp_file) is True


class TestPreprocessForDill:
    """测试 preprocess_for_dill 函数"""
    
    def test_preprocess_basic_types(self):
        """测试预处理基本类型"""
        # 基本类型应该直接返回
        assert preprocess_for_dill(42) == 42
        assert preprocess_for_dill("string") == "string"
        assert preprocess_for_dill(True) is True
        assert preprocess_for_dill(None) is None
        assert preprocess_for_dill(3.14) == 3.14
    
    def test_preprocess_classes_and_functions(self):
        """测试预处理类和函数"""
        # 类对象应该直接返回
        class TestClass:
            pass
        
        assert preprocess_for_dill(TestClass) is TestClass
        
        # 函数应该直接返回
        def test_func():
            pass
        
        assert preprocess_for_dill(test_func) is test_func
    
    def test_preprocess_skip_blacklisted(self):
        """测试预处理跳过黑名单对象"""
        thread = threading.Thread(target=lambda: None)
        result = preprocess_for_dill(thread)
        assert result is SKIP_VALUE
    
    def test_preprocess_dictionary(self):
        """测试预处理字典"""
        original = {
            'safe_key': 'safe_value',
            'number': 42,
            'nested': {'inner': 'value'}
        }
        
        result = preprocess_for_dill(original)
        
        assert isinstance(result, dict)
        assert result['safe_key'] == 'safe_value'
        assert result['number'] == 42
        assert result['nested']['inner'] == 'value'
    
    def test_preprocess_dictionary_with_blacklisted(self):
        """测试预处理包含黑名单项的字典"""
        thread = threading.Thread(target=lambda: None)
        original = {
            'safe': 'value',
            'thread': thread  # 应该被跳过
        }
        
        result = preprocess_for_dill(original)
        
        assert isinstance(result, dict)
        assert result['safe'] == 'value'
        assert 'thread' not in result  # 黑名单项应该被移除
    
    def test_preprocess_list(self):
        """测试预处理列表"""
        original = [1, 2, 'string', {'nested': 'dict'}]
        result = preprocess_for_dill(original)
        
        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0] == 1
        assert result[3]['nested'] == 'dict'
    
    def test_preprocess_list_with_blacklisted(self):
        """测试预处理包含黑名单项的列表"""
        thread = threading.Thread(target=lambda: None)
        original = [1, thread, 'safe']
        
        result = preprocess_for_dill(original)
        
        assert isinstance(result, list)
        assert len(result) == 2  # thread 被移除
        assert 1 in result
        assert 'safe' in result
    
    def test_preprocess_set(self):
        """测试预处理集合"""
        original = {1, 2, 'string'}
        result = preprocess_for_dill(original)
        
        assert isinstance(result, set)
        assert 1 in result
        assert 'string' in result
    
    def test_preprocess_complex_object(self):
        """测试预处理复杂对象"""
        class ComplexClass:
            def __init__(self):
                self.safe_attr = "safe"
                self.logger = "fake_logger"  # 会被过滤
                self.data = [1, 2, 3]
        
        obj = ComplexClass()
        result = preprocess_for_dill(obj)
        
        assert isinstance(result, ComplexClass)
        assert hasattr(result, 'safe_attr')
        assert hasattr(result, 'data')
        assert not hasattr(result, 'logger')  # 应该被过滤
    
    def test_preprocess_circular_reference(self):
        """测试预处理循环引用"""
        class Node:
            def __init__(self, value):
                self.value = value
                self.parent = None
                self.children = []
        
        # 创建循环引用
        parent = Node("parent")
        child = Node("child")
        parent.children.append(child)
        child.parent = parent
        
        result = preprocess_for_dill(parent)
        
        # 应该能处理循环引用而不崩溃
        assert result is not None
        assert hasattr(result, 'value')
    
    def test_preprocess_object_with_custom_exclude(self):
        """测试预处理有自定义排除配置的对象"""
        class CustomExcludeClass:
            __state_exclude__ = ['custom_exclude']
            
            def __init__(self):
                self.keep_this = "keep"
                self.custom_exclude = "exclude"
                self.also_keep = "also_keep"
        
        obj = CustomExcludeClass()
        result = preprocess_for_dill(obj)
        
        assert hasattr(result, 'keep_this')
        assert hasattr(result, 'also_keep')
        assert not hasattr(result, 'custom_exclude')


class TestPostprocessFromDill:
    """测试 postprocess_from_dill 函数"""
    
    def test_postprocess_basic_types(self):
        """测试后处理基本类型"""
        assert postprocess_from_dill(42) == 42
        assert postprocess_from_dill("string") == "string"
        assert postprocess_from_dill(None) is None
    
    def test_postprocess_skip_value(self):
        """测试后处理 SKIP_VALUE"""
        result = postprocess_from_dill(SKIP_VALUE)
        assert result is None
    
    def test_postprocess_dictionary(self):
        """测试后处理字典"""
        original = {
            'key1': 'value1',
            'key2': SKIP_VALUE,  # 应该被过滤
            'key3': 'value3'
        }
        
        result = postprocess_from_dill(original)
        
        assert isinstance(result, dict)
        assert result['key1'] == 'value1'
        assert result['key3'] == 'value3'
        assert 'key2' not in result  # SKIP_VALUE 项应该被移除
    
    def test_postprocess_list(self):
        """测试后处理列表"""
        original = [1, SKIP_VALUE, 'keep', SKIP_VALUE, 3]
        result = postprocess_from_dill(original)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert 1 in result
        assert 'keep' in result
        assert 3 in result
    
    def test_postprocess_set(self):
        """测试后处理集合"""
        original = {1, SKIP_VALUE, 'keep'}
        result = postprocess_from_dill(original)
        
        assert isinstance(result, set)
        assert 1 in result
        assert 'keep' in result
        # SKIP_VALUE 应该被转换为 None，但 None 不会加入集合
    
    def test_postprocess_complex_object(self):
        """测试后处理复杂对象"""
        class TestClass:
            def __init__(self):
                self.keep_attr = "keep"
                self.skip_attr = SKIP_VALUE
        
        obj = TestClass()
        result = postprocess_from_dill(obj)
        
        assert hasattr(result, 'keep_attr')
        assert not hasattr(result, 'skip_attr')  # SKIP_VALUE 属性应该被删除
    
    def test_postprocess_nested_structures(self):
        """测试后处理嵌套结构"""
        original = {
            'list': [1, SKIP_VALUE, 'keep'],
            'dict': {'keep': 'value', 'skip': SKIP_VALUE},
            'skip_key': SKIP_VALUE
        }
        
        result = postprocess_from_dill(original)
        
        assert 'list' in result
        assert 'dict' in result
        assert 'skip_key' not in result
        
        assert len(result['list']) == 2
        assert 'skip' not in result['dict']


class TestIntegrationPreprocessPostprocess:
    """测试预处理和后处理的集成"""
    
    def test_round_trip_consistency(self):
        """测试往返一致性"""
        original = {
            'string': 'value',
            'number': 42,
            'list': [1, 2, 3],
            'nested': {'inner': 'value'}
        }
        
        # 预处理然后后处理
        preprocessed = preprocess_for_dill(original)
        postprocessed = postprocess_from_dill(preprocessed)
        
        assert postprocessed == original
    
    def test_round_trip_with_filtering(self):
        """测试带过滤的往返"""
        import threading
        
        class TestClass:
            def __init__(self):
                self.keep = "keep_value"
                self.logger = "should_be_filtered"
                self.thread = threading.Thread(target=lambda: None)
        
        obj = TestClass()
        
        # 预处理和后处理
        preprocessed = preprocess_for_dill(obj)
        postprocessed = postprocess_from_dill(preprocessed)
        
        # 检查过滤效果
        assert hasattr(postprocessed, 'keep')
        assert not hasattr(postprocessed, 'logger')
        assert not hasattr(postprocessed, 'thread')


if __name__ == "__main__":
    pytest.main([__file__])
