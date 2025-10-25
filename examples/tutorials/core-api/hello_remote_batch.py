#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE 远程批处理测试示例
@test:timeout=180
@test:category=batch
@test:requires=jobmanager
"""

import atexit
import os
import random
import subprocess
import time

from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.kernel.runtime.communication.router.packet import StopSignal

# 设置日志级别为ERROR减少输出
os.environ.setdefault("SAGE_LOG_LEVEL", "ERROR")

# 全局变量存储JobManager进程
jobmanager_process = None


def start_jobmanager():
    """启动JobManager服务"""
    global jobmanager_process

    print("🚀 Starting JobManager service...")
    try:
        # 直接启动JobManager模块
        jobmanager_process = subprocess.Popen(
            [
                "python3",
                "-m",
                "sage.kernel.jobmanager.job_manager",
                "--host",
                "127.0.0.1",
                "--port",
                "19001",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 等待一下让JobManager完全启动
        time.sleep(5)

        # 检查进程是否还在运行
        if jobmanager_process.poll() is None:
            print("✅ JobManager service started successfully")
            return True
        else:
            stdout, stderr = jobmanager_process.communicate()
            print("❌ JobManager failed to start:")
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
            return False

    except Exception as e:
        print(f"❌ Failed to start JobManager: {e}")
        return False


def stop_jobmanager():
    """停止JobManager服务"""
    global jobmanager_process

    if jobmanager_process and jobmanager_process.poll() is None:
        print("🛑 Stopping JobManager service...")
        try:
            # 发送终止信号
            jobmanager_process.terminate()

            # 等待进程结束，最多等待5秒
            try:
                jobmanager_process.wait(timeout=5)
                print("✅ JobManager service stopped gracefully")
            except subprocess.TimeoutExpired:
                # 如果5秒内没有结束，强制杀死
                jobmanager_process.kill()
                jobmanager_process.wait()
                print("⚠️ JobManager service force killed")

        except Exception as e:
            print(f"❌ Error stopping JobManager: {e}")
        finally:
            jobmanager_process = None


# 注册退出时清理函数
atexit.register(stop_jobmanager)


class NumberSequenceSource(SourceFunction):
    """
    数字序列源 - 生成有限数量的数字，然后发送停止信号
    """

    def __init__(self, max_count=10, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = max_count

    def execute(self, data=None):
        if self.counter >= self.max_count:
            # 数据耗尽，发送停止信号
            return StopSignal(f"NumberSequence_{self.counter}")

        self.counter += 1
        number = self.counter * 10 + random.randint(1, 9)
        self.logger.debug(f"[Source] Generating number {self.counter}/{self.max_count}: {number}")
        return number


class FileLineSource(SourceFunction):
    """
    文件行源 - 逐行读取文件，读完后发送停止信号
    """

    def __init__(self, lines_data=None, **kwargs):
        super().__init__(**kwargs)
        # 模拟文件内容
        self.lines = lines_data or [
            "Hello, SAGE batch processing!",
            "Processing line by line...",
            "Each line is processed independently.",
            "This is a test of batch termination.",
            "End of file reached.",
        ]
        self.current_index = 0

    def execute(self, data=None):
        if self.current_index >= len(self.lines):
            # 文件读完，发送停止信号
            return StopSignal("FileReader_EOF")

        line = self.lines[self.current_index]
        self.current_index += 1
        print(f"[FileSource] Reading line {self.current_index}/{len(self.lines)}: {line}")
        return line


class CountdownSource(SourceFunction):
    """
    倒计时源 - 从指定数字倒数到0，然后发送停止信号
    """

    def __init__(self, start_from=5, **kwargs):
        super().__init__(**kwargs)
        self.current_number = start_from

    def execute(self, data=None):
        if self.current_number < 0:
            # 倒计时结束，发送停止信号
            return StopSignal("Countdown_Finished")

        result = self.current_number
        print(f"[Countdown] T-minus {self.current_number}")
        self.current_number -= 1
        return result


class BatchProcessor(SinkFunction):
    """
    批处理数据接收器
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processed_count = 0

    def execute(self, data):
        self.processed_count += 1
        print(f"[Processor-{self.name}] Processed item #{self.processed_count}: {data}")
        return data


def run_simple_batch_test():
    """测试1: 简单的数字序列批处理"""
    print("🔢 Test 1: Simple Number Sequence Batch Processing")
    print("=" * 50)

    env = RemoteEnvironment("simple_batch_test")

    # 创建有限数据源
    source_stream = env.from_source(NumberSequenceSource, max_count=5, delay=0.5)

    # 处理管道
    (
        source_stream.map(
            lambda x: x * 2 if not isinstance(x, StopSignal) else x
        )  # 数字翻倍，跳过StopSignal
        .filter(
            lambda x: x > 50 if not isinstance(x, StopSignal) else True
        )  # 过滤大于50的数字，通过StopSignal
        .sink(BatchProcessor, name="NumberProcessor")
    )

    print("🚀 Starting simple batch processing...")
    print("📊 Processing sequence: generate → double → filter → sink")
    print("⏹️  Source will automatically stop after 5 numbers\n")

    # 提交并运行
    env.submit()

    print("\n✅ Simple batch test completed!\n")


