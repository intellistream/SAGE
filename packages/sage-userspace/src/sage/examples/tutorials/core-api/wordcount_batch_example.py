"""
有界流WordCount示例
使用BatchFunction处理固定数据集，展示词频统计的批处理模式
"""
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.function.batch_function import BatchFunction
from collections import Counter


class TextDataBatch(BatchFunction):
    """文本数据批处理源 - 提供固定的文本数据集"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sentences = [
            "hello world sage framework",
            "this is a streaming data processing example",
            "lambda functions make the code much cleaner",
            "word count is a classic big data example",
            "sage provides powerful stream processing capabilities"
        ]
        self.counter = 0

    def execute(self):
        """返回下一个句子，如果没有更多句子则返回None"""
        if self.counter >= len(self.sentences):
            return None  # 返回None表示批处理完成

        sentence = self.sentences[self.counter]
        self.counter += 1
        return sentence


def main():
    """运行有界流WordCount示例"""
    # 创建本地环境
    env = LocalEnvironment("batch_wordcount")

    # 全局词汇计数器
    word_counts = Counter()
    total_processed = 0

    def update_word_count(words_with_count):
        """更新全局词汇计数"""
        nonlocal word_counts, total_processed
        word, count = words_with_count
        word_counts[word] += count
        total_processed += count
        return words_with_count

    # 构建批处理管道
    result = (env
        .from_batch(TextDataBatch)                        # 批数据源

        # 数据清洗和预处理
        .map(lambda sentence: sentence.lower())           # 转小写
        .map(lambda sentence: sentence.strip())           # 去除首尾空白
        .filter(lambda sentence: len(sentence) > 0)       # 过滤空字符串

        # 分词处理
        .flatmap(lambda sentence: sentence.split())       # 按空格分词
        .filter(lambda word: len(word) > 2)               # 过滤长度小于3的词
        .map(lambda word: word.replace(",", "").replace(".", ""))  # 去除标点

        # 词汇统计
        .map(lambda word: (word, 1))                      # 转换为(word, count)格式
        .map(update_word_count)                           # 更新计数器
        .sink(lambda x: None)                            # 添加sink确保数据流完整
    )

    print("🚀 Starting Batch WordCount Example")

    try:
        # 提交并运行批处理作业
        env.submit()
        import time
        time.sleep(2)  # wait for batch processing to complete

        # 打印最终统计结果
        print("\n📊 Final Word Count Results:")
        print("=" * 60)
        for word, count in word_counts.most_common():
            print(f"{word:20}: {count:3d}")
        print("=" * 60)
        print(f"Total words processed: {total_processed}")

    except Exception as e:
        print(f"❌ 批处理执行失败: {str(e)}")
    finally:
        env.close()


if __name__ == "__main__":
    main()