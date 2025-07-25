import os
import pickle
import inspect
import threading
import importlib
from typing import Any, Dict, List, Set, Type, Optional, Union
from collections.abc import Mapping, Sequence, Set as AbstractSet
import dill


class SerializationError(Exception):
    """序列化相关错误"""
    pass


# 不可序列化类型黑名单
_BLACKLIST = [
    threading.Thread,  # 线程
    type(open),        # 文件句柄
    type(threading.Lock),    # 锁
    type(threading.RLock),   # 递归锁
    threading.Event,   # 事件
    threading.Condition,  # 条件变量
]

# 序列化时需要排除的属性名
_ATTRIBUTE_BLACKLIST = {
    'logger',          # 日志对象
    '_logger',         # 私有日志对象
    'server_socket',   # socket对象
    'server_thread',   # 线程对象
    '_server_thread',  # 私有线程对象
    'client_socket',   # socket对象
    '__weakref__',     # 弱引用
    'runtime_context', # 运行时上下文
    # 'memory_collection', # 内存集合（通常是Ray Actor句柄）
    'env',             # 环境引用（避免循环引用）
    # '_dag_node_factory',  # 工厂对象
    # '_operator_factory',  # 工厂对象
    # '_function_factory',  # 工厂对象
}

# 哨兵值，表示应该跳过的值
_SKIP_VALUE = object()


def _gather_attrs(obj):
    """枚举实例 __dict__ 和 @property 属性。"""
    attrs = dict(getattr(obj, "__dict__", {}))
    for name, prop in inspect.getmembers(type(obj), lambda x: isinstance(x, property)):
        try:
            attrs[name] = getattr(obj, name)
        except Exception:
            pass
    return attrs


def _filter_attrs(attrs, include, exclude):
    """根据 include/exclude 过滤字段字典。"""
    if include:
        return {k: attrs[k] for k in include if k in attrs}
    
    # 合并用户定义的exclude和系统默认的exclude
    all_exclude = set(exclude or []) | _ATTRIBUTE_BLACKLIST
    return {k: v for k, v in attrs.items() if k not in all_exclude}


def _should_skip(v):
    """判断对象是否应该跳过序列化"""
    # 检查黑名单 - 修改为更精确的检查
    for i, blacklisted_type in enumerate(_BLACKLIST):
        if isinstance(v, blacklisted_type):
            # print(f"Skipping blacklisted instance {i}: {type(v)}, {v}")
            return True
    
    # 检查是否是模块（通常不应该序列化）
    if inspect.ismodule(v):
        # print(f"Skipping module: {v}")
        return True
    
    return False


def _preprocess_for_dill(obj, _seen=None):
    """
    递归预处理对象，清理不可序列化的内容，为dill序列化做准备。
    
    Args:
        obj: 要预处理的对象
        _seen: 已处理对象的集合，用于处理循环引用
    
    Returns:
        预处理后的对象，可以安全地交给dill序列化
    """
    # print(f"_preprocess_for_dill called for object: {obj}")
    if _seen is None:
        _seen = set()
    
    # 防止循环引用
    obj_id = id(obj)
    if obj_id in _seen:
        # print(f"Skipping already seen object: {obj}")
        return _SKIP_VALUE
    
    # 基本类型直接返回
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    # 类对象可以直接被dill序列化，不需要预处理
    if inspect.isclass(obj):
        # print(f"Processing class object: {obj}")
        return obj
    
    # 函数对象也可以直接被dill序列化
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        # print(f"Processing function object: {obj}")
        return obj

    # 检查是否应该跳过
    if _should_skip(obj):
        return _SKIP_VALUE
    


    # 处理字典
    if isinstance(obj, Mapping):
        _seen.add(obj_id)
        try:
            cleaned = {}
            for k, v in obj.items():
                if not _should_skip(k) and not _should_skip(v):
                    cleaned_k = _preprocess_for_dill(k, _seen)
                    cleaned_v = _preprocess_for_dill(v, _seen)
                    if cleaned_k is not _SKIP_VALUE and ((cleaned_v is not _SKIP_VALUE) or (cleaned_v is None)):
                        cleaned[cleaned_k] = cleaned_v
            return cleaned
        finally:
            _seen.remove(obj_id)
    
    # 处理序列（列表、元组等）
    if isinstance(obj, Sequence) and not isinstance(obj, str):
        _seen.add(obj_id)
        try:
            cleaned = []
            for item in obj:
                if not _should_skip(item):
                    cleaned_item = _preprocess_for_dill(item, _seen)
                    if cleaned_item is not _SKIP_VALUE:
                        cleaned.append(cleaned_item)
            return type(obj)(cleaned) if cleaned else []
        finally:
            _seen.remove(obj_id)
    
    # 处理集合
    if isinstance(obj, AbstractSet):
        _seen.add(obj_id)
        try:
            cleaned = set()
            for item in obj:
                if not _should_skip(item):
                    cleaned_item = _preprocess_for_dill(item, _seen)
                    if cleaned_item is not _SKIP_VALUE:
                        cleaned.add(cleaned_item)
            return type(obj)(cleaned) if cleaned else set()
        finally:
            _seen.remove(obj_id)
    
    # 处理复杂对象
    if hasattr(obj, '__dict__'):
        # print(f"Processing complex object: {obj}")
        # print(f"dict is {obj.__dict__}")
        _seen.add(obj_id)
        try:
            # 创建一个新的对象实例
            obj_class = type(obj)
            
            # 尝试创建空实例
            try:
                cleaned_obj = obj_class.__new__(obj_class)
            except Exception:
                # 如果无法创建空实例，返回原对象让dill处理
                return obj
            
            # 获取和过滤属性
            custom_include = getattr(obj.__class__, "__state_include__", [])
            custom_exclude = getattr(obj.__class__, "__state_exclude__", [])
            # if len(custom_exclude) is not 0:
            #     print(f"custom_exclude is {custom_exclude}")
            # 一般不用include字段，只用exclude字段就行了    
            
            attrs = _gather_attrs(obj)
            # if len(custom_exclude) is not 0:
            #     print(f"attrs is {attrs}")

            filtered_attrs = _filter_attrs(attrs, custom_include, custom_exclude)
            # if len(custom_exclude) is not 0:
            #     print(f"filtered_attrs is {filtered_attrs}")
            
            # 递归清理属性
            for attr_name, attr_value in filtered_attrs.items():
                # print(f"Processing attribute: {attr_name} = {attr_value}")
                if not _should_skip(attr_value):
                    # print(f"Cleaning attribute: {attr_name}")
                    cleaned_value = _preprocess_for_dill(attr_value, _seen)
                    if cleaned_value is not _SKIP_VALUE:
                        try:
                            setattr(cleaned_obj, attr_name, cleaned_value)
                        except Exception:
                            # 忽略设置失败的属性
                            pass
            
            return cleaned_obj
        finally:
            _seen.remove(obj_id)
    
    # 对于其他对象，直接返回给dill处理
    return obj


