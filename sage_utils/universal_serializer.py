import os
import pickle
import inspect
import threading
import importlib
from typing import Any, Dict, List, Set, Type, Optional, Union
from collections.abc import Mapping, Sequence, Set as AbstractSet
from sage_utils.custom_logger import CustomLogger


class SerializationError(Exception):
    """序列化相关错误"""
    pass


# 扩展的不可序列化类型黑名单
_BLACKLIST = (
    type(open),        # 文件句柄
    type(threading.Thread),  # 线程
    type(threading.Lock),    # 锁
    type(threading.RLock),   # 递归锁
    type(threading.Event),   # 事件
    type(threading.Condition),  # 条件变量
    type(lambda: None),   # 函数类型（除非特殊处理）
    type(print),       # 内置函数
    type(len),         # 内置函数
)


# 序列化时需要排除的属性名
_ATTRIBUTE_BLACKLIST = {
    'logger',          # 日志对象
    '_logger',         # 私有日志对象
    'server_socket',   # socket对象
    'server_thread',   # 线程对象
    '_server_thread',  # 私有线程对象
    'client_socket',   # socket对象
    '__weakref__',     # 弱引用
    '__dict__',        # 防止递归
    'runtime_context', # 运行时上下文
    'memory_collection', # 内存集合（通常是Ray Actor句柄）
    'env',             # 环境引用（避免循环引用）
    '_dag_node_factory',  # 工厂对象
    '_operator_factory',  # 工厂对象
    '_function_factory',  # 工厂对象
}


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


def _is_serializable(v):
    print(f"Checking serializability of value: {v} (type: {type(v)})")
    """判断对象能否通过 pickle 序列化，且不在黑名单中。"""
    if isinstance(v, _BLACKLIST):
        print(f"Value {v} is in blacklist, not serializable")
        return False
    
    # 检查是否是模块（模块通常不应该序列化）
    if inspect.ismodule(v):
        print(f"Value {v} is a module, not serializable")
        return False
    
    # 检查是否是类（类定义通过类路径序列化，这里返回False让其他逻辑处理）
    if inspect.isclass(v):
        return False
    
    try:
        pickle.dumps(v)
        return True
    except Exception:
        print(f"exception not serializable")
        return False


def _is_complex_object(v):
    """判断是否是需要递归序列化的复杂对象"""
    # 基本类型不需要递归
    if isinstance(v, (int, float, str, bool, type(None))):
        return False
    
    # 容器类型需要递归处理内容，但不是复杂对象本身
    if isinstance(v, (Mapping, Sequence, AbstractSet)) and not isinstance(v, str):
        return False
    
    # 有__dict__属性的对象通常是复杂对象
    if hasattr(v, '__dict__'):
        return True
    
    return False
def _can_be_serialized(v):
    """判断对象是否可以被序列化（直接pickle或通过递归结构）"""
    # 先检查是否在黑名单中
    if isinstance(v, _BLACKLIST):
        return False
    
    # 检查是否是模块
    if inspect.ismodule(v):
        return False
    
    # 检查是否是类
    if inspect.isclass(v):
        return True
    
    # 如果可以直接pickle，当然可以序列化
    if _is_serializable(v):
        return True
    
    # 如果是复杂对象，检查是否可以通过递归结构序列化
    if _is_complex_object(v):
        return True
    
    return False


# 在文件开头添加哨兵值
_SKIP_VALUE = object()  # 用作哨兵值，表示应该跳过的值

