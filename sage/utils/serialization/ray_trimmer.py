"""
Ray对象清理器 - 专门用于Ray远程调用的对象预处理
"""
from typing import Any, Dict, List, Optional

from .exceptions import SerializationError
from .config import SKIP_VALUE, RAY_TRANSFORMATION_EXCLUDE_ATTRS, RAY_OPERATOR_EXCLUDE_ATTRS
from .preprocessor import preprocess_for_dill, gather_attrs, filter_attrs, should_skip


def trim_object_for_ray(obj: Any, 
                       include: Optional[List[str]] = None,
                       exclude: Optional[List[str]] = None) -> Any:
    """
    为Ray远程调用预处理对象，移除不可序列化的内容
    
    这个函数只做清理工作，不进行实际的序列化，让Ray自己处理序列化过程。
    适用于在ray.remote调用前清理对象，避免序列化错误。
    
    Args:
        obj: 要预处理的对象
        include: 包含的属性列表（如果指定，只保留这些属性）
        exclude: 排除的属性列表（这些属性将被移除）
        
    Returns:
        清理后的对象，可以安全地传递给Ray进行序列化
        
    Example:
        # 清理transformation对象用于Ray调用
        cleaned_trans = trim_object_for_ray(transformation, 
                                          exclude=['logger', 'env', '_operator_factory'])
        
        # 现在可以安全地传递给Ray
        result = ray_actor.process_transformation.remote(cleaned_trans)
    """
    try:
        # 如果指定了include或exclude，直接使用用户的过滤规则
        if include or exclude:
            attrs = gather_attrs(obj)
            filtered_attrs = filter_attrs(attrs, include, exclude)
            
            # 创建新对象并设置过滤后的属性
            obj_class = type(obj)
            try:
                final_obj = obj_class.__new__(obj_class)
                for attr_name, attr_value in filtered_attrs.items():
                    try:
                        setattr(final_obj, attr_name, attr_value)
                    except Exception:
                        pass  # 忽略设置失败的属性
                return final_obj
            except Exception:
                # 如果无法创建新实例，回退到预处理
                pass
        
        # 如果没有特殊的include/exclude需求，使用现有的预处理函数
        cleaned_obj = preprocess_for_dill(obj)
        return cleaned_obj if cleaned_obj is not SKIP_VALUE else None
        
    except Exception as e:
        # 如果预处理失败，返回None或抛出异常
        raise SerializationError(f"Object trimming for Ray failed: {e}")


class RayObjectTrimmer:
    """专门用于Ray远程调用的对象预处理器"""
    
    @staticmethod
    def trim_for_remote_call(obj: Any,
                           include: Optional[List[str]] = None,
                           exclude: Optional[List[str]] = None,
                           deep_clean: bool = True) -> Any:
        """
        为Ray远程调用准备对象
        
        Args:
            obj: 要清理的对象
            include: 只保留这些属性
            exclude: 排除这些属性
            deep_clean: 是否进行深度清理（递归处理嵌套对象）
        
        Returns:
            清理后可以传递给Ray的对象
        """
        if not deep_clean:
            # 浅层清理：只处理顶层对象的属性
            if hasattr(obj, '__dict__'):
                attrs = gather_attrs(obj)
                filtered_attrs = filter_attrs(attrs, include, exclude)
                
                obj_class = type(obj)
                try:
                    cleaned_obj = obj_class.__new__(obj_class)
                    for attr_name, attr_value in filtered_attrs.items():
                        if not should_skip(attr_value):
                            try:
                                setattr(cleaned_obj, attr_name, attr_value)
                            except Exception:
                                pass
                    return cleaned_obj
                except Exception:
                    return obj
            return obj
        else:
            # 深度清理：使用完整的预处理流程，并递归处理嵌套对象
            cleaned = trim_object_for_ray(obj, include, exclude)
            
            # 确保嵌套对象也被正确清理
            if cleaned and hasattr(cleaned, '__dict__'):
                for attr_name, attr_value in list(cleaned.__dict__.items()):
                    if hasattr(attr_value, '__dict__'):
                        # 递归清理嵌套对象，使用默认的黑名单清理（应用ATTRIBUTE_BLACKLIST）
                        from .config import ATTRIBUTE_BLACKLIST
                        nested_cleaned = RayObjectTrimmer.trim_for_remote_call(
                            attr_value, include=None, exclude=list(ATTRIBUTE_BLACKLIST), deep_clean=True
                        )
                        setattr(cleaned, attr_name, nested_cleaned)
            
            return cleaned
    
    @staticmethod
    def trim_transformation_for_ray(transformation_obj) -> Any:
        """
        专门为Transformation对象定制的清理方法
        移除常见的不可序列化属性
        """
        return RayObjectTrimmer.trim_for_remote_call(
            transformation_obj, 
            exclude=RAY_TRANSFORMATION_EXCLUDE_ATTRS
        )
    
    @staticmethod
    def trim_operator_for_ray(operator_obj) -> Any:
        """
        专门为Operator对象定制的清理方法
        """
        return RayObjectTrimmer.trim_for_remote_call(
            operator_obj,
            exclude=RAY_OPERATOR_EXCLUDE_ATTRS
        )
    
    @staticmethod
    def validate_ray_serializable(obj: Any, max_depth: int = 3) -> Dict[str, Any]:
        """
        验证对象是否可以被Ray序列化
        
        Args:
            obj: 要验证的对象
            max_depth: 最大检查深度
        
        Returns:
            验证结果字典，包含是否可序列化和问题列表
        """
        try:
            import ray
        except ImportError:
            return {
                'is_serializable': False,
                'issues': ['Ray is not installed'],
                'size_estimate': 0
            }
        
        result = {
            'is_serializable': False,
            'issues': [],
            'size_estimate': 0
        }
        
        try:
            # 尝试Ray的内部序列化
            serialized = ray.cloudpickle.dumps(obj)
            result['is_serializable'] = True
            result['size_estimate'] = len(serialized)
            
        except Exception as e:
            result['issues'].append(f"Ray serialization failed: {str(e)}")
            
            # 尝试识别具体的问题
            if hasattr(obj, '__dict__'):
                for attr_name, attr_value in obj.__dict__.items():
                    if should_skip(attr_value):
                        result['issues'].append(f"Problematic attribute: {attr_name} = {type(attr_value)}")
        
        return result