def _postprocess_from_dill(obj, _seen=None):
    """递归后处理从dill反序列化的对象，清理哨兵值。"""
    # print(f"_postprocess_from_dill called for object: {obj}")
    if _seen is None:
        _seen = set()
    
    # 防止循环引用
    obj_id = id(obj)
    if obj_id in _seen:
        return obj
    
    # 基本类型直接返回
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    # 跳过哨兵值
    if obj is _SKIP_VALUE:
        return None
    
    # 处理字典
    if isinstance(obj, Mapping):
        _seen.add(obj_id)
        try:
            cleaned = {}
            for k, v in obj.items():
                # print(f"Processing dict item: {k} = {v}")
                # 修复：只过滤掉哨兵值，保留所有合法值（包括None、False、0等）
                if k is not _SKIP_VALUE and v is not _SKIP_VALUE:
                    cleaned_k = _postprocess_from_dill(k, _seen)
                    cleaned_v = _postprocess_from_dill(v, _seen)
                    # 保留所有值，包括None、False、0、空字典等
                    cleaned[cleaned_k] = cleaned_v
                    # print(f"Cleaned dict item: {cleaned_k} = {cleaned_v}")
            return cleaned
        finally:
            _seen.remove(obj_id)
    
    # 处理序列
    if isinstance(obj, Sequence) and not isinstance(obj, str):
        _seen.add(obj_id)
        try:
            cleaned = []
            for item in obj:
                if item is not _SKIP_VALUE:
                    cleaned_item = _postprocess_from_dill(item, _seen)
                    # 保留所有值，包括None、False、0等
                    cleaned.append(cleaned_item)
            return type(obj)(cleaned)
        finally:
            _seen.remove(obj_id)
    
    # 处理集合
    if isinstance(obj, AbstractSet):
        _seen.add(obj_id)
        try:
            cleaned = set()
            for item in obj:
                if item is not _SKIP_VALUE:
                    cleaned_item = _postprocess_from_dill(item, _seen)
                    # 集合中不能包含None，但可以包含False、0等
                    if cleaned_item is not None:
                        cleaned.add(cleaned_item)
            return type(obj)(cleaned)
        finally:
            _seen.remove(obj_id)
    
    # 处理复杂对象
    if hasattr(obj, '__dict__'):
        _seen.add(obj_id)
        try:
            # 递归清理属性
            for attr_name, attr_value in list(obj.__dict__.items()):
                if attr_value is _SKIP_VALUE:
                    # 删除哨兵值属性
                    try:
                        delattr(obj, attr_name)
                    except Exception:
                        pass
                else:
                    # 递归清理属性值，保留所有合法值
                    cleaned_value = _postprocess_from_dill(attr_value, _seen)
                    try:
                        setattr(obj, attr_name, cleaned_value)
                    except Exception:
                        pass
            
            return obj
        finally:
            _seen.remove(obj_id)
    
    return obj


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
        if dill is None:
            raise SerializationError("dill is required for serialization. Install with: pip install dill")
        
        try:
            # 预处理对象，清理不可序列化的内容
            cleaned_obj = _preprocess_for_dill(obj)
            
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
        if dill is None:
            raise SerializationError("dill is required for deserialization. Install with: pip install dill")
        
        try:
            # 使用dill反序列化
            obj = dill.loads(data)
            
            # 后处理对象，清理哨兵值
            return _postprocess_from_dill(obj)
            
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
            
            # 检查类型是否匹配
            if type(obj) != type(loaded_obj):
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
            
        except Exception:
            return False


