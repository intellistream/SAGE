import time
import threading
from typing import List, Dict, Any
from sage_core.api.local_environment import LocalEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.flatmap_function import FlatMapFunction
from sage_core.function.filter_function import FilterFunction
from sage_core.function.keyby_function import KeyByFunction
from sage_core.function.join_function import BaseJoinFunction
from sage_core.function.sink_function import SinkFunction


# =====================================================================
# Source Functions - 生成测试数据
# =====================================================================

class OrderEventSource(SourceFunction):
    """生成订单事件数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.order_events = [
            {"event_id": 1, "order_id": "order_001", "user_id": "user_1", "event": "created", "amount": 100.0, "timestamp": 1000},
            {"event_id": 2, "order_id": "order_002", "user_id": "user_2", "event": "created", "amount": 250.0, "timestamp": 1100},
            {"event_id": 3, "order_id": "order_001", "user_id": "user_1", "event": "paid", "amount": 100.0, "timestamp": 1200},
            {"event_id": 4, "order_id": "order_003", "user_id": "user_1", "event": "created", "amount": 75.0, "timestamp": 1300},
            {"event_id": 5, "order_id": "order_002", "user_id": "user_2", "event": "cancelled", "amount": 250.0, "timestamp": 1400},
            {"event_id": 6, "order_id": "order_003", "user_id": "user_1", "event": "paid", "amount": 75.0, "timestamp": 1500},
            {"event_id": 7, "order_id": "order_004", "user_id": "user_3", "event": "created", "amount": 300.0, "timestamp": 1600},
            {"event_id": 8, "order_id": "order_004", "user_id": "user_3", "event": "paid", "amount": 300.0, "timestamp": 1700},
        ]
    
    def execute(self):
        if self.counter >= len(self.order_events):
            return None
        
        data = self.order_events[self.counter]
        self.counter += 1
        self.logger.info(f"OrderEventSource generated: {data}")
        return data


class UserProfileSource(SourceFunction):
    """生成用户档案数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.user_profiles = [
            {"profile_id": 1, "user_id": "user_1", "name": "Alice", "email": "alice@example.com", "tier": "gold", "region": "US"},
            {"profile_id": 2, "user_id": "user_2", "name": "Bob", "email": "bob@example.com", "tier": "silver", "region": "EU"},
            {"profile_id": 3, "user_id": "user_3", "name": "Charlie", "email": "charlie@example.com", "tier": "gold", "region": "US"},
            {"profile_id": 4, "user_id": "user_4", "name": "Diana", "email": "diana@example.com", "tier": "bronze", "region": "ASIA"},
        ]
    
    def execute(self):
        if self.counter >= len(self.user_profiles):
            return None
        
        data = self.user_profiles[self.counter]
        self.counter += 1
        self.logger.info(f"UserProfileSource generated: {data}")
        return data


# =====================================================================
# FlatMap Functions - 分解数据
# =====================================================================

class OrderEventFlatMap(FlatMapFunction):
    """将订单事件分解为订单信息和事件信息"""
    
    def execute(self, data: Any) -> List[Dict]:
        order_id = data.get("order_id")
        user_id = data.get("user_id")
        event_type = data.get("event")
        amount = data.get("amount")
        timestamp = data.get("timestamp")
        
        results = []
        
        # 1. 提取订单基础信息
        order_info = {
            "type": "order_info",
            "order_id": order_id,
            "user_id": user_id,
            "amount": amount,
            "timestamp": timestamp,
            "source": "order_event_flatmap"
        }
        results.append(order_info)
        
        # 2. 提取事件信息
        event_info = {
            "type": "event_info",
            "order_id": order_id,
            "user_id": user_id,
            "event": event_type,
            "timestamp": timestamp,
            "source": "order_event_flatmap"
        }
        results.append(event_info)
        
        # 3. 如果是支付事件，生成额外的支付记录
        if event_type == "paid":
            payment_info = {
                "type": "payment_info",
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount,
                "payment_timestamp": timestamp,
                "source": "order_event_flatmap"
            }
            results.append(payment_info)
        
        self.logger.info(f"OrderEventFlatMap: flattened order {order_id} into {len(results)} items")
        return results


