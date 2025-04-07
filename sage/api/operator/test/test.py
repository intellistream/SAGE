from json import load
from typing import List, Tuple

from ..operator_impl.promptor import QAPromptor
from ..operator_impl.generator import OpenAIGenerator
from ..operator_impl.reranker import BGEReranker
from ..operator_impl.refiner import AbstractiveRecompRefiner
from ..operator_impl.source import FileSource
from ..operator_impl.sink import TerminalSink
from ..operator_impl.writer import SimpleWriter
from ..operator_impl.retriever import SimpleRetriever
from ..base_operator_api import Data
import yaml

#目前调用不了memory接口，写了一个测试类
class Retriever_test(SimpleRetriever):

    def __init__(self, config):
        super().__init__(config)
    
    def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:
        input_query=data.data
        context=[
            "Mitosis is a type of cell division that results in two genetically identical daughter cells from a single parent cell.",
            "Meiosis is a form of cell division that produces four genetically distinct daughter cells, each with half the number of chromosomes of the original cell.",
            "Mitosis occurs in somatic (non-reproductive) cells and is used for growth and tissue repair.",
            "Meiosis only occurs in germ cells (sperm and egg) and is essential for sexual reproduction.",
            "A key difference is that meiosis includes two rounds of cell division (meiosis I and II), while mitosis only includes one.",
            "Mitosis maintains the chromosome number of the original cell, whereas meiosis reduces it by half.",
            "Crossing over, which increases genetic variation, occurs during meiosis but not mitosis."
        ]
        return Data((input_query,context))


def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config=load_config("./sage/api/operator/test/config.yaml")

query="What are the main differences between mitosis and meiosis?"

source=FileSource(config)
retriver=Retriever_test(config)
promptor=QAPromptor(config)
generator=OpenAIGenerator(config)
reranker=BGEReranker(config)
refiner=AbstractiveRecompRefiner(config)
sink=TerminalSink(config)
output=source.execute()
output=retriver.execute(output)
output=reranker.execute(output)
output=refiner.execute(output)
output = promptor.execute(output)
output = generator.execute(output)
sink.execute(output)

