#!/usr/bin/env python3
"""
测试脚本：诊断 Join 操作符的停止信号问题
"""

import logging
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.keyby_function import KeyByFunction
from sage.core.api.function.join_function import BaseJoinFunction

# 启用详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')

class TestSourceOne(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 2:  # 只生成2条数据
            return None
        return {"id": self.counter, "msg": f"Hello-{self.counter}", "type": "hello"}

class TestSourceTwo(BatchFunction):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        if self.counter > 2:  # 只生成2条数据
            return None
        return {"id": self.counter, "msg": f"World-{self.counter}", "type": "world"}

class TestKeyBy(KeyByFunction):
    def execute(self, data):
        return data.get("id")

class TestSink(SinkFunction):
    def execute(self, data):
        print(f"🔗 Result: {data}")

class TestJoin(BaseJoinFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hello_cache = {}
        self.world_cache = {}

    def execute(self, payload, key, tag):
        results = []
        
        if tag == 0:  # SourceOne
            self.hello_cache.setdefault(key, []).append(payload)
            if key in self.world_cache:
                for world_data in self.world_cache[key]:
                    results.append({
                        "id": key,
                        "msg": f"{payload['msg']} + {world_data['msg']}"
                    })
        elif tag == 1:  # SourceTwo
            self.world_cache.setdefault(key, []).append(payload)
            if key in self.hello_cache:
                for hello_data in self.hello_cache[key]:
                    results.append({
                        "id": key,
                        "msg": f"{hello_data['msg']} + {payload['msg']}"
                    })
        
        return results

def main():
    print("=== 诊断 Join 停止信号问题 ===")
    
    env = LocalEnvironment("test_join_stop_signal")
    
    # 创建两个源
    source1 = env.from_batch(TestSourceOne)
    source2 = env.from_batch(TestSourceTwo)
    
    # 构建拓扑
    source1.keyby(TestKeyBy).connect(source2.keyby(TestKeyBy)).join(TestJoin).sink(TestSink)
    
    # 提交任务
    print("提交任务...")
    env.submit(autostop=True)
    
    print("任务完成")

if __name__ == "__main__":
    main()
