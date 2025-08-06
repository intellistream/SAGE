"""
通用序列化器 - 基于dill的通用序列化功能
"""
import os
import dill
from typing import Any, List, Optional

from .exceptions import SerializationError
from .preprocessor import preprocess_for_dill, postprocess_from_dill, gather_attrs, filter_attrs


class UniversalSerializer:
    """基于dill的通用序列化器，预处理清理不可序列化内容"""
    
    @staticmethod
    def serialize_object(obj: Any, 
                        include: Optional[List[str]] = None,
                        exclude: Optional[List[str]] = None) -> bytes:
        """
        序列化任意对象
        
        Args:
            obj: 要序列化的对象
            include: 包含的属性列表
            exclude: 排除的属性列表
            
        Returns:
            序列化后的字节数据
        """
        if not dill:
            raise SerializationError("dill is required for serialization. Install with: pip install dill")
        
        try:
            # 预处理对象，清理不可序列化的内容
            # 注意：include/exclude 参数通过对象的 __state_include__/__state_exclude__ 属性处理
            # 或者需要在预处理前应用这些过滤器
            if include or exclude:
                # 如果有自定义的 include/exclude，需要特殊处理
                if hasattr(obj, '__dict__'):
                    # 创建一个临时对象来应用过滤器
                    obj_class = type(obj)
                    try:
                        temp_obj = obj_class.__new__(obj_class)
                        attrs = gather_attrs(obj)
                        filtered_attrs = filter_attrs(attrs, include, exclude)
                        
                        for attr_name, attr_value in filtered_attrs.items():
                            try:
                                setattr(temp_obj, attr_name, attr_value)
                            except Exception:
                                pass
                        obj = temp_obj
                    except Exception:
                        # 如果无法创建临时对象，使用原对象
                        pass
            
            cleaned_obj = preprocess_for_dill(obj)
            
            # 使用dill序列化
            return dill.dumps(cleaned_obj)
            
        except Exception as e:
            raise SerializationError(f"Object serialization failed: {e}")
    
    @staticmethod
    def deserialize_object(data: bytes) -> Any:
        """
        反序列化对象
        
        Args:
            data: 序列化的字节数据
            
        Returns:
            反序列化后的对象
        """
        if not dill:
            raise SerializationError("dill is required for deserialization. Install with: pip install dill")
        
        try:
            # 使用dill反序列化
            obj = dill.loads(data)
            
            # 后处理对象，清理哨兵值
            return postprocess_from_dill(obj)
            
        except Exception as e:
            raise SerializationError(f"Object deserialization failed: {e}")
    
    @staticmethod
    def save_object_state(obj: Any, path: str,
                         include: Optional[List[str]] = None,
                         exclude: Optional[List[str]] = None):
        """将对象状态保存到文件"""
        serialized_data = UniversalSerializer.serialize_object(obj, include, exclude)
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(serialized_data)
    
    @staticmethod
    def load_object_from_file(path: str) -> Any:
        """从文件加载对象"""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(path, 'rb') as f:
            data = f.read()
        
        return UniversalSerializer.deserialize_object(data)
    
    @staticmethod
    def load_object_state(obj: Any, path: str) -> bool:
        """从文件加载对象状态到现有对象"""
        if not os.path.isfile(path):
            return False
        
        try:
            # 加载序列化的对象
            loaded_obj = UniversalSerializer.load_object_from_file(path)
            
            # 检查类型是否兼容（允许相同类名的类）
            if (type(obj).__name__ != type(loaded_obj).__name__ and 
                type(obj) != type(loaded_obj)):
                return False
            
            # 复制属性
            if hasattr(loaded_obj, '__dict__'):
                # 检查对象的include/exclude配置
                include = getattr(obj, "__state_include__", [])
                exclude = getattr(obj, "__state_exclude__", [])
                
                for attr_name, attr_value in loaded_obj.__dict__.items():
                    # 应用include/exclude过滤
                    if include and attr_name not in include:
                        continue
                    if attr_name in (exclude or []):
                        continue
                    
                    try:
                        setattr(obj, attr_name, attr_value)
                    except Exception:
                        pass
            
            return True
            
        except Exception as e:
            # 调试用：打印异常信息
            # print(f"Debug: load_object_state failed with: {e}")
            return False
