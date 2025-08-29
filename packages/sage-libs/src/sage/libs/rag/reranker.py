import torch
from typing import List, Tuple
from transformers import AutoModelForSequenceClassification, AutoTokenizer,AutoModelForCausalLM
import logging

from sage.core.api.function.map_function import MapFunction



class BGEReranker(MapFunction):
    """
    A reranker that uses the BAAI/bge-reranker-v2-m3 model to reorder a list of retrieved documents.
    The model assigns relevance scores to the documents and ranks them accordingly.

    Input: A tuple of (query, List[retrieved_documents])
    Output: A tuple of (query, List[reranked_documents_with_scores])

    Attributes:
        logger: Logger for logging error and information messages.
        config: Configuration dictionary containing reranker settings (model name, top_k, etc.).
        device: Device ('cuda' or 'cpu') where the model will be loaded.
        tokenizer: Tokenizer used to preprocess input queries and documents.
        model: The pre-trained reranking model.
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        """
        Initializes the BGEReranker with configuration settings and loads the model.

        :param config: Dictionary containing configuration options, including model name and device settings.
        """
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"  # Set device to GPU if available, otherwise CPU
        
        # Load tokenizer and model using the provided model name
        self.tokenizer, self.model = self._load_model(self.config["model_name"])
        self.model = self.model.to(self.device)
        self.model.eval()  # Set the model to evaluation mode

    def _load_model(self, model_name: str):
        """
        Loads the tokenizer and model for the reranker.

        :param model_name: Name of the pre-trained model to load.
        :return: Tuple containing the tokenizer and the model.
        """
        try:
            self.logger.info(f"Loading reranker: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)  # Load the tokenizer
            model = AutoModelForSequenceClassification.from_pretrained(model_name)  # Load the model
            return tokenizer, model
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")
        
    def execute(self, data: Tuple[str, List[str]]):
        """
        Executes the reranking process:
        1. Unpacks the input data (query and list of documents).
        2. Generates query-document pairs.
        3. Calculates relevance scores using the model.
        4. Sorts documents based on their relevance scores.

        :param data: A Data object containing a tuple of (query, doc_set), where:
                     - query: The user query.
                     - doc_set: List of retrieved documents.
        :return: A Data object containing a tuple (query, reranked_documents_with_scores).
        """
        try:
            # 处理不同的输入格式
            if isinstance(data, dict):
                # 来自 ChromaRetriever 的字典格式: {"query": ..., "results": [...]}
                query = data.get("query", "")
                doc_set = data.get("results", [])
                if not query:
                    self.logger.error("Missing 'query' field in dictionary input")
                    return {"query": "", "results": []}
            elif isinstance(data, (tuple, list)) and len(data) == 2:
                # 传统的元组格式: (query, doc_set)
                query, doc_set = data
            else:
                self.logger.error(f"Unexpected input format for BGEReranker: {type(data)}")
                return {"query": "", "results": []}
            
            top_k = self.config.get("topk") or self.config.get("top_k", 3)  # Get the top-k parameter for reranking

            # Handle empty document set case
            if not doc_set:
                print("BGEReranker received empty document set, returning empty results")
                # 返回与输入格式一致的输出
                if isinstance(data, dict):
                    return {"query": query, "results": []}
                else:
                    return query, []

            # Generate query-document pairs for scoring
            pairs = [(query, doc) for doc in doc_set]

            # Tokenize the pairs and move inputs to the appropriate device
            raw_inputs = self.tokenizer(
                            pairs,
                            padding=True,
                            truncation=True,
                            max_length=512,
                            return_tensors="pt"
                        )
            inputs = {
                k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                for k, v in raw_inputs.items()
            }


            
            # Perform inference and calculate scores
            scores = self.model(**inputs).logits.view(-1).float()

            # Create a list of scored documents
            scored_docs = [
                {"retrieved_docs": doc, "relevance_score": score}
                for doc, score in zip(doc_set, scores)
            ]
            
            # Sort the documents by relevance score in descending order
            reranked_docs = sorted(scored_docs, key=lambda x: x["relevance_score"], reverse=True)[:top_k]
            reranked_docs_list = [doc["retrieved_docs"] for doc in reranked_docs]
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Rerank Results: {reranked_docs_list }\033[0m ")
            self.logger.debug(f"Top score: {reranked_docs[0]['relevance_score'] if reranked_docs else 'N/A'}")

            print(f"Rerank Results: {reranked_docs_list}")

        except Exception as e:
            raise RuntimeError(f"BGEReranker error: {str(e)}")
        
        # 返回与输入格式一致的输出
        if isinstance(data, dict):
            return {"query": query, "results": reranked_docs_list}
        else:
            return [query, reranked_docs_list]  # Return the reranked documents along with the original query


class LLMbased_Reranker(MapFunction):
    """
    A reranker that uses the BAAI/bge-reranker-v2-gemma model to determine if a retrieved document contains an answer to a given query.
    It scores the documents with 'Yes' or 'No' predictions based on whether the document answers the query.

    Input: A tuple of (query, List[retrieved_documents])
    Output: A tuple of (query, List[reranked_documents_with_scores])

    Attributes:
        logger: Logger for logging error and information messages.
        config: Configuration dictionary containing reranker settings (model name, top_k, etc.).
        device: Device ('cuda' or 'cpu') where the model will be loaded.
        tokenizer: Tokenizer used to preprocess input queries and documents.
        model: The pre-trained reranking model.
        yes_loc: Token ID representing 'Yes' (used for scoring).
    """

    def __init__(self, config, model_name: str = "BAAI/bge-reranker-v2-gemma"):
        """
        Initializes the LLMbased_Reranker with configuration settings and loads the model.

        :param config: Dictionary containing configuration options, including model name and device settings.
        :param model_name: Name of the pre-trained model to load (default is "BAAI/bge-reranker-v2-gemma").
        """
        super().__init__()
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"  # Set device to GPU if available, otherwise CPU

        # Load tokenizer and model using the provided model name
        self.tokenizer, self.model = self._load_model(model_name)
        self.model = self.model.to(self.device)
        
        # Get the token ID for the 'Yes' token (used for classification)
        self.yes_loc = self.tokenizer('Yes', add_special_tokens=False)['input_ids'][0]

    def _load_model(self, model_name: str):
        """
        Loads the tokenizer and model for the reranker.

        :param model_name: Name of the pre-trained model to load.
        :return: Tuple containing the tokenizer and the model.
        """
        try:
            self.logger.info(f"Loading reranker: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)  # Load the tokenizer
            model = AutoModelForCausalLM.from_pretrained(model_name)  # Load the model
            return tokenizer, model
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")

    def get_inputs(self, pairs, tokenizer, prompt=None, max_length=1024):
        """
        Prepares the input for the model, including the prompt and the query-document pairs.

        :param pairs: List of query-document pairs.
        :param tokenizer: The tokenizer used to process the input data.
        :param prompt: Optional prompt to guide the model (defaults to a generic query-passage prompt).
        :param max_length: Maximum length of the tokenized input sequences.
        :return: A tensor of tokenized inputs, ready for model inference.
        """
        if prompt is None:
            prompt = "Given a query A and a passage B, determine whether the passage contains an answer to the query by providing a prediction of either 'Yes' or 'No'."
        
        sep = "\n"
        prompt_inputs = tokenizer(prompt, return_tensors=None, add_special_tokens=False)['input_ids']
        sep_inputs = tokenizer(sep, return_tensors=None, add_special_tokens=False)['input_ids']
        
        inputs = []
        for query, passage in pairs:
            query_inputs = tokenizer(f'A: {query}', return_tensors=None, add_special_tokens=False, max_length=max_length * 3 // 4, truncation=True)
            passage_inputs = tokenizer(f'B: {passage}', return_tensors=None, add_special_tokens=False, max_length=max_length, truncation=True)
            
            item = tokenizer.prepare_for_model(
                [tokenizer.bos_token_id] + query_inputs['input_ids'],
                sep_inputs + passage_inputs['input_ids'],
                truncation='only_second',
                max_length=max_length,
                padding=False,
                return_attention_mask=False,
                return_token_type_ids=False,
                add_special_tokens=False
            )
            item['input_ids'] = item['input_ids'] + sep_inputs + prompt_inputs
            item['attention_mask'] = [1] * len(item['input_ids'])
            inputs.append(item)
        
        return tokenizer.pad(
            inputs,
            padding=True,
            max_length=max_length + len(sep_inputs) + len(prompt_inputs),
            pad_to_multiple_of=8,
            return_tensors='pt',
        )

    # @torch.inference_mode()
    def execute(self, data: Tuple[str, List[str]]) -> Tuple[str, List[str]]:
        """
        Executes the reranking process:
        1. Unpacks the input data (query and list of documents).
        2. Generates query-document pairs for classification.
        3. Calculates relevance scores based on 'Yes'/'No' predictions.
        4. Sorts documents based on their relevance scores.

        :param data: A Data object containing a tuple of (query, doc_set), where:
                     - query: The user query.
                     - doc_set: List of retrieved documents.
        :return: A Data object containing a tuple (query, reranked_documents_with_scores).
        """
        try:
            # 处理不同的输入格式
            if isinstance(data, dict):
                # 来自 ChromaRetriever 的字典格式: {"query": ..., "results": [...]}
                query = data.get("query", "")
                doc_set = data.get("results", [])
                if not query:
                    self.logger.error("Missing 'query' field in dictionary input")
                    return {"query": "", "results": []}
            elif isinstance(data, (tuple, list)) and len(data) == 2:
                # 传统的元组格式: (query, doc_set)
                query, doc_set = data
            else:
                self.logger.error(f"Unexpected input format for LLMbased_Reranker: {type(data)}")
                return {"query": "", "results": []}
            
            doc_set = [doc_set]  # Wrap doc_set in a list for processing
            top_k = self.config["topk"]  # Get the top-k parameter for reranking
            emit_docs = []  # Initialize the list to store reranked documents

            for retrieved_docs in doc_set:
                # Generate query-document pairs for classification
                pairs = [[query, doc] for doc in retrieved_docs]
                
                # Tokenize the pairs and move inputs to the appropriate device
                with torch.no_grad():
                    raw_inputs = self.get_inputs(pairs, self.tokenizer)
                    inputs = {k: v.to(self.device) for k, v in raw_inputs.items()}

                    scores = self.model(**inputs, return_dict=True).logits[:, -1, self.yes_loc].view(-1).float()

                # Create a list of scored documents
                scored_docs = [
                    {"retrieved_docs": doc, "relevance_score": score}
                    for doc, score in zip(retrieved_docs, scores)
                ]
                
                # Sort the documents by relevance score in descending order
                reranked_docs = sorted(scored_docs, key=lambda x: x["relevance_score"], reverse=True)[:top_k]
                reranked_docs_list = [doc["retrieved_docs"] for doc in reranked_docs]
                emit_docs.append(reranked_docs_list)
                self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Rerank Results: {reranked_docs_list }\033[0m ")
                self.logger.debug(f"Top score: {reranked_docs[0]['relevance_score'] if reranked_docs else 'N/A'}")

        except Exception as e:
            self.logger.error(f"{str(e)} when RerankerFuncton")
            raise RuntimeError(f"Reranker error: {str(e)}")
        
        emit_docs = emit_docs[0]  # Only return the first set of reranked documents
        
        # 返回与输入格式一致的输出
        if isinstance(data, dict):
            return {"query": query, "results": emit_docs}
        else:
            return (query, emit_docs)  # Return the reranked documents along with the original query


# if __name__ == '__main__':

#    # 设置配置
#     config1 = {
#         "reranker": {
#             "model_name":"BAAI/bge-reranker-v2-m3",
#             "top_k": 3
#         }
#     }

#     config2 = {
#         "reranker": {
#             "model_name":"BAAI/bge-reranker-v2-gemma",
#             "top_k": 3
#         }
#     }

#     # 创建实例
#     # reranker = BGEReranker(config)
#     reranker = LLMbased_Reranker(config2)
#     # 测试数据
#     query = "What is the capital of France?"
#     docs = [
#         "Paris is the capital of France.",
#         "Berlin is a city in Germany.",
#         "The Eiffel Tower is located in Paris.",
#         "France is a country in Western Europe.",
#         "Madrid is the capital of Spain."
#     ]

#     # 执行重排
#     input_data = (query, docs)
#     output = reranker.execute(input_data)

#     # 输出结果
#     result_query, result_docs = output
#     print("Query:", result_query)
#     print("Top-k Re-ranked Documents:")
#     for i, doc in enumerate(result_docs, 1):
#         print(f"{i}. {doc}")