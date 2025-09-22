import logging
import time

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.comap_function import BaseCoMapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment


# 初始数据源：启动计数器
class CounterStartSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.started = False

    def execute(self):
        if not self.started:
            self.started = True
            logging.info("🚀 Starting counter...")
            # 只发送一次初始值，随后就返回None
            return {"count": 0, "message": "Counter initialized"}
        return None


# 反馈处理器：接收计数器值和反馈值
class CounterProcessor(BaseCoMapFunction):
    def map0(self, data):
        """处理初始计数器数据（来自输入流0）"""
        logging.info(f"📥 Initial data: {data}")
        return data

    def map1(self, data):
        """处理反馈数据（来自输入流1 - future stream）"""
        logging.info(f"🔄 Feedback data: {data}")
        return data


# 计数增加器
class CounterIncrementer(BaseFunction):
    def execute(self, data):
        if data is None:
            return None

        current_count = data.get("count", 0)
        new_count = current_count + 1

        result = {
            "count": new_count,
            "message": f"Counter value: {new_count}",
            "should_continue": new_count < 10,
        }

        logging.info(f"🔢 Counter incremented: {current_count} → {new_count}")
        return result


# 退出条件检查器
class ExitChecker(BaseFunction):
    def execute(self, data):
        if data is None:
            return None

        count = data.get("count", 0)
        should_continue = data.get("should_continue", True)

        if not should_continue:
            logging.info(f"🏁 Counter reached target value: {count}. Stopping...")
            return None  # 停止数据流

        logging.info(f"✅ Counter check passed: {count} < 10, continuing...")
        return data


# 反馈延迟器：添加延迟以便观察反馈循环
class FeedbackDelayer(BaseFunction):
    def execute(self, data):
        if data is None:
            return None

        logging.info(f"⏱️  Adding delay before feedback...")
        time.sleep(1)  # 1秒延迟，便于观察
        logging.info(f"🔙 Sending feedback: {data}")
        return data


# 最终输出
class CounterSink(SinkFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_name = kwargs.get("name", "CounterSink")

    def execute(self, data):
        if data is not None:
            count = data.get("count", 0)
            message = data.get("message", "No message")
            logging.info(f"[{self.custom_name}] 📊 {message}")

            if count >= 10:
                logging.info(
                    f"[{self.custom_name}] 🎉 Counter completed! Final value: {count}"
                )
        return data


def main():
    # 创建环境
    env = LocalEnvironment("future_stream_example")

    logging.info("🚀 Starting Future Stream Example")
    logging.info("🔄 Demonstrating feedback edges with a counting loop")
    logging.info("📊 Counter will increment from 0 to 10 using feedback")
    logging.info("⏹️  Press Ctrl+C to stop\n")

    logging.info("🔗 Creating feedback loop with future stream...")

    # 1. 声明future stream（反馈边）
    logging.info("📋 Step 1: Declaring future stream for feedback...")
    feedback_stream = env.from_future("counter_feedback")

    # 2. 创建初始数据源
    logging.info("📋 Step 2: Creating initial counter source...")
    counter_source = env.from_source(CounterStartSource, delay=0.5)

    # 3. 连接初始流和反馈流
    logging.info("📋 Step 3: Connecting initial stream with feedback stream...")
    connected_streams = counter_source.connect(feedback_stream)

    # 4. 处理连接的流（初始值 + 反馈值）
    logging.info("📋 Step 4: Processing connected streams...")
    processed_data = connected_streams.comap(CounterProcessor)

    # 5. 增加计数器
    logging.info("📋 Step 5: Setting up counter incrementer...")
    incremented_data = processed_data.map(CounterIncrementer)

    # 6. 检查退出条件
    logging.info("📋 Step 6: Setting up exit condition checker...")
    checked_data = incremented_data.map(ExitChecker)

    # 7. 输出到终端
    logging.info("📋 Step 7: Setting up output sink...")
    output_data = checked_data.sink(CounterSink, name="CounterOutput")

    # 8. 创建反馈分支（添加延迟后反馈）
    logging.info("📋 Step 8: Creating feedback branch...")
    feedback_data = checked_data.map(FeedbackDelayer)

    # 9. 填充future stream，建立反馈边
    logging.info("📋 Step 9: Filling future stream to create feedback edge...")
    feedback_data.fill_future(feedback_stream)

    logging.info("\n🔄 Feedback loop structure:")
    logging.info(
        "   CounterSource → [Connected with Future] → CounterProcessor → Incrementer → ExitChecker → CounterSink"
    )
    logging.info(
        "                           ↑                                                        ↓"
    )
    logging.info(
        "                           └────────────────── FeedbackDelayer ←────────────────────┘"
    )
    logging.info()

    logging.info("✅ Pipeline validation:")
    logging.info(f"   - Pipeline transformations: {len(env.pipeline)}")

    try:

        logging.info("🎬 Starting feedback loop execution...")
        logging.info("📈 Watch the counter increment in a feedback loop:\n")

        # 运行流处理
        env.submit()

        time.sleep(10)  # 运行15秒，足够计数到10

    except KeyboardInterrupt:
        logging.info("\n\n🛑 Stopping Future Stream Example...")

    finally:
        logging.info("\n📋 Example completed!")
        logging.info("💡 This example demonstrated:")
        logging.info("   - Creating a future stream with env.from_future()")
        logging.info("   - Using future stream in connected streams")
        logging.info("   - Processing initial and feedback data with CoMap")
        logging.info("   - Incrementing counter in a feedback loop")
        logging.info("   - Conditional exit based on counter value")
        logging.info("   - Filling future stream to create feedback edge")
        logging.info("\n🔄 Feedback Loop Features:")
        logging.info("   - Initial value flows through the system")
        logging.info("   - Processed result feeds back to the beginning")
        logging.info("   - Loop continues until exit condition is met")
        logging.info("   - Clean termination when counter reaches 10")
        env.close()


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