# 便捷函数
def serialize_object(obj: Any, 
                    include: Optional[List[str]] = None,
                    exclude: Optional[List[str]] = None) -> bytes:
    """序列化对象的便捷函数"""
    return UniversalSerializer.serialize_object(obj, include, exclude)


def deserialize_object(data: bytes) -> Any:
    """反序列化对象的便捷函数"""
    return UniversalSerializer.deserialize_object(data)


def save_object_state(obj: Any, path: str,
                     include: Optional[List[str]] = None,
                     exclude: Optional[List[str]] = None):
    """保存对象状态的便捷函数"""
    return UniversalSerializer.save_object_state(obj, path, include, exclude)


def load_object_from_file(path: str) -> Any:
    """从文件加载对象的便捷函数"""
    return UniversalSerializer.load_object_from_file(path)


def load_object_state(obj: Any, path: str) -> bool:
    """加载对象状态的便捷函数"""
    return UniversalSerializer.load_object_state(obj, path)


# 向后兼容的函数
def pack_object(obj: Any, 
               include: Optional[List[str]] = None,
               exclude: Optional[List[str]] = None) -> bytes:
    """打包对象的便捷函数（向后兼容）"""
    return serialize_object(obj, include, exclude)


def unpack_object(data: bytes) -> Any:
    """解包对象的便捷函数（向后兼容）"""
    return deserialize_object(data)


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
        # 使用现有的预处理函数，但不进行dill序列化
        cleaned_obj = _preprocess_for_dill(obj)
        
        # 如果有额外的include/exclude需求，再次过滤
        if cleaned_obj is not _SKIP_VALUE and hasattr(cleaned_obj, '__dict__'):
            # 应用用户指定的include/exclude
            if include or exclude:
                attrs = _gather_attrs(cleaned_obj)
                filtered_attrs = _filter_attrs(attrs, include, exclude)
                
                # 创建新对象并设置过滤后的属性
                obj_class = type(cleaned_obj)
                try:
                    final_obj = obj_class.__new__(obj_class)
                    for attr_name, attr_value in filtered_attrs.items():
                        try:
                            setattr(final_obj, attr_name, attr_value)
                        except Exception:
                            pass  # 忽略设置失败的属性
                    return final_obj
                except Exception:
                    # 如果无法创建新实例，返回原对象
                    return cleaned_obj
        
        return cleaned_obj if cleaned_obj is not _SKIP_VALUE else None
        
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
                attrs = _gather_attrs(obj)
                filtered_attrs = _filter_attrs(attrs, include, exclude)
                
                obj_class = type(obj)
                try:
                    cleaned_obj = obj_class.__new__(obj_class)
                    for attr_name, attr_value in filtered_attrs.items():
                        if not _should_skip(attr_value):
                            try:
                                setattr(cleaned_obj, attr_name, attr_value)
                            except Exception:
                                pass
                    return cleaned_obj
                except Exception:
                    return obj
            return obj
        else:
            # 深度清理：使用完整的预处理流程
            return trim_object_for_ray(obj, include, exclude)
    
    @staticmethod
    def trim_transformation_for_ray(transformation_obj) -> Any:
        """
        专门为Transformation对象定制的清理方法
        移除常见的不可序列化属性
        """
        exclude_attrs = [
            'logger', '_logger',           # 日志对象
            'env',                         # 环境引用（避免循环引用）
            'runtime_context',             # 运行时上下文
            '_dag_node_factory',           # 懒加载工厂
            '_operator_factory',           # 懒加载工厂  
            '_function_factory',           # 懒加载工厂
            'server_socket',               # socket对象
            'server_thread', '_server_thread',  # 线程对象
        ]
        
        return RayObjectTrimmer.trim_for_remote_call(
            transformation_obj, 
            exclude=exclude_attrs
        )
    
    @staticmethod
    def trim_operator_for_ray(operator_obj) -> Any:
        """
        专门为Operator对象定制的清理方法
        """
        exclude_attrs = [
            'logger', '_logger',
            'runtime_context',
            'emit_context',
            'server_socket', 'client_socket',
            'server_thread', '_server_thread',
            '__weakref__',
        ]
        
        return RayObjectTrimmer.trim_for_remote_call(
            operator_obj,
            exclude=exclude_attrs
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
        import ray
        
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
                    if _should_skip(attr_value):
                        result['issues'].append(f"Problematic attribute: {attr_name} = {type(attr_value)}")
        
        return result