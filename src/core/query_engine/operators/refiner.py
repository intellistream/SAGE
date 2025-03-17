import logging
import torch
from transformers import AutoModel, AutoTokenizer, AutoModelForSeq2SeqLM
from src.core.query_engine.operators.base_operator import BaseOperator
import re
import numpy as np
from abc import abstractmethod
import math



class BaseRefiner(BaseOperator):
    """Base class for all refiners"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    @abstractmethod
    def load_model(self):

        raise NotImplementedError
    @abstractmethod
    def execute(self, input_data, **kwargs):
        """
        Input data format:
        {
            "question": str,
            "retrieval_result": List[dict]  # Original documents
        }
        """
        raise NotImplementedError


class ExtractiveRefiner(BaseRefiner):
    """Extractive refiner implementation
       using finetuned contrieval models"""

    def __init__(self, config):
        super().__init__(config)
        self.logger.debug("Initializing Extractive Refiner")
        self._initialize_encoder()

    def _initialize_encoder(self):
        self.compression_ratio  = self.config.get("compression ratio", 0.25)
        self.pooling_method = self.config.get("pooling_method", "mean")
        self.encode_max_length = self.config.get("encode_max_length", 512)
        self.mini_batch_size = self.config.get('mini_batch_size', 256)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name=self.config.get("model_name", "facebook/contriever-msmarco")
        self.tokenizer, self.model = self.load_model(self.model_name)
        self.logger.info("Initialize Extractive Refiner Successfully")

    def load_model(self,model_name):
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name)
        return tokenizer, model

    def _process_retrieval_result(self, retrieval_result):
        """Preprocess retrieval results"""
        return [
            "\n".join(doc_item.split("\n")[:])
            for doc_item in retrieval_result
        ]

    def mean_pooling(self,token_embeddings, mask):
        token_embeddings = token_embeddings.masked_fill(~mask[..., None].bool(), 0.)
        sentence_embeddings = token_embeddings.sum(dim=1) / mask.sum(dim=1)[..., None]
        return sentence_embeddings

    def _select_topk_sentences(self, sent_list, score_list,top_k):
        scores = np.array(score_list)
        topk_indices = np.argpartition(-scores, top_k)[:top_k]
        topk_indices.sort()  # 保持原顺序
        return [sent_list[i] for i in topk_indices]

    def execute(self, input_data , **kwargs):
        try:

            # Unpack input data
            query=input_data.natural_query
            context_ltm = input_data.context_ltm
            context_stm = input_data.context_stm
            external_docs = input_data.external_docs
            doc_set = [context_ltm, context_stm, external_docs]
            emit_docs = []
            for retrieval_docs in doc_set:
                #process the retrieval docs
                retrieval_docs = self._process_retrieval_result(retrieval_docs)
                sent_list=[]
                # Split documents into sentences
                for retrieval_doc in retrieval_docs:
                    sent_list += self._split_into_sentences(retrieval_doc)

                # Encode question and sentences
                inputs = self.tokenizer([query] + sent_list, max_length=self.encode_max_length,padding=True, truncation=True, return_tensors='pt').to(self.device)
                self.model.to(self.device)
                self.model.eval()
                # Compute token embeddings
                with torch.no_grad():
                    outputs = self.model(**inputs)
                embeddings = self.mean_pooling(outputs[0], inputs['attention_mask']).detach().cpu()
                query_embeddings=embeddings[0]
                sents_embeddings=embeddings[1:]
                #compute the scores
                scores=[]
                for sent_embedding in sents_embeddings:
                    score=query_embeddings@sent_embedding
                    scores.append(score)
                print("scores:",scores)
                print("compressed_size",math.ceil(len(scores)*self.compression_ratio))
                #make the compression by the scores
                compressed_sents = self._select_topk_sentences(sent_list, scores,math.ceil(self.compression_ratio*len(sent_list)))
                emit_docs.append(compressed_sents)
            input_data.context_ltm=emit_docs[0]
            input_data.context_stm=emit_docs[1]
            input_data.external_docs=emit_docs[2]

            self.emit(input_data)
        except Exception as e:
            self.logger.error(f"Refining failed: {str(e)}")
            raise RuntimeError(f"Refining error: {str(e)}")



    def _split_into_sentences(self, text):
        return [sent.strip() for sent in re.split(r'(?<=[.!?])\s+', text) if len(sent.strip()) > 5]



class AbstractiveRecompRefiner(BaseRefiner):
    """Abstractive refiner using RECOMP approach"""

    def __init__(self, config):
        super().__init__(config)
        self._initialize_model()

    def _initialize_model(self):
        self.max_input_length = self.config.get("refiner_max_input_length", 1024)
        self.max_output_length = self.config.get("refiner_max_output_length", 256)
        self.model_name=self.config.get("model_name", "google-t5/t5-large")
        # Initialize model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def execute(self, input_data, **kwargs):
        try:
            # Prepare input
            query=input_data.natural_query
            context_ltm = input_data.context_ltm
            context_stm = input_data.context_stm
            external_docs = input_data.external_docs
            doc_set = [context_ltm, context_stm, external_docs]
            emit_docs = []
            for retrieval_docs in doc_set:
                query,processed_docs=self._format_input(query, retrieval_docs)
                input_prompt=self.build_prompt(query, processed_docs)
                # Generate summary
                summary = ''.join(self._generate_summary(input_prompt))
                print("summary:",summary)
                summary=[summary]
                emit_docs.append(summary)
            # Emit processed result
            input_data.context_ltm=emit_docs[0]
            input_data.context_stm=emit_docs[1]
            input_data.external_docs=emit_docs[2]
            self.emit(input_data)
        except Exception as e:
            self.logger.error(f"Refining failed: {str(e)}")
            raise RuntimeError(f"Refining error: {str(e)}")

    def _format_input(self, question, retrieval_result):
        processed_docs = [
            "\n".join(doc.split("\n")[:])
            for doc in retrieval_result
        ]
        processed_docs = '\n'.join(processed_docs)
        return question, processed_docs

    def build_prompt(self,question, docs):
        return f"""
    Generate a concise, factual summary from the document below that specifically answers the question. Follow these requirements:
    1. Extract ONLY information directly related to the question
    2. Present results using bullet points or short structured paragraphs
    3. Include critical elements: 
       - Numerical data/percentages 
       - Time periods/dates 
       - Definitive conclusions
       - Named entities (people/organizations/locations)
    4. Exclude speculative statements and irrelevant details

    Question:
    {question}

    Document:
    {docs}
    Summery:
    """


    def _generate_summary(self, formatted_input):
        inputs = self.tokenizer(
            formatted_input,
            return_tensors="pt",
            max_length=self.max_input_length,
            truncation=True
        ).to(self.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=self.max_output_length,
                num_beams=self.config.get("num_beams", 4),
                early_stopping=True
            ).detach().cpu()

        return self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )