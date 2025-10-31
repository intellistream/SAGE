import time

from sage.common.core import BatchFunction, MapFunction, SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment


class SyncBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 5

    def execute(self):
        if self.counter >= self.max_count:
            return None
        self.counter += 1
        data = f"hello, No. {str(self.counter)} one by one world~"
        print(f" ⚡ {data}")
        return data


class UpperMap(MapFunction):
    def execute(self, data):
        print(" 🔔 uppering word!!!")
        time.sleep(1)
        return data.upper()


class SyncSink(SinkFunction):
    def execute(self, data):
        print(f" ✅ {data}")
        time.sleep(1)


def main():
    env = LocalEnvironment("Test_Sync")
    env.from_batch(SyncBatch).map(UpperMap).sink(SyncSink)
    env.submit(autostop=True)
    print("Hello one by one World 批处理示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
