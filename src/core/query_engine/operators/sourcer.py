from confluent_kafka import Consumer, KafkaException
from src.core.query_engine.operators.base_operator import BaseOperator

class BaseSource(BaseOperator):
    def __init__(self):
        super().__init__()

    def execute(self,**kwargs):
        pass

class KafkaSource(BaseSource):

    def __init__(self,conf,topic):
        super().__init__()
        self.consumer=Consumer(conf)
        self.consumer.subscribe([topic])
    def execute(self, **kwargs):
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0) 
                if msg is None:
                    continue
                if msg.error():
                    print(f"Kafka 错误: {msg.error()}")
                    continue
                
                msg=msg.value().decode('utf-8')
                self.emit((msg))

        finally:
            self.consumer.close()