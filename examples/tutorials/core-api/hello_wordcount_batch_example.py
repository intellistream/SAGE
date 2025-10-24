from sage.common.utils.logging.custom_logger import CustomLogger
from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.flatmap_function import FlatMapFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.kernel.api.local_environment import LocalEnvironment


# 批处理数据源：生成几行句子
class SentenceBatch(BatchFunction):
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
        if self.index >= len(self.sentences):
            return None
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


class PrintResult(SinkFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counts = {}

    def execute(self, data):
        word, cnt = data
        self.counts[word] = self.counts.get(word, 0) + cnt

    def close(self):
        print("WordCount 结果：")
        for word, count in self.counts.items():
            print(f"{word}: {count}")


def main():
    env = LocalEnvironment("WordCount")

    # 批处理：句子 -> 拆分单词 -> 转换为(word,1) -> 聚合 -> 输出
    env.from_batch(SentenceBatch).flatmap(SplitWords).map(WordToPair).sink(PrintResult)

    env.submit(autostop=True)
    print("WordCount 批处理示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
