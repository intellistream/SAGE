from typing import List, TypeVar,Generic
T = TypeVar('T')
T_in = TypeVar('T_in')  # 输入类型
T_out = TypeVar('T_out')  # 输出类型

class Record(Generic[T]):
    def __init__(self, data: T, metadata: dict = None):
        self.data = data  # 存储实际的数据
        self.metadata = metadata or {}  # 存储元信息（可选）

class Pipeline:
    def __init__(self):
        self.operators = [QAPromptor(),AnswerGenerator(),ResultFormatter()] # 一系列的 Operator

    def run(self, initial_record: Record[T_in]) -> Record[T_out]:
        record = initial_record  # 初始数据记录
        for operator in self.operators:
            record = operator.run(record)  # 顺序执行 Operator
        return record


from typing import Tuple
from dataclasses import dataclass
from typing import List

@dataclass
class PromptInputState:
    query: str
    external_docs: List[str]

@dataclass
class PromptOutputState:
    prompt_messages: List[dict]  # LLM 消息格式（role, content）

class QAPromptor():
    def __init__(self,):
        pass

    def run(self, record: Record[PromptInputState]) -> Record[PromptOutputState]:
        input_state = record.data
        query = input_state.query
        external_corpus = "".join(input_state.external_docs)

        system_prompt_data = {
            "external_corpus": external_corpus
        }

        system_prompt = {"role": "system", "content": "1111"}
        user_prompt = {"role": "user", "content": f"Question: {query}"}
        messages = [system_prompt, user_prompt]

        return Record(data=PromptOutputState(prompt_messages=messages), metadata=record.metadata)


class AnswerGenerator():
    def run(self, record: Record[PromptOutputState]) -> Record[str]:
        # 简单模拟调用模型生成答案
        prompt = record.data.prompt_messages
        answer = "This is a simulated answer."
        return Record(data=answer, metadata=record.metadata)

class ResultFormatter():
    def run(self, record: Record[str]) -> Record[dict]:
        # 格式化最终答案
        formatted_result = {
            "answer": record.data,
            "metadata": record.metadata
        }
        return Record(data=formatted_result, metadata=record.metadata)


# 1. 定义初始数据
input_state = PromptInputState(
    query="What is the capital of France?",
    external_docs=["France is a country in Europe.", "Paris is the capital of France."]
)
initial_record = Record(data=input_state)

# 2. 创建各个 Operator
qa_promptor = QAPromptor()
answer_generator = AnswerGenerator()
result_formatter = ResultFormatter()

# 3. 创建 Pipeline 并添加 Operator 顺序
pipeline = Pipeline()

# 4. 执行 Pipeline
result = pipeline.run(initial_record)

# 5. 输出最终结果
print(result.data)  # { "answer": "This is a simulated answer.", "metadata": {} }

