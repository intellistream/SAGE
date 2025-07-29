# import pytest
# import time
# import threading
# import json
# from typing import Any, Dict, List
# from pathlib import Path
# import tempfile
# from unittest.mock import Mock, patch, MagicMock

# from sage.core.api.local_environment import LocalEnvironment
# from sage.core.function.kafka_source import KafkaSourceFunction
# from sage.core.function.base_function import BaseFunction
# from sage.core.function.sink_function import SinkFunction


# class MockKafkaMessage:
#     """模拟Kafka消息"""
#     def __init__(self, value, key=None, timestamp=None, partition=0, offset=0):
#         self.value = value
#         self.key = key if key is not None else f"key_{offset}".encode('utf-8')
#         self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
#         self.partition = partition
#         self.offset = offset


# class MockKafkaConsumer:
#     """模拟KafkaConsumer"""
#     def __init__(self, *topics, **kwargs):
#         self.topics = topics
#         self.config = kwargs
#         self.messages = []
#         self.poll_count = 0
#         self._closed = False
#         # 保存反序列化器
#         self.value_deserializer = kwargs.get('value_deserializer', lambda x: x)
        
#     def poll(self, timeout_ms=1000, max_records=500, update_offsets=True):
#         """模拟poll方法"""
#         if self._closed or self.poll_count >= 3:  # 限制poll次数避免无限循环
#             return {}
        
#         self.poll_count += 1
        
#         if self.messages:
#             # 返回一批消息，应用反序列化器
#             topic_partition = Mock()
#             messages = []
#             for msg in self.messages[:max_records]:
#                 # 创建新的消息对象，应用反序列化器
#                 deserialized_msg = Mock()
#                 # 应用反序列化器到原始消息的value
#                 if callable(self.value_deserializer):
#                     deserialized_msg.value = self.value_deserializer(msg.value)
#                 else:
#                     deserialized_msg.value = msg.value
#                 deserialized_msg.key = msg.key
#                 deserialized_msg.timestamp = msg.timestamp
#                 deserialized_msg.partition = msg.partition
#                 deserialized_msg.offset = msg.offset
#                 messages.append(deserialized_msg)
            
#             self.messages = self.messages[max_records:]
#             return {topic_partition: messages}
        
#         return {}
    
#     def close(self):
#         """关闭消费者"""
#         self._closed = True
    
#     def add_messages(self, messages):
#         """添加模拟消息"""
#         self.messages.extend(messages)


# class KafkaDebugProcessor(BaseFunction):
#     """处理Kafka消息的调试函数"""
    
#     def __init__(self, ctx=None, **kwargs):
#         super().__init__(ctx=ctx, **kwargs)
#         self.processed_count = 0
    
#     def execute(self, data: Any):
#         if data is None:
#             return None
        
#         self.processed_count += 1
        
#         # 提取Kafka消息信息
#         value = data.get('value', {}) if isinstance(data, dict) else data
#         timestamp = data.get('timestamp', 0) if isinstance(data, dict) else 0
#         partition = data.get('partition', 0) if isinstance(data, dict) else 0
#         offset = data.get('offset', 0) if isinstance(data, dict) else 0
        
#         result = {
#             "type": "processed_kafka_message",
#             "processed_count": self.processed_count,
#             "original_value": value,
#             "kafka_metadata": {
#                 "timestamp": timestamp,
#                 "partition": partition,
#                 "offset": offset
#             }
#         }
        
#         if self.ctx:
#             self.logger.info(f"Processed Kafka message #{self.processed_count}: {value}")
        
#         return result


# class KafkaTestSink(SinkFunction):
#     """Kafka测试结果收集器"""
    
#     _lock = threading.Lock()
#     _received_data = {}
    
#     def __init__(self, ctx=None, **kwargs):
#         super().__init__(ctx=ctx, **kwargs)
#         self.parallel_index = None
#         self.received_count = 0
    
#     def execute(self, data: Any):
#         if self.ctx:
#             self.parallel_index = self.ctx.parallel_index
        
#         if data is None:
#             return None
        
#         with self._lock:
#             if self.parallel_index not in self._received_data:
#                 self._received_data[self.parallel_index] = []
#             self._received_data[self.parallel_index].append(data)
        
