import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class BGEReranker():
    """
    A re-ranker operator that re-ranks a list of documents based on a given context.
    """
    
    def __init__(self, top_n, model_name="BAAI/bge-reranker-large", use_fp16=False):
        """
        Initialize the Reranker operator.
        :param top_n: The number of documents to re-rank.
        :param model_name: The Hugging Face model to use for re-ranking.
        :param use_fp16: Whether to use FP16 for faster inference.
        """
        self.top_n = top_n
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()
        self.use_fp16 = use_fp16

    def execute(self, input_data, **kwargs):
        """
        Re-rank a list of results based on the given context.
        :param input_data: A tuple containing the context or query and a list of documents.
        :param kwargs: Additional parameters for re-ranking.
        :return: Re-ranked results.
        """
        try:
            query, docs = input_data
            logging.info(f"Re-ranking {len(docs)} results based on context: {query}")

            # Re-rank the results based on the context
            reranked_results, scores = self.rerank(query=query[0], docs=docs)
            results = [result for result in reranked_results]

            return results
        except Exception as e:
            logging.error(f"Error during re-ranking: {str(e)}")
            return []

    def rerank(self, query, docs):
        """
        Re-rank a list of documents based on a given context.
        :param query: The context or query to use for re-ranking.
        :param docs: A list of documents to re-rank.
        :return: Re-ranked documents.
        """
        # Prepare pairs of query and documents
        pairs = [[query, doc] for doc in docs]

        # Tokenize and encode the pairs
        inputs = self.tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=512)
        
        # Move tensors to GPU if available
        if torch.cuda.is_available():
            self.model = self.model.cuda()
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Get scores
        with torch.no_grad():
            outputs = self.model(**inputs, return_dict=True).logits.view(-1).float()
        
        # Get top_n documents based on scores
        top_n_indices = torch.argsort(outputs, descending=True)[:self.top_n]
        top_n_docs = [docs[i] for i in top_n_indices]
        
        return top_n_docs, outputs[top_n_indices]