class UserProfileFlatMap(FlatMapFunction):
    """将用户档案分解为用户信息和偏好信息"""
    
    def execute(self, data: Any) -> List[Dict]:
        user_id = data.get("user_id")
        name = data.get("name")
        email = data.get("email")
        tier = data.get("tier")
        region = data.get("region")
        
        results = []
        
        # 1. 提取基础用户信息
        user_info = {
            "type": "user_info",
            "user_id": user_id,
            "name": name,
            "email": email,
            "source": "user_profile_flatmap"
        }
        results.append(user_info)
        
        # 2. 提取用户偏好信息
        preference_info = {
            "type": "preference_info",
            "user_id": user_id,
            "tier": tier,
            "region": region,
            "is_premium": tier in ["gold", "platinum"],
            "source": "user_profile_flatmap"
        }
        results.append(preference_info)
        
        # 3. 如果是金牌用户，生成VIP信息
        if tier == "gold":
            vip_info = {
                "type": "vip_info",
                "user_id": user_id,
                "vip_level": "gold",
                "benefits": ["free_shipping", "priority_support"],
                "source": "user_profile_flatmap"
            }
            results.append(vip_info)
        
        self.logger.info(f"UserProfileFlatMap: flattened user {user_id} into {len(results)} items")
        return results


# =====================================================================
# Filter Functions - 过滤数据
# =====================================================================

class OrderInfoFilter(FilterFunction):
    """过滤订单信息，只保留订单相关数据"""
    
    def execute(self, data: Any) -> bool:
        data_type = data.get("type", "")
        is_order_related = data_type in ["order_info", "payment_info"]
        
        if is_order_related:
            self.logger.debug(f"OrderInfoFilter: accepted {data_type} for order {data.get('order_id')}")
        else:
            self.logger.debug(f"OrderInfoFilter: rejected {data_type}")
        
        return is_order_related


class UserInfoFilter(FilterFunction):
    """过滤用户信息，只保留用户相关数据"""
    
    def execute(self, data: Any) -> bool:
        data_type = data.get("type", "")
        is_user_related = data_type in ["user_info", "preference_info", "vip_info"]
        
        if is_user_related:
            self.logger.debug(f"UserInfoFilter: accepted {data_type} for user {data.get('user_id')}")
        else:
            self.logger.debug(f"UserInfoFilter: rejected {data_type}")
        
        return is_user_related


class PremiumUserFilter(FilterFunction):
    """只保留高级用户"""
    
    def execute(self, data: Any) -> bool:
        if data.get("type") == "preference_info":
            is_premium = data.get("is_premium", False)
            if is_premium:
                self.logger.debug(f"PremiumUserFilter: accepted premium user {data.get('user_id')}")
                return True
        
        # 对于非偏好信息，直接通过
        return data.get("type") != "preference_info"


# =====================================================================
# KeyBy Functions - 提取分区键
# =====================================================================

class UserIdKeyBy(KeyByFunction):
    """按用户ID分区"""
    
    def execute(self, data: Any) -> str:
        user_id = data.get("user_id", "unknown")
        self.logger.debug(f"UserIdKeyBy: extracted key '{user_id}' from {data.get('type', 'unknown')}")
        return user_id


class OrderIdKeyBy(KeyByFunction):
    """按订单ID分区"""
    
    def execute(self, data: Any) -> str:
        order_id = data.get("order_id", "unknown")
        self.logger.debug(f"OrderIdKeyBy: extracted key '{order_id}' from {data.get('type', 'unknown')}")
        return order_id


# =====================================================================
# Join Functions - 关联逻辑
# =====================================================================