def _prepare(v, _seen=None):
    """递归清洗容器类型，过滤不可序列化元素。"""
    if _seen is None:
        _seen = set()
    
    # 防止循环引用
    obj_id = id(v)
    if obj_id in _seen:
        return _SKIP_VALUE
    
    # 基本类型直接返回
    if isinstance(v, (int, float, str, bool, type(None))):
        return v

    # 处理类对象 - 序列化为类路径
    if inspect.isclass(v):
        return {
            '__class_reference__': _get_class_path(v),
            '__serializer_version__': '1.0'
        }

    # 处理字典
    if isinstance(v, Mapping):
        _seen.add(obj_id)
        try:
            result = {}
            for k, val in v.items():
                print(f"Processing dict item: {k} -> {val}")
                if _can_be_serialized(k) and _can_be_serialized(val):
                    prepared_k = _prepare(k, _seen)
                    prepared_v = _prepare(val, _seen)
                    # 只过滤掉哨兵值
                    if prepared_k is not _SKIP_VALUE and prepared_v is not _SKIP_VALUE:
                        result[prepared_k] = prepared_v
                        print(f"Added to result: {prepared_k} -> {prepared_v}")
            return result
        finally:
            _seen.remove(obj_id)
    
    # 处理序列（列表、元组等）
    if isinstance(v, Sequence) and not isinstance(v, str):
        _seen.add(obj_id)
        try:
            cleaned = []
            for x in v:
                if _can_be_serialized(x):
                    prepared_x = _prepare(x, _seen)
                    # 只过滤掉哨兵值
                    if prepared_x is not _SKIP_VALUE:
                        cleaned.append(prepared_x)
            return type(v)(cleaned) if cleaned else []
        finally:
            _seen.remove(obj_id)
    
    # 处理集合
    if isinstance(v, AbstractSet):
        _seen.add(obj_id)
        try:
            cleaned = set()
            for x in v:
                if _can_be_serialized(x):
                    prepared_x = _prepare(x, _seen)
                    # 只过滤掉哨兵值
                    if prepared_x is not _SKIP_VALUE:
                        cleaned.add(prepared_x)
            return type(v)(cleaned) if cleaned else set()
        finally:
            _seen.remove(obj_id)
    
    # 处理复杂对象
    if _is_complex_object(v):
        _seen.add(obj_id)
        try:
            return _serialize_complex_object(v, _seen)
        finally:
            _seen.remove(obj_id)
    
    # 对于其他可直接序列化的对象，直接返回
    if _is_serializable(v):
        return v
    
    # 不可序列化的对象返回哨兵值
    return _SKIP_VALUE


def _serialize_complex_object(obj, _seen=None):
    """递归序列化复杂对象的内部结构"""
    if _seen is None:
        _seen = set()
    
    # 获取对象的类信息
    obj_class = type(obj)
    
    # 检查对象是否有自定义的序列化配置
    custom_include = getattr(obj, "__state_include__", [])
    custom_exclude = getattr(obj, "__state_exclude__", [])
    
    # 收集所有属性
    attrs = _gather_attrs(obj)
    
    # 过滤属性
    filtered_attrs = _filter_attrs(attrs, custom_include, custom_exclude)
    
    # 准备序列化数据 - 递归处理每个属性
    prepared_attrs = {}
    for k, v in filtered_attrs.items():
        print(f"Preparing attribute: {k} -> {v}")
        prepared_value = _prepare(v, _seen)
        # 只过滤掉哨兵值
        if prepared_value is not _SKIP_VALUE:
            prepared_attrs[k] = prepared_value
            print(f"Prepared attribute: {k} -> {prepared_value}")
    
    # 构建序列化数据
    return {
        '__class_path__': _get_class_path(obj_class),
        '__attributes__': prepared_attrs,
        '__serializer_version__': '1.0'
    }

def _get_class_path(cls):
    """获取类的完整路径"""
    return f"{cls.__module__}.{cls.__qualname__}"


def _load_class(class_path: str) -> Type:
    """动态加载类"""
    try:
        module_name, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except Exception as e:
        raise SerializationError(f"Failed to load class {class_path}: {e}")


def _restore_value(value):
    """递归恢复值"""
    if isinstance(value, dict) and '__class_path__' in value:
        # 这是一个序列化的复杂对象
        return _deserialize_complex_object(value)
    elif isinstance(value, dict) and '__class_reference__' in value:
        # 这是一个类引用
        class_path = value['__class_reference__']
        return _load_class(class_path)
    elif isinstance(value, list):
        return [_restore_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: _restore_value(v) for k, v in value.items()}
    elif isinstance(value, set):
        return {_restore_value(item) for item in value}
    else:
        return value


def _deserialize_complex_object(data: Dict[str, Any]) -> Any:
    """反序列化复杂对象"""
    # 验证数据格式
    if not isinstance(data, dict) or '__class_path__' not in data:
        raise SerializationError("Invalid serialized data format")
    
    # 加载类
    class_path = data['__class_path__']
    obj_class = _load_class(class_path)
    
    try:
        obj = obj_class.__new__(obj_class)
    except Exception:
        raise SerializationError(f"Cannot create instance of {class_path}")
    
    # 恢复属性
    attributes = data.get('__attributes__', {})
    for attr_name, attr_value in attributes.items():
        try:
            # 递归反序列化属性值
            restored_value = _restore_value(attr_value)
            setattr(obj, attr_name, restored_value)
        except Exception as e:
            # 忽略设置失败的属性，但记录日志
            pass
    
    return obj


