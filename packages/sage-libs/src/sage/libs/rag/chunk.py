from typing import Any, List, Literal, Optional, Union
from sage.core.api.function.map_function import MapFunction

from typing import Any, List, Optional
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

class CharacterSplitter(MapFunction):
    """
    A source rag that reads a file and splits its contents into overlapping chunks.

    Input: None (reads directly from a file at the configured path).
    Output: A Data object containing a list of text chunks.

    Config:
        - data_path: Path to the input text file.
        - chunk_size: Number of tokens per chunk (default: 512).
        - overlap: Number of overlapping tokens (default: 128).
    """

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.chunk_size = self.config.get("chunk_size", 512)
        self.overlap = self.config.get("overlap", 128)
        self.separator = self.config.get("separator", None)

    def _split_text(self, text: str) -> List[str]:
        """
        支持用户指定分割符分块，否则按字符分块。
        """
        if self.separator:
            return [chunk for chunk in text.split(self.separator) if chunk.strip()]
        # ...existing code...
        tokens = list(text)  # character-level split
        chunks = []
        start = 0
        if not tokens:
            return [""]
        while start < len(tokens):
            end = start + self.chunk_size
            chunk = tokens[start:end]
            chunks.append("".join(chunk))
            next_start = start + self.chunk_size - self.overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start
        return chunks

    def execute(self, document: dict) -> List[str]:
        """
        接收 document 对象，分割其 content 字段为 chunk。
        :param document: {"content": ..., "metadata": ...}
        :return: List[str] 分块后的文本列表
        """
        content = document.get("content", "")
        try:
            chunks = self._split_text(content)
            return chunks
        except Exception as e:
            self.logger.error(f"CharacterSplitter error: {e}", exc_info=True)


class SentenceTransformersTokenTextSplitter(MapFunction):
    """
    A source rag that splits text into tokens using SentenceTransformer's tokenizer.

    Input: A Data object containing the text to be split.
    Output: A Data object containing a list of token-based text chunks.

    Config:
        - chunk_overlap: Number of overlapping tokens between chunks (default: 50).
        - model_name: The model name for SentenceTransformer (default: "sentence-transformers/all-mpnet-base-v2").
        - chunk_size: Optional number of tokens per chunk.
    """

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config.get("chunk", {})
        self.model_name = self.config.get("model_name", "sentence-transformers/all-mpnet-base-v2")
        self.chunk_size = self.config.get("chunk_size", 512)
        self.chunk_overlap = self.config.get("chunk_overlap", 50)

        try:
            # Load the SentenceTransformer model
            self._model = SentenceTransformer(self.model_name)
            # Use AutoTokenizer for transformer-based tokenization
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        except ImportError:
            raise ImportError(
                "Could not import sentence_transformers or transformers python packages. "
                "Please install them with `pip install sentence-transformers transformers`."
            )
        except Exception as e:
            self.logger.error(f"Error while loading model or tokenizer: {e}")
            raise e
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size.")
        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be greater than 0.")

    def split_text_on_tokens(self, text: str) -> List[str]:
        """
        Splits incoming text into smaller chunks using the tokenizer.

        :param text: The full text string to be split.
        :return: A list of token-based text chunks.
        """
        print(text)
        _max_length_equal_32_bit_integer: int = 2**32
        splits: List[str] = []
        input_ids = self.tokenizer.encode(text, truncation=True, padding=False)
        start_idx = 0

        print(f"Input IDs: {input_ids}")

        # Iterate through the text and split it into chunks
        while start_idx < len(input_ids):
            print(f"Start Index: {start_idx}")
            # Define the end of the current chunk
            cur_idx = min(start_idx + self.chunk_size, len(input_ids))
            chunk_ids = input_ids[start_idx:cur_idx]

            # Decode the chunk and add it to the list of splits
            splits.append(self.tokenizer.decode(chunk_ids, skip_special_tokens=True))
            
            # Move the starting index forward with the overlap
            start_idx = cur_idx - self.chunk_overlap

            # Break the loop when we've processed all tokens
            if cur_idx == len(input_ids):
                break

        return splits

    def execute(self, data: str) -> List[str]:
        """
        Splits the input text data into smaller token-based chunks.

        :param data: The input Data object containing the text to be split.
        :return: A Data object containing a list of token-based text chunks.
        """
        content = data
        # print(f"Content: {content}")
        try:
            chunks = self.split_text_on_tokens(content)
            return chunks
        except Exception as e:
            self.logger.error(f"SentenceTransformersTokenTextSplitter error: {e}", exc_info=True)

# config={
#     "chunk": {
#         "chunk_size": 8,
#         "chunk_overlap": 2,
#         "model_name": "sentence-transformers/all-mpnet-base-v2",
#     }
# }

# split=SentenceTransformersTokenTextSplitter(config)
# print(split.execute(Data("This is a operator_test sentence to be split into smaller chunks.This is a operator_test sentence to be split into smaller chunks.This is a operator_test sentence to be split into smaller chunks.This is a operator_test sentence to be split into smaller chunks.")))


