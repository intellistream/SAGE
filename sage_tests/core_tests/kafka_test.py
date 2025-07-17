import pytest
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_core.function.kafka_source import KafkaSourceFunction
from sage_core.function.base_function import BaseFunction


class TestKafkaSourceFunction:
    """KafkaSourceFunction单元测试"""
    
    def test_kafka_source_initialization(self):
        """测试KafkaSourceFunction初始化"""
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            auto_offset_reset="earliest",
            value_deserializer="json",
            buffer_size=1000,
            max_poll_records=100
        )
        
        # 验证配置参数
        assert kafka_source.bootstrap_servers == "localhost:9092"
        assert kafka_source.topic == "test_topic"
        assert kafka_source.group_id == "test_group"
        assert kafka_source.auto_offset_reset == "earliest"
        assert kafka_source.value_deserializer == "json"
        assert kafka_source.buffer_size == 1000
        assert kafka_source.max_poll_records == 100
        
        # 验证运行时对象未初始化
        assert kafka_source._consumer is None
        assert kafka_source._local_buffer is None
        assert kafka_source._consumer_thread is None
        assert kafka_source._running is False
        assert kafka_source._initialized is False
    
    def test_get_deserializer(self):
        """测试反序列化器获取"""
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group"
        )
        
        # 测试JSON反序列化器
        kafka_source.value_deserializer = "json"
        deserializer = kafka_source._get_deserializer()
        test_data = b'{"key": "value"}'
        result = deserializer(test_data)
        assert result == {"key": "value"}
        
        # 测试字符串反序列化器
        kafka_source.value_deserializer = "string"
        deserializer = kafka_source._get_deserializer()
        test_data = b'hello world'
        result = deserializer(test_data)
        assert result == "hello world"
        
        # 测试字节反序列化器
        kafka_source.value_deserializer = "bytes"
        deserializer = kafka_source._get_deserializer()
        test_data = b'binary data'
        result = deserializer(test_data)
        assert result == b'binary data'
        
        # 测试自定义函数
        custom_func = lambda x: x.decode('utf-8').upper()
        kafka_source.value_deserializer = custom_func
        deserializer = kafka_source._get_deserializer()
        test_data = b'hello'
        result = deserializer(test_data)
        assert result == "HELLO"
        
        # 测试无效反序列化器
        kafka_source.value_deserializer = "invalid"
        with pytest.raises(ValueError, match="Unsupported deserializer"):
            kafka_source._get_deserializer()
    
    @patch('kafka.KafkaConsumer')
    def test_lazy_initialization(self, mock_kafka_consumer):
        """测试延迟初始化"""
        # 模拟KafkaConsumer
        mock_consumer_instance = Mock()
        mock_consumer_instance.poll.return_value = {}  # 修复：返回空字典避免迭代错误
        mock_kafka_consumer.return_value = mock_consumer_instance
        
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            buffer_size=100
        )
        
        # 首次调用execute应该触发初始化
        result = kafka_source.execute(None)
        
        # 验证初始化完成
        assert kafka_source._initialized is True
        assert kafka_source._running is True
        assert kafka_source._local_buffer is not None
        assert kafka_source._consumer_thread is not None
        
        # 修复：分别验证调用参数而不是直接比较函数对象
        mock_kafka_consumer.assert_called_once()
        call_args = mock_kafka_consumer.call_args
        assert call_args[0] == ("test_topic",)
        assert call_args[1]['bootstrap_servers'] == "localhost:9092"
        assert call_args[1]['group_id'] == "test_group" 
        assert call_args[1]['auto_offset_reset'] == "latest"
        assert callable(call_args[1]['value_deserializer'])
        assert call_args[1]['max_poll_records'] == 500
        assert call_args[1]['consumer_timeout_ms'] == 1000
        
        # 第二次调用不应该重新初始化
        mock_kafka_consumer.reset_mock()
        kafka_source.execute(None)
        mock_kafka_consumer.assert_not_called()
        
        # 清理资源
        kafka_source._running = False
        if kafka_source._consumer_thread:
            kafka_source._consumer_thread.join(timeout=1.0)
        
        @patch('kafka.KafkaConsumer')  # 修正mock路径
        def test_consume_loop_with_messages(self, mock_kafka_consumer):
            """测试消费循环处理消息"""
            # 模拟Kafka消息
            mock_message = Mock()
            mock_message.value = {"user_id": "123", "action": "login"}
            mock_message.timestamp = 1640995200000
            mock_message.partition = 0
            mock_message.offset = 42
            mock_message.key = b"user_123"
            
            # 模拟consumer.poll返回
            mock_consumer_instance = Mock()
            mock_topic_partition = Mock()
            mock_consumer_instance.poll.side_effect = [
                {mock_topic_partition: [mock_message]},
                {},
                {}
            ]
            mock_kafka_consumer.return_value = mock_consumer_instance
            
            kafka_source = KafkaSourceFunction(
                bootstrap_servers="localhost:9092",
                topic="test_topic",
                group_id="test_group",
                buffer_size=10
            )
            
            # 触发初始化
            kafka_source.execute(None)
            
            # 等待消费线程处理消息
            time.sleep(0.2)
            
            # 验证消息被正确处理
            result = kafka_source.execute(None)
            assert result is not None
            assert result['value'] == {"user_id": "123", "action": "login"}
            assert result['timestamp'] == 1640995200000
            assert result['partition'] == 0
            assert result['offset'] == 42
            assert result['key'] == "user_123"
            
            # 清理资源
            kafka_source._running = False
            if kafka_source._consumer_thread:
                kafka_source._consumer_thread.join(timeout=1.0)
    
    @patch('kafka.KafkaConsumer')  # 修正mock路径
    def test_buffer_full_handling(self, mock_kafka_consumer):
        """测试缓冲区满时的背压处理"""
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            buffer_size=1  # 很小的缓冲区
        )
        
        # 模拟消费者
        mock_consumer_instance = Mock()
        mock_consumer_instance.poll.return_value = {}  # 添加这行：返回空字典
        mock_kafka_consumer.return_value = mock_consumer_instance
        
        # 手动初始化
        kafka_source._lazy_init()
        
        # 填满缓冲区
        test_message = {"test": "data"}
        kafka_source._local_buffer.put_nowait(test_message)
        
        # 再次尝试添加消息（应该触发背压处理）
        new_message = {"new": "data"}
        try:
            kafka_source._local_buffer.put_nowait(new_message)
        except:
            pass  # 预期会失败
        
        # 验证缓冲区大小限制
        assert kafka_source._local_buffer.qsize() <= kafka_source.buffer_size
        
        # 清理资源
        kafka_source._running = False
        if kafka_source._consumer_thread:
            kafka_source._consumer_thread.join(timeout=1.0)
    
    def test_serialization_deserialization(self):
        """测试序列化和反序列化"""
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            auto_offset_reset="earliest",
            value_deserializer="json",
            buffer_size=1000,
            custom_param="custom_value"
        )
        
        # 模拟运行时状态
        kafka_source._running = True
        kafka_source._initialized = True
        kafka_source._consumer = Mock()
        kafka_source._local_buffer = Mock()
        kafka_source._consumer_thread = Mock()
        
        # 获取序列化状态
        state = kafka_source.__getstate__()
        
        # 验证运行时对象被排除
        assert state['_consumer'] is None
        assert state['_local_buffer'] is None
        assert state['_consumer_thread'] is None
        assert state['_running'] is False
        assert state['_initialized'] is False
        
        # 验证配置信息被保留
        assert state['bootstrap_servers'] == "localhost:9092"
        assert state['topic'] == "test_topic"
        assert state['group_id'] == "test_group"
        assert state['kafka_config']['custom_param'] == "custom_value"
        
        # 创建新实例并恢复状态
        new_kafka_source = KafkaSourceFunction("dummy", "dummy", "dummy")
        new_kafka_source.__setstate__(state)
        
        # 验证状态恢复
        assert new_kafka_source.bootstrap_servers == "localhost:9092"
        assert new_kafka_source.topic == "test_topic"
        assert new_kafka_source.group_id == "test_group"
        assert new_kafka_source._running is False
        assert new_kafka_source._initialized is False
    
    def test_get_stats(self):
        """测试统计信息获取"""
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group"
        )
        
        # 未初始化时的统计信息
        stats = kafka_source.get_stats()
        assert stats['initialized'] is False
        
        # 模拟初始化后的统计信息
        kafka_source._initialized = True
        kafka_source._running = True
        kafka_source._local_buffer = Mock()
        kafka_source._local_buffer.qsize.return_value = 5
        
        stats = kafka_source.get_stats()
        assert stats['initialized'] is True
        assert stats['topic'] == "test_topic"
        assert stats['group_id'] == "test_group"
        assert stats['running'] is True
        assert stats['buffer_size'] == 5
        assert stats['max_buffer_size'] == 10000
    
    @patch('kafka.KafkaConsumer')  # 修正mock路径
    def test_initialization_error_handling(self, mock_kafka_consumer):
        """测试初始化错误处理"""
        # 模拟KafkaConsumer初始化失败
        mock_kafka_consumer.side_effect = Exception("Connection failed")
        
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="invalid_server:9092",
            topic="test_topic",
            group_id="test_group"
        )
        
        # 初始化应该失败并抛出异常
        with pytest.raises(Exception, match="Connection failed"):
            kafka_source._lazy_init()
        
        # 验证状态保持未初始化
        assert kafka_source._initialized is False
        assert kafka_source._running is False


