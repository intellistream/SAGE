import os
import faiss
from typing import List, Dict
from app.utils import load_corpus, load_docs
from app.embedding_methods.encoder import Encoder
from app.embedding_methods.ste_encoder import STEncoder
from app.retriever.base_retriever import BaseTextRetriever

class FaissRetriever(BaseTextRetriever):
    r"""Faiss retriever based on pre-built faiss index."""

    def __init__(self, config: dict, corpus=None):
        super().__init__(config)
        self.load_corpus(corpus)
        self.load_index()
        self.load_model()

    def load_corpus(self, corpus):
        """Load the corpus."""
        if corpus is None:
            self.corpus = load_corpus(self.corpus_path)
        else:
            self.corpus = corpus

    def load_index(self):
        """Load the FAISS index."""
        if self.index_path is None or not os.path.exists(self.index_path):
            raise Warning(f"Index file {self.index_path} does not exist!")
        self.index = faiss.read_index(self.index_path)
        if self.use_faiss_gpu:
            co = faiss.GpuMultipleClonerOptions()
            co.useFloat16 = True
            co.shard = True
            self.index = faiss.index_cpu_to_all_gpus(self.index, co=co)

    def update_additional_setting(self):
        """Update additional settings for dense retrieval."""
        self.query_max_length = self._config["retrieval_query_max_length"]
        self.pooling_method = self._config['retrieval_pooling_method']
        self.use_fp16 = self._config['retrieval_use_fp16']
        self.batch_size = self._config["retrieval_batch_size"]
        self.instruction = self._config["instruction"]
        self.retrieval_model_path = self._config['retrieval_model_path']
        self.use_st = self._config["use_sentence_transformer"]
        self.use_faiss_gpu = self._config['faiss_gpu']

    def load_model(self):
        """Load the encoder model."""
        if self.use_st:
            self.encoder = STEncoder(
                model_name=self.retrieval_method,
                model_path=self.retrieval_model_path,
                max_length=self.query_max_length,
                use_fp16=self.use_fp16,
                instruction=self.instruction,
            )
        else:
            self.encoder = Encoder(
                model_name=self.retrieval_method,
                model_path=self.retrieval_model_path,
                pooling_method=self.pooling_method,
                max_length=self.query_max_length,
                use_fp16=self.use_fp16,
                instruction=self.instruction,
            )

    def search(self, query: str, num: int = None, return_score=False) -> List[Dict[str, str]]:
        """Search for documents using dense retrieval.

        Args:
            query: The query string.
            num: The number of documents to retrieve.
            return_score: Whether to return the scores of the documents.

        Returns:
            A list of documents or a tuple of (documents, scores) if return_score is True.
        """
        if num is None:
            num = self.topk

        # Encode the query
        query_emb = self.encoder.encode(query)
        # Search the FAISS index
        scores, idxs = self.index.search(query_emb, k=num)
        scores = scores.tolist()[0]
        idxs = idxs.tolist()[0]

        # Load documents from the corpus
        results = load_docs(self.corpus, idxs)

        if return_score:
            return results, scores
        else:
            return results

    def batch_search(self, query: List[str], num: int = None, return_score=False):
        """Batch search for documents using dense retrieval.

        Args:
            query: A list of query strings.
            num: The number of documents to retrieve for each query.
            return_score: Whether to return the scores of the documents.

        Returns:
            A list of lists of documents or a tuple of (results, scores) if return_score is True.
        """
        if isinstance(query, str):
            query = [query]
        if num is None:
            num = self.topk

        # Encode the queries in batches
        emb = self.encoder.encode(query, batch_size=self.batch_size, is_query=True)
        # Search the FAISS index
        scores, idxs = self.index.search(emb, k=num)
        scores = scores.tolist()
        idxs = idxs.tolist()

        # Load documents from the corpus
        flat_idxs = sum(idxs, [])
        results = load_docs(self.corpus, flat_idxs)
        results = [results[i * num: (i + 1) * num] for i in range(len(idxs))]

        if return_score:
            return results, scores
        else:
            return results