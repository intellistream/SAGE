from typing import List, Optional

import sage


# 无人机依靠大模型做决策，ds做到无人机上，缺乏实时信息，ds给的建议不准确。
# 我们系统替代ds部署，操作员联系无人机，无人机可以针对性采集周围数据
# 具体采集那些数据由操作员决定，无人机做预处理，源源不断，整理，总结到知识库。on-demand，由操作员控制
# 在更新过程中，操作员提醒无人机做自主决策。
# 无人机需要执行很多pipeline，external记忆更新，on-demand的query执行
# 无人机编队等等，通信，多轮对话，被采集，可以有操作员决定，也可以无人机自己决定。
# 把sage组里的所有同学，一对一的聊，负责哪一块就把这块重点讲一下，需要做什么调整？记下来。
# 于此同时，把设计和全套方案告诉他。让他知道我们的系统设计改成这个样子。如果要调整，需要怎么样调整，我们这边需要这么调整。
# 听一听其他同学的想法，如果有精彩的，好的意见，信息记录下来，坐下来思考，怎么设计，好不好，有什么参考一下。

# ---- Implement Operators ----
# Web source operator: reads from web to ingest relavant knowledge to internal memory
class WebSource(sage.operator.SourceFunction):
    def __init__(self):
        super().__init__()

    def execute(self, context=None) -> str:
        # TODO: Replace with real web fetcher
        return "Lisa is an open-source language model developed by XYZ Labs. It focuses on efficient reasoning."

class WebChunker(sage.operator.ChunkFunction):
    def __init__(self, max_tokens: int = 20):
        super().__init__()
        self.max_tokens = max_tokens

    def execute(self, input: str, context=None) -> List[str]:
        words = input.split()
        return [" ".join(words[i:i+self.max_tokens]) for i in range(0, len(words), self.max_tokens)]

class SimpleSummarizer(sage.operator.SummarizeFunction):
    def __init__(self):
        super().__init__()
        self.model = None

    def _init_model(self):
        if self.model is None:
            self.model = sage.model.apply_generator_model("llama_8b")

    def execute(self, chunk: str, context=None) -> str:
        self._init_model()
        return self.model.generate("Summarize this:\n" + chunk)

class MemoryWriter(sage.operator.WriterFunction):
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.embedding_model = sage.model.apply_embedding_model("default")
        self.dcm = sage.memory.connect("dynamic_contextual_memory")
        self.write_func = sage.memory.write_func

    def execute(self, input: str, context=None) -> None:
        self.dcm.write(input, self.write_func)


# ---- Initialize and Submit Pipeline ----
pipeline = sage.pipeline.Pipeline("external_memory_ingestion")

knowledge_stream = pipeline.add_source(WebSource())
chunked_stream = knowledge_stream.chunk(WebChunker())
summarized_stream = chunked_stream.summarize(SimpleSummarizer())
summarized_stream.save_context(MemoryWriter())

pipeline.submit(config={"is_long_running": True, "duration": 1, "frequency": 30})