class TestKafkaSourceIntegration:
    """Kafka Source集成测试"""
    
    def test_environment_kafka_source_creation(self):
        """测试Environment创建Kafka源"""
        env = LocalEnvironment()
        
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            auto_offset_reset="earliest",
            buffer_size=5000
        )
        
        # 验证DataStream创建
        assert kafka_stream is not None
        assert len(env._pipeline) == 1
        
        # 验证Transformation类型
        transformation = env._pipeline[0]
        assert transformation.function_class == KafkaSourceFunction
        
        # 验证参数传递
        expected_kwargs = {
            'bootstrap_servers': "localhost:9092",
            'topic': "test_topic", 
            'group_id': "test_group",
            'auto_offset_reset': "earliest",
            'value_deserializer': "json",
            'buffer_size': 5000,
            'max_poll_records': 500
        }
        
        for key, value in expected_kwargs.items():
            assert transformation.function_kwargs[key] == value
    
    def test_remote_environment_kafka_source(self):
        """测试远程环境中的Kafka源"""
        env = RemoteEnvironment()
        env.set_memory()
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="kafka-cluster:9092",
            topic="production_topic",
            group_id="production_group"
        )
        
        # 验证远程环境下的配置
        assert env.platform == "remote"
        assert kafka_stream is not None
        
        transformation = env._pipeline[0]
        assert transformation.function_kwargs['bootstrap_servers'] == "kafka-cluster:9092"
        assert transformation.function_kwargs['topic'] == "production_topic"


