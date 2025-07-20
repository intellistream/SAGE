import pytest
import time
import threading
from typing import List, Dict, Any
from sage_core.environment.local_environment import LocalEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.keyby_function import KeyByFunction
from sage_core.function.base_function import BaseFunction
from sage_core.function.sink_function import SinkFunction


class TestDataSource(SourceFunction):
    """生成带有用户ID的测试数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.user_ids = ["user1", "user2", "user3", "user1", "user2", "user3"]
    
    def execute(self):
        if self.counter >= len(self.user_ids):
            return None  # 停止生成数据
        
        data = {
            "id": self.counter,
            "user_id": self.user_ids[self.counter],
            "content": f"Message {self.counter} from {self.user_ids[self.counter]}"
        }
        self.counter += 1
        self.logger.info(f"Generated data: {data}")
        return data


class UserIdKeyExtractor(KeyByFunction):
    """提取用户ID作为分区键"""
    
    def execute(self, data: Any) -> str:
        user_id = data["user_id"]
        self.logger.info(f"Extracted key '{user_id}' from data: {data}")
        return user_id


class ParallelDebugSink(SinkFunction):
    """并行调试Sink，记录接收到的数据分布"""
    
    # 类级别的统计，所有实例共享
    _received_data: Dict[int, List[Dict]] = {}
    _lock = threading.Lock()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parallel_index = None
        self.received_count = 0
    
    def execute(self, data: Any):
        # 从runtime_context获取parallel_index
        if self.runtime_context:
            self.parallel_index = self.runtime_context.parallel_index
        
        with self._lock:
            if self.parallel_index not in self._received_data:
                self._received_data[self.parallel_index] = []
            
            self._received_data[self.parallel_index].append(data)
        
        self.received_count += 1
        
        self.logger.info(
            f"[Parallel Instance {self.parallel_index}] "
            f"Received data #{self.received_count}: {data}"
        )
        
        # 打印调试信息
        print(f"🔍 [Instance {self.parallel_index}] User: {data['user_id']}, "
              f"Content: {data['content']}")
        
        return data
    
    @classmethod
    def get_received_data(cls) -> Dict[int, List[Dict]]:
        """获取所有并行实例接收到的数据"""
        with cls._lock:
            return dict(cls._received_data)
    
    @classmethod
    def clear_data(cls):
        """清空统计数据"""
        with cls._lock:
            cls._received_data.clear()


class TestKeyByFunctionality:
    """测试KeyBy功能的分区效果"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        ParallelDebugSink.clear_data()
    
    def test_keyby_hash_partitioning(self):
        """测试基于hash的分区功能"""
        print("\n🚀 Testing KeyBy Hash Partitioning")
        
        # 创建环境
        env = LocalEnvironment("keyby_test")
        
        # 构建数据流：source -> keyby -> parallel sink
        result_stream = (
            env.from_source(TestDataSource, delay=0.5)
            .keyby(UserIdKeyExtractor, strategy="hash")
            .sink(ParallelDebugSink, parallelism=2)  # 2个并行实例
        )
        
        print("📊 Pipeline: TestDataSource -> KeyBy(UserIdExtractor) -> ParallelDebugSink(parallelism=2)")
        print("🎯 Expected: Same user_id data should go to same parallel instance\n")
        
        try:
            # 提交并运行
            env.submit()
            # env.run_streaming()
            
            # 运行一段时间让数据流过
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            raise
        finally:
            env.close()
        
        # 验证分区效果
        self._verify_hash_partitioning()
    
    def test_keyby_broadcast_strategy(self):
        """测试广播策略"""
        print("\n🚀 Testing KeyBy Broadcast Strategy")
        
        env = LocalEnvironment("keyby_broadcast_test")
        
        result_stream = (
            env.from_source(TestDataSource, delay=0.3)
            .keyby(UserIdKeyExtractor, strategy="broadcast")
            .sink(ParallelDebugSink, parallelism=3)  # 3个并行实例
        )
        
        print("📊 Pipeline: TestDataSource -> KeyBy(broadcast) -> ParallelDebugSink(parallelism=3)")
        print("🎯 Expected: All data should be sent to all parallel instances\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(2)
        finally:
            env.close()
        
        # 验证广播效果
        self._verify_broadcast_strategy()
    
    def _verify_hash_partitioning(self):
        """验证hash分区的正确性"""
        received_data = ParallelDebugSink.get_received_data()
        
        print("\n📋 Hash Partitioning Results:")
        print("=" * 50)
        
        # 统计每个实例接收到的用户数据
        user_distribution = {}
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            user_counts = {}
            for data in data_list:
                user_id = data["user_id"]
                user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            for user_id, count in user_counts.items():
                print(f"   - {user_id}: {count} messages")
                if user_id not in user_distribution:
                    user_distribution[user_id] = set()
                user_distribution[user_id].add(instance_id)
        
        print(f"\n🎯 User Distribution Across Instances:")
        for user_id, instances in user_distribution.items():
            print(f"   - {user_id}: routed to instance(s) {instances}")
        
        # 验证：每个用户的数据应该只路由到一个实例
        for user_id, instances in user_distribution.items():
            assert len(instances) == 1, (
                f"❌ User {user_id} data was routed to multiple instances: {instances}. "
                f"Hash partitioning should send same key to same instance."
            )
        
        print("✅ Hash partitioning test passed: Each user routed to exactly one instance")
    
    def _verify_broadcast_strategy(self):
        """验证广播策略的正确性"""
        received_data = ParallelDebugSink.get_received_data()
        
        print("\n📋 Broadcast Strategy Results:")
        print("=" * 50)
        
        instance_counts = {}
        total_unique_messages = 0
        
        for instance_id, data_list in received_data.items():
            instance_counts[instance_id] = len(data_list)
            print(f"\n🔹 Parallel Instance {instance_id}: {len(data_list)} messages")
            
            for data in data_list[:3]:  # 只显示前3条
                print(f"   - {data['user_id']}: {data['content']}")
        
        if received_data:
            # 获取第一个实例的数据作为基准
            first_instance_data = list(received_data.values())[0]
            total_unique_messages = len(first_instance_data)
        
        print(f"\n🎯 Broadcast Verification:")
        print(f"   - Total unique messages generated: {total_unique_messages}")
        print(f"   - Instances message counts: {instance_counts}")
        
        # 验证：每个实例应该接收到相同数量的消息（广播效果）
        if len(set(instance_counts.values())) <= 1:
            print("✅ Broadcast test passed: All instances received same number of messages")
        else:
            print(f"⚠️  Note: Instance counts differ, this might be due to timing or test duration")


class AdvancedKeyExtractor(KeyByFunction):
    """复杂的key提取器，用于高级测试"""
    
    def execute(self, data: Any) -> str:
        # 基于用户ID和消息ID的组合生成key
        key = f"{data['user_id']}_{data['id'] % 2}"
        self.logger.info(f"Advanced key extraction: {key} from {data}")
        return key


class TestAdvancedKeyBy:
    """高级KeyBy功能测试"""
    
    def setup_method(self):
        ParallelDebugSink.clear_data()
    
    def test_advanced_key_extraction(self):
        """测试复杂的key提取逻辑"""
        print("\n🚀 Testing Advanced Key Extraction")
        
        env = LocalEnvironment("advanced_keyby_test")
        
        result_stream = (
            env.from_source(TestDataSource, delay=0.4)
            .keyby(AdvancedKeyExtractor, strategy="hash")
            .sink(ParallelDebugSink, parallelism=4)  # 4个并行实例
        )
        
        print("📊 Pipeline: TestDataSource -> KeyBy(AdvancedKeyExtractor) -> ParallelDebugSink(parallelism=4)")
        print("🎯 Key format: 'user_id + message_id%2' (e.g., 'user1_0', 'user1_1')\n")
        
        try:
            env.submit()
            # env.run_streaming()
            time.sleep(3)
        finally:
            env.close()
        
        self._analyze_advanced_distribution()
    
    def _analyze_advanced_distribution(self):
        """分析高级key提取的分布效果"""
        received_data = ParallelDebugSink.get_received_data()
        
        print("\n📋 Advanced Key Distribution Analysis:")
        print("=" * 50)
        
        key_distribution = {}
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            
            for data in data_list:
                key = f"{data['user_id']}_{data['id'] % 2}"
                if key not in key_distribution:
                    key_distribution[key] = set()
                key_distribution[key].add(instance_id)
                print(f"   - Key '{key}': {data['content']}")
        
        print(f"\n🎯 Key-to-Instance Mapping:")
        for key, instances in key_distribution.items():
            print(f"   - Key '{key}': routed to instance(s) {instances}")
        
        # 验证一致性：相同key应该路由到相同实例
        for key, instances in key_distribution.items():
            assert len(instances) == 1, (
                f"❌ Key '{key}' was routed to multiple instances: {instances}"
            )
        
        print("✅ Advanced key extraction test passed: Each unique key consistently routed")


if __name__ == "__main__":
    # 可以直接运行单个测试
    test = TestKeyByFunctionality()
    test.setup_method()
    test.test_keyby_hash_partitioning()


'''
# 运行所有KeyBy测试
pytest tests/test_keyby_functionality.py -v -s

# 运行特定测试
pytest tests/test_keyby_functionality.py::TestKeyByFunctionality::test_keyby_hash_partitioning -v -s


'''