#         self.received_count += 1
        
#         if self.ctx:
#             self.logger.info(f"[Instance {self.parallel_index}] Received: {data}")
        
#         print(f"🔍 [Instance {self.parallel_index}] Kafka Test Sink received: {data}")
        
#         return data
    
#     @classmethod
#     def read_results(cls):
#         """读取测试结果"""
#         with cls._lock:
#             results = dict(cls._received_data)
#         return results
    
#     @classmethod
#     def clear_results(cls):
#         """清理结果"""
#         with cls._lock:
#             cls._received_data.clear()


# class TestKafkaSourceFunctionality:
#     """测试Kafka Source功能"""
    
#     def setup_method(self):
#         """测试前清理"""
#         KafkaTestSink.clear_results()
    
#     @patch('kafka.KafkaConsumer')
#     def test_basic_kafka_source_pipeline(self, mock_kafka_consumer_class):
#         """测试基本的Kafka Source流水线"""
#         print("\n🚀 Testing Basic Kafka Source Pipeline")
        
#         # 创建模拟消息 - 对于JSON反序列化器，原始数据需要是JSON字符串的bytes
#         test_messages = [
#             MockKafkaMessage(
#                 value=json.dumps({"event": "user_login", "user_id": "user1", "timestamp": 1640995200}).encode('utf-8'),
#                 offset=0
#             ),
#             MockKafkaMessage(
#                 value=json.dumps({"event": "page_view", "user_id": "user1", "page": "/home"}).encode('utf-8'),
#                 offset=1
#             ),
#             MockKafkaMessage(
#                 value=json.dumps({"event": "user_logout", "user_id": "user1"}).encode('utf-8'),
#                 offset=2
#             ),
#         ]
        
#         # 设置mock
#         mock_consumer = MockKafkaConsumer()
#         mock_consumer.add_messages(test_messages)
        
#         # 创建一个带有调试功能的MockKafkaConsumer实例
#         def create_mock_consumer(*topics, **kwargs):
#             consumer = MockKafkaConsumer(*topics, **kwargs)
#             consumer.add_messages(test_messages)
#             # 包装反序列化器用于调试
#             if 'value_deserializer' in kwargs and callable(kwargs['value_deserializer']):
#                 original_deserializer = kwargs['value_deserializer']
#                 def debug_deserializer(raw_data):
#                     result = original_deserializer(raw_data)
#                     print(f"🔧 Debug: Deserializing {raw_data} -> {result}")
#                     return result
#                 consumer.value_deserializer = debug_deserializer
#             return consumer
            
#         mock_kafka_consumer_class.side_effect = create_mock_consumer
        
#         # 创建测试环境
#         env = LocalEnvironment("basic_kafka_test")
        
#         # 构建流水线
#         kafka_stream = env.from_kafka_source(
#             bootstrap_servers="localhost:9092",
#             topic="test_topic",
#             group_id="test_group",
#             value_deserializer="json",
#             buffer_size=100
#         )
        
#         result_stream = (
#             kafka_stream
#             .map(KafkaDebugProcessor)
#             .sink(KafkaTestSink, parallelism=1)
#         )
        
#         print("📊 Pipeline: KafkaSource -> map(KafkaDebugProcessor) -> Sink")
#         print("🎯 Expected: Process JSON messages from Kafka\n")
        
#         try:
#             env.submit()
#             time.sleep(2)  # 等待处理消息
#         finally:
#             env.close()
        
#         time.sleep(0.5)
#         self._verify_basic_kafka_results(test_messages)
    
#     @patch('kafka.KafkaConsumer')
#     def test_kafka_source_with_string_deserializer(self, mock_kafka_consumer_class):
#         """测试字符串反序列化的Kafka Source"""
#         print("\n🚀 Testing Kafka Source with String Deserializer")
        
#         # 创建字符串消息
#         test_messages = [
#             MockKafkaMessage(value="Hello Kafka", offset=0),
#             MockKafkaMessage(value="String message 1", offset=1),
#             MockKafkaMessage(value="String message 2", offset=2),
#         ]
        
#         mock_consumer = MockKafkaConsumer()
#         mock_consumer.add_messages(test_messages)
#         mock_kafka_consumer_class.return_value = mock_consumer
        
