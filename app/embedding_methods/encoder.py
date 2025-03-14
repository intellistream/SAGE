from typing import List, Union
import torch
import numpy as np
from tqdm import tqdm
from app.utils import parse_query, load_model

class Encoder:
    """
    Encoder class for encoding queries using a specified model.

    Attributes:
        model_name (str): The name of the model.
        model_path (str): The path to the model.
        pooling_method (str): The method used for pooling.
        max_length (int): The maximum length of the input sequences.
        use_fp16 (bool): Whether to use FP16 precision.
        instruction (str): Additional instructions for parsing queries.

    Methods:
        encode(query_list: List[str], is_query=True) -> np.ndarray:
            Encodes a list of queries into embeddings.
    """

    def __init__(self, model_name, model_path, pooling_method="mean", max_length=512, use_fp16=False, instruction=None):
        self.model_name = model_name
        self.model_path = model_path
        self.pooling_method = pooling_method
        self.max_length = max_length
        self.use_fp16 = use_fp16
        self.instruction = instruction
        self.gpu_num = torch.cuda.device_count()
        self.model, self.tokenizer = load_model(model_path=model_path, use_fp16=use_fp16)

    @torch.inference_mode()
    def single_batch_encode(self, query_list: Union[List[str], str], is_query=True) -> np.ndarray:
        """
        Encode a single batch of queries or documents.

        Args:
            query_list (Union[List[str], str]): List of queries or a single query.
            is_query (bool): Whether the input is a query (True) or a document (False).

        Returns:
            np.ndarray: Embeddings of the input queries or documents.
        """
        query_list = parse_query(self.model_name, query_list, self.instruction, is_query)

        inputs = self.tokenizer(
            query_list, max_length=self.max_length, padding=True, truncation=True, return_tensors="pt"
        )
        inputs = {k: v.cuda() for k, v in inputs.items()}

        if "T5" in type(self.model).__name__ or (isinstance(self.model, torch.nn.DataParallel) and "T5" in type(self.model.module).__name__):
            # T5-based retrieval model
            decoder_input_ids = torch.zeros((inputs["input_ids"].shape[0], 1), dtype=torch.long).to(
                inputs["input_ids"].device
            )
            output = self.model(**inputs, decoder_input_ids=decoder_input_ids, return_dict=True)
            query_emb = output.last_hidden_state[:, 0, :]

        else:
            output = self.model(**inputs, return_dict=True)
            pooler_output = output.get('pooler_output', None)
            last_hidden_state = output.get('last_hidden_state', None)
            query_emb = self._apply_pooling(pooler_output, last_hidden_state, inputs["attention_mask"])

        if "dpr" not in self.model_name:
            query_emb = torch.nn.functional.normalize(query_emb, dim=-1)
        query_emb = query_emb.detach().cpu().numpy()
        query_emb = query_emb.astype(np.float32, order="C")
        return query_emb

    def _apply_pooling(self, pooler_output, last_hidden_state, attention_mask):
        """
        Apply pooling method to the model's output.

        Args:
            pooler_output (torch.Tensor): Pooler output from the model.
            last_hidden_state (torch.Tensor): Last hidden state from the model.
            attention_mask (torch.Tensor): Attention mask for the input.

        Returns:
            torch.Tensor: Pooled embeddings.
        """
        if self.pooling_method == "mean":
            return self._mean_pooling(last_hidden_state, attention_mask)
        elif self.pooling_method == "cls":
            return self._cls_pooling(last_hidden_state)
        elif self.pooling_method == "pooler":
            return self._pooler_output(pooler_output)
        else:
            raise ValueError(f"Unsupported pooling method: {self.pooling_method}")

    def _mean_pooling(self, last_hidden_state, attention_mask):
        """
        Mean pooling over the last hidden state.

        Args:
            last_hidden_state (torch.Tensor): Last hidden state from the model.
            attention_mask (torch.Tensor): Attention mask for the input.

        Returns:
            torch.Tensor: Mean-pooled embeddings.
        """
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def _cls_pooling(self, last_hidden_state):
        """
        CLS token pooling.

        Args:
            last_hidden_state (torch.Tensor): Last hidden state from the model.

        Returns:
            torch.Tensor: CLS token embeddings.
        """
        return last_hidden_state[:, 0]

    def _pooler_output(self, pooler_output):
        """
        Pooler output.

        Args:
            pooler_output (torch.Tensor): Pooler output from the model.

        Returns:
            torch.Tensor: Pooler output embeddings.
        """
        if pooler_output is None:
            raise ValueError("Pooler output is not available for this model.")
        return pooler_output

    @torch.inference_mode()
    def encode(self, query_list: List[str], batch_size=64, is_query=True) -> np.ndarray:
        """
        Encode a list of queries or documents.

        Args:
            query_list (List[str]): List of queries or documents.
            batch_size (int): Batch size for encoding.
            is_query (bool): Whether the input is a query (True) or a document (False).

        Returns:
            np.ndarray: Embeddings of the input queries or documents.
        """
        query_emb = []
        for i in tqdm(range(0, len(query_list), batch_size), desc="Encoding process: "):
            query_emb.append(self.single_batch_encode(query_list[i : i + batch_size], is_query))
        query_emb = np.concatenate(query_emb, axis=0)
        return query_emb

    @torch.inference_mode()
    def multi_gpu_encode(self, query_list: Union[List[str], str], batch_size=64, is_query=True) -> np.ndarray:
        """
        Encode a list of queries or documents using multiple GPUs.

        Args:
            query_list (Union[List[str], str]): List of queries or a single query.
            batch_size (int): Batch size for encoding.
            is_query (bool): Whether the input is a query (True) or a document (False).

        Returns:
            np.ndarray: Embeddings of the input queries or documents.
        """
        if self.gpu_num > 1:
            self.model = torch.nn.DataParallel(self.model)
        return self.encode(query_list, batch_size, is_query)