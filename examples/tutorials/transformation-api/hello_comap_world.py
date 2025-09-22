# 此例意在说明如何将两个流通过comap合为一个流

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.comap_function import BaseCoMapFunction

# 定义两个简单数据源：
class SourceOne(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 5:
            return None
        return {"msg": f"No.{self.counter}: Hello"}

class SourceTwo(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 10:
            return None
        return {"msg": f"World! #{self.counter}"}

class HelloCoMapProcessor(BaseCoMapFunction):
    def map0(self, data):
        return f"[Stream0] 👋 {data['msg']}"
    
    def map1(self, data):
        return f"[Stream1] 🌍 {data['msg']}"

class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)

def main():
    env = LocalEnvironment("Hello_CoMap_World")

    # 两个数据源
    source1 = env.from_batch(SourceOne)
    source2 = env.from_batch(SourceTwo)

    # 将两个流 connect 在一起，并用 comap 分开处理
    source1.connect(source2).comap(HelloCoMapProcessor).sink(PrintSink)

    env.submit(autostop=True)
    print("Hello Comap World 示例结束")

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()