#         env = LocalEnvironment("string_kafka_test")
        
#         kafka_stream = env.from_kafka_source(
#             bootstrap_servers="localhost:9092",
#             topic="string_topic",
#             group_id="string_group",
#             value_deserializer="string",
#             buffer_size=50
#         )
        
#         result_stream = (
#             kafka_stream
#             .map(KafkaDebugProcessor)
#             .sink(KafkaTestSink, parallelism=1)
#         )
        
#         print("📊 Pipeline: KafkaSource(string) -> map(KafkaDebugProcessor) -> Sink")
#         print("🎯 Expected: Process string messages from Kafka\n")
        
#         try:
#             env.submit()
#             time.sleep(2)
#         finally:
#             env.close()
        
#         time.sleep(0.5)
#         self._verify_string_kafka_results(test_messages)
    
#     @patch('kafka.KafkaConsumer')
#     def test_kafka_source_custom_deserializer(self, mock_kafka_consumer_class):
#         """测试自定义反序列化器的Kafka Source"""
#         print("\n🚀 Testing Kafka Source with Custom Deserializer")
        
#         def custom_deserializer(raw_data):
#             """自定义反序列化：添加前缀"""
#             print(f"🔧 Custom deserializer called with: {raw_data}")
#             if isinstance(raw_data, bytes):
#                 data = raw_data.decode('utf-8')
#             else:
#                 data = str(raw_data)
#             result = f"CUSTOM_{data}"
#             print(f"🔧 Deserializer output: {result}")
#             return result
        
#         # 创建测试消息 - 注意这里value需要是bytes
#         test_messages = [
#             MockKafkaMessage(value=b"message1", offset=0),
#             MockKafkaMessage(value=b"message2", offset=1),
#         ]
        
#         # 创建mock consumer并预设反序列化器
#         mock_consumer = MockKafkaConsumer()
#         mock_consumer.add_messages(test_messages)
#         mock_consumer.value_deserializer = custom_deserializer
        
#         mock_kafka_consumer_class.return_value = mock_consumer
        
#         env = LocalEnvironment("custom_deserializer_kafka_test")
        
#         kafka_stream = env.from_kafka_source(
#             bootstrap_servers="localhost:9092",
#             topic="custom_topic",
#             group_id="custom_group",
#             value_deserializer=custom_deserializer,
#             buffer_size=50
#         )
        
#         result_stream = (
#             kafka_stream
#             .map(KafkaDebugProcessor)
#             .sink(KafkaTestSink, parallelism=1)
#         )
        
#         print("📊 Pipeline: KafkaSource(custom) -> map(KafkaDebugProcessor) -> Sink")
#         print("🎯 Expected: Process custom deserialized messages\n")
        
#         try:
#             env.submit()
#             time.sleep(2)
#         finally:
#             env.close()
        
#         time.sleep(0.5)
#         self._verify_custom_kafka_results()
    
#     @patch('kafka.KafkaConsumer')
#     def test_kafka_source_parallel_processing(self, mock_kafka_consumer_class):
#         """测试Kafka Source并行处理"""
#         print("\n🚀 Testing Kafka Source Parallel Processing")
        
#         # 创建更多消息用于并行处理
#         test_messages = []
#         for i in range(10):
#             test_messages.append(
#                 MockKafkaMessage(
#                     value={"batch": "parallel_test", "message_id": i, "data": f"data_{i}"},
#                     offset=i
#                 )
#             )
        
#         mock_consumer = MockKafkaConsumer()
#         mock_consumer.add_messages(test_messages)
#         mock_kafka_consumer_class.return_value = mock_consumer
        
#         env = LocalEnvironment("parallel_kafka_test")
        
#         kafka_stream = env.from_kafka_source(
#             bootstrap_servers="localhost:9092",
#             topic="parallel_topic",
#             group_id="parallel_group",
#             value_deserializer="json"
#         )
        
#         result_stream = (
#             kafka_stream
#             .map(KafkaDebugProcessor, parallelism=3)  # 并行度3
#             .sink(KafkaTestSink, parallelism=2)       # 并行度2
#         )
        
#         print("📊 Pipeline: KafkaSource -> map(parallelism=3) -> Sink(parallelism=2)")
#         print("🎯 Expected: Parallel processing of Kafka messages\n")
        
