import logging
import torch
from src.core.embedding.text_preprocessor import TextPreprocessor
from src.core.query_engine.operators.web_workflow.bge_reranker import BGEReranker
from langchain_community.retrievers import BM25Retriever
from sentence_transformers import SentenceTransformer
import numpy as np

class HybridRetriever():
    """
    A hybrid retriever operator that utilizes both sparse and dense retrieval methods to fetch documents.
    """

    def __init__(self, 
                embedder_model="BAAI/bge-large-en-v1.5",
                rerank_model="BAAI/bge-reranker-large",):
        """
        Initialize the Retriever operator.
        :param embedder_model: An embedder instance to generate embeddings.
        :param rerank_model: An reranker instance to rerank the results.
        """
        super().__init__()
        self.embedder = TextPreprocessor(model_name=embedder_model)  # Instantiate the embedder
        self.sentence_model = SentenceTransformer(
            embedder_model,
            device=torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            ),
        )
        self.reranker = BGEReranker(top_n=20, model_name=rerank_model)
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, query, first_results, **kwargs):
        """
        Retrieve data relevant to the input query from long-term memory.
        :param query: natural query.
        :param first_results: The first results retrieved by the sparse retriever.
        :param kwargs: Additional parameters (e.g., number of results).
        :return: Retrieved data.
        """
        try:
            # SparseRetriever:
            bm25_retriever = BM25Retriever.from_texts(first_results)
            bm25_retriever.k = kwargs.get("M", 1)
            bm25_results = bm25_retriever.invoke(query)
            sparse_results = [doc.page_content for doc in bm25_results]
            self.logger.info(f"BM25Retriever retrieved {len(sparse_results)} results.")

            # DenseRetriever:
            chunk_embeddings = self.calculate_embeddings(first_results)

            # Calculate embeddings for query
            query_embedding = self.calculate_embeddings(query)[0]

            # Calculate cosine similarity between query and chunk embeddings,
            cosine_scores = (chunk_embeddings * query_embedding).sum(1)

            cosine_scores = np.array(cosine_scores).flatten()

            N = kwargs.get("N", 1)

            # Get the indices of the top-N highest cosine similarity scores
            top_n_indices = np.argsort(-cosine_scores)[:N]

            # Retrieve the top-N chunks based on the indices
            dense_results = [first_results[i] for i in top_n_indices]
            self.logger.info(f"DenseRetriever retrieved {len(dense_results)} results.")

            # Rerank
            self.reranker.top_n = N
            dense_results = self.reranker.execute((query, dense_results))

            # TODO:RRF加权融合，现在暂时直接返回
            results = sparse_results + dense_results

            return results

        except Exception as e:
            self.logger.error(f"Error during retrieval: {str(e)}")
            raise RuntimeError(f"Retriever execution failed: {str(e)}")

    def calculate_embeddings(self, sentences):
        """
        Compute normalized embeddings for a list of sentences using a sentence encoding model.
        params: sentences (List[str]): A list of sentences for which embeddings are to be computed.
        returns: np.ndarray: An array of normalized embeddings for the given sentences.
        """
        embeddings = self.sentence_model.encode(
            sentences=sentences,
            normalize_embeddings=True,
            batch_size=128,
        )     
        return embeddings