class UniversalSerializer:
    """通用序列化器，基于反选机制自动处理所有可序列化对象"""
    
    @staticmethod
    def serialize_object(obj: Any, 
                        include: Optional[List[str]] = None,
                        exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """序列化任意对象"""
        try:
            # 使用_serialize_complex_object来处理顶层对象
            return _serialize_complex_object(obj)
            
        except Exception as e:
            raise SerializationError(f"Object serialization failed: {e}")
    
    @staticmethod
    def deserialize_object(data: Dict[str, Any]) -> Any:
        """反序列化对象"""
        try:
            return _deserialize_complex_object(data)
            
        except Exception as e:
            raise SerializationError(f"Object deserialization failed: {e}")
    
    @staticmethod
    def pack_object(obj: Any, 
                   include: Optional[List[str]] = None,
                   exclude: Optional[List[str]] = None) -> bytes:
        """将对象打包为二进制数据"""
        serialized_data = UniversalSerializer.serialize_object(obj, include, exclude)
        return pickle.dumps(serialized_data)
    
    @staticmethod
    def unpack_object(data: bytes, 
                     constructor_args: Optional[tuple] = None,
                     constructor_kwargs: Optional[dict] = None) -> Any:
        """从二进制数据解包对象"""
        serialized_data = pickle.loads(data)
        return UniversalSerializer.deserialize_object(serialized_data, constructor_args, constructor_kwargs)
    
    @staticmethod
    def save_object_state(obj: Any, path: str,
                         include: Optional[List[str]] = None,
                         exclude: Optional[List[str]] = None):
        """将对象状态保存到文件"""
        serialized_data = UniversalSerializer.serialize_object(obj, include, exclude)
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(serialized_data, f)
    
    @staticmethod
    def load_object_state(obj: Any, path: str) -> bool:
        """从文件加载对象状态"""
        if not os.path.isfile(path):
            return False
        
        try:
            with open(path, 'rb') as f:
                serialized_data = pickle.load(f)
            
            # 只恢复属性，不创建新对象
            attributes = serialized_data.get('__attributes__', {})
            
            # 检查对象的include/exclude配置
            include = getattr(obj, "__state_include__", [])
            exclude = getattr(obj, "__state_exclude__", [])
            
            for attr_name, attr_value in attributes.items():
                # 应用include/exclude过滤
                if include and attr_name not in include:
                    continue
                if attr_name in (exclude or []):
                    continue
                
                try:
                    restored_value = _restore_value(attr_value)
                    setattr(obj, attr_name, restored_value)
                except Exception:
                    # 忽略设置失败的属性
                    pass
            
            return True
            
        except Exception as e:
            return False


# 便捷函数
def serialize_object(obj: Any, 
                    include: Optional[List[str]] = None,
                    exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """序列化对象的便捷函数"""
    return UniversalSerializer.serialize_object(obj, include, exclude)


def deserialize_object(data: Dict[str, Any]) -> Any:
    """反序列化对象的便捷函数"""
    return UniversalSerializer.deserialize_object(data)


def pack_object(obj: Any, 
               include: Optional[List[str]] = None,
               exclude: Optional[List[str]] = None) -> bytes:
    """打包对象的便捷函数"""
    return UniversalSerializer.pack_object(obj, include, exclude)


def unpack_object(data: bytes, 
                 constructor_args: Optional[tuple] = None,
                 constructor_kwargs: Optional[dict] = None) -> Any:
    """解包对象的便捷函数"""
    return UniversalSerializer.unpack_object(data, constructor_args, constructor_kwargs)


def save_object_state(obj: Any, path: str,
                     include: Optional[List[str]] = None,
                     exclude: Optional[List[str]] = None):
    """保存对象状态的便捷函数"""
    return UniversalSerializer.save_object_state(obj, path, include, exclude)


def load_object_state(obj: Any, path: str) -> bool:
    """加载对象状态的便捷函数"""
    return UniversalSerializer.load_object_state(obj, path)