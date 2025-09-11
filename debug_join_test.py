#!/usr/bin/env python3
"""
简化的Join测试 - 调试None值问题
"""

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.keyby_function import KeyByFunction
from sage.core.api.function.join_function import BaseJoinFunction
from sage.common.utils.logging.custom_logger import CustomLogger

class SimpleSource1(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 2:  # 只生成2个数据
            print(f"SimpleSource1 returning None at counter={self.counter}")
            return None
        result = {"id": self.counter, "value": f"A-{self.counter}"}
        print(f"SimpleSource1 returning: {result}")
        return result

class SimpleSource2(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 2:  # 只生成2个数据
            print(f"SimpleSource2 returning None at counter={self.counter}")
            return None
        result = {"id": self.counter, "value": f"B-{self.counter}"}
        print(f"SimpleSource2 returning: {result}")
        return result

class SimpleKeyBy(KeyByFunction):
    def execute(self, data):
        key = data.get("id")
        print(f"SimpleKeyBy extracting key {key} from {data}")
        return key

class SimpleJoin(BaseJoinFunction):
    def __init__(self):
        super().__init__()
        self.cache_a = {}
        self.cache_b = {}

    def execute(self, payload, key, tag):
        print(f"SimpleJoin.execute: payload={payload}, key={key}, tag={tag}")
        
        if payload is None:
            print("WARNING: SimpleJoin received None payload!")
            return []
        
        results = []
        
        if tag == 0:  # Source1
            self.cache_a[key] = payload
            if key in self.cache_b:
                result = {"key": key, "joined": f"{payload['value']}+{self.cache_b[key]['value']}"}
                results.append(result)
                print(f"SimpleJoin emitting: {result}")
        elif tag == 1:  # Source2
            self.cache_b[key] = payload
            if key in self.cache_a:
                result = {"key": key, "joined": f"{self.cache_a[key]['value']}+{payload['value']}"}
                results.append(result)
                print(f"SimpleJoin emitting: {result}")
        
        return results

class DebugSink(SinkFunction):
    def execute(self, data):
        print(f"DebugSink received: {data} (type: {type(data)})")

def main():
    env = LocalEnvironment("debug_join")

    source1 = env.from_batch(SimpleSource1)
    source2 = env.from_batch(SimpleSource2)

    source1.keyby(SimpleKeyBy).connect(source2.keyby(SimpleKeyBy)).join(SimpleJoin).sink(DebugSink)

    print("Starting execution...")
    env.submit(autostop=True)
    print("Execution finished")

if __name__ == "__main__":
    # 启用详细日志
    import logging
    logging.basicConfig(level=logging.INFO)
    main()
