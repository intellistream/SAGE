import time 
from sage.core.api.service.base_service import BaseService
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.common.utils.logging.custom_logger import CustomLogger

# 批处理数据源：生成10条 Hello, World! 数据
class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10  # 生成10个数据包后返回None
    
    def execute(self):
        if self.counter >= self.max_count:
            return None  # 返回None表示批处理完成
        self.counter += 1
        return f"Hello, World! #{self.counter}"


# 简单 SinkFunction，调用hello服务并打印结果
class PrintSink(SinkFunction):
    def execute(self, data):
        self.call_service["hello_service"].hello()
        print(data)


class HelloService(BaseService):
    def __init__(self):
        self.message = "hello service!!!"
        
    def hello(self):
        print(self.message)


def main():
    env = LocalEnvironment("hello_service")
    env.register_service("hello_service", HelloService)

    env.from_batch(HelloBatch).sink(PrintSink)

    try:
        print("Waiting for batch processing to complete...")
        env.submit(autostop=True)
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        print("Hello Service 批处理示例结束")

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()  # 禁用debug日志以获得更简洁的输出
    main()