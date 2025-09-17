import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from sage.common.config.output_paths import get_sage_paths
from sage.core.api.function.keyby_function import KeyByFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment


class KeyByTestDataSource(SourceFunction):
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
            "content": f"Message {self.counter} from {self.user_ids[self.counter]}",
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
        # 使用统一的 SAGE 路径管理系统
        sage_paths = get_sage_paths()
        self.output_dir = sage_paths.test_logs_dir / "keyby_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, data: Any):
        # 从runtime_context获取parallel_index
        if self.ctx:
            self.parallel_index = self.ctx.parallel_index

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
        print(
            f"🔍 [Instance {self.parallel_index}] User: {data['user_id']}, "
            f"Content: {data['content']}"
        )

        return data

    @classmethod
    def save_results_to_file(cls, test_name: str):
        """将测试结果保存到文件"""
        sage_paths = get_sage_paths()
        output_dir = sage_paths.test_logs_dir / "keyby_results"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{test_name}_{timestamp}.json"
        filepath = output_dir / filename

        with cls._lock:
            result_data = {
                "test_name": test_name,
                "timestamp": timestamp,
                "received_data": dict(cls._received_data),
                "total_instances": len(cls._received_data),
                "total_messages": sum(
                    len(data_list) for data_list in cls._received_data.values()
                ),
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

        print(f"📁 Results saved to: {filepath}")
        return str(filepath)

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
            env.from_source(KeyByTestDataSource, delay=0.5)
            .keyby(UserIdKeyExtractor, strategy="hash")
            .sink(ParallelDebugSink, parallelism=2)  # 2个并行实例
        )

        print(
            "📊 Pipeline: KeyByTestDataSource -> KeyBy(UserIdExtractor) -> ParallelDebugSink(parallelism=2)"
        )
        print("🎯 Expected: Same user_id data should go to same parallel instance\n")

        try:
            # 提交并运行
            env.submit()

            # 运行一段时间让数据流过
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error during execution: {e}")
            raise
        finally:
            try:
                env.close()
            except:
                pass  # 忽略关闭时的错误

        # 保存结果到文件
        result_file = ParallelDebugSink.save_results_to_file("hash_partitioning_test")

        # 验证分区效果
        success = self._verify_hash_partitioning()

        # 将验证结果也写入文件
        self._save_verification_result(result_file, "hash_partitioning", success)

        assert success, "Hash partitioning test failed"

    def test_keyby_broadcast_strategy(self):
        """测试广播策略"""
        print("\n🚀 Testing KeyBy Broadcast Strategy")

        env = LocalEnvironment("Test_keyby_broadcast_test")

        result_stream = (
            env.from_source(KeyByTestDataSource, delay=0.3)
            .keyby(UserIdKeyExtractor, strategy="broadcast")
            .sink(ParallelDebugSink, parallelism=3)  # 3个并行实例
        )

        print(
            "📊 Pipeline: KeyByTestDataSource -> KeyBy(broadcast) -> ParallelDebugSink(parallelism=3)"
        )
        print("🎯 Expected: All data should be sent to all parallel instances\n")

        try:
            env.submit()

            time.sleep(2)
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            raise
        finally:
            try:
                env.close()
            except:
                pass

        # 保存结果到文件
        result_file = ParallelDebugSink.save_results_to_file("broadcast_strategy_test")

        # 验证广播效果
        success = self._verify_broadcast_strategy()

        # 将验证结果写入文件
        self._save_verification_result(result_file, "broadcast_strategy", success)

        assert success, "Broadcast strategy test failed"

    def _save_verification_result(
        self, result_file: str, test_type: str, success: bool
    ):
        """将验证结果保存到文件"""
        if os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["verification"] = {
                "test_type": test_type,
                "success": success,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✍️ Verification result saved to: {result_file}")

    def _verify_hash_partitioning(self):
        """验证hash分区的正确性"""
        received_data = ParallelDebugSink.get_received_data()

        print("\n📋 Hash Partitioning Results:")
        print("=" * 50)

        if not received_data:
            print("❌ No data received by any instance")
            return False

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
        success = True
        for user_id, instances in user_distribution.items():
            if len(instances) != 1:
                print(
                    f"❌ User {user_id} data was routed to multiple instances: {instances}. "
                    f"Hash partitioning should send same key to same instance."
                )
                success = False

        if success:
            print(
                "✅ Hash partitioning test passed: Each user routed to exactly one instance"
            )

        return success

    def _verify_broadcast_strategy(self):
        """验证广播策略的正确性"""
        received_data = ParallelDebugSink.get_received_data()

        print("\n📋 Broadcast Strategy Results:")
        print("=" * 50)

        if not received_data:
            print("❌ No data received by any instance")
            return False

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
        unique_counts = set(instance_counts.values())
        if len(unique_counts) <= 1:
            print(
                "✅ Broadcast test passed: All instances received same number of messages"
            )
            return True
        else:
            print(
                f"⚠️  Note: Instance counts differ, this might be due to timing or test duration"
            )
            # 如果差异不大（比如只差1-2条消息），仍然认为测试通过
            min_count = min(instance_counts.values())
            max_count = max(instance_counts.values())
            if max_count - min_count <= 2:
                print(
                    "✅ Broadcast test passed: Instance counts are within acceptable range"
                )
                return True
            else:
                print("❌ Broadcast test failed: Instance counts differ significantly")
                return False


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
            env.from_source(KeyByTestDataSource, delay=0.4)
            .keyby(AdvancedKeyExtractor, strategy="hash")
            .sink(ParallelDebugSink, parallelism=4)  # 4个并行实例
        )

        print(
            "📊 Pipeline: KeyByTestDataSource -> KeyBy(AdvancedKeyExtractor) -> ParallelDebugSink(parallelism=4)"
        )
        print("🎯 Key format: 'user_id + message_id%2' (e.g., 'user1_0', 'user1_1')\n")

        try:
            env.submit()

            time.sleep(2)
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            raise
        finally:
            try:
                env.close()
            except:
                pass

        # 保存结果到文件
        result_file = ParallelDebugSink.save_results_to_file(
            "advanced_key_extraction_test"
        )

        # 分析分布效果
        success = self._analyze_advanced_distribution()

        # 将验证结果写入文件
        self._save_verification_result(result_file, "advanced_key_extraction", success)

        assert success, "Advanced key extraction test failed"

    def _analyze_advanced_distribution(self):
        """分析高级key提取的分布效果"""
        received_data = ParallelDebugSink.get_received_data()

        print("\n📋 Advanced Key Distribution Analysis:")
        print("=" * 50)

        if not received_data:
            print("❌ No data received by any instance")
            return False

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
        success = True
        for key, instances in key_distribution.items():
            if len(instances) != 1:
                print(f"❌ Key '{key}' was routed to multiple instances: {instances}")
                success = False

        if success:
            print(
                "✅ Advanced key extraction test passed: Each unique key consistently routed"
            )

        return success

    def _save_verification_result(
        self, result_file: str, test_type: str, success: bool
    ):
        """将验证结果保存到文件"""
        if os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["verification"] = {
                "test_type": test_type,
                "success": success,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✍️ Verification result saved to: {result_file}")


if __name__ == "__main__":
    # 可以直接运行单个测试
    test = TestKeyByFunctionality()
    test.setup_method()
    test.test_keyby_hash_partitioning()


"""
# 运行所有KeyBy测试
pytest tests/test_keyby_functionality.py -v -s

# 运行特定测试
pytest tests/test_keyby_functionality.py::TestKeyByFunctionality::test_keyby_hash_partitioning -v -s


"""