#         try:
#             env.submit()
#             time.sleep(3)
#         finally:
#             env.close()
        
#         time.sleep(0.5)
#         self._verify_parallel_kafka_results(test_messages)
    
#     def _verify_basic_kafka_results(self, expected_messages):
#         """验证基本Kafka测试结果"""
#         received_data = KafkaTestSink.read_results()
        
#         print("\n📋 Basic Kafka Source Results:")
#         print("=" * 50)
        
#         processed_messages = []
        
#         for instance_id, data_list in received_data.items():
#             print(f"\n🔹 Parallel Instance {instance_id}:")
            
#             for data in data_list:
#                 if data.get("type") == "processed_kafka_message":
#                     processed_messages.append(data)
#                     original_value = data.get("original_value", {})
#                     kafka_meta = data.get("kafka_metadata", {})
                    
#                     print(f"   - Message: {original_value}")
#                     print(f"     Metadata: partition={kafka_meta.get('partition')}, "
#                           f"offset={kafka_meta.get('offset')}")
        
#         print(f"\n🎯 Kafka Processing Summary:")
#         print(f"   - Expected messages: {len(expected_messages)}")
#         print(f"   - Processed messages: {len(processed_messages)}")
        
#         # 验证：应该有处理过的消息
#         assert len(processed_messages) > 0, "❌ No processed Kafka messages received"
        
#         # 验证：消息内容应该匹配
#         processed_values = [msg.get("original_value", {}) for msg in processed_messages]
#         expected_events = ["user_login", "page_view", "user_logout"]
        
#         for expected_event in expected_events:
#             found = any(
#                 isinstance(pv, dict) and pv.get("event") == expected_event 
#                 for pv in processed_values
#             )
#             assert found, f"❌ Expected event not found: {expected_event}"
        
#         print("✅ Basic Kafka Source test passed: Messages processed correctly")
    
#     def _verify_string_kafka_results(self, expected_messages):
#         """验证字符串Kafka测试结果"""
#         received_data = KafkaTestSink.read_results()
        
#         print("\n📋 String Kafka Source Results:")
#         print("=" * 50)
        
#         processed_messages = []
        
#         for instance_id, data_list in received_data.items():
#             for data in data_list:
#                 if data.get("type") == "processed_kafka_message":
#                     processed_messages.append(data)
#                     original_value = data.get("original_value")
#                     print(f"   - String Message: '{original_value}'")
        
#         print(f"\n🎯 String Processing Summary:")
#         print(f"   - Expected messages: {len(expected_messages)}")
#         print(f"   - Processed messages: {len(processed_messages)}")
        
#         assert len(processed_messages) > 0, "❌ No string messages received"
        
#         # 验证字符串内容
#         processed_values = [msg.get("original_value") for msg in processed_messages]
#         for expected_msg in expected_messages:
#             assert expected_msg.value in processed_values, f"❌ String message not found: {expected_msg.value}"
        
#         print("✅ String Kafka Source test passed: String messages processed correctly")
    
#     def _verify_custom_kafka_results(self):
#         """验证自定义反序列化测试结果"""
#         received_data = KafkaTestSink.read_results()
        
#         print("\n📋 Custom Deserializer Kafka Results:")
#         print("=" * 50)
        
#         processed_messages = []
        
#         for instance_id, data_list in received_data.items():
#             for data in data_list:
#                 if data and data.get("type") == "processed_kafka_message":
#                     processed_messages.append(data)
#                     original_value = data.get("original_value")
#                     print(f"   - Custom Message: '{original_value}'")
        
#         print(f"\n🎯 Custom Processing Summary:")
#         print(f"   - Processed messages: {len(processed_messages)}")
        
#         assert len(processed_messages) > 0, "❌ No custom messages received"
        
#         # 验证自定义前缀
#         for msg in processed_messages:
#             original_value = str(msg.get("original_value", ""))
#             assert original_value.startswith("CUSTOM_"), f"❌ Custom prefix missing: {original_value}"
        
#         print("✅ Custom deserializer test passed: Custom processing applied correctly")
    
#     def _verify_parallel_kafka_results(self, expected_messages):
#         """验证并行处理测试结果"""
#         received_data = KafkaTestSink.read_results()
        
