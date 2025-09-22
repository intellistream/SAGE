from abc import abstractmethod
from typing import Any, Optional, Dict, List
from sage.core.api.function.base_function import BaseFunction


class BaseJoinFunction(BaseFunction):
    """
    Base class for Join functions that handle multi-stream data joining.
    
    The operator will call execute() with structured input containing:
    - payload: the actual data
    - key: the partition key that triggered this call  
    - tag: which stream this data came from (0 for left, 1 for right)
    
    The function manages its own join logic and state.
    """
    
    @property 
    def is_join(self) -> bool:
        """Identify this as a Join function for operator routing"""
        return True
    
    @abstractmethod
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        """
        Process data from a specific stream and return join results.
        
        Args:
            payload: The actual data from the stream
            key: The partition key (extracted by keyby)
            tag: Stream identifier (0=left/first stream, 1=right/second stream)
            
        Returns:
            List[Any]: List of join results to emit (can be empty)
                      Return empty list if no output should be generated
        
        Note:
            The function should manage its own state to correlate data
            between different streams. Common patterns:
            - Cache data from one stream until matching data arrives
            - Implement time-based windows for temporal joins
            - Handle different join semantics (inner, outer, etc.)
        """
        pass


# 具体实现示例
class UserOrderInnerJoin(BaseJoinFunction):
    """
    Inner Join: 只有当用户和订单数据都存在时才输出
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}      # {user_id: user_data}
        self.order_cache = {}     # {user_id: [order_data, ...]}
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        results = []
        
        if tag == 0:  # 用户数据流
            # 缓存用户数据
            self.user_cache[key] = payload
            
            # 检查是否有对应的订单
            if key in self.order_cache:
                user_data = payload
                for order_data in self.order_cache[key]:
                    joined = self._create_join_result(user_data, order_data, key)
                    results.append(joined)
                # 清理已匹配的订单（inner join特性）
                del self.order_cache[key]
                
        elif tag == 1:  # 订单数据流
            # 检查是否有对应的用户
            if key in self.user_cache:
                user_data = self.user_cache[key]
                joined = self._create_join_result(user_data, payload, key)
                results.append(joined)
            else:
                # 缓存订单等待用户数据
                if key not in self.order_cache:
                    self.order_cache[key] = []
                self.order_cache[key].append(payload)
        
        return results
    
    def _create_join_result(self, user_data: Any, order_data: Any, user_id: Any) -> Dict:
        return {
            "user_id": user_id,
            "user_name": user_data.get("name"),
            "user_email": user_data.get("email"),
            "order_id": order_data.get("id"),
            "order_amount": order_data.get("amount"),
            "join_timestamp": order_data.get("timestamp")
        }


class UserOrderLeftJoin(BaseJoinFunction):
    """
    Left Outer Join: 保留所有用户，订单可能为空
    """
    
    def __init__(self, timeout_ms: int = 30000, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}      # {user_id: (user_data, timestamp)}
        self.order_cache = {}     # {user_id: [order_data, ...]}
        self.timeout_ms = timeout_ms
        import time
        self.current_time = lambda: int(time.time() * 1000)
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        results = []
        current_time = self.current_time()
        
        if tag == 0:  # 用户数据流
            # 检查是否有对应的订单
            if key in self.order_cache:
                user_data = payload
                for order_data in self.order_cache[key]:
                    joined = self._create_join_result(user_data, order_data, key)
                    results.append(joined)
                del self.order_cache[key]
            else:
                # 缓存用户数据，设置超时
                self.user_cache[key] = (payload, current_time)
                
        elif tag == 1:  # 订单数据流
            if key in self.user_cache:
                user_data, _ = self.user_cache[key]
                joined = self._create_join_result(user_data, payload, key)
                results.append(joined)
                del self.user_cache[key]
            else:
                # 缓存订单
                if key not in self.order_cache:
                    self.order_cache[key] = []
                self.order_cache[key].append(payload)
        
        # 检查超时的用户数据（Left Join特性：输出没有订单的用户）
        expired_users = []
        for user_id, (user_data, timestamp) in self.user_cache.items():
            if current_time - timestamp > self.timeout_ms:
                # 输出没有订单的用户
                no_order_result = self._create_join_result(user_data, None, user_id)
                results.append(no_order_result)
                expired_users.append(user_id)
        
        # 清理过期用户
        for user_id in expired_users:
            del self.user_cache[user_id]
        
        return results
    
    def _create_join_result(self, user_data: Any, order_data: Any, user_id: Any) -> Dict:
        return {
            "user_id": user_id,
            "user_name": user_data.get("name"),
            "user_email": user_data.get("email"),
            "order_id": order_data.get("id") if order_data else None,
            "order_amount": order_data.get("amount") if order_data else 0,
            "has_order": order_data is not None
        }


class WindowedEventJoin(BaseJoinFunction):
    """
    基于时间窗口的事件关联
    """
    
    def __init__(self, window_ms: int = 60000, **kwargs):
        super().__init__(**kwargs)
        self.window_ms = window_ms
        self.event_buffer = {}  # {key: [(event_data, timestamp, tag), ...]}
        import time
        self.current_time = lambda: int(time.time() * 1000)
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        current_time = self.current_time()
        results = []
        
        # 清理过期事件
        self._cleanup_expired_events(current_time)
        
        # 添加当前事件到缓冲区
        if key not in self.event_buffer:
            self.event_buffer[key] = []
        self.event_buffer[key].append((payload, current_time, tag))
        
        # 检查窗口内的事件组合
        if key in self.event_buffer:
            window_events = self._get_window_events(key, current_time)
            
            # 按业务逻辑组合事件
            combinations = self._find_event_combinations(window_events)
            for combo in combinations:
                joined_event = self._create_event_combination(combo, key)
                results.append(joined_event)
        
        return results
    
    def _cleanup_expired_events(self, current_time: int):
        cutoff_time = current_time - self.window_ms
        
        for key in list(self.event_buffer.keys()):
            valid_events = [
                (data, ts, tag) for data, ts, tag in self.event_buffer[key]
                if ts >= cutoff_time
            ]
            if valid_events:
                self.event_buffer[key] = valid_events
            else:
                del self.event_buffer[key]
    
    def _get_window_events(self, key: Any, current_time: int) -> List:
        cutoff_time = current_time - self.window_ms
        return [
            (data, ts, tag) for data, ts, tag in self.event_buffer[key]
            if ts >= cutoff_time
        ]
    
    def _find_event_combinations(self, events: List) -> List:
        # 示例：查找登录后的购买事件
        combinations = []
        login_events = [(data, ts) for data, ts, tag in events if tag == 0 and data.get("action") == "login"]
        purchase_events = [(data, ts) for data, ts, tag in events if tag == 1 and data.get("action") == "purchase"]
        
        for login_data, login_time in login_events:
            for purchase_data, purchase_time in purchase_events:
                if purchase_time > login_time:  # 购买在登录之后
                    combinations.append((login_data, purchase_data))
        
        return combinations
    
    def _create_event_combination(self, combo, key: Any) -> Dict:
        login_data, purchase_data = combo
        return {
            "user_id": key,
            "login_time": login_data.get("timestamp"),
            "purchase_time": purchase_data.get("timestamp"),
            "purchase_amount": purchase_data.get("amount"),
            "time_to_purchase": purchase_data.get("timestamp") - login_data.get("timestamp"),
            "conversion": True
        }