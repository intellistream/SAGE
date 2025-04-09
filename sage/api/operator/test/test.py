from json import load
from typing import List, Tuple
import os
import sys

# 添加项目根路径到 PYTHONPATH 和 sys.path
project_root = os.getcwd()
print(project_root)

# os.environ["PYTHONPATH"] = f"{project_root}:{os.environ.get('PYTHONPATH', '')}"
print(f"{project_root}:{os.environ.get('PYTHONPATH', '')}")
sys.path.insert(0, project_root)

from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.reranker import BGEReranker
from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import TerminalSink
from sage.api.operator.operator_impl.writer import SimpleWriter
from sage.api.operator.operator_impl.retriever import SimpleRetriever
from sage.api.operator import Data
import yaml
from sage.api.memory.memory_api import (
    create_table,
    connect,
    init_default_manager,
    get_default_manager,
)

import pytest

def init_memory():
    manager=init_default_manager()

    lsm=create_table("long_term_memory",manager)

    contexts=[
        "Mitosis is a type of cell division that results in two genetically identical daughter cells from a single parent cell.",
        "Meiosis is a form of cell division that produces four genetically distinct daughter cells, each with half the number of chromosomes of the original cell.",
        "Mitosis occurs in somatic (non-reproductive) cells and is used for growth and tissue repair.",
        "Meiosis only occurs in germ cells (sperm and egg) and is essential for sexual reproduction.",
        "A key difference is that meiosis includes two rounds of cell division (meiosis I and II), while mitosis only includes one.",
        "Mitosis maintains the chromosome number of the original cell, whereas meiosis reduces it by half.",
        "Crossing over, which increases genetic variation, occurs during meiosis but not mitosis."
    ]

    for context in contexts:
        lsm.store(context)


def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config=load_config("./sage/api/operator/test/config.yaml")

def test_operator_pipline():
    init_memory()
    source=FileSource(config)
    retriver=SimpleRetriever(config)
    promptor=QAPromptor(config)
    generator=OpenAIGenerator(config)
    reranker=BGEReranker(config)
    sink=TerminalSink(config)
    output=source.execute()
    output=retriver.execute(output)

    output=reranker.execute(output)
    output = promptor.execute(output)
    output = generator.execute(output)
    sink.execute(output)
    assert("True" in output.data[0])