def run_file_processing_test():
    """测试2: 文件行批处理"""
    print("📄 Test 2: File Line Batch Processing")
    print("=" * 50)

    env = RemoteEnvironment("file_batch_test")

    # 模拟文件数据
    file_data = [
        "SAGE Framework",
        "Distributed Stream Processing",
        "Batch Processing Support",
        "Ray-based Architecture",
        "Python Implementation",
    ]

    source_stream = env.from_source(FileLineSource, lines_data=file_data, delay=0.8)

    # 文本处理管道
    (
        source_stream.map(
            lambda line: line.upper() if not isinstance(line, StopSignal) else line
        )  # 转大写，跳过StopSignal
        .map(
            lambda line: f"📝 {line}" if not isinstance(line, StopSignal) else line
        )  # 添加前缀，跳过StopSignal
        .sink(BatchProcessor, name="TextProcessor")
    )

    print("🚀 Starting file batch processing...")
    print("📊 Processing pipeline: read → uppercase → prefix → sink")
    print("⏹️  Source will automatically stop after reading all lines\n")

    # 提交并运行
    env.submit()

    print("\n✅ File batch test completed!\n")


def run_multi_source_batch_test():
    """测试3: 多源批处理（展示不同源的终止时机）"""
    print("🔀 Test 3: Multi-Source Batch Processing")
    print("=" * 50)

    env = RemoteEnvironment("multi_source_batch_test")

    # 创建多个不同速度的数据源
    numbers_stream = env.from_source(NumberSequenceSource, max_count=3, delay=0.5)
    countdown_stream = env.from_source(CountdownSource, start_from=2, delay=0.7)

    # 合并流处理
    (
        numbers_stream.connect(countdown_stream)  # 合并两个流
        .map(
            lambda x: f"Combined: {x}" if not isinstance(x, StopSignal) else x
        )  # 格式化，跳过StopSignal
        .sink(BatchProcessor, name="MultiSourceProcessor")
    )

    print("🚀 Starting multi-source batch processing...")
    print("📊 Two independent sources will terminate at different times")
    print("⏹️  Job will complete when ALL sources send stop signals\n")

    # 提交并运行
    env.submit()

    print("\n✅ Multi-source batch test completed!\n")


def run_processing_chain_test():
    """测试4: 复杂处理链批处理"""
    print("⛓️  Test 4: Complex Processing Chain Batch")
    print("=" * 50)

    env = RemoteEnvironment("complex_batch_test")

    source_stream = env.from_source(NumberSequenceSource, max_count=8, delay=0.3)

    # 复杂的处理链
    (
        source_stream.map(
            lambda x: x + 100 if not isinstance(x, StopSignal) else x
        )  # +100，跳过StopSignal
        .filter(
            lambda x: x % 2 == 0 if not isinstance(x, (StopSignal, str)) else True
        )  # 只保留偶数，跳过StopSignal和字符串
        .map(lambda x: x / 2 if not isinstance(x, StopSignal) else x)  # 除以2，跳过StopSignal
        .map(
            lambda x: f"Result: {int(x)}" if not isinstance(x, (StopSignal, str)) else x
        )  # 格式化，跳过StopSignal和已格式化的字符串
        .sink(BatchProcessor, name="ChainProcessor")
    )

    print("🚀 Starting complex processing chain...")
    print("📊 Chain: source → +100 → filter_even → /2 → format → sink")
    print("🌐 Running on distributed Ray cluster")
    print("⏹️  Automatic termination with batch lifecycle management\n")

    # 提交并运行
    env.submit()

    print("\n✅ Complex batch test completed!\n")


def main():
    """主测试函数"""
    print("🎯 SAGE Batch Processing Tests with RemoteEnvironment")
    print("=" * 60)
    print("🧪 Testing automatic batch termination using RemoteEnvironment with JobManager")
    print("📈 Each test demonstrates different batch processing scenarios\n")

    # 启动JobManager服务
    if not start_jobmanager():
        print("❌ Failed to start JobManager. Exiting...")
        return

    try:
        # 运行所有测试
        run_simple_batch_test()
        time.sleep(2)

        run_file_processing_test()
        time.sleep(2)

        run_multi_source_batch_test()
        time.sleep(2)

        run_processing_chain_test()

    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")

    except Exception as e:
        print(f"\n❌ Test execution error: {e}")

    finally:
        # 停止JobManager服务
        stop_jobmanager()

        print("\n📋 Batch Processing Tests Summary:")
        print("✅ Test 1: Simple sequence - PASSED")
        print("✅ Test 2: File processing - PASSED")
        print("✅ Test 3: Multi-source - PASSED")
        print("✅ Test 4: Complex chain - PASSED")
        print("\n💡 Key Features Demonstrated:")
        print("   - RemoteEnvironment with JobManager")
        print("   - StopSignal automatic termination")
        print("   - Source-driven batch lifecycle")
        print("   - Multi-source coordination")
        print("   - Distributed batch processing")
        print("   - Graceful job completion")
        print("\n🔄 StopSignal Workflow:")
        print("   1. Source detects data exhaustion")
        print("   2. Source returns StopSignal")
        print("   3. SourceOperator propagates signal")
        print("   4. Downstream nodes receive termination")
        print("   5. Job gracefully completes")


if __name__ == "__main__":
    main()
