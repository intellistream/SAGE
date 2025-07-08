import weakref
import gc
from typing import Any, Set, Optional
import logging


class Destroyable:
    """
    可销毁的基类，提供自动资源清理功能
    继承此类的对象可以通过 destroy() 方法安全地清理所有引用
    """
    
    # 类级别的销毁跟踪
    _destroyed_instances: Set[int] = set()
    _destruction_in_progress: Set[int] = set()
    
    def __init__(self):
        # 初始化销毁状态
        self._destroyed = False
        self._destruction_started = False
        
        # 保护字段列表，这些字段在销毁时不会被清理
        self._protected_attrs = {
            '_destroyed', '_destruction_started', '_protected_attrs',
            '_logger_backup', '__class__', '__dict__', '__weakref__',
            '_destruction_path'  # 新增：用于跟踪销毁路径
        }
        
        # 用于跟踪销毁路径，防止循环引用
        self._destruction_path = set()
    
    def destroy(self, force: bool = False, _depth: int = 0) -> bool:
        """销毁对象及其所有引用"""
        obj_id = id(self)
        indent = "  " * _depth
        
        # 检查销毁状态
        if self._destroyed:
            if _depth == 0:
                print(f"{indent}[DESTROY] {self.__class__.__name__} 已经被销毁")
            return True
        
        if not force and obj_id in self._destruction_in_progress:
            if _depth == 0:
                print(f"{indent}[DESTROY] {self.__class__.__name__} 正在销毁中，跳过")
            return False
        
        try:
            # 标记开始销毁
            self._destruction_started = True
            self._destruction_in_progress.add(obj_id)
            
            if _depth == 0:
                print(f"{indent}[DESTROY] 开始销毁 {self.__class__.__name__} (id: {obj_id})")
            
            # 特殊处理 logger：不递归销毁，只断开引用
            if hasattr(self, 'logger') and self.logger:
                try:
                    # 备份用于最终日志
                    logger_backup = self.logger
                    self._logger_backup = logger_backup
                    
                    # 只断开引用，不递归销毁 logger 内部
                    self.logger = None
                    print(f"{indent}[DESTROY] 断开 logger 引用")
                except Exception as e:
                    print(f"{indent}[DESTROY ERROR] 处理 logger 失败: {e}")
            
            # 销毁其他属性
            destroyed_count = self._destroy_attributes(_depth + 1)
            
            # 标记完成销毁
            self._destroyed = True
            self._destroyed_instances.add(obj_id)
            
            # 最终日志
            if hasattr(self, '_logger_backup') and self._logger_backup:
                try:
                    self._logger_backup.info(f"{self.__class__.__name__} destroyed with {destroyed_count} attributes")
                except:
                    pass
            
            if _depth == 0:
                print(f"{indent}[DESTROY] {self.__class__.__name__} 销毁完成，清理了 {destroyed_count} 个属性")
            
            return True
            
        except Exception as e:
            print(f"{indent}[DESTROY ERROR] 销毁 {self.__class__.__name__} 时出错: {e}")
            return False
        finally:
            # 清理销毁进度标记
            self._destruction_in_progress.discard(obj_id)
    
    def _destroy_attributes(self, depth: int) -> int:
        """销毁所有属性，返回销毁的属性数量"""
        destroyed_count = 0
        indent = "  " * depth
        
        # 获取所有属性
        attrs_to_destroy = []
        for attr_name in list(self.__dict__.keys()):
            if attr_name not in self._protected_attrs:
                attrs_to_destroy.append(attr_name)
        
        # 按优先级销毁属性
        for attr_name in attrs_to_destroy:
            try:
                val = getattr(self, attr_name, None)
                if val is None:
                    continue
                
                # 销毁属性值
                destroyed = self._destroy_value(val, attr_name, depth + 1)
                if destroyed:
                    destroyed_count += 1
                
                # 清空属性引用
                setattr(self, attr_name, None)
                
            except Exception as e:
                print(f"{indent}[DESTROY ERROR] 清理属性 '{attr_name}' 失败: {e}")
        
        return destroyed_count
    
    def _destroy_value(self, val: Any, attr_name: str, depth: int) -> bool:
        """
        销毁单个值
        """
        indent = "  " * depth
        
        # 防止递归深度过深
        if depth > 10:  # 设置最大递归深度
            print(f"{indent}[DESTROY] 递归深度过深，跳过 '{attr_name}'")
            return False
        
        # 循环引用检测
        obj_id = id(val)
        if obj_id in self._destruction_path:
            print(f"{indent}[DESTROY] 检测到循环引用，跳过 '{attr_name}'")
            return False
        
        try:
            # 添加到销毁路径
            self._destruction_path.add(obj_id)
            
            # 1. 跳过特殊系统对象
            if self._is_system_object(val):
                print(f"{indent}[DESTROY] 跳过系统对象 '{attr_name}': {val.__class__.__name__}")
                return False
            
            # 2. Destroyable 对象
            if isinstance(val, Destroyable) and val is not self:
                print(f"{indent}[DESTROY] 销毁属性 '{attr_name}': {val.__class__.__name__}")
                val.destroy(_depth=depth)
                return True
            
            # 3. 容器类型
            elif isinstance(val, dict):
                return self._destroy_dict(val, attr_name, depth)
            elif isinstance(val, (list, set)):
                return self._destroy_collection(val, attr_name, depth)
            elif isinstance(val, tuple):
                return self._destroy_tuple(val, attr_name, depth)
            
            # 4. 有清理方法的对象（但不是系统对象）
            elif hasattr(val, 'close') and callable(val.close) and not self._is_system_object(val):
                print(f"{indent}[DESTROY] 关闭属性 '{attr_name}': {val.__class__.__name__}")
                val.close()
                return True
            elif hasattr(val, 'cleanup') and callable(val.cleanup) and not self._is_system_object(val):
                print(f"{indent}[DESTROY] 清理属性 '{attr_name}': {val.__class__.__name__}")
                val.cleanup()
                return True
            
            # 5. 复杂对象（有 __dict__ 的自定义对象）
            elif hasattr(val, '__dict__') and not self._is_simple_object(val) and not self._is_system_object(val):
                return self._destroy_complex_object(val, attr_name, depth)
            
            # 6. 基础类型，不需要特殊处理
            else:
                return False
                
        except Exception as e:
            print(f"{indent}[DESTROY ERROR] 销毁值 '{attr_name}' 失败: {e}")
            return False
        finally:
            # 从销毁路径中移除
            self._destruction_path.discard(obj_id)
    def _is_system_object(self, obj: Any) -> bool:
        """判断是否为系统对象（不应该被销毁）"""
        # 基础类型
        if self._is_simple_object(obj):
            return True
        
        # Logging 系统对象
        if hasattr(obj, '__class__'):
            class_name = obj.__class__.__name__
            module_name = getattr(obj.__class__, '__module__', '')
            
            # Python logging 模块的对象
            if module_name.startswith('logging'):
                return True
            
            # 常见的系统类型
            system_classes = {
                'LoggingAdapter', 'Logger', 'Handler', 'Formatter', 
                'Filter', 'LogRecord', 'Manager', 'RootLogger',
                'StreamHandler', 'FileHandler', 'NullHandler',
                'PlaceHolder'
            }
            if class_name in system_classes:
                return True
        
        # 内置模块的对象
        if hasattr(obj, '__module__'):
            builtin_modules = {
                'builtins', 'sys', 'os', 'threading', 'queue',
                'logging', 'logging.handlers', 'io', 'codecs'
            }
            if obj.__module__ in builtin_modules:
                return True
        
        # 线程相关对象
        if hasattr(obj, '__class__') and 'Thread' in obj.__class__.__name__:
            return True
        
        # 队列相关对象
        if hasattr(obj, '__class__') and 'Queue' in obj.__class__.__name__:
            return True
        
        return False
    def _destroy_dict(self, d: dict, attr_name: str, depth: int) -> bool:
        """销毁字典"""
        if not d:
            return False
            
        indent = "  " * depth
        print(f"{indent}[DESTROY] 清理字典 '{attr_name}' ({len(d)} 项)")
        
        for key, value in list(d.items()):
            self._destroy_value(value, f"{attr_name}[{key}]", depth + 1)
        
        d.clear()
        return True
    
    def _destroy_collection(self, collection, attr_name: str, depth: int) -> bool:
        """销毁列表或集合"""
        if not collection:
            return False
            
        indent = "  " * depth
        collection_type = "列表" if isinstance(collection, list) else "集合"
        print(f"{indent}[DESTROY] 清理{collection_type} '{attr_name}' ({len(collection)} 项)")
        
        if isinstance(collection, list):
            for i, item in enumerate(collection):
                self._destroy_value(item, f"{attr_name}[{i}]", depth + 1)
        else:  # set
            for i, item in enumerate(list(collection)):
                self._destroy_value(item, f"{attr_name}[{i}]", depth + 1)
        
        collection.clear()
        return True
    
    def _destroy_tuple(self, t: tuple, attr_name: str, depth: int) -> bool:
        """销毁元组（只能销毁内容，不能修改元组本身）"""
        if not t:
            return False
            
        indent = "  " * depth
        print(f"{indent}[DESTROY] 清理元组 '{attr_name}' ({len(t)} 项)")
        
        for i, item in enumerate(t):
            self._destroy_value(item, f"{attr_name}[{i}]", depth + 1)
        
        return True
    
    def _destroy_complex_object(self, obj: Any, attr_name: str, depth: int) -> bool:
        """销毁复杂对象"""
        indent = "  " * depth
        
        # 检查是否为系统对象
        if self._is_system_object(obj):
            print(f"{indent}[DESTROY] 跳过系统对象 '{attr_name}': {obj.__class__.__name__}")
            return False
        
        print(f"{indent}[DESTROY] 清理复杂对象 '{attr_name}': {obj.__class__.__name__}")
        
        # 限制属性数量，防止清理过多系统属性
        attrs = list(vars(obj).keys())
        if len(attrs) > 50:  # 如果属性过多，可能是系统对象
            print(f"{indent}[DESTROY] 对象属性过多 ({len(attrs)})，可能是系统对象，跳过详细清理")
            return False
        
        # 递归清理对象的属性
        for sub_attr in attrs[:20]:  # 限制处理的属性数量
            try:
                # 跳过私有和系统属性
                if sub_attr.startswith('_') or sub_attr in {'manager', 'parent', 'handlers', 'filters'}:
                    continue
                    
                sub_val = getattr(obj, sub_attr)
                self._destroy_value(sub_val, f"{attr_name}.{sub_attr}", depth + 1)
                setattr(obj, sub_attr, None)
            except Exception as e:
                print(f"{indent}[DESTROY ERROR] 清理子属性 '{sub_attr}' 失败: {e}")
        
        return True
    

    def _is_simple_object(self, obj: Any) -> bool:
        """判断是否为简单对象（不需要特殊清理）"""
        simple_types = (
            str, int, float, bool, bytes, type(None),
            type, type(lambda: None)  # 类型和函数
        )
        
        # 基础类型
        if isinstance(obj, simple_types):
            return True
        
        # 内置模块的对象
        if hasattr(obj, '__module__') and obj.__module__ in ('builtins', 'types'):
            return True
        
        # 没有 __dict__ 的对象通常是简单对象
        if not hasattr(obj, '__dict__'):
            return True
        
        return False
    
    def is_destroyed(self) -> bool:
        """检查对象是否已被销毁"""
        return self._destroyed
    
    def is_destroying(self) -> bool:
        """检查对象是否正在销毁过程中"""
        return self._destruction_started and not self._destroyed
    
    @classmethod
    def get_destruction_stats(cls) -> dict:
        """获取销毁统计信息"""
        return {
            'destroyed_count': len(cls._destroyed_instances),
            'in_progress_count': len(cls._destruction_in_progress),
            'destroyed_instances': list(cls._destroyed_instances),
            'in_progress_instances': list(cls._destruction_in_progress)
        }
    
    @classmethod
    def force_gc_cleanup(cls) -> int:
        """强制垃圾回收"""
        print("[GC] 开始强制垃圾回收...")
        collected = gc.collect()
        print(f"[GC] 垃圾回收完成，回收了 {collected} 个对象")
        return collected
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            if not self._destroyed:
                self.destroy()
        except:
            pass  # 析构函数中不抛出异常


