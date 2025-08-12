import os
import pickle
import inspect
import threading
import io
import types
from collections.abc import Mapping, Sequence, Set

# TODO: state 的持久化管理不应该由 function来定义，而是应该交给系统自动在operator / task里面生成。
# 不可序列化类型黑名单
_BLACKLIST = (
    io.IOBase,                    # 文件句柄基类（包括所有文件类型）
    threading.Thread,             # 线程
    types.BuiltinFunctionType,    # 内置函数（如 open, len 等）
)

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
    return {k: v for k, v in attrs.items() if k not in exclude}

def _is_serializable(v):
    """判断对象能否通过 pickle 序列化，且不在黑名单中。"""
    if isinstance(v, _BLACKLIST):
        return False
    try:
        pickle.dumps(v)
        return True
    except Exception:
        return False

def _prepare(v, _visited=None):
    """递归清洗容器类型，过滤不可序列化元素。"""
    if _visited is None:
        _visited = set()
    
    # 基本类型直接返回
    if isinstance(v, (int, float, str, bool, type(None))):
        return v
    
    # 循环引用检测：使用id()来跟踪对象
    obj_id = id(v)
    if obj_id in _visited:
        # 发现循环引用，返回占位符或None
        return None
    
    # 只对容器类型进行循环引用跟踪
    if isinstance(v, (Mapping, Sequence, Set)) and not isinstance(v, str):
        _visited.add(obj_id)
    
    try:
        if isinstance(v, Mapping):
            result = {
                _prepare(k, _visited): _prepare(val, _visited)
                for k, val in v.items()
                if _is_serializable(k) and _is_serializable(val)
            }
            return result
        if isinstance(v, Sequence) and not isinstance(v, str):
            cleaned = [_prepare(x, _visited) for x in v if _is_serializable(x)]
            return type(v)(cleaned)
        if isinstance(v, Set):
            return type(v)(_prepare(x, _visited) for x in v if _is_serializable(x))
        if _is_serializable(v):
            return v
        return None
    finally:
        # 在退出时移除对象id，允许同一对象在不同路径中被处理
        if isinstance(v, (Mapping, Sequence, Set)) and not isinstance(v, str):
            _visited.discard(obj_id)

def save_function_state(func, path):
    """
    将 func 的可序列化字段保存到 path 文件中。
    自动应用 __state_include__ 和 __state_exclude__。
    """
    include = getattr(func, "__state_include__", [])
    exclude = getattr(func, "__state_exclude__", [])
    attrs = _gather_attrs(func)
    filtered = _filter_attrs(attrs, include, exclude)
    prepared = {k: _prepare(v) for k, v in filtered.items()}

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(prepared, f)

def load_function_state(func, path):
    """
    如果 path 存在，则从中加载字段映射并设置到 func 上。
    忽略当前 include/exclude 中不该加载的字段。
    """
    if not os.path.isfile(path):
        return
    with open(path, "rb") as f:
        data = pickle.load(f)

    include = getattr(func, "__state_include__", [])
    exclude = getattr(func, "__state_exclude__", [])
    for k, v in data.items():
        if include and k not in include:
            continue
        if k in exclude:
            continue
        setattr(func, k, v)