#         print("\n📋 Parallel Kafka Processing Results:")
#         print("=" * 50)
        
#         processed_messages = []
#         instance_counts = {}
        
#         for instance_id, data_list in received_data.items():
#             instance_counts[instance_id] = len(data_list)
#             print(f"\n🔹 Sink Instance {instance_id}: {len(data_list)} messages")
            
#             for data in data_list:
#                 if data.get("type") == "processed_kafka_message":
#                     processed_messages.append(data)
        
#         print(f"\n🎯 Parallel Processing Summary:")
#         print(f"   - Expected messages: {len(expected_messages)}")
#         print(f"   - Processed messages: {len(processed_messages)}")
#         print(f"   - Sink instances: {len(instance_counts)}")
#         print(f"   - Distribution: {instance_counts}")
        
#         assert len(processed_messages) > 0, "❌ No parallel messages received"
#         assert len(instance_counts) > 1, "❌ Messages not distributed across instances"
        
#         print("✅ Parallel Kafka processing test passed: Messages distributed correctly")


# class TestKafkaSourceConfiguration:
#     """测试Kafka Source配置"""
    
#     def setup_method(self):
#         KafkaTestSink.clear_results()
    
#     @patch('kafka.KafkaConsumer')
#     def test_kafka_source_configuration_options(self, mock_kafka_consumer_class):
#         """测试各种Kafka配置选项"""
#         print("\n🚀 Testing Kafka Source Configuration Options")
        
#         mock_consumer = MockKafkaConsumer()
#         mock_consumer.add_messages([
#             MockKafkaMessage(value={"config_test": True}, offset=0)
#         ])
#         mock_kafka_consumer_class.return_value = mock_consumer
        
#         env = LocalEnvironment("config_kafka_test")
        
#         # 测试完整配置
#         kafka_stream = env.from_kafka_source(
#             bootstrap_servers="kafka-cluster:9092,kafka-cluster:9093",
#             topic="config_topic",
#             group_id="config_group",
#             auto_offset_reset="earliest",
#             value_deserializer="json",
#             buffer_size=5000,
#             max_poll_records=100,
#             session_timeout_ms=30000,
#             security_protocol="SASL_SSL"
#         )
        
#         result_stream = kafka_stream.sink(KafkaTestSink, parallelism=1)
        
#         print("📊 Pipeline: KafkaSource(full_config) -> Sink")
#         print("🎯 Expected: Verify configuration parameters\n")
        
#         try:
#             env.submit()
#             time.sleep(1.5)
#         finally:
#             env.close()
        
#         # 验证KafkaConsumer被正确调用
#         mock_kafka_consumer_class.assert_called_once()
#         call_args = mock_kafka_consumer_class.call_args
        
#         # 验证配置参数
#         assert call_args[0] == ("config_topic",)
#         config = call_args[1]
#         assert config['bootstrap_servers'] == "kafka-cluster:9092,kafka-cluster:9093"
#         assert config['group_id'] == "config_group"
#         assert config['auto_offset_reset'] == "earliest"
#         assert config['max_poll_records'] == 100
#         assert config['session_timeout_ms'] == 30000
#         assert config['security_protocol'] == "SASL_SSL"
        
#         print("✅ Kafka configuration test passed: All parameters configured correctly")


# if __name__ == "__main__":
#     # 可以直接运行单个测试
#     test = TestKafkaSourceFunctionality()
#     test.setup_method()
#     test.test_basic_kafka_source_pipeline()

# '''
# 用法示例:

# # 运行所有Kafka测试
# pytest sage_tests/core_tests/kafka_test.py -v -s

# # 运行特定测试
# pytest sage_tests/core_tests/kafka_test.py::TestKafkaSourceFunctionality::test_basic_kafka_source_pipeline -v -s
# pytest sage_tests/core_tests/kafka_test.py::TestKafkaSourceFunctionality::test_kafka_source_parallel_processing -v -s
# pytest sage_tests/core_tests/kafka_test.py::TestKafkaSourceConfiguration::test_kafka_source_configuration_options -v -s

# # 直接运行文件进行快速测试
# python sage_tests/core_tests/kafka_test.py
# '''