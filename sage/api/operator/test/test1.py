# from csv import writer
from json import load
from typing import List, Tuple
import os
import sys

from sage.api.operator import Data
from numpy import source
import test

import logging
# 添加项目根路径到 PYTHONPATH 和 sys.path
project_root = os.getcwd()
print(project_root)

# os.environ["PYTHONPATH"] = f"{project_root}:{os.environ.get('PYTHONPATH', '')}"
print(f"{project_root}:{os.environ.get('PYTHONPATH', '')}")
sys.path.insert(0, project_root)

import yaml
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)
config_arxiv=load_config("./sage/api/operator/test/config_arxiv.yaml")
print(config_arxiv)
from sage.api.operator.operator_impl_test.arxiv import ArxivPDFDownloader,ArxivPDFParser

def test_arxiv():
    downloader = ArxivPDFDownloader(config_arxiv)
    parser = ArxivPDFParser(config_arxiv)
    query='ti:"Retrieval Augmented Generation" OR abs:"Retrieval Augmented Generation"'
    query = Data(query)
    # Step 1: Download PDFs
    print("Downloading PDFs...")
    pdfs = downloader.execute(query)
    assert isinstance(pdfs.data, List) and len(pdfs.data) > 0, "No PDFs downloaded."

    # Step 2: Parse PDFs
    print("Parsing PDFs...")
    parsed_data = parser.execute(pdfs)
    assert isinstance(parsed_data.data, List) and len(parsed_data.data) > 0, "No data parsed from PDFs."

    print("Test completed successfully.")
test_arxiv()
