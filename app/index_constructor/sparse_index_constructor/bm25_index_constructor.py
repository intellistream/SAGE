import os
from abc import ABC, abstractmethod
from app.index_constructor.sparse_index_constructor.sparse_index_constructor import SparseIndexConstructor

class BM25IndexConstructor(SparseIndexConstructor):
    """Concrete class for building BM25 index."""

    def __init__(self, corpus_path, save_dir, backend="bm25s", dir_name = None):
        super().__init__(corpus_path, save_dir)
        self.backend = backend
        self.dir_name = dir_name

    def build_index(self):
        """Build the BM25 index using the specified backend."""
        self._build_with_bm25s()

    def _build_with_bm25s(self):
        """Build BM25 index using BM25s."""
        import bm25s
        import Stemmer

        self.save_dir = os.path.join(self.save_dir, "bm25")
        if self.dir_name is not None:
            self.save_dir = os.path.join(self.save_dir, self.dir_name)
        os.makedirs(self.save_dir, exist_ok=True)

        print("Building BM25 index with BM25s...")

        stemmer = Stemmer.Stemmer("english")
        corpus_text = [item["contents"] for item in self.corpus]
        tokenizer = bm25s.tokenization.Tokenizer(stopwords='en', stemmer=stemmer)
        corpus_tokens = tokenizer.tokenize(corpus_text, return_as='tuple')

        retriever = bm25s.BM25(corpus=self.corpus, backend="numba")
        retriever.index(corpus_tokens)

        retriever.save(self.save_dir)
        tokenizer.save_vocab(self.save_dir)
        tokenizer.save_stopwords(self.save_dir)
        print("BM25 index built successfully.")