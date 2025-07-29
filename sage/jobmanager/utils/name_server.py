from typing import Set
import threading

class NameServer:
    """简单的名称服务器，确保对象名称唯一性"""
    
    _registered_names: Set[str] = set()
    _name_counters: dict = {}
    _lock = threading.RLock()
    
    @classmethod
    def register_name(cls, name: str) -> str:
        """
        注册一个名称，如果冲突则自动添加数字后缀
        
        Args:
            name: 期望的名称
            
        Returns:
            处理完冲突后的唯一名称
        """
        if not name or not name.strip():
            raise ValueError("名称不能为空")
        
        name = name.strip()
        
        with cls._lock:
            # 如果名称不冲突，直接注册
            if name not in cls._registered_names:
                cls._registered_names.add(name)
                return name
            
            # 处理名称冲突，添加数字后缀
            counter = cls._name_counters.get(name, 0)
            while True:
                counter += 1
                candidate = f"{name}_{counter}"
                if candidate not in cls._registered_names:
                    cls._registered_names.add(candidate)
                    cls._name_counters[name] = counter
                    return candidate
    
    @classmethod
    def unregister_name(cls, name: str) -> bool:
        """
        注销一个名称
        
        Args:
            name: 要注销的名称
            
        Returns:
            是否成功注销
        """
        with cls._lock:
            if name in cls._registered_names:
                cls._registered_names.remove(name)
                return True
            return False
    
    @classmethod
    def is_name_available(cls, name: str) -> bool:
        """检查名称是否可用"""
        with cls._lock:
            return name not in cls._registered_names
    
    @classmethod
    def clear_all(cls) -> None:
        """清空所有注册的名称"""
        with cls._lock:
            cls._registered_names.clear()
            cls._name_counters.clear()
    
    @classmethod
    def get_registered_count(cls) -> int:
        """获取已注册名称数量"""
        with cls._lock:
            return len(cls._registered_names)
        
def get_name(base: str) -> str:
    """
    获取一个唯一名称，是对 NameServer.register_name 的简洁封装。
    
    Args:
        base: 基础名称，如 "retriever"
        
    Returns:
        唯一化后的名称，如 "retriever_2"
    """
    return NameServer.register_name(base)