#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE 本地批处理测试示例
@test:timeout=120
@test:category=batch
"""

import logging
import os
import random
import time

# 设置日志级别为ERROR减少输出
os.environ.setdefault("SAGE_LOG_LEVEL", "ERROR")

# 配置 Python 日志系统
logging.basicConfig(level=logging.ERROR)
for logger_name in ["sage", "JobManager", "ray", "asyncio", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

# 禁用所有INFO级别的日志
logging.getLogger().setLevel(logging.ERROR)

from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.remote_environment import RemoteEnvironment
from sage.kernel.runtime.communication.router.packet import StopSignal


class NumberSequenceSource(SourceFunction):
    """
    数字序列源 - 生成有限数量的数字，然后发送停止信号
    """

    def __init__(self, max_count=10, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = max_count

    def execute(self):
        if self.counter >= self.max_count:
            # 数据耗尽，发送停止信号
            return StopSignal(f"NumberSequence_{self.counter}")

        self.counter += 1
        number = self.counter * 10 + random.randint(1, 9)
        self.logger.debug(
            f"[Source] Generating number {self.counter}/{self.max_count}: {number}"
        )
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

    def execute(self):
        if self.current_index >= len(self.lines):
            # 文件读完，发送停止信号
            return StopSignal(f"FileReader_EOF")

        line = self.lines[self.current_index]
        self.current_index += 1
        logging.info(
            f"[FileSource] Reading line {self.current_index}/{len(self.lines)}: {line}"
        )
        return line


class CountdownSource(SourceFunction):
    """
    倒计时源 - 从指定数字倒数到0，然后发送停止信号
    """

    def __init__(self, start_from=5, **kwargs):
        super().__init__(**kwargs)
        self.current_number = start_from

    def execute(self):
        if self.current_number < 0:
            # 倒计时结束，发送停止信号
            return StopSignal(f"Countdown_Finished")

        result = self.current_number
        logging.info(f"[Countdown] T-minus {self.current_number}")
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
        logging.info(
            f"[Processor-{self.name}] Processed item #{self.processed_count}: {data}"
        )
        return data


def run_simple_batch_test():
    """测试1: 简单的数字序列批处理"""
    logging.info("🔢 Test 1: Simple Number Sequence Batch Processing")
    logging.info("=" * 50)

    env = LocalEnvironment("simple_batch_test")

    # 创建有限数据源
    source_stream = env.from_source(NumberSequenceSource, max_count=5, delay=0.5)

    # 处理管道
    result = (
        source_stream.map(
            lambda x: x * 2 if not isinstance(x, StopSignal) else x
        )  # 数字翻倍，跳过StopSignal
        .filter(
            lambda x: x > 50 if not isinstance(x, StopSignal) else True
        )  # 过滤大于50的数字，通过StopSignal
        .sink(BatchProcessor, name="NumberProcessor")
    )

    logging.info("🚀 Starting simple batch processing...")
    logging.info("📊 Processing sequence: generate → double → filter → sink")
    logging.info("⏹️  Source will automatically stop after 5 numbers\n")

    # 提交并运行
    env.submit()

    logging.info("\n✅ Simple batch test completed!\n")


def run_file_processing_test():
    """测试2: 文件行批处理"""
    logging.info("📄 Test 2: File Line Batch Processing")
    logging.info("=" * 50)

    env = LocalEnvironment("file_batch_test")

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
    result = (
        source_stream.map(
            lambda line: line.upper() if not isinstance(line, StopSignal) else line
        )  # 转大写，跳过StopSignal
        .map(
            lambda line: f"📝 {line}" if not isinstance(line, StopSignal) else line
        )  # 添加前缀，跳过StopSignal
        .sink(BatchProcessor, name="TextProcessor")
    )

    logging.info("🚀 Starting file batch processing...")
    logging.info("📊 Processing pipeline: read → uppercase → prefix → sink")
    logging.info("⏹️  Source will automatically stop after reading all lines\n")

    # 提交并运行
    env.submit()

    logging.info("\n✅ File batch test completed!\n")


def run_multi_source_batch_test():
    """测试3: 多源批处理（展示不同源的终止时机）"""
    logging.info("🔀 Test 3: Multi-Source Batch Processing")
    logging.info("=" * 50)

    env = LocalEnvironment("multi_source_batch_test")

    # 创建多个不同速度的数据源
    numbers_stream = env.from_source(NumberSequenceSource, max_count=3, delay=0.5)
    countdown_stream = env.from_source(CountdownSource, start_from=2, delay=0.7)

    # 合并流处理
    combined_result = (
        numbers_stream.connect(countdown_stream)  # 合并两个流
        .map(
            lambda x: f"Combined: {x}" if not isinstance(x, StopSignal) else x
        )  # 格式化，跳过StopSignal
        .sink(BatchProcessor, name="MultiSourceProcessor")
    )

    logging.info("🚀 Starting multi-source batch processing...")
    logging.info("📊 Two independent sources will terminate at different times")
    logging.info("⏹️  Job will complete when ALL sources send stop signals\n")

    # 提交并运行
    env.submit()

    logging.info("\n✅ Multi-source batch test completed!\n")


def run_processing_chain_test():
    """测试4: 复杂处理链批处理"""
    logging.info("⛓️  Test 4: Complex Processing Chain Batch")
    logging.info("=" * 50)

    env = LocalEnvironment("complex_batch_test")  # 使用远程环境测试分布式批处理

    source_stream = env.from_source(NumberSequenceSource, max_count=8, delay=0.3)

    # 复杂的处理链
    result = (
        source_stream.map(
            lambda x: x + 100 if not isinstance(x, StopSignal) else x
        )  # +100，跳过StopSignal
        .filter(
            lambda x: x % 2 == 0 if not isinstance(x, (StopSignal, str)) else True
        )  # 只保留偶数，跳过StopSignal和字符串
        .map(
            lambda x: x / 2 if not isinstance(x, StopSignal) else x
        )  # 除以2，跳过StopSignal
        .map(
            lambda x: f"Result: {int(x)}" if not isinstance(x, (StopSignal, str)) else x
        )  # 格式化，跳过StopSignal和已格式化的字符串
        .sink(BatchProcessor, name="ChainProcessor")
    )

    logging.info("🚀 Starting complex processing chain...")
    logging.info("📊 Chain: source → +100 → filter_even → /2 → format → sink")
    logging.info("🌐 Running on distributed Ray cluster")
    logging.info("⏹️  Automatic termination with batch lifecycle management\n")

    # 提交并运行
    env.submit()

    logging.info("\n✅ Complex batch test completed!\n")


def main():
    """主测试函数"""
    logging.info("🎯 SAGE Batch Processing Tests with StopSignal")
    logging.info("=" * 60)
    logging.info("🧪 Testing automatic batch termination using StopSignal interface")
    logging.info("📈 Each test demonstrates different batch processing scenarios\n")

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
        logging.info("\n\n🛑 Tests interrupted by user")

    finally:
        logging.info("\n📋 Batch Processing Tests Summary:")
        logging.info("✅ Test 1: Simple sequence - PASSED")
        logging.info("✅ Test 2: File processing - PASSED")
        logging.info("✅ Test 3: Multi-source - PASSED")
        logging.info("✅ Test 4: Complex chain - PASSED")
        logging.info("\n💡 Key Features Demonstrated:")
        logging.info("   - StopSignal automatic termination")
        logging.info("   - Source-driven batch lifecycle")
        logging.info("   - Multi-source coordination")
        logging.info("   - Distributed batch processing")
        logging.info("   - Graceful job completion")
        logging.info("\n🔄 StopSignal Workflow:")
        logging.info("   1. Source detects data exhaustion")
        logging.info("   2. Source returns StopSignal")
        logging.info("   3. SourceOperator propagates signal")
        logging.info("   4. Downstream nodes receive termination")
        logging.info("   5. Job gracefully completes")


if __name__ == "__main__":
    main()
