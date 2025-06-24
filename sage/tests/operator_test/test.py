# from csv import writer
import os
import sys

# 添加项目根路径到 PYTHONPATH 和 sys.path
project_root = os.getcwd()
print(project_root)

# os.environ["PYTHONPATH"] = f"{project_root}:{os.environ.get('PYTHONPATH', '')}"
print(f"{project_root}:{os.environ.get('PYTHONPATH', '')}")
sys.path.insert(0, project_root)

from sage.api.operator.operator_impl.source import FileSourceFunction
# from sage.api.operator.operator_impl.writer import LongTimeWriter,MemWriter
# from sage.api.operator.operator_impl.retriever import SimpleRetriever
from sage.api.operator.operator_impl.agent  import BaseAgent
from sage.api.operator.operator_impl.evaluate import (
    F1Evaluate,
    BertRecallEvaluate,
    RougeLEvaluate,
    BRSEvaluate,
)
from sage.api.operator.operator_impl_test.sink import FileSink
from sage.api.operator import Data
import yaml


# def init_memory():
#     manager=init_default_manager()

#     lsm=create_table("long_term_memory",manager)

#     # contexts=[
#     #     "Mitosis is a type of cell division that results in two genetically identical daughter cells from a single parent cell.",
#     #     "Meiosis is a form of cell division that produces four genetically distinct daughter cells, each with half the number of chromosomes of the original cell.",
#     #     "Mitosis occurs in somatic (non-reproductive) cells and is used for growth and tissue repair.",
#     #     "Meiosis only occurs in germ cells (sperm and egg) and is essential for sexual reproduction.",
#     #     "A key difference is that meiosis includes two rounds of cell division (meiosis I and II), while mitosis only includes one.",
#     #     "Mitosis maintains the chromosome number of the original cell, whereas meiosis reduces it by half.",
#     #     "Crossing over, which increases genetic variation, occurs during meiosis but not mitosis."
#     # ]

#     # for context in contexts:
#     #     lsm.store(context)


def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config_QA=load_config("./sage/api/operator/operator_test/config_qa.yaml")
config_multi_turn=load_config("./sage/api/operator/operator_test/config_multi_turn.yaml")
config_long_mem_write=load_config("./sage/api/operator/operator_test/config_long_mem_write.yaml")
config_agent_search=load_config("./sage/api/operator/operator_test/config_agent_search.yaml")
# def test_QA_pipline():
#     init_memory()
#     source=FileSource(config_QA)
#     retriver=SimpleRetriever(config_QA)
#     promptor=QAPromptor(config_QA)
#     generator=OpenAIGenerator(config_QA)
#     # reranker=BGEReranker(config_QA)
#     sink=TerminalSink(config_QA)
#     output=source.execute()
#     output=retriver.execute(output)

#     # output=reranker.execute(output)
#     output = promptor.execute(output)
#     output = generator.execute(output)
#     sink.execute(output)
#     # assert("False" in output.data[0])

# def test_operator_short_memory():
#     print("First Round")
#     init_memory()
#     manager=get_default_manager()
#     stm=create_table("short_term_memory",manager)

#     source=FileSource(config_multi_turn)
#     retriver=SimpleRetriever(config_multi_turn)
#     promptor=QAPromptor(config_multi_turn)
#     generator=OpenAIGenerator(config_multi_turn)
#     reranker=BGEReranker(config_multi_turn)
#     writer=LongTimeWriter(config_multi_turn)
#     sink=TerminalSink(config_multi_turn)

#     output=source.execute()
#     output=retriver.execute(output)
#     # output=reranker.execute(output)
#     output = promptor.execute(output)
#     output = generator.execute(output)
#     output = writer.execute(output)
#     sink.execute(output)

#     print("Second Round")
#     output=source.execute()
#     output=retriver.execute(output)
#     output=reranker.execute(output)
#     output = promptor.execute(output)
#     output = generator.execute(output)
#     output = writer.execute(output)
#     sink.execute(output)

#     # assert("False" in output.data[0])

def test_agent_with_search():
    source=FileSourceFunction(config_agent_search)
    agent=BaseAgent(config_agent_search)
    output=source.execute()
    output=agent.execute(output)

# def test_load_memory():
#     init_memory()
#     source=FileSource(config_long_mem_write)
#     chunk=CharacterSplitter(config_long_mem_write)
#     # chunk1=TokenTextSplitter(config_long_mem_write)
#     write=MemWriter(config_long_mem_write)
#     output=source.execute()
#     output=chunk.execute(output)
#     # output=chunk1.execute(output)
#     output=write.execute(output)

def test_evaluate_functions():
    # 模拟一条数据：reference 和 generated
    reference = "The cat sits on the mat."
    generated = "A cat is sitting on a mat."

    data = Data((reference, generated))

    config = {}  # 测试时config可以是空的

    # 初始化所有评估器
    f1_eval = F1Evaluate(config)
    bert_recall_eval = BertRecallEvaluate(config)
    rouge_l_eval = RougeLEvaluate(config)
    brs_eval = BRSEvaluate(config)

    # 分别执行
    print("\n=== F1 Evaluate ===")
    f1_eval.execute(data)

    print("\n=== BERT Recall Evaluate ===")
    bert_recall_eval.execute(data)

    print("\n=== ROUGE-L Evaluate ===")
    rouge_l_eval.execute(data)

    print("\n=== BRS Evaluate ===")
    brs_eval.execute(data)

test_evaluate_functions()
# test_load_memory()
test_agent_with_search()
# test_operator_short_memory()
# test_QA_pipline()