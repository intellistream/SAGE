import time

from sage.common.core.functions.base_function import BaseFunction
from sage.common.core.functions.comap_function import BaseCoMapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment


# 初始数据源：启动计数器
class CounterStartSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.started = False

    def execute(self, data=None):
        if not self.started:
            self.started = True
            print("🚀 Starting counter...")
            # 只发送一次初始值，随后就返回None
            return {"count": 0, "message": "Counter initialized"}
        return None


# 反馈处理器：接收计数器值和反馈值
class CounterProcessor(BaseCoMapFunction):
    def map0(self, data):
        """处理初始计数器数据（来自输入流0）"""
        print(f"📥 Initial data: {data}")
        return data

    def map1(self, data):
        """处理反馈数据（来自输入流1 - future stream）"""
        print(f"🔄 Feedback data: {data}")
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

        print(f"🔢 Counter incremented: {current_count} → {new_count}")
        return result


# 退出条件检查器
class ExitChecker(BaseFunction):
    def execute(self, data):
        if data is None:
            return None

        count = data.get("count", 0)
        should_continue = data.get("should_continue", True)

        if not should_continue:
            print(f"🏁 Counter reached target value: {count}. Stopping...")
            return None  # 停止数据流

        print(f"✅ Counter check passed: {count} < 10, continuing...")
        return data


# 反馈延迟器：添加延迟以便观察反馈循环
class FeedbackDelayer(BaseFunction):
    def execute(self, data):
        if data is None:
            return None

        print("⏱️  Adding delay before feedback...")
        time.sleep(1)  # 1秒延迟，便于观察
        print(f"🔙 Sending feedback: {data}")
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
            print(f"[{self.custom_name}] 📊 {message}")

            if count >= 10:
                print(
                    f"[{self.custom_name}] 🎉 Counter completed! Final value: {count}"
                )
        return data


def main():
    # 创建环境
    env = LocalEnvironment("future_stream_example")

    print("🚀 Starting Future Stream Example")
    print("🔄 Demonstrating feedback edges with a counting loop")
    print("📊 Counter will increment from 0 to 10 using feedback")
    print("⏹️  Press Ctrl+C to stop\n")

    print("🔗 Creating feedback loop with future stream...")

    # 1. 声明future stream（反馈边）
    print("📋 Step 1: Declaring future stream for feedback...")
    feedback_stream = env.from_future("counter_feedback")

    # 2. 创建初始数据源
    print("📋 Step 2: Creating initial counter source...")
    counter_source = env.from_source(CounterStartSource, delay=0.5)

    # 3. 连接初始流和反馈流
    print("📋 Step 3: Connecting initial stream with feedback stream...")
    connected_streams = counter_source.connect(feedback_stream)

    # 4. 处理连接的流（初始值 + 反馈值）
    print("📋 Step 4: Processing connected streams...")
    processed_data = connected_streams.comap(CounterProcessor)

    # 5. 增加计数器
    print("📋 Step 5: Setting up counter incrementer...")
    incremented_data = processed_data.map(CounterIncrementer)

    # 6. 检查退出条件
    print("📋 Step 6: Setting up exit condition checker...")
    checked_data = incremented_data.map(ExitChecker)

    # 7. 输出到终端
    print("📋 Step 7: Setting up output sink...")
    checked_data.sink(CounterSink, name="CounterOutput")

    # 8. 创建反馈分支（添加延迟后反馈）
    print("📋 Step 8: Creating feedback branch...")
    feedback_data = checked_data.map(FeedbackDelayer)

    # 9. 填充future stream，建立反馈边
    print("📋 Step 9: Filling future stream to create feedback edge...")
    feedback_data.fill_future(feedback_stream)

    print("\n🔄 Feedback loop structure:")
    print(
        "   CounterSource → [Connected with Future] → CounterProcessor → Incrementer → ExitChecker → CounterSink"
    )
    print(
        "                           ↑                                                        ↓"
    )
    print(
        "                           └────────────────── FeedbackDelayer ←────────────────────┘"
    )
    print()

    print("✅ Pipeline validation:")
    print(f"   - Pipeline transformations: {len(env.pipeline)}")

    try:

        print("🎬 Starting feedback loop execution...")
        print("📈 Watch the counter increment in a feedback loop:\n")

        # 运行流处理
        env.submit()

        time.sleep(10)  # 运行15秒，足够计数到10

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping Future Stream Example...")

    finally:
        print("\n📋 Example completed!")
        print("💡 This example demonstrated:")
        print("   - Creating a future stream with env.from_future()")
        print("   - Using future stream in connected streams")
        print("   - Processing initial and feedback data with CoMap")
        print("   - Incrementing counter in a feedback loop")
        print("   - Conditional exit based on counter value")
        print("   - Filling future stream to create feedback edge")
        print("\n🔄 Feedback Loop Features:")
        print("   - Initial value flows through the system")
        print("   - Processed result feeds back to the beginning")
        print("   - Loop continues until exit condition is met")
        print("   - Clean termination when counter reaches 10")
        env.close()


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
