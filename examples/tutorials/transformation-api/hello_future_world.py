from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.comap_function import BaseCoMapFunction
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from time import sleep

# 启动信号源（只发一次启动信号）
class StartSource(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.started = False

    def execute(self):
        if not self.started:
            self.started = True
            print("已发送启动信号")
            return {"signal": "start"}
        else:
            return None


# 合流处理器（map0 = 启动，map1 = 反馈）
class SignalMerger(BaseCoMapFunction):
    def map0(self, data):
        print(f">>> StartSource：收到启动数据: {data}")
        return data

    def map1(self, data):
        print(f">>> PipelineSource： 收到反馈数据: {data}")
        return data


# 从语句列表中按顺序取语句（只在收到反馈时推进）
class SentenceProvider(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sentences = [
            "这是第一句。",
            "这是第二句。",
            "这是第三句。",
            "所有语句已完成！"
        ]
        self.index = 0

    def execute(self, data):
        if data is None:
            return None

        if self.index >= len(self.sentences):
            print("全部语句已输出完毕，结束数据流。")
            return None

        sentence = self.sentences[self.index]
        self.index += 1
        new_data = {"句子": sentence}
        print(f">>> SentenceProvider 提供句子: {new_data}")
        return new_data


# Sink：打印句子（立即打印，不加 sleep）
class FeedbackSink(SinkFunction):
    def execute(self, data):
        if data:
            print(f">>> Sink 打印: {data}")
        return data


# 延迟反馈算子：控制节奏
class FeedbackDelayer(BaseFunction):
    def execute(self, data):
        if data is None:
            return None
        sleep(1)  # 控制间隔
        print(">>> FeedbackDelayer等待 2 秒后反馈...")
        return data


def main():
    env = LocalEnvironment("句子顺序输出")

    # 1. 启动源
    start_stream = env.from_source(StartSource)

    # 2. future stream 用于反馈
    feedback_stream = env.from_future("feedback")

    # 3. 合流
    merged = start_stream.connect(feedback_stream).comap(SignalMerger)

    # 4. 语句提供器
    provided = merged.map(SentenceProvider)

    # 5. Sink，打印结果
    sinked = provided.sink(FeedbackSink)

    # 6. 在反馈前加延迟
    delayed = sinked.map(FeedbackDelayer)

    # 7. 把延迟后的结果反馈到 future stream
    delayed.fill_future(feedback_stream)


    env.submit()

    from time import sleep
    sleep(6)  # 给足够时间让所有数据处理完成

    print("Hello Future World 示例结束")

if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
