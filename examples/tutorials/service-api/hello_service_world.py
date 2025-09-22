from sage.core.api.service.base_service import BaseService
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.common.utils.logging.custom_logger import CustomLogger

class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10  
    
    def execute(self):
        if self.counter >= self.max_count:
            return None  
        self.counter += 1
        return f"Hello, World! #{self.counter}"

class PrintSink(SinkFunction):
    def execute(self, data):
        # 调用服务
        self.call_service["hello_service"].hello()
        print(data)

# 继承BaseService创建一个简单的服务
class HelloService(BaseService):
    def __init__(self):
        self.message = "hello service!!!"
        
    def hello(self):
        print(self.message)


def main():
    env = LocalEnvironment("hello_service")

    # 注册服务
    env.register_service("hello_service", HelloService)

    env.from_batch(HelloBatch).sink(PrintSink)

    env.submit(autostop=True)
    print("Hello Service World 示例完成!")

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()