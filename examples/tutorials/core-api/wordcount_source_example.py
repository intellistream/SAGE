import time

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.flatmap_function import FlatMapFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment


# 流数据源：每次输出一行句子
class SentenceSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sentences = [
            "hello world",
            "hello sage",
            "hello chatgpt",
            "world of ai",
            "sage world",
        ]
        self.index = 0

    def execute(self):
        # 无限流：每次输出一句话，模拟流数据源
        if self.index >= len(self.sentences):
            self.index = 0  # 重置索引，实现循环输出
        sentence = self.sentences[self.index]
        self.index += 1
        return sentence


# 拆分句子为单词
class SplitWords(FlatMapFunction):
    def execute(self, data):
        return data.split()


# 转换为 (word, 1)
class WordToPair(MapFunction):
    def execute(self, data):
        return (data, 1)


# SinkFunction 输出结果：每次输出单词计数
class PrintResult(SinkFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counts = {}

    def execute(self, data):
        word, cnt = data
        self.counts[word] = self.counts.get(word, 0) + cnt

        # 每次接收到新数据时，输出当前统计结果
        print("当前单词计数：")
        for word, count in self.counts.items():
            print(f"{word}: {count}")
        print("------")


def main():
    env = LocalEnvironment("WordCount")

    # 流式处理：句子 -> 拆分单词 -> 转换为(word,1) -> 输出每次的单词统计
    env.from_source(SentenceSource).flatmap(SplitWords).map(WordToPair).sink(
        PrintResult
    )

    env.submit()  # 设置为 False 以保持流式执行

    # 模拟流式数据源持续运行一段时间（这里设定为 10 秒）
    time.sleep(10)
    print("WordCount 流式示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
