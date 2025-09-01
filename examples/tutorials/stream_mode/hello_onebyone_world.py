from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.communication.metronome import create_metronome
import time 

metronome = create_metronome("sync_metronome")

class SyncBatch(BatchFunction):
    use_metronome = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 5
        self.metronome = metronome

    def execute(self):
        if self.counter >= self.max_count:
            return None
        self.counter += 1
        data = f"hello, No. {str(self.counter)} one by one world~"
        print(f" ⚡ {data}")
        return data

class UpperMap(MapFunction):
    def execute(self, data):
        print(f" 🔔 uppering word!!!")
        time.sleep(1)  
        return data.upper()

class SyncSink(SinkFunction):
    use_metronome = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metronome = metronome
        
    def execute(self, data):
        print(f" ✅ {data}")
        time.sleep(1)  

def main():   
    metronome.release_once()
    env = LocalEnvironment("Test_Sync")
    env.from_batch(SyncBatch).map(UpperMap).sink(SyncSink)
    env.submit(autostop=True)
    print("Hello one by one World 批处理示例结束")

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
