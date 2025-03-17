import logging
import torch
from typing import List, Tuple
from transformers import AutoModelForSequenceClassification, AutoTokenizer,AutoModelForCausalLM
from src.core.query_engine.operators.base_operator import BaseOperator
from src.core.query_engine.query_compilation.query_state import QueryState
from abc import abstractmethod

class BaseReranker(BaseOperator):

    def __init__(self, model_name: str):
        """
        :param model_name: 模型名称/路径
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model_name = model_name
        self.model = None

    @abstractmethod
    def _load_model(self,model_name):
        pass

    @abstractmethod
    def execute(self, input_data, **kwargs):
        pass


class BGEReranker(BaseReranker):
    """
    For normal reranker (bge-reranker-base / bge-reranker-large / bge-reranker-v2-m3 )
    Reranker using BAAI/bge-reranker-v2-m3 model
    Input: Tuple of (query, List[retrieved_documents])
    Output: Tuple of (query, List[reranked_documents_with_scores])
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = None):
        super().__init__(model_name)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # 初始化模型和分词器
        self.tokenizer, self.model = self._load_model(model_name)
        self.model = self.model.to(self.device)
        self.model.eval()

    def _load_model(self, model_name: str):
        """load the tokenizer and model"""
        try:
            self.logger.info(f"Loading reranker: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            return tokenizer, model
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")

    @torch.inference_mode()
    def execute(self, input_data, **kwargs):
        """
        process
        1. unpack the input date
        2. generate <queue,doc> pairs
        3. calculate score
        4. sort by score
        """
        try:
            query = input_data.natural_query
            context_ltm=input_data.context_ltm
            context_stm = input_data.context_stm
            external_docs = input_data.external_docs
            doc_set=[context_ltm,context_stm, external_docs]

            top_k = kwargs.get("top_k", 5)
            # self.logger.info(f"Processing {len(retrieved_docs)} docs for: {query[:50]}...")
            pairs=[]
            # 生成需要评分的文本对
            for  docs in doc_set:
                pairs.append([
                    [query, doc]
                    for doc in docs
                ])

            # 分词处理
            emitted_docs = []
            for i,pair in enumerate(pairs):
                inputs = self.tokenizer(
                    pair,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(self.device)
                # 模型推理
                scores = self.model(**inputs).logits.view(-1).float()
                # 合并分数到文档
                scored_docs = [
                    {"retrieved_docs": doc, "relevance_score": score}
                    for doc, score in zip(doc_set[i], scores)
                ]
                reranked_docs = sorted(
                    scored_docs,
                    key=lambda x: x["relevance_score"],
                    reverse=True
                )[:top_k]
                reranked_docs_list = [doc["retrieved_docs"] for doc in reranked_docs]

                self.logger.debug(f"Top score: {reranked_docs[0]['relevance_score'] if reranked_docs else 'N/A'}")
                emitted_docs.append(reranked_docs_list)
            input_data.context_ltm=emitted_docs[0]
            input_data.context_stm=emitted_docs[1]
            input_data.external_docs=emitted_docs[2]
            # 发送处理结果
            self.emit(input_data)

        except Exception as e:
            self.logger.error(f"Reranking failed: {str(e)}")
            raise RuntimeError(f"BGEReranker error: {str(e)}")

class LLMbased_Reranker(BaseReranker):
    """
    For BAAI/bge-reranker-v2-gemma
    Reranker using  BAAI/bge-reranker-v2-gemma
    Input: Tuple of (query, List[retrieved_documents])
    Output: Tuple of (query, List[reranked_documents_with_scores])
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-gemma", device: str = None):
        super().__init__(model_name)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 初始化模型和分词器
        self.tokenizer, self.model = self._load_model(model_name)
        self.model = self.model.to(self.device)
        self.yes_loc = self.tokenizer('Yes', add_special_tokens=False)['input_ids'][0]

    def _load_model(self, model_name: str):
        """load the tokenizer and model"""
        try:
            self.logger.info(f"Loading reranker: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name)
            return tokenizer, model
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")

    def get_inputs(self,pairs, tokenizer, prompt=None, max_length=1024):
        if prompt is None:
            prompt = "Given a query A and a passage B, determine whether the passage contains an answer to the query by providing a prediction of either 'Yes' or 'No'."
        sep = "\n"
        prompt_inputs = tokenizer(prompt,
                                  return_tensors=None,
                                  add_special_tokens=False)['input_ids']
        sep_inputs = tokenizer(sep,
                               return_tensors=None,
                               add_special_tokens=False)['input_ids']
        inputs = []
        for query, passage in pairs:
            query_inputs = tokenizer(f'A: {query}',
                                     return_tensors=None,
                                     add_special_tokens=False,
                                     max_length=max_length * 3 // 4,
                                     truncation=True)
            passage_inputs = tokenizer(f'B: {passage}',
                                       return_tensors=None,
                                       add_special_tokens=False,
                                       max_length=max_length,
                                       truncation=True)
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

    @torch.inference_mode()
    def execute(self, input_data, **kwargs):
        """
        process
        1. unpack the input date
        2. generate <queue,doc> pairs
        3. calculate score
        4. sort by score
        """
        try:
            query = input_data.natural_query
            context_ltm = input_data.context_ltm
            context_stm = input_data.context_stm
            external_docs = input_data.external_docs
            doc_set=[context_ltm, context_stm, external_docs]

            top_k = kwargs.get("top_k", 5)
            # self.logger.info(f"Processing {len(retrieved_docs)} docs for: {query[:50]}...")
            emit_docs = []
            for i,retrieved_docs in enumerate(doc_set):
                # 生成需要评分的文本对
                pairs = [
                    [query, doc]
                    for doc in retrieved_docs
                ]
                # 分词处理
                with torch.no_grad():
                    inputs = self.get_inputs(pairs, self.tokenizer).to(self.device)
                    scores = self.model(**inputs, return_dict=True).logits[:, -1, self.yes_loc].view(-1, ).float()
                # 合并分数到文档
                scored_docs = [
                    {"retrieved_docs": doc, "relevance_score": score}
                    for doc, score in zip(retrieved_docs, scores)
                ]
                reranked_docs = sorted(
                    scored_docs,
                    key=lambda x: x["relevance_score"],
                    reverse=True
                )[:top_k]
                reranked_docs_list = [doc["retrieved_docs"] for doc in reranked_docs]
                emit_docs.append(reranked_docs_list)
                self.logger.debug(f"Top score: {reranked_docs[0]['relevance_score'] if reranked_docs else 'N/A'}")

            input_data.context_ltm=emit_docs[0]
            input_data.context_stm=emit_docs[1]
            input_data.external_docs=emit_docs[2]

            # 发送处理结果
            self.emit(input_data)

        except Exception as e:
            self.logger.error(f"Reranking failed: {str(e)}")
            raise RuntimeError(f"Reranker error: {str(e)}")


