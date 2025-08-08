import logging
import json
import threading
import time

from sage.core.api.local_environment import LocalEnvironment
from sage.lib.io_utils.sink import TerminalSink
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.retriever import DenseRetriever
from sage.utils.config.loader import load_config


class InteractiveKafkaProducer:
    """交互式Kafka生产者，将用户输入发送到Kafka"""
    
    def __init__(self, bootstrap_servers="localhost:9092", topic="user_queries"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        self.running = False
        
    def start(self):
        """启动Kafka生产者"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # 确保消息可靠传递
                retries=3,
                batch_size=16384,
                linger_ms=10
            )
            self.running = True
            logging.info(f"Kafka producer started, connected to {self.bootstrap_servers}")
            return True
        except Exception as e:
            logging.error(f"Failed to start Kafka producer: {e}")
            return False
    
    def send_query(self, query_text):
        """发送查询到Kafka"""
        if not self.running or not self.producer:
            logging.error("Kafka producer not running")
            return False
            
        try:
            # 构造查询消息
            message = {
                "query": query_text,
                "timestamp": time.time(),
                "user_id": "interactive_user"
            }
            
            # 发送到Kafka
            future = self.producer.send(
                self.topic, 
                value=message,
                key=f"query_{int(time.time())}"
            )
            
            # 等待发送确认
            future.get(timeout=10)
            logging.info(f"Query sent to Kafka: {query_text[:50]}...")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send query to Kafka: {e}")
            return False
    
    def stop(self):
        """停止Kafka生产者"""
        self.running = False
        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
                logging.info("Kafka producer stopped")
            except Exception as e:
                logging.error(f"Error stopping Kafka producer: {e}")


def extract_query_from_kafka(kafka_data):
    """从Kafka消息中提取查询文本的Function"""
    from sage.core.api.function.base_function import BaseFunction
    
    class QueryExtractor(BaseFunction):
        def execute(self, data):
            if data is None:
                return None
                
            try:
                # 从Kafka消息中提取查询
                kafka_message = data['value']
                query_text = kafka_message.get('query', '')
                
                if query_text:
                    self.logger.info(f"Processing query: {query_text[:50]}...")
                    return query_text
                else:
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error extracting query from Kafka message: {e}")
                return None
    
    return QueryExtractor


def pipeline_run():
    """创建并运行基于Kafka的数据处理管道"""
    env = LocalEnvironment("kafka_query")
    env.set_memory(config=None)  # 初始化内存配置
    
    # 创建Kafka数据源
    kafka_stream = env.from_kafka_source(
        bootstrap_servers="localhost:9092",
        topic="user_queries",
        group_id="sage_rag_consumer",
        auto_offset_reset="latest",  # 只处理新消息
        value_deserializer="json",
        buffer_size=1000,
        max_poll_records=100
    )
    
    # 构建数据处理流程
    query_extractor = extract_query_from_kafka(None)
    query_stream = kafka_stream.map(query_extractor)
    query_and_chunks_stream = query_stream.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["local"])
    response_stream.sink(TerminalSink, config["sink"])

    # 提交管道并运行
    env.submit()

    
    # 等待pipeline启动
    time.sleep(2)
    logging.info("Kafka RAG pipeline started successfully")


def interactive_mode():
    """交互式模式：用户输入通过Kafka发送"""
    # 启动Kafka生产者
    producer = InteractiveKafkaProducer(
        bootstrap_servers="localhost:9092",
        topic="user_queries"
    )
    
    if not producer.start():
        logging.error("Failed to start Kafka producer. Exiting.")
        return
    
    try:
        print("\n" + "="*60)
        print("🚀 SAGE Kafka-powered RAG System Started!")
        print("📋 Type your questions and get AI-powered answers")
        print("💡 Type 'exit' to quit")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n🤔 Your question >>> ").strip()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    logging.info("User requested exit")
                    print("👋 Goodbye! Thanks for using SAGE!")
                    break
                
                if not user_input:
                    print("⚠️  Please enter a valid question")
                    continue
                
                # 发送到Kafka
                if producer.send_query(user_input):
                    print("✅ Query submitted, processing...")
                else:
                    print("❌ Failed to submit query. Please try again.")
                    
            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt")
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logging.error(f"Error in interactive mode: {e}")
                print(f"❌ Error: {e}")
                
    finally:
        producer.stop()


def main():
    """主函数：启动pipeline和交互模式"""
    try:
        # 启动pipeline
        pipeline_thread = pipeline_run()
        
        # 启动交互模式
        interactive_mode()
        
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Application error: {e}")
    finally:
        logging.info("SAGE Kafka RAG system shutdown complete")


if __name__ == '__main__':
    
    # 加载配置
    config = load_config('./config_instance.yaml')
    
    # 检查Kafka连接
    try:
        from kafka import KafkaProducer
        test_producer = KafkaProducer(
            bootstrap_servers="127.0.0.1:9092",
            request_timeout_ms=5000
        )
        test_producer.close()
        logging.info("✅ Kafka connection verified")
    except Exception as e:
        logging.error(f"❌ Kafka connection failed: {e}")
        logging.error("Please ensure Kafka is running on 127.0.0.1:9092")
        exit(1)
    
    # 启动应用
    main()