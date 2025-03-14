import json
import warnings
from typing import List, Dict
import bm25s
import Stemmer
from app.retriever.base_retriever import BaseTextRetriever
from app.utils import load_corpus

class BM25Retriever(BaseTextRetriever):
    r"""BM25 retriever based on bm25s backend."""

    def __init__(self, config, corpus=None):
        super().__init__(config)
        self.load_model_corpus(corpus)

    def update_additional_setting(self):
        self.backend = "bm25s"

    def load_model_corpus(self, corpus):
        """Load the BM25 model and corpus."""
        self.corpus = load_corpus(self.corpus_path) if corpus is None else corpus

        self.searcher = bm25s.BM25.load(self.index_path, mmap=True, load_corpus=False)

        stemmer = Stemmer.Stemmer("english")
        self.tokenizer = bm25s.tokenization.Tokenizer(stopwords='en', stemmer=stemmer)
        self.tokenizer.load_stopwords(self.index_path)
        self.tokenizer.load_vocab(self.index_path)

        self.searcher.corpus = self.corpus
        self.searcher.backend = "numba"

    def search(self, query: str, num: int = None, return_score=False) -> List[Dict[str, str]]:
        """Search for documents using BM25.

        Args:
            query: The query string.
            num: The number of documents to retrieve.
            return_score: Whether to return the scores of the documents.

        Returns:
            A list of documents or a tuple of (documents, scores) if return_score is True.
        """
        if num is None:
            num = self.topk

        # Tokenize the query
        query_tokens = self.tokenizer.tokenize([query], return_as='tuple', update_vocab=False)
        # Retrieve documents
        results, scores = self.searcher.retrieve(query_tokens, k=num)
        results = list(results[0])
        scores = list(scores[0])

        if return_score:
            return results, scores
        else:
            return results

    def batch_search(self, query, num: int = None, return_score=False):
        """Batch search for documents using BM25.

        Args:
            query: A list of query strings.
            num: The number of documents to retrieve for each query.
            return_score: Whether to return the scores of the documents.

        Returns:
            A list of lists of documents or a tuple of (results, scores) if return_score is True.
        """
        if num is None:
            num = self.topk

        # Tokenize the queries
        query_tokens = self.tokenizer.tokenize(query, return_as='tuple', update_vocab=False)
        # Retrieve documents
        results, scores = self.searcher.retrieve(query_tokens, k=num)

        if return_score:
            return results, scores
        else:
            return results