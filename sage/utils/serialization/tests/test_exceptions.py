"""
测试 sage.utils.serialization.exceptions 模块
"""
import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sage.utils.serialization.exceptions import SerializationError


class TestSerializationError:
    """测试 SerializationError 异常类"""
    
    def test_serialization_error_creation(self):
        """测试异常创建"""
        error = SerializationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_serialization_error_inheritance(self):
        """测试异常继承关系"""
        error = SerializationError("Test")
        assert isinstance(error, Exception)
        assert issubclass(SerializationError, Exception)
    
    def test_serialization_error_with_empty_message(self):
        """测试空消息异常"""
        error = SerializationError("")
        assert str(error) == ""
    
    def test_serialization_error_with_none_message(self):
        """测试 None 消息异常"""
        error = SerializationError(None)
        assert str(error) == "None"
    
    def test_serialization_error_raising(self):
        """测试异常抛出"""
        with pytest.raises(SerializationError) as exc_info:
            raise SerializationError("Test exception raising")
        
        assert str(exc_info.value) == "Test exception raising"
    
    def test_serialization_error_catching(self):
        """测试异常捕获"""
        try:
            raise SerializationError("Catch test")
        except SerializationError as e:
            assert str(e) == "Catch test"
        except Exception:
            pytest.fail("Should catch SerializationError specifically")


if __name__ == "__main__":
    pytest.main([__file__])
