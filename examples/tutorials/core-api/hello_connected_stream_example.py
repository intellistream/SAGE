import logging
import time

from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment


# 简单的数字源
class NumberSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0

    def execute(self):
        self.counter += 1
        return self.counter


# 简单的统计汇总函数
class StatsSink(SinkFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def execute(self, data):
        logging.info(f"[{self.name}] Received: {data}")
        return data


def main():
    # 创建环境
    env = LocalEnvironment("simple_connected_example")

    # 设置日志级别为WARNING以减少调试输出
    env.set_console_log_level("WARNING")

    logging.info("🚀 Starting Simple Connected Streams Example")
    logging.info("📊 Demonstrating multiple stream processing and connection")
    logging.info("⏹️  Press Ctrl+C to stop\n")

    # 创建主数据源
    main_stream = env.from_source(NumberSource, delay=1.0)

    # 分支1：偶数流
    even_stream = (
        main_stream.filter(lambda x: x % 2 == 0).map(lambda x: ("EVEN", x))
        # .logging.info("🔵 Even Stream")
    )

    # 分支2：奇数流
    odd_stream = (
        main_stream.filter(lambda x: x % 2 == 1).map(lambda x: ("ODD", x))
        # .logging.info("🔴 Odd Stream")
    )

    # 分支3：倍数流（3的倍数）
    multiple_stream = (
        main_stream.filter(lambda x: x % 3 == 0).map(lambda x: ("MULTIPLE_3", x))
        # .logging.info("🟡 Multiple-3 Stream")
    )

    # 分支4：大数流（大于5）
    large_stream = (
        main_stream.filter(lambda x: x > 5).map(lambda x: ("LARGE", x))
        # .logging.info("🟢 Large Stream")
    )

    # 使用 ConnectedStreams 将所有分支连接起来
    logging.info("\n🔗 Connecting all streams...")
    connected_streams = (
        even_stream.connect(odd_stream).connect(multiple_stream).connect(large_stream)
    )

    # 对连接的流进行统一处理
    final_result = (
        connected_streams.map(lambda data: f"Processed: {data[0]} -> {data[1]}")
        .logging.info("🎯 Final Result")
        .sink(StatsSink, name="FinalSink")
    )

    logging.info("📈 All streams connected and processing...\n")

    try:
        # 运行流处理
        env.submit()

        time.sleep(5)  # 运行5秒

    except KeyboardInterrupt:
        logging.info("\n\n🛑 Stopping Simple Connected Streams Example...")

    finally:
        logging.info("\n📋 Example completed!")
        logging.info("💡 This example demonstrated:")
        logging.info("   - Multiple stream branches from single source")
        logging.info("   - Independent filtering and processing")
        logging.info("   - ConnectedStreams merging multiple flows")
        logging.info("   - Unified final processing of merged streams")
        env.close()


if __name__ == "__main__":
    main()