# 便捷函数
def destroy_all(*objects) -> int:
    """
    批量销毁多个对象
    
    Args:
        *objects: 要销毁的对象列表
        
    Returns:
        int: 成功销毁的对象数量
    """
    destroyed_count = 0
    
    for obj in objects:
        try:
            if isinstance(obj, Destroyable):
                if obj.destroy():
                    destroyed_count += 1
            elif hasattr(obj, 'destroy') and callable(obj.destroy):
                obj.destroy()
                destroyed_count += 1
            else:
                print(f"[DESTROY WARNING] 对象 {obj.__class__.__name__} 不支持销毁")
        except Exception as e:
            print(f"[DESTROY ERROR] 销毁对象失败: {e}")
    
    print(f"[DESTROY] 批量销毁完成，成功销毁 {destroyed_count}/{len(objects)} 个对象")
    return destroyed_count


def deep_clear(obj, _depth=0):
    """
    递归清空对象中嵌套的 dict、list、set、tuple 等容器中的所有引用。
    保持向后兼容的独立函数版本。
    """
    if isinstance(obj, Destroyable):
        obj.destroy(_depth=_depth)
        return
    
    indent = "  " * _depth
    
    if isinstance(obj, dict):
        print(f"{indent}[CLEAR] 清理字典 ({len(obj)} 项)")
        for key in list(obj.keys()):
            deep_clear(obj[key], _depth + 1)
            obj[key] = None
        obj.clear()

    elif isinstance(obj, list):
        print(f"{indent}[CLEAR] 清理列表 ({len(obj)} 项)")
        for i in range(len(obj)):
            deep_clear(obj[i], _depth + 1)
            obj[i] = None
        obj.clear()

    elif isinstance(obj, set):
        print(f"{indent}[CLEAR] 清理集合 ({len(obj)} 项)")
        for item in list(obj):
            deep_clear(item, _depth + 1)
        obj.clear()

    elif isinstance(obj, tuple):
        print(f"{indent}[CLEAR] 清理元组 ({len(obj)} 项)")
        for item in obj:
            deep_clear(item, _depth + 1)

    elif hasattr(obj, "destroy") and callable(obj.destroy):
        print(f"{indent}[CLEAR] 销毁 {obj.__class__.__name__}")
        obj.destroy()

    elif hasattr(obj, "__dict__"):
        print(f"{indent}[CLEAR] 清理对象 {obj.__class__.__name__}")
        for attr in list(vars(obj).keys()):
            deep_clear(getattr(obj, attr), _depth + 1)
            setattr(obj, attr, None)