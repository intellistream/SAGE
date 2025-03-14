import os
import argparse
from app.retriever.bm25_retriever import BM25Retriever
from app.retriever.faiss_retriever import FaissRetriever

parser = argparse.ArgumentParser(description="BM25 Retriever Test Script")
parser.add_argument("-test", type=str, help="The index to search for")

args = parser.parse_args()

def bm25test():
    # 设置索引和语料库路径
    index_dir = "app/index_constructor/test/index/bm25/clapnq_test"
    corpus_path = os.path.join(index_dir, "corpus.jsonl")

    # 初始化BM25Retriever
    config = {
        "corpus_path": corpus_path,
        "index_path": index_dir,
        "retrieval_topk": 5,
        "retrieval_method": "bm25"
    }

    retriever = BM25Retriever(config)

    # 定义查询
    query = "Egocentrism is the inability to differentiate between self and other. More specifically, it is the inability to untangle subjective schemas from objective reality; an inability to understand or assume any perspective other than their own."

    # 执行搜索
    results = retriever.search(query, return_score=True)

    # 打印结果
    print("Search Results:")
    for doc, score in zip(results[0], results[1]):
        print(f'Document: {doc["contents"]}')
        print(f"Score: {score}")
        print("-" * 40)


def faiss_test():


    # 配置参数
    config = {
        "retrieval_query_max_length": 512,
        "retrieval_pooling_method": "mean",
        "retrieval_method": "e5",
        "retrieval_use_fp16": False,
        "retrieval_batch_size": 16,
        "instruction": None,
        "retrieval_model_path": "intfloat/e5-base-v2",
        "use_sentence_transformer": False,
        "faiss_gpu": False,
        "retrieval_topk": 5,
        "corpus_path": "data/corpus/clapnq.jsonl",
        "index_path": "app/index_constructor/test/index/Flat.index"
    }

    # 初始化 FaissRetriever
    retriever = FaissRetriever(config)

    # 测试搜索功能
    query = "Egocentrism is the inability to differentiate between self and other. More specifically, it is the inability to untangle subjective schemas from objective reality; an inability to understand or assume any perspective other than their own."

    results = retriever.search(query, num=3, return_score=True)
    print("Single Query Results:")
    for doc, score in zip(results[0], results[1]):
        print(f'Document: {doc["contents"]}, Score: {score}')

if args.test == "bm25":
    bm25test()
elif args.test == "faiss":
    faiss_test()
else:
    raise ValueError("Invalid test type. Expected 'bm25' or 'faiss'.")

"""
python -m app.retriever.retrieval_test -test faiss
python -m app.retriever.retrieval_test -test bm25
"""