class ProcessTestEvent(BaseFunction):
    """测试用的处理函数"""
    def execute(self, data):
        if data is None:
            return None
        
        event = data.get('value', {})
        return {
            'processed': True,
            'original': event,
            'timestamp': data.get('timestamp')
        }


class CollectResults(BaseFunction):
    """收集测试结果的Sink函数"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []
    
    def execute(self, data):
        if data is not None:
            self.results.append(data)
        return data


class TestKafkaSourcePipeline:
    """Kafka Source Pipeline测试"""
    
    @patch('kafka.KafkaConsumer')  # 修正mock路径
    def test_end_to_end_pipeline_setup(self, mock_kafka_consumer):
        """测试端到端的Kafka消费pipeline设置"""
        # 模拟KafkaConsumer
        mock_consumer_instance = Mock()
        mock_kafka_consumer.return_value = mock_consumer_instance
        
        # 创建测试pipeline
        env = LocalEnvironment()
        
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            buffer_size=10
        )
        
        # 添加处理逻辑
        collector = CollectResults()
        
        # 使用lambda函数创建sink（避免复杂的sink创建）
        processed_stream = kafka_stream.map(ProcessTestEvent)
        
        # 验证pipeline构建
        assert len(env._pipeline) == 2  # source + map
        
        # 验证source配置
        source_transformation = env._pipeline[0]
        assert source_transformation.function_class == KafkaSourceFunction
        assert source_transformation.function_kwargs['topic'] == "test_topic"
        
        # 验证map配置
        map_transformation = env._pipeline[1]
        assert map_transformation.function_class == ProcessTestEvent
    
    def test_kafka_source_with_custom_deserializer(self):
        """测试自定义反序列化器"""
        def custom_deserializer(data):
            """自定义反序列化：添加前缀"""
            json_data = json.loads(data.decode('utf-8'))
            json_data['custom_prefix'] = 'CUSTOM_'
            return json_data
        
        env = LocalEnvironment()
        
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            value_deserializer=custom_deserializer
        )
        
        # 验证自定义反序列化器传递
        transformation = env._pipeline[0]
        assert transformation.function_kwargs['value_deserializer'] == custom_deserializer


class TestKafkaSourceConfiguration:
    """Kafka Source配置测试"""
    
    def test_default_configuration(self):
        """测试默认配置"""
        env = LocalEnvironment()
        
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group"
        )
        
        transformation = env._pipeline[0]
        
        # 验证默认值
        assert transformation.function_kwargs['auto_offset_reset'] == 'latest'
        assert transformation.function_kwargs['value_deserializer'] == 'json'
        assert transformation.function_kwargs['buffer_size'] == 10000
        assert transformation.function_kwargs['max_poll_records'] == 500
    
    def test_custom_configuration(self):
        """测试自定义配置"""
        env = LocalEnvironment()
        
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="custom:9092",
            topic="custom_topic",
            group_id="custom_group",
            auto_offset_reset="earliest",
            value_deserializer="string",
            buffer_size=20000,
            max_poll_records=1000,
            session_timeout_ms=30000,
            security_protocol="SSL"
        )
        
        transformation = env._pipeline[0]
        
        # 验证自定义值
        assert transformation.function_kwargs['bootstrap_servers'] == "custom:9092"
        assert transformation.function_kwargs['topic'] == "custom_topic"
        assert transformation.function_kwargs['group_id'] == "custom_group"
        assert transformation.function_kwargs['auto_offset_reset'] == "earliest"
        assert transformation.function_kwargs['value_deserializer'] == "string"
        assert transformation.function_kwargs['buffer_size'] == 20000
        assert transformation.function_kwargs['max_poll_records'] == 1000
        assert transformation.function_kwargs['session_timeout_ms'] == 30000
        assert transformation.function_kwargs['security_protocol'] == "SSL"


class TestKafkaSourceMessageProcessing:
    """Kafka消息处理测试"""
    
    @patch('kafka.KafkaConsumer')
    def test_message_processing_flow(self, mock_kafka_consumer):
        """测试消息处理流程"""
        # 创建mock消息
        mock_message = Mock()
        mock_message.value = {"event": "test", "data": "sample"}
        mock_message.timestamp = 1640995200000
        mock_message.partition = 0
        mock_message.offset = 1
        mock_message.key = b"test_key"
        
        # 配置mock consumer
        mock_consumer_instance = Mock()
        mock_topic_partition = Mock()
        mock_consumer_instance.poll.return_value = {mock_topic_partition: [mock_message]}
        mock_kafka_consumer.return_value = mock_consumer_instance
        
        # 创建KafkaSourceFunction
        kafka_source = KafkaSourceFunction(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group",
            buffer_size=10
        )
        
        # 触发初始化和消息处理
        kafka_source.execute(None)
        time.sleep(0.1)  # 等待消费线程处理
        
        # 获取处理后的消息
        processed_message = kafka_source.execute(None)
        
        assert processed_message is not None
        assert processed_message['value'] == {"event": "test", "data": "sample"}
        assert processed_message['timestamp'] == 1640995200000
        assert processed_message['partition'] == 0
        assert processed_message['offset'] == 1
        assert processed_message['key'] == "test_key"
        
        # 清理
        kafka_source._running = False
        if kafka_source._consumer_thread:
            kafka_source._consumer_thread.join(timeout=1.0)


# pytest配置和工具函数
def setup_module():
    """模块级别的设置"""
    print("Setting up Kafka Source tests...")

def teardown_module():
    """模块级别的清理"""
    print("Tearing down Kafka Source tests...")


# 运行测试的入口
if __name__ == "__main__":
    # 运行测试
    pytest.main([
        __file__,
        "-v",  # 详细输出
        "-s",  # 显示print输出
        "--tb=short",  # 简短的traceback
        "--durations=10",  # 显示最慢的10个测试
        "-x"  # 遇到第一个失败就停止
    ])