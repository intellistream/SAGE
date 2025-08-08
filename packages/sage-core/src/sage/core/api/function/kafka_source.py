from sage.core.api.function.source_function import SourceFunction
from typing import Callable, Dict, Any, TYPE_CHECKING
import threading, json, queue
if TYPE_CHECKING:
    from sage.kernel import TaskContext


class KafkaSourceFunction(SourceFunction):
    """
    Flink风格的Kafka Source Function
    采用延迟初始化模式，完美支持Ray分布式序列化
    """
    
    def __init__(self, 
                 bootstrap_servers: str,
                 topic: str,
                 group_id: str,
                 auto_offset_reset: str = 'latest',
                 value_deserializer: str = 'json',
                 ctx:'TaskContext' = None,
                 buffer_size: int = 10000,
                 max_poll_records: int = 500,
                 **kafka_config):
        super().__init__(ctx)
        
        # 可序列化的配置信息
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.value_deserializer = value_deserializer
        self.buffer_size = buffer_size
        self.max_poll_records = max_poll_records
        self.kafka_config = kafka_config
        
        # 运行时对象，不参与序列化
        self._consumer = None
        self._local_buffer = None
        self._consumer_thread = None
        self._running = False
        self._initialized = False
    
    def _get_deserializer(self) -> Callable:
        """获取反序列化函数"""
        if self.value_deserializer == 'json':
            return lambda x: json.loads(x.decode('utf-8'))
        elif self.value_deserializer == 'string':
            return lambda x: x.decode('utf-8')
        elif self.value_deserializer == 'bytes':
            return lambda x: x
        elif callable(self.value_deserializer):
            return self.value_deserializer
        else:
            raise ValueError(f"Unsupported deserializer: {self.value_deserializer}")
    
    def _lazy_init(self):
        """
        延迟初始化：在远程节点上创建Kafka连接
        类似Flink的SourceFunction.run()模式
        """
        if self._initialized:
            return
        
        try:
            from kafka import KafkaConsumer
            
            # 创建本地缓冲区
            self._local_buffer = queue.Queue(maxsize=self.buffer_size)
            
            # 创建Kafka Consumer（在远程节点上）
            deserializer = self._get_deserializer()
            self._consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=deserializer,
                max_poll_records=self.max_poll_records,
                consumer_timeout_ms=1000,
                **self.kafka_config
            )
            
            # 启动后台消费线程
            self._running = True
            self._consumer_thread = threading.Thread(
                target=self._consume_loop, 
                daemon=True
            )
            self._consumer_thread.start()
            
            self._initialized = True
            self.logger.info(f"Kafka source initialized for topic: {self.topic}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka source: {e}")
            raise

    def _consume_loop(self):
        """Kafka消费主循环，在后台线程执行"""
        try:
            while self._running:
                try:
                    msg_pack = self._consumer.poll(timeout_ms=1000)
                    if not msg_pack:
                        continue
                    
                    for topic_partition, messages in msg_pack.items():
                        for message in messages:
                            if not self._running:
                                break
                            
                            # 构造消息对象
                            kafka_message = {
                                'value': message.value,
                                'timestamp': message.timestamp,
                                'partition': message.partition,
                                'offset': message.offset,
                                'key': message.key.decode('utf-8') if message.key else None
                            }
                            
                            # 推送到本地缓冲区
                            try:
                                self._local_buffer.put_nowait(kafka_message)
                            except queue.Full:
                                # 背压处理：丢弃最老的消息
                                try:
                                    self._local_buffer.get_nowait()
                                    self._local_buffer.put_nowait(kafka_message)
                                except queue.Empty:
                                    pass
                                    
                except Exception as e:
                    if self._running:
                        self.logger.error(f"Error in Kafka consume loop: {e}")
                        
        except Exception as e:
            self.logger.error(f"Fatal error in Kafka consumer: {e}")
        finally:
            self._cleanup()



    def execute(self, _:Any = None):
        """
        SAGE Function接口：获取Kafka消息
        首次调用时触发延迟初始化
        """
        if not self._initialized:
            self._lazy_init()
        
        try:
            return self._local_buffer.get_nowait()
        except queue.Empty:
            return None
    
    def _cleanup(self):
        """清理资源"""
        if self._consumer:
            try:
                self._consumer.close()
                self.logger.info("Kafka consumer closed")
            except Exception as e:
                self.logger.error(f"Error closing Kafka consumer: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取消费统计信息"""
        if not self._initialized:
            return {'initialized': False}
        
        return {
            'initialized': True,
            'topic': self.topic,
            'group_id': self.group_id,
            'running': self._running,
            'buffer_size': self._local_buffer.qsize() if self._local_buffer else 0,
            'max_buffer_size': self.buffer_size
        }
    
    def __getstate__(self):
        """
        控制序列化过程：只序列化配置信息
        类似Flink的transient字段机制
        """
        state = self.__dict__.copy()
        # 排除运行时对象
        state['_consumer'] = None
        state['_local_buffer'] = None
        state['_consumer_thread'] = None
        state['_running'] = False
        state['_initialized'] = False
        return state
    
    def __setstate__(self, state):
        """反序列化后恢复状态"""
        self.__dict__.update(state)
        # 重置运行时对象
        self._consumer = None
        self._local_buffer = None
        self._consumer_thread = None
        self._running = False
        self._initialized = False