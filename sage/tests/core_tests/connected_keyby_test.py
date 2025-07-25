import pytest
import time
import threading
from typing import List, Dict, Any
from core.api.local_environment import LocalEnvironment
from core.function.source_function import SourceFunction
from core.function.keyby_function import KeyByFunction
from core.function.comap_function import BaseCoMapFunction
from core.function.sink_function import SinkFunction


class UserDataSource(SourceFunction):
    """生成用户数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.users = [
            {"id": 1, "user_id": "user1", "name": "Alice", "type": "user"},
            {"id": 2, "user_id": "user2", "name": "Bob", "type": "user"},
            {"id": 3, "user_id": "user3", "name": "Charlie", "type": "user"},
            {"id": 4, "user_id": "user1", "name": "Alice Updated", "type": "user"},
        ]
    
    def execute(self):
        if self.counter >= len(self.users):
            return None
        
        data = self.users[self.counter]
        self.counter += 1
        self.logger.info(f"UserSource generated: {data}")
        return data


class EventDataSource(SourceFunction):
    """生成事件数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.events = [
            {"id": 101, "user_id": "user1", "event": "login", "session_id": "sess1", "type": "event"},
            {"id": 102, "user_id": "user2", "event": "click", "session_id": "sess2", "type": "event"},
            {"id": 103, "user_id": "user3", "event": "purchase", "session_id": "sess3", "type": "event"},
            {"id": 104, "user_id": "user1", "event": "logout", "session_id": "sess1", "type": "event"},
        ]
    
    def execute(self):
        if self.counter >= len(self.events):
            return None
        
        data = self.events[self.counter]
        self.counter += 1
        self.logger.info(f"EventSource generated: {data}")
        return data


class UserIdKeyExtractor(KeyByFunction):
    """提取用户ID作为分区键"""
    
    def execute(self, data: Any) -> str:
        user_id = data["user_id"]
        self.logger.info(f"UserIdExtractor: key '{user_id}' from {data.get('type', 'unknown')} data")
        return user_id


class SessionIdKeyExtractor(KeyByFunction):
    """提取会话ID作为分区键"""
    
    def execute(self, data: Any) -> str:
        # 对于用户数据，使用user_id作为session key（模拟场景）
        if data.get("type") == "user":
            session_key = f"user_session_{data['user_id']}"
        else:
            session_key = data.get("session_id", "default_session")
        
        self.logger.info(f"SessionIdExtractor: key '{session_key}' from {data.get('type', 'unknown')} data")
        return session_key


class ConnectedDebugSink(SinkFunction):
    """调试用的Sink，记录接收到的连接流数据分布"""
    
    # 类级别的统计
    _received_data: Dict[int, List[Dict]] = {}
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

        data_type = data.get('type', 'unknown')
        key_info = data.get('user_id', 'no_key')

        self.logger.info(
            f"[Instance {self.parallel_index}] "
            f"Received {data_type} data #{self.received_count}: {data}"
        )

        # 打印调试信息
        print(f"🔍 [Instance {self.parallel_index}] Type: {data_type}, "
              f"Key: {key_info}, Data: {data}")

        return data
    
    @classmethod
    def get_received_data(cls) -> Dict[int, List[Dict]]:
        with cls._lock:
            return dict(cls._received_data)
    
    @classmethod
    def clear_data(cls):
        with cls._lock:
            cls._received_data.clear()


class JoinCoMapFunction(BaseCoMapFunction):
    """示例CoMap函数，用于连接用户和事件数据"""
    is_comap = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}  # 简单的用户数据缓存
    
    def map0(self, user_data):
        """处理用户数据流 (stream 0)"""
        user_id = user_data["user_id"]
        self.user_cache[user_id] = user_data
        
        result = {
            "type": "user_update",
            "user_id": user_id,
            "user_info": user_data,
            "source_stream": 0
        }
        
        self.logger.info(f"CoMap map0: processed user {user_id}")
        return result
    
    def map1(self, event_data):
        """处理事件数据流 (stream 1)"""
        user_id = event_data["user_id"]
        user_info = self.user_cache.get(user_id, {"name": "Unknown"})
        
        result = {
            "type": "enriched_event",
            "user_id": user_id,
            "event_info": event_data,
            "user_info": user_info,
            "source_stream": 1
        }
        
        self.logger.info(f"CoMap map1: enriched event for user {user_id}")
        return result


