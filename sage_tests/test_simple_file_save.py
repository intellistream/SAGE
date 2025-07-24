#!/usr/bin/env python3
"""
简化的Join测试，专门测试结果保存到文件的机制
"""

import time
import threading
import tempfile
import json
from typing import List, Dict, Any
from pathlib import Path
from sage_core.api.local_environment import LocalEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.sink_function import SinkFunction


class SimpleDataSource(SourceFunction):
    """生成简单测试数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.data = [
            {"id": 1, "type": "test", "message": "Hello World"},
            {"id": 2, "type": "test", "message": "Join Test"},
            {"id": 3, "type": "test", "message": "File Save Test"},
        ]
    
    def execute(self):
        if self.counter >= len(self.data):
            return None
        
        data = self.data[self.counter]
        self.counter += 1
        if self.ctx:
            self.logger.info(f"SimpleDataSource generated: {data}")
        return data


class TestResultSink(SinkFunction):
    """测试结果保存的Sink"""
    
    def __init__(self, output_file=None, **kwargs):
        super().__init__(**kwargs)
        self.parallel_index = None
        self.received_count = 0
        
        # 如果没有指定输出文件，使用临时文件
        if output_file is None:
            self.output_file = Path(tempfile.gettempdir()) / "simple_test_results.json"
        else:
            self.output_file = Path(output_file)
            
        if self.ctx:
            self.logger.info(f"TestResultSink initialized, output file: {self.output_file}")

    def execute(self, data: Any):
        if self.ctx:
            self.parallel_index = self.ctx.parallel_index

        self.received_count += 1

        if self.ctx:
            self.logger.info(
                f"[Instance {self.parallel_index}] "
                f"Received data #{self.received_count}: {data}"
            )

        # 打印调试信息
        print(f"📄 [Instance {self.parallel_index}] Data: {data}")
        
        # 保存到文件
        self._append_record({
            "parallel_index": self.parallel_index,
            "sequence": self.received_count,
            "data": data,
            "timestamp": time.time()
        })

        return data
    
    def _append_record(self, record):
        """原子性地追加记录到文件"""
        try:
            # 以追加模式打开文件
            with open(self.output_file, 'a') as f:
                # 写入一行JSON
                f.write(json.dumps(record) + '\n')
                f.flush()
        except Exception as e:
            if self.ctx:
                self.logger.error(f"Failed to write record: {e}")
    
    @classmethod
    def read_results(cls, output_file=None):
        """读取测试结果"""
        if output_file is None:
            output_file = Path(tempfile.gettempdir()) / "simple_test_results.json"
        else:
            output_file = Path(output_file)
        
        results = {}
        
        if not output_file.exists():
            print(f"📂 No results file found: {output_file}")
            return results
        
        try:
            with open(output_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        parallel_index = record.get("parallel_index", 0)
                        data = record.get("data")
                        
                        if parallel_index not in results:
                            results[parallel_index] = []
                        
                        results[parallel_index].append(data)
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Failed to parse line {line_num}: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Failed to read results file: {e}")
        
        print(f"📂 Read {sum(len(data_list) for data_list in results.values())} records from {len(results)} parallel instances")
        return results
    
    @classmethod
    def clear_results(cls, output_file=None):
        """清理结果"""
        if output_file is None:
            output_file = Path(tempfile.gettempdir()) / "simple_test_results.json"
        else:
            output_file = Path(output_file)
        
        if output_file.exists():
            output_file.unlink()
            print(f"🗑️ Cleared results file: {output_file}")


def test_simple_file_save():
    """测试简单的文件保存功能"""
    print("\n🚀 Testing Simple File Save Mechanism")
    
    # 清理旧结果
    TestResultSink.clear_results()
    
    env = LocalEnvironment("simple_file_test")
    
    # 创建简单的管道：Source -> Sink
    result = (env
        .from_source(SimpleDataSource, delay=0.3)
        .sink(TestResultSink, parallelism=2)
    )
    
    print("📊 Pipeline: SimpleDataSource -> TestResultSink (parallelism=2)")
    print("🎯 Expected: Data saved to file and read back\n")
    
    try:
        env.submit()
        
        # 等待数据处理
        time.sleep(3)
    finally:
        env.close()
    
    # 等待一下确保文件写入完成
    time.sleep(1)
    
    # 读取并验证结果
    results = TestResultSink.read_results()
    
    print("\n📋 File Save Test Results:")
    print("=" * 50)
    
    total_records = 0
    for instance_id, data_list in results.items():
        print(f"\n🔹 Parallel Instance {instance_id}:")
        for i, data in enumerate(data_list):
            print(f"   Record {i+1}: {data}")
            total_records += 1
    
    print(f"\n🎯 Summary:")
    print(f"   - Total records saved and read: {total_records}")
    print(f"   - Parallel instances: {len(results)}")
    
    if total_records > 0:
        print("✅ File save mechanism test passed!")
    else:
        print("❌ File save mechanism test failed: No records found")
    
    return total_records > 0


if __name__ == "__main__":
    success = test_simple_file_save()
    if not success:
        exit(1)
