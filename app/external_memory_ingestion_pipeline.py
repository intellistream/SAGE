import sage
from typing import Tuple, List

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

    # Produces a query from text
    def execute(self, context=None) -> str:
        # TODO: Mock the original example
        return "What is the Lisa?"

#
class MemoryWriter(sage.operator.WriterFunction):
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.embedding_model = sage.model.apply_embedding_model("default")
        self.dcm = sage.memory.connect("dynamic_contextual_memory")
        self.write_func = sage.memory.write_func

    def execute(self, input: str, context=None) -> None:
        self.dcm.write(input, self.write_func)


# ---- Initialize and Submit Pipeline ----
# Create a new pipeline instance
pipeline = sage.pipeline.Pipeline("example_pipeline")

# Step 1: Define the data source (e.g., incoming user query)
knowledge_stream = pipeline.add_source(WebSource())

# Step 4: Generate the final response using a language model
response_stream = knowledge_stream.save_context(MemoryWriter())

# Submit the pipeline to the SAGE runtime
pipeline.submit(is_long_running = True, duration = 1, frequency = 30)

