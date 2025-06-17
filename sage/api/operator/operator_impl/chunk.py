from typing import Any, List, Literal, Optional, Union
from sage.api.operator import ChunkFunction
from sage.api.operator import Data
from typing import Any, List, Optional
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

class CharacterSplitter(ChunkFunction):
    """
    A source function that reads a file and splits its contents into overlapping chunks.

    Input: None (reads directly from a file at the configured path).
    Output: A Data object containing a list of text chunks.

    Config:
        - data_path: Path to the input text file.
        - chunk_size: Number of tokens per chunk (default: 512).
        - overlap: Number of overlapping tokens (default: 128).
    """

    def __init__(self, config):
        super().__init__()
        self.config = config.get("chunk",{})
        self.chunk_size = self.config.get("chunk_size", 512)
        self.overlap = self.config.get("overlap", 128)

    def _split_text(self, text: str) -> List[str]:
        """
        Splits text into chunks of length `chunk_size` with `overlap` between chunks.

        :param text: The full text string to be split.
        :return: A list of chunked text strings.
        """
        tokens = list(text)  # character-level split
        chunks = []
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk = tokens[start:end]
            chunks.append("".join(chunk))
            start += self.chunk_size - self.overlap  # move forward with overlap
        return chunks

    def execute(self,data:Data[str]) -> Data[List[str]]:
        """
        Reads and splits the file into overlapping text chunks.

        :return: A Data object containing a list of text chunks.
        """
        content=data.data
        try:
            chunks = self._split_text(content)
            return Data(chunks)
        except Exception as e:
            self.logger.error(f"CharacterSplitter error: {e}")
        return Data([])  # Return empty list if error occurs


class SentenceTransformersTokenTextSplitter(ChunkFunction):
    """
    A source function that splits text into tokens using SentenceTransformer's tokenizer.

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

    def execute(self, data: Data[str]) -> Data[List[str]]:
        """
        Splits the input text data into smaller token-based chunks.

        :param data: The input Data object containing the text to be split.
        :return: A Data object containing a list of token-based text chunks.
        """
        content = data.data
        # print(f"Content: {content}")
        try:
            chunks = self.split_text_on_tokens(content)
            return Data(chunks)
        except Exception as e:
            self.logger.error(f"SentenceTransformersTokenTextSplitter error: {e}")
            return Data([])  # Return empty list if error occurs

# config={
#     "chunk": {
#         "chunk_size": 8,
#         "chunk_overlap": 2,
#         "model_name": "sentence-transformers/all-mpnet-base-v2",
#     }
# }

# split=SentenceTransformersTokenTextSplitter(config)
# print(split.execute(Data("This is a test sentence to be split into smaller chunks.This is a test sentence to be split into smaller chunks.This is a test sentence to be split into smaller chunks.This is a test sentence to be split into smaller chunks.")).data)