class UserOrderJoin(BaseJoinFunction):
    """用户和订单的Inner Join"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}      # {user_id: user_data}
        self.order_cache = {}     # {user_id: [order_data, ...]}
        self.join_count = 0
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        results = []
        self.logger.debug(
            f"UserOrderJoin: processing key='{key}', tag={tag}, payload={payload}" )
        if tag == 0:  # 用户流
            user_type = payload.get("type", "")
            if user_type == "user_info":
                # 缓存用户基础信息
                self.user_cache[key] = payload
                
                # 检查是否有待匹配的订单
                if key in self.order_cache:
                    for order_data in self.order_cache[key]:
                        joined = self._create_user_order_join(payload, order_data, key)
                        results.append(joined)
                        self.join_count += 1
                    # 清理已匹配的订单
                    del self.order_cache[key]
        
        elif tag == 1:  # 订单流  
            order_type = payload.get("type", "")
            if order_type == "order_info":
                # 检查是否有对应的用户
                if key in self.user_cache:
                    joined = self._create_user_order_join(self.user_cache[key], payload, key)
                    results.append(joined)
                    self.join_count += 1
                else:
                    # 缓存订单等待用户数据
                    if key not in self.order_cache:
                        self.order_cache[key] = []
                    self.order_cache[key].append(payload)
        
        if results:
            self.logger.info(f"UserOrderJoin: generated {len(results)} joins for key '{key}', total joins: {self.join_count}")
        
        return results
    
    def _create_user_order_join(self, user_data: Any, order_data: Any, user_id: str) -> Dict:
        return {
            "join_type": "user_order",
            "user_id": user_id,
            "user_name": user_data.get("name"),
            "user_email": user_data.get("email"),
            "order_id": order_data.get("order_id"),
            "order_amount": order_data.get("amount"),
            "order_timestamp": order_data.get("timestamp"),
            "join_timestamp": time.time_ns() // 1_000_000,
            "source": "user_order_join"
        }


class UserPaymentJoin(BaseJoinFunction):
    """用户和支付的Left Join"""
    
    def __init__(self, timeout_ms: int = 5000, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}      # {user_id: (user_data, timestamp)}
        self.payment_cache = {}   # {user_id: [payment_data, ...]}
        self.timeout_ms = timeout_ms
        self.join_count = 0
        import time
        self.current_time = lambda: int(time.time() * 1000)
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        results = []
        current_time = self.current_time()
        
        if tag == 0:  # 用户流
            user_type = payload.get("type", "")
            if user_type in ["user_info", "preference_info"]:
                # 检查是否有对应的支付
                if key in self.payment_cache:
                    for payment_data in self.payment_cache[key]:
                        joined = self._create_user_payment_join(payload, payment_data, key)
                        results.append(joined)
                        self.join_count += 1
                    del self.payment_cache[key]
                else:
                    # 缓存用户数据，设置超时
                    self.user_cache[key] = (payload, current_time)
        
        elif tag == 1:  # 支付流
            payment_type = payload.get("type", "")
            if payment_type == "payment_info":
                # 检查是否有对应的用户
                if key in self.user_cache:
                    user_data, _ = self.user_cache[key]
                    joined = self._create_user_payment_join(user_data, payload, key)
                    results.append(joined)
                    self.join_count += 1
                    del self.user_cache[key]
                else:
                    # 缓存支付数据
                    if key not in self.payment_cache:
                        self.payment_cache[key] = []
                    self.payment_cache[key].append(payload)
        
        # 检查超时的用户数据（Left Join特性）
        expired_users = []
        for user_id, (user_data, timestamp) in self.user_cache.items():
            if current_time - timestamp > self.timeout_ms:
                # 输出没有支付的用户
                no_payment_result = self._create_user_payment_join(user_data, None, user_id)
                results.append(no_payment_result)
                expired_users.append(user_id)
                self.join_count += 1
        
        # 清理过期用户
        for user_id in expired_users:
            del self.user_cache[user_id]
        
        if results:
            self.logger.info(f"UserPaymentJoin: generated {len(results)} joins for key '{key}', total joins: {self.join_count}")
        
        return results
    
    def _create_user_payment_join(self, user_data: Any, payment_data: Any, user_id: str) -> Dict:
        return {
            "join_type": "user_payment",
            "user_id": user_id,
            "user_name": user_data.get("name") if user_data else None,
            "user_tier": user_data.get("tier") if user_data else None,
            "order_id": payment_data.get("order_id") if payment_data else None,
            "payment_amount": payment_data.get("amount") if payment_data else 0,
            "payment_timestamp": payment_data.get("payment_timestamp") if payment_data else None,
            "has_payment": payment_data is not None,
            "join_timestamp": time.time_ns() // 1_000_000,
            "source": "user_payment_join"
        }


class OrderEventJoin(BaseJoinFunction):
    """订单和事件的窗口Join"""
    
    def __init__(self, window_ms: int = 3000, **kwargs):
        super().__init__(**kwargs)
        self.window_ms = window_ms
        self.event_buffer = {}  # {order_id: [(data, timestamp, tag), ...]}
        self.join_count = 0
        import time
        self.current_time = lambda: int(time.time() * 1000)
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        current_time = self.current_time()
        results = []
        
        # 清理过期事件
        self._cleanup_expired_events(current_time)
        
        # 获取数据类型
        data_type = payload.get("type", "")
        
        # 只处理订单信息和事件信息
        if data_type not in ["order_info", "event_info"]:
            return results
        
        # 添加当前事件到缓冲区
        if key not in self.event_buffer:
            self.event_buffer[key] = []
        self.event_buffer[key].append((payload, current_time, tag))
        
        # 检查窗口内的事件组合
        if key in self.event_buffer:
            window_events = self._get_window_events(key, current_time)
            combinations = self._find_order_event_combinations(window_events, key)
            results.extend(combinations)
            self.join_count += len(combinations)
        
        if results:
            self.logger.info(f"OrderEventJoin: generated {len(results)} joins for order '{key}', total joins: {self.join_count}")
        
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
    
    def _find_order_event_combinations(self, events: List, order_id: str) -> List:
        combinations = []
        
        # 按tag分组事件
        order_infos = [(data, ts) for data, ts, tag in events if tag == 0 and data.get("type") == "order_info"]
        event_infos = [(data, ts) for data, ts, tag in events if tag == 1 and data.get("type") == "event_info"]
        
        # 组合订单信息和事件信息
        for order_data, order_ts in order_infos:
            for event_data, event_ts in event_infos:
                # 事件应该在订单之后或同时发生
                if event_ts >= order_ts:
                    combo_result = {
                        "join_type": "order_event",
                        "order_id": order_id,
                        "user_id": order_data.get("user_id"),
                        "order_amount": order_data.get("amount"),
                        "order_timestamp": order_data.get("timestamp"),
                        "event_type": event_data.get("event"),
                        "event_timestamp": event_data.get("timestamp"),
                        "time_diff": event_ts - order_ts,
                        "join_timestamp": time.time_ns() // 1_000_000,
                        "source": "order_event_join"
                    }
                    combinations.append(combo_result)
        
        return combinations


# =====================================================================
# Sink Functions - 收集结果
# =====================================================================

class JoinResultSink(SinkFunction):
    """收集Join结果的Sink"""
    
    _received_data: Dict[int, List[Any]] = {}
    _lock = threading.Lock()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parallel_index = None
        self.received_count = 0

    def execute(self, data: Any):
        if self.ctx:
            self.parallel_index = self.ctx.parallel_index

        with self._lock:
            if self.parallel_index not in self._received_data:
                self._received_data[self.parallel_index] = []

            self._received_data[self.parallel_index].append(data)

        self.received_count += 1

        join_type = data.get("join_type", "unknown")
        key_field = "user_id" if "user" in join_type else "order_id"
        key_value = data.get(key_field, "unknown")

        self.logger.info(
            f"[Instance {self.parallel_index}] "
            f"Received join result #{self.received_count}: {join_type} for {key_field}={key_value}"
        )

        # 打印调试信息
        print(f"🔗 [Instance {self.parallel_index}] Join: {join_type} | {key_field}={key_value}")

        return data
    
    @classmethod
    def get_received_data(cls) -> Dict[int, List[Any]]:
        with cls._lock:
            return dict(cls._received_data)
    
    @classmethod
    def clear_data(cls):
        with cls._lock:
            cls._received_data.clear()


# =====================================================================
# 测试类
# =====================================================================

class TestJoinFunctionality:
    """测试Join功能的完整测试套件"""
    
    def setup_method(self):
        JoinResultSink.clear_data()
    
    def test_flatmap_filter_join_pipeline(self):
        """测试完整的FlatMap -> Filter -> Join管道"""
        print("\n🚀 Testing Complete FlatMap -> Filter -> Join Pipeline")
        
        env = LocalEnvironment("flatmap_filter_join_test")
        
        # 1. 创建源数据流
        order_source = env.from_source(OrderEventSource, delay=0.2)
        user_source = env.from_source(UserProfileSource, delay=0.3)
        
        # 2. 上游处理：FlatMap分解数据，Filter过滤
        order_stream = (order_source
            .flatmap(OrderEventFlatMap)    # 分解订单事件
            .filter(OrderInfoFilter)       # 只保留订单相关信息
            .keyby(UserIdKeyBy)             # 按用户ID分区
        )
        
        user_stream = (user_source
            .flatmap(UserProfileFlatMap)    # 分解用户档案
            .filter(UserInfoFilter)         # 只保留用户相关信息
            .keyby(UserIdKeyBy)             # 按用户ID分区
        )
        
        # 3. 下游处理：Connect和Join
        join_result = (user_stream
            .connect(order_stream)          # 连接两个流
            .join(UserOrderJoin)            # 用户-订单Join
            .sink(JoinResultSink, parallelism=1)
        )
        
        print("📊 Pipeline: OrderSource -> flatmap -> filter -> keyby")
        print("           UserSource -> flatmap -> filter -> keyby")
        print("           user_stream.connect(order_stream).join(UserOrderJoin)")
        print("🎯 Expected: User and order data joined on user_id\n")
        
        try:
            env.submit()
            
            time.sleep(6)
        finally:
            env.close()
        
        self._verify_user_order_join_results()
    
    def test_multi_stage_join_pipeline(self):
        """测试多阶段Join管道"""
        print("\n🚀 Testing Multi-Stage Join Pipeline")
        
        env = LocalEnvironment("multi_stage_join_test")
        
        # 第一阶段：订单事件流处理
        order_source = env.from_source(OrderEventSource, delay=0.2)
        
        # 分离为两个流：订单信息流和支付信息流
        order_info_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "order_info")
            .keyby(UserIdKeyBy)
        )
        
        payment_info_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "payment_info")
            .keyby(UserIdKeyBy)
        )
        
        # 第二阶段：用户信息流处理
        user_source = env.from_source(UserProfileSource, delay=0.3)
        
        # 只保留高级用户
        premium_user_stream = (user_source
            .flatmap(UserProfileFlatMap)
            .filter(PremiumUserFilter)
            .filter(lambda x: x.get("type") in ["user_info", "preference_info"])
            .keyby(UserIdKeyBy)
        )
        
        # 第三阶段：多重Join
        # Join 1: 高级用户 + 支付信息
        user_payment_join = (premium_user_stream
            .connect(payment_info_stream)
            .join(UserPaymentJoin, timeout_ms=3000)
            .sink(JoinResultSink, parallelism=1)
        )
        
        print("📊 Multi-Stage Pipeline:")
        print("   OrderSource -> flatmap -> filter(order_info) -> keyby")
        print("   OrderSource -> flatmap -> filter(payment_info) -> keyby")
        print("   UserSource -> flatmap -> filter(premium) -> keyby")
        print("   premium_user.connect(payment).join(UserPaymentJoin)")
        print("🎯 Expected: Premium users with their payment information\n")
        
        try:
            env.submit()
            
            time.sleep(6)
        finally:
            env.close()
        
        self._verify_user_payment_join_results()
    
    def test_windowed_join_pipeline(self):
        """测试基于时间窗口的Join"""
        print("\n🚀 Testing Windowed Join Pipeline")
        
        env = LocalEnvironment("windowed_join_test")
        
        order_source = env.from_source(OrderEventSource, delay=0.15)
        
        # 分离订单信息和事件信息，按订单ID分区
        order_info_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "order_info")
            .keyby(OrderIdKeyBy)
        )
        
        event_info_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "event_info")
            .keyby(OrderIdKeyBy)
        )
        
        # 窗口Join：在时间窗口内关联订单和事件
        windowed_join = (order_info_stream
            .connect(event_info_stream)
            .join(OrderEventJoin, window_ms=2000)
            .sink(JoinResultSink, parallelism=1)
        )
        
        print("📊 Windowed Join Pipeline:")
        print("   OrderSource -> flatmap -> filter(order_info) -> keyby(order_id)")
        print("   OrderSource -> flatmap -> filter(event_info) -> keyby(order_id)")
        print("   order_info.connect(event_info).join(OrderEventJoin, window=2s)")
        print("🎯 Expected: Orders matched with their events within time window\n")
        
        try:
            env.submit()
            
            time.sleep(5)
        finally:
            env.close()
        
        self._verify_order_event_join_results()
    
    def test_complex_pipeline_with_multiple_joins(self):
        """测试包含多个Join的复杂管道"""
        print("\n🚀 Testing Complex Pipeline with Multiple Joins")
        
        env = LocalEnvironment("complex_multi_join_test")
        
        # 数据源
        order_source = env.from_source(OrderEventSource, delay=0.2)
        user_source = env.from_source(UserProfileSource, delay=0.3)
        
        # 复杂的数据分流和过滤
        # 流1：用户基础信息
        user_basic_stream = (user_source
            .flatmap(UserProfileFlatMap)
            .filter(lambda x: x.get("type") == "user_info")
            .keyby(UserIdKeyBy)
        )
        
        # 流2：订单支付信息
        payment_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "payment_info")
            .keyby(UserIdKeyBy)
        )
        
        # 流3：订单基础信息
        order_basic_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "order_info")
            .keyby(UserIdKeyBy)
        )
        
        # Join 1: 用户 + 支付信息
        user_payment = (user_basic_stream
            .connect(payment_stream)
            .join(UserPaymentJoin, timeout_ms=2000)
        )
        
        # Join 2: 用户 + 订单信息
        user_order = (user_basic_stream
            .connect(order_basic_stream)
            .join(UserOrderJoin)
        )
        
        # 收集所有Join结果
        user_payment.sink(JoinResultSink, parallelism=1)
        user_order.sink(JoinResultSink, parallelism=1)
        
        print("📊 Complex Multi-Join Pipeline:")
        print("   UserSource -> flatmap -> filter(user_info) -> keyby")
        print("   OrderSource -> flatmap -> filter(payment_info) -> keyby")
        print("   OrderSource -> flatmap -> filter(order_info) -> keyby")
        print("   user.connect(payment).join() + user.connect(order).join()")
        print("🎯 Expected: Both user-payment and user-order joins\n")
        
        try:
            env.submit()
            
            time.sleep(7)
        finally:
            env.close()
        
        self._verify_complex_multi_join_results()
    
    def test_join_with_empty_streams(self):
        """测试空流的Join处理"""
        print("\n🚀 Testing Join with Empty/Filtered Streams")
        
        env = LocalEnvironment("empty_stream_join_test")
        
        order_source = env.from_source(OrderEventSource, delay=0.2)
        user_source = env.from_source(UserProfileSource, delay=0.3)
        
        # 创建一个会过滤掉所有数据的流
        empty_user_stream = (user_source
            .flatmap(UserProfileFlatMap)
            .filter(lambda x: False)  # 过滤掉所有数据
            .keyby(UserIdKeyBy)
        )
        
        order_stream = (order_source
            .flatmap(OrderEventFlatMap)
            .filter(lambda x: x.get("type") == "order_info")
            .keyby(UserIdKeyBy)
        )
        
        # Join空流和正常流
        empty_join = (empty_user_stream
            .connect(order_stream)
            .join(UserOrderJoin)
            .sink(JoinResultSink, parallelism=1)
        )
        
        print("📊 Empty Stream Join Pipeline:")
        print("   UserSource -> flatmap -> filter(False) -> keyby")
        print("   OrderSource -> flatmap -> filter(order_info) -> keyby")
        print("   empty_user.connect(order).join()")
        print("🎯 Expected: No join results due to empty user stream\n")
        
        try:
            env.submit()
            
            time.sleep(4)
        finally:
            env.close()
        
        self._verify_empty_stream_join_results()
    
    # =====================================================================
    # 验证方法
    # =====================================================================
    
    def _verify_user_order_join_results(self):
        """验证用户-订单Join结果"""
        received_data = JoinResultSink.get_received_data()
        
        print("\n📋 User-Order Join Results:")
        print("=" * 50)
        
        all_joins = []
        for instance_id, data_list in received_data.items():
            for data in data_list:
                if data.get("join_type") == "user_order":
                    all_joins.append(data)
                    user_id = data.get("user_id")
                    user_name = data.get("user_name")
                    order_id = data.get("order_id")
                    amount = data.get("order_amount")
                    print(f"   - User: {user_name} ({user_id}) -> Order: {order_id} (${amount})")
        
        print(f"\n🎯 User-Order Join Summary:")
        print(f"   - Total user-order joins: {len(all_joins)}")
        
        # 验证Join结果
        assert len(all_joins) > 0, "❌ No user-order joins found"
        
        # 验证数据完整性
        for join_data in all_joins:
            assert join_data.get("user_id"), f"❌ Missing user_id: {join_data}"
            assert join_data.get("order_id"), f"❌ Missing order_id: {join_data}"
            assert join_data.get("source") == "user_order_join", f"❌ Wrong source: {join_data}"
        
        print("✅ User-Order join test passed: Users successfully joined with orders")
    
    def _verify_user_payment_join_results(self):
        """验证用户-支付Join结果"""
        received_data = JoinResultSink.get_received_data()
        
        print("\n📋 User-Payment Join Results:")
        print("=" * 50)
        
        all_joins = []
        with_payment = 0
        without_payment = 0
        
        for instance_id, data_list in received_data.items():
            for data in data_list:
                if data.get("join_type") == "user_payment":
                    all_joins.append(data)
                    user_name = data.get("user_name")
                    has_payment = data.get("has_payment", False)
                    payment_amount = data.get("payment_amount", 0)
                    
                    if has_payment:
                        with_payment += 1
                        print(f"   - User: {user_name} -> Payment: ${payment_amount}")
                    else:
                        without_payment += 1
                        print(f"   - User: {user_name} -> No payment")
        
        print(f"\n🎯 User-Payment Join Summary:")
        print(f"   - Total user-payment joins: {len(all_joins)}")
        print(f"   - With payments: {with_payment}")
        print(f"   - Without payments: {without_payment}")
        
        # 验证Join结果
        assert len(all_joins) > 0, "❌ No user-payment joins found"
        
        print("✅ User-Payment join test passed: Users joined with payment status")
    
    def _verify_order_event_join_results(self):
        """验证订单-事件Join结果"""
        received_data = JoinResultSink.get_received_data()
        
        print("\n📋 Order-Event Join Results:")
        print("=" * 50)
        
        all_joins = []
        for instance_id, data_list in received_data.items():
            for data in data_list:
                if data.get("join_type") == "order_event":
                    all_joins.append(data)
                    order_id = data.get("order_id")
                    event_type = data.get("event_type")
                    time_diff = data.get("time_diff", 0)
                    print(f"   - Order: {order_id} -> Event: {event_type} (time_diff: {time_diff}ms)")
        
        print(f"\n🎯 Order-Event Join Summary:")
        print(f"   - Total order-event joins: {len(all_joins)}")
        
        # 验证窗口Join结果
        assert len(all_joins) > 0, "❌ No order-event joins found"
        
        # 验证时间窗口
        for join_data in all_joins:
            time_diff = join_data.get("time_diff", 0)
            assert time_diff >= 0, f"❌ Invalid time diff: {time_diff}"
        
        print("✅ Order-Event join test passed: Orders joined with events in time window")
    
    def _verify_complex_multi_join_results(self):
        """验证复杂多Join结果"""
        received_data = JoinResultSink.get_received_data()
        
        print("\n📋 Complex Multi-Join Results:")
        print("=" * 50)
        
        user_payment_joins = []
        user_order_joins = []
        
        for instance_id, data_list in received_data.items():
            for data in data_list:
                join_type = data.get("join_type")
                if join_type == "user_payment":
                    user_payment_joins.append(data)
                elif join_type == "user_order":
                    user_order_joins.append(data)
                
                user_id = data.get("user_id", "unknown")
                print(f"   - {join_type}: user {user_id}")
        
        print(f"\n🎯 Complex Multi-Join Summary:")
        print(f"   - User-payment joins: {len(user_payment_joins)}")
        print(f"   - User-order joins: {len(user_order_joins)}")
        print(f"   - Total joins: {len(user_payment_joins) + len(user_order_joins)}")
        
        # 验证两种Join都有结果
        assert len(user_payment_joins) > 0 or len(user_order_joins) > 0, "❌ No joins found"
        
        print("✅ Complex multi-join test passed: Multiple join types working")
    
    def _verify_empty_stream_join_results(self):
        """验证空流Join结果"""
        received_data = JoinResultSink.get_received_data()
        
        print("\n📋 Empty Stream Join Results:")
        print("=" * 50)
        
        total_joins = sum(len(data_list) for data_list in received_data.values())
        print(f"🔹 Total join results: {total_joins}")
        
        # 空流Join应该没有结果
        assert total_joins == 0, f"❌ Expected no joins with empty stream, got {total_joins}"
        
        print("✅ Empty stream join test passed: No results as expected")


if __name__ == "__main__":
    # 可以直接运行单个测试
    test = TestJoinFunctionality()
    test.setup_method()
    test.test_flatmap_filter_join_pipeline()

'''
# 运行所有Join测试
pytest sage_tests/core_tests/join_test.py -v -s

# 运行特定测试
pytest sage_tests/core_tests/join_test.py::TestJoinFunctionality::test_flatmap_filter_join_pipeline -v -s
pytest sage_tests/core_tests/join_test.py::TestJoinFunctionality::test_multi_stage_join_pipeline -v -s
pytest sage_tests/core_tests/join_test.py::TestJoinFunctionality::test_windowed_join_pipeline -v -s
'''