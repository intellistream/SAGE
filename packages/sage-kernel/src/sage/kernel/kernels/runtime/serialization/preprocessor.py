"""
对象预处理器 - 处理序列化前的对象清理
"""
import inspect
from typing import Any, Dict, List, Optional, Set as TypingSet
from collections.abc import Mapping, Sequence, Set as AbstractSet

from .config import BLACKLIST, ATTRIBUTE_BLACKLIST, SKIP_VALUE


def gather_attrs(obj) -> Dict[str, Any]:
    """枚举实例 __dict__ 和 @property 属性。"""
    attrs = dict(getattr(obj, "__dict__", {}))
    for name, prop in inspect.getmembers(type(obj), lambda x: isinstance(x, property)):
        try:
            attrs[name] = getattr(obj, name)
        except Exception:
            pass
    return attrs


def filter_attrs(attrs: Dict[str, Any], 
                include: Optional[List[str]], 
                exclude: Optional[List[str]]) -> Dict[str, Any]:
    """根据 include/exclude 过滤字段字典。"""
    if include:
        # 如果指定了include，只保留include中的属性，忽略默认的blacklist
        return {k: attrs[k] for k in include if k in attrs}
    
    # 合并用户定义的exclude和系统默认的exclude
    all_exclude = set(exclude or []) | ATTRIBUTE_BLACKLIST
    
    # 过滤掉不能设置的特殊属性
    UNSETABLE_ATTRS = {'__weakref__', '__dict__', '__class__'}
    
    return {k: v for k, v in attrs.items() 
            if k not in all_exclude and k not in UNSETABLE_ATTRS}


def should_skip(obj: Any) -> bool:
    """判断对象是否应该跳过序列化"""
    # 检查黑名单 - 修改为更精确的检查
    for blacklisted_type in BLACKLIST:
        try:
            if isinstance(obj, blacklisted_type):
                # print(f"Skipping blacklisted instance: {type(obj)}, {obj}")
                return True
        except (TypeError, AttributeError):
            # 某些类型检查可能失败，继续检查其他类型
            continue
    
    # 检查是否是模块（通常不应该序列化）
    if inspect.ismodule(obj):
        # print(f"Skipping module: {obj}")
        return True
    
    # 额外检查：特定类型名称匹配（用于处理类型检查失败的情况）
    obj_type_name = type(obj).__name__
    if obj_type_name in ('lock', '_thread.lock', 'LockType', '_TemporaryFileWrapper'):
        return True
    
    return False


def has_circular_reference(obj: Any, _seen: Optional[TypingSet[int]] = None, max_depth: int = 10) -> bool:
    """检查对象是否包含循环引用"""
    if _seen is None:
        _seen = set()
    
    if max_depth <= 0:
        return False
        
    obj_id = id(obj)
    if obj_id in _seen:
        return True
    
    # 基本类型不会有循环引用
    if isinstance(obj, (int, float, str, bool, type(None))):
        return False
    
    _seen.add(obj_id)
    try:
        # 检查字典
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                if has_circular_reference(k, _seen, max_depth - 1) or has_circular_reference(v, _seen, max_depth - 1):
                    return True
        
        # 检查序列
        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            for item in obj:
                if has_circular_reference(item, _seen, max_depth - 1):
                    return True
        
        # 检查集合
        elif isinstance(obj, AbstractSet):
            for item in obj:
                if has_circular_reference(item, _seen, max_depth - 1):
                    return True
        
        # 检查复杂对象
        elif hasattr(obj, '__dict__'):
            for attr_value in obj.__dict__.values():
                if has_circular_reference(attr_value, _seen, max_depth - 1):
                    return True
        
        return False
    finally:
        _seen.remove(obj_id)