class TestConnectedStreamsKeyBy:
    """测试ConnectedStreams的KeyBy功能"""
    
    def setup_method(self):
        ConnectedDebugSink.clear_data()
    
    def test_unified_keyby(self):
        """测试统一的KeyBy - 两个流使用相同的key selector"""
        print("\n🚀 Testing Connected Streams Unified KeyBy")
        
        env = LocalEnvironment("connected_unified_keyby_test")
        
        # 创建两个数据源
        user_stream = env.from_source(UserDataSource, delay=0.3)
        event_stream = env.from_source(EventDataSource, delay=0.4)
        
        # 连接流并应用统一的keyby
        result_stream = (
            user_stream
            .connect(event_stream)
            .keyby(UserIdKeyExtractor)  # 两个流都使用UserIdKeyExtractor
            .map(lambda x: x)  # 透明传递
            .sink(ConnectedDebugSink, parallelism=2)
        )
        
        print("📊 Pipeline: UserStream + EventStream -> ConnectedStreams.keyby(UserIdExtractor) -> Sink(parallelism=2)")
        print("🎯 Expected: Data with same user_id should go to same parallel instance\n")
        
        try:
            env.submit()
            
            time.sleep(3)
        finally:
            env.close()
        
        self._verify_unified_keyby_partitioning()
    
    def test_per_stream_keyby(self):
        """测试Flink风格的per-stream KeyBy - 每个流使用不同的key selector"""
        print("\n🚀 Testing Connected Streams Per-Stream KeyBy (Flink-style)")
        
        env = LocalEnvironment("connected_per_stream_keyby_test")
        
        user_stream = env.from_source(UserDataSource, delay=0.3)
        event_stream = env.from_source(EventDataSource, delay=0.4)
        
        # 连接流并应用不同的keyby策略
        result_stream = (
            user_stream
            .connect(event_stream)
            .keyby([UserIdKeyExtractor, SessionIdKeyExtractor])  # 每个流不同的extractor
            .map(lambda x: x)  # 透明传递
            .sink(ConnectedDebugSink, parallelism=3)
        )
        
        print("📊 Pipeline: UserStream + EventStream -> ConnectedStreams.keyby([UserIdExtractor, SessionIdExtractor]) -> Sink(parallelism=3)")
        print("🎯 Expected: Stream 0 by user_id, Stream 1 by session_id\n")
        
        try:
            env.submit()
            
            time.sleep(3)
        finally:
            env.close()
        
        self._verify_per_stream_keyby_partitioning()
    
    def test_keyby_with_comap(self):
        """测试KeyBy后接CoMap操作"""
        print("\n🚀 Testing Connected Streams KeyBy + CoMap")
        
        env = LocalEnvironment("connected_keyby_comap_test")
        
        user_stream = env.from_source(UserDataSource, delay=0.3)
        event_stream = env.from_source(EventDataSource, delay=0.4)
        
        # KeyBy后进行CoMap join操作
        result_stream = (
            user_stream
            .connect(event_stream)
            .keyby(UserIdKeyExtractor)  # 统一使用user_id作为key
            .comap(JoinCoMapFunction)   # 进行数据join
            .sink(ConnectedDebugSink, parallelism=2)
        )
        
        print("📊 Pipeline: UserStream + EventStream -> keyby(UserIdExtractor) -> comap(JoinCoMapFunction) -> Sink")
        print("🎯 Expected: Same user_id data co-located for join operation\n")
        
        try:
            env.submit()
            
            time.sleep(4)  # 给更多时间让join操作完成
        finally:
            env.close()
        
        self._verify_keyby_comap_results()
    
    def test_invalid_keyby_configurations(self):
        """测试无效的KeyBy配置"""
        print("\n🚀 Testing Invalid KeyBy Configurations")
        
        env = LocalEnvironment("invalid_keyby_test")
        
        user_stream = env.from_source(UserDataSource, delay=0.5)
        event_stream = env.from_source(EventDataSource, delay=0.5)
        connected = user_stream.connect(event_stream)
        
        # 测试1：key selector数量不匹配
        with pytest.raises(ValueError, match="Key selector count .* must match stream count"):
            connected.keyby([UserIdKeyExtractor])  # 只有1个selector，但有2个stream
        
        # 测试2：Lambda函数不支持
        with pytest.raises(NotImplementedError, match="Lambda functions are not supported"):
            connected.keyby(lambda x: x["user_id"])
        
        print("✅ Invalid configuration tests passed")
        
        env.close()
    
    def _verify_unified_keyby_partitioning(self):
        """验证统一KeyBy的分区效果"""
        received_data = ConnectedDebugSink.get_received_data()
        
        print("\n📋 Unified KeyBy Partitioning Results:")
        print("=" * 60)
        
        user_distribution = {}
        
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            
            for data in data_list:
                user_id = data["user_id"]
                data_type = data["type"]
                
                if user_id not in user_distribution:
                    user_distribution[user_id] = set()
                user_distribution[user_id].add(instance_id)
                
                print(f"   - User {user_id} ({data_type}): {data.get('name', data.get('event', 'N/A'))}")
        
        print(f"\n🎯 User Distribution Across Instances:")
        for user_id, instances in user_distribution.items():
            print(f"   - {user_id}: routed to instance(s) {instances}")
        
        # 验证：每个用户的所有数据（无论来自哪个流）都应该路由到同一个实例
        for user_id, instances in user_distribution.items():
            assert len(instances) == 1, (
                f"❌ User {user_id} data was routed to multiple instances: {instances}. "
                f"Unified keyby should send same key to same instance."
            )
        
        print("✅ Unified keyby test passed: Each user's data from both streams routed to same instance")
    
    def _verify_per_stream_keyby_partitioning(self):
        """验证per-stream KeyBy的分区效果"""
        received_data = ConnectedDebugSink.get_received_data()
        
        print("\n📋 Per-Stream KeyBy Partitioning Results:")
        print("=" * 60)
        
        stream0_key_distribution = {}  # user_id distribution
        stream1_key_distribution = {}  # session_id distribution
        
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            
            for data in data_list:
                data_type = data["type"]
                
                if data_type == "user":
                    # Stream 0: 按user_id分区
                    key = data["user_id"]
                    if key not in stream0_key_distribution:
                        stream0_key_distribution[key] = set()
                    stream0_key_distribution[key].add(instance_id)
                    print(f"   - Stream0 key '{key}': {data['name']}")
                    
                elif data_type == "event":
                    # Stream 1: 按session_id分区
                    key = data.get("session_id", "unknown")
                    if key not in stream1_key_distribution:
                        stream1_key_distribution[key] = set()
                    stream1_key_distribution[key].add(instance_id)
                    print(f"   - Stream1 key '{key}': {data['event']}")
        
        print(f"\n🎯 Stream 0 (User) Key Distribution:")
        for key, instances in stream0_key_distribution.items():
            print(f"   - User {key}: routed to instance(s) {instances}")
        
        print(f"\n🎯 Stream 1 (Event) Key Distribution:")
        for key, instances in stream1_key_distribution.items():
            print(f"   - Session {key}: routed to instance(s) {instances}")
        
        # 验证：每个流的相同key应该路由到相同实例
        for key, instances in stream0_key_distribution.items():
            assert len(instances) == 1, f"❌ Stream0 key {key} routed to multiple instances: {instances}"
        
        for key, instances in stream1_key_distribution.items():
            assert len(instances) == 1, f"❌ Stream1 key {key} routed to multiple instances: {instances}"
        
        print("✅ Per-stream keyby test passed: Each stream's keys correctly partitioned")
    
    def _verify_keyby_comap_results(self):
        """验证KeyBy + CoMap的结果"""
        received_data = ConnectedDebugSink.get_received_data()
        
        print("\n📋 KeyBy + CoMap Results:")
        print("=" * 60)
        
        user_updates = []
        enriched_events = []
        
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            
            for data in data_list:
                result_type = data.get("type", "unknown")
                user_id = data.get("user_id", "unknown")
                source_stream = data.get("source_stream", -1)
                
                if result_type == "user_update":
                    user_updates.append(data)
                    print(f"   - User Update: {user_id} from stream {source_stream}")
                elif result_type == "enriched_event":
                    enriched_events.append(data)
                    event_name = data.get("event_info", {}).get("event", "unknown")
                    print(f"   - Enriched Event: {user_id} {event_name} from stream {source_stream}")
        
        print(f"\n🎯 CoMap Results Summary:")
        print(f"   - User updates: {len(user_updates)}")
        print(f"   - Enriched events: {len(enriched_events)}")
        
        # 验证：应该有用户更新和丰富的事件
        assert len(user_updates) > 0, "❌ No user updates received from CoMap"
        assert len(enriched_events) > 0, "❌ No enriched events received from CoMap"
        
        print("✅ KeyBy + CoMap test passed: Both user updates and enriched events received")


if __name__ == "__main__":
    # 可以直接运行单个测试
    test = TestConnectedStreamsKeyBy()
    test.setup_method()
    test.test_unified_keyby()

'''
# 运行所有Connected KeyBy测试
pytest sage_tests/operator_tests/connected_keyby_test.py -v -s

# 运行特定测试
pytest sage_tests/operator_tests/connected_keyby_test.py::TestConnectedStreamsKeyBy::test_unified_keyby -v -s
pytest sage_tests/operator_tests/connected_keyby_test.py::TestConnectedStreamsKeyBy::test_per_stream_keyby -v -s
pytest sage_tests/operator_tests/connected_keyby_test.py::TestConnectedStreamsKeyBy::test_keyby_with_comap -v -s
'''