def preprocess_for_dill(obj: Any, _seen: Optional[TypingSet[int]] = None) -> Any:
    """
    递归预处理对象，清理不可序列化的内容，为dill序列化做准备。
    
    Args:
        obj: 要预处理的对象
        _seen: 已处理对象的集合，用于处理循环引用
    
    Returns:
        预处理后的对象，可以安全地交给dill序列化
    """
    # print(f"preprocess_for_dill called for object: {obj}")
    if _seen is None:
        _seen = set()
    
    # 防止循环引用 - 如果检测到循环引用，直接返回原对象让dill处理
    obj_id = id(obj)
    if obj_id in _seen:
        return obj
    
    # 对于复杂对象，先检查是否有循环引用
    if hasattr(obj, '__dict__') and has_circular_reference(obj):
        # 如果有循环引用，直接返回原对象让dill处理
        return obj
    
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
    if should_skip(obj):
        return SKIP_VALUE
    
    # 处理字典
    if isinstance(obj, Mapping):
        _seen.add(obj_id)
        try:
            cleaned = {}
            for k, v in obj.items():
                if not should_skip(k) and not should_skip(v):
                    cleaned_k = preprocess_for_dill(k, _seen)
                    cleaned_v = preprocess_for_dill(v, _seen)
                    if cleaned_k is not SKIP_VALUE and ((cleaned_v is not SKIP_VALUE) or (cleaned_v is None)):
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
                if not should_skip(item):
                    cleaned_item = preprocess_for_dill(item, _seen)
                    if cleaned_item is not SKIP_VALUE:
                        cleaned.append(cleaned_item)
            # 保持原始类型：如果是元组，返回元组；如果是列表，返回列表
            if isinstance(obj, tuple):
                return tuple(cleaned) if cleaned else ()
            else:
                return type(obj)(cleaned) if cleaned else []
        finally:
            _seen.remove(obj_id)
    
    # 处理集合
    if isinstance(obj, AbstractSet):
        _seen.add(obj_id)
        try:
            cleaned = set()
            for item in obj:
                if not should_skip(item):
                    cleaned_item = preprocess_for_dill(item, _seen)
                    if cleaned_item is not SKIP_VALUE:
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
            
            attrs = gather_attrs(obj)
            # if len(custom_exclude) is not 0:
            #     print(f"attrs is {attrs}")

            filtered_attrs = filter_attrs(attrs, custom_include, custom_exclude)
            # if len(custom_exclude) is not 0:
            #     print(f"filtered_attrs is {filtered_attrs}")
            
            # 递归清理属性
            for attr_name, attr_value in filtered_attrs.items():
                # print(f"Processing attribute: {attr_name} = {attr_value}")
                if not should_skip(attr_value):
                    # print(f"Cleaning attribute: {attr_name}")
                    cleaned_value = preprocess_for_dill(attr_value, _seen)
                    if cleaned_value is not SKIP_VALUE:
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


def postprocess_from_dill(obj: Any, _seen: Optional[TypingSet[int]] = None) -> Any:
    """递归后处理从dill反序列化的对象，清理哨兵值。"""
    # print(f"postprocess_from_dill called for object: {obj}")
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
    if obj is SKIP_VALUE:
        return None
    
    # 处理字典
    if isinstance(obj, Mapping):
        _seen.add(obj_id)
        try:
            cleaned = {}
            for k, v in obj.items():
                # print(f"Processing dict item: {k} = {v}")
                # 修复：只过滤掉哨兵值，保留所有合法值（包括None、False、0等）
                if k is not SKIP_VALUE and v is not SKIP_VALUE:
                    cleaned_k = postprocess_from_dill(k, _seen)
                    cleaned_v = postprocess_from_dill(v, _seen)
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
                if item is not SKIP_VALUE:
                    cleaned_item = postprocess_from_dill(item, _seen)
                    # 保留所有值，包括None、False、0等
                    cleaned.append(cleaned_item)
            # 保持原始类型：如果是元组，返回元组；如果是列表，返回列表
            if isinstance(obj, tuple):
                return tuple(cleaned)
            else:
                return type(obj)(cleaned)
        finally:
            _seen.remove(obj_id)
    
    # 处理集合
    if isinstance(obj, AbstractSet):
        _seen.add(obj_id)
        try:
            cleaned = set()
            for item in obj:
                if item is not SKIP_VALUE:
                    cleaned_item = postprocess_from_dill(item, _seen)
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
                if attr_value is SKIP_VALUE:
                    # 删除哨兵值属性
                    try:
                        delattr(obj, attr_name)
                    except Exception:
                        pass
                else:
                    # 递归清理属性值，保留所有合法值
                    cleaned_value = postprocess_from_dill(attr_value, _seen)
                    try:
                        setattr(obj, attr_name, cleaned_value)
                    except Exception:
                        pass
            
            return obj
        finally:
            _seen.remove(obj_id)
    
    return obj
