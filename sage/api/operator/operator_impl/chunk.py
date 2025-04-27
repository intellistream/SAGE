from __future__ import annotations

import re
from typing import Any, List, Literal, Optional, Union

from sage.api.operator import ChunkFunction
from sage.api.operator import Data
from typing import List
import re
import copy
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import (
    AbstractSet,
    Any,
    Callable,
    Collection,
    Iterable,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

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
        self.config = config["chunk"]
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

from typing import Any, List, Optional, cast

@dataclass(frozen=True)
class Tokenizer:
    """Tokenizer data class."""

    chunk_overlap: int
    """Overlap in tokens between chunks"""
    tokens_per_chunk: int
    """Maximum number of tokens per chunk"""
    decode: Callable[[List[int]], str]
    """ Function to decode a list of token ids to a string"""
    encode: Callable[[str], List[int]]
    """ Function to encode a string to a list of token ids"""


def split_text_on_tokens(text: str, tokenizer: Tokenizer) -> List[str]:
    """Split incoming text and return chunks using tokenizer."""
    splits: List[str] = []
    input_ids = tokenizer.encode(text)
    print(input_ids)
    # start_idx = 0
    # cur_idx = min(start_idx + tokenizer.tokens_per_chunk, len(input_ids))
    # chunk_ids = input_ids[start_idx:cur_idx]
    # while start_idx < len(input_ids):
    #     splits.append(tokenizer.decode(chunk_ids))
    #     if cur_idx == len(input_ids):
    #         break
    #     start_idx += tokenizer.tokens_per_chunk - tokenizer.chunk_overlap
    #     cur_idx = min(start_idx + tokenizer.tokens_per_chunk, len(input_ids))
    #     chunk_ids = input_ids[start_idx:cur_idx]
    # return splits

class TokenTextSplitter(ChunkFunction):
    """
    A source function that splits input text into overlapping token chunks using
    a SentenceTransformer tokenizer.

    Input: str (the full input text)
    Output: List[str] (chunks of token-level text)

    Config:
        - model_name: Name of the SentenceTransformer model (default: all-mpnet-base-v2)
        - chunk_size: Number of tokens per chunk (default: model max length)
        - overlap: Number of overlapping tokens (default: 50)
    """

    def __init__(self, config):
        super().__init__()
        self.config = config["chunk"]
        self.model_name = self.config.get("model_name", "sentence-transformers/all-mpnet-base-v2")
        self.chunk_size = self.config.get("chunk_size", 128)  # Use model default if None
        self.overlap = self.config.get("overlap", 32)

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "Please install `sentence-transformers` with `pip install sentence-transformers`."
            )

        self.model = SentenceTransformer(self.model_name)
        self.tokenizer = self.model.tokenizer
        self.max_tokens = self.model.max_seq_length

        if self.chunk_size is None:
            self.chunk_size = self.max_tokens
        elif self.chunk_size > self.max_tokens:
            raise ValueError(
                f"chunk_size ({self.chunk_size}) exceeds model max_seq_length ({self.max_tokens})"
            )

        # Wrap encode/decode functions
        def encode_strip_special(text: str) -> List[int]:
            return self._encode(text)[1:-1]

        self.tokenizer_wrapper = Tokenizer(
            chunk_overlap=self.overlap,
            tokens_per_chunk=self.chunk_size,
            encode=encode_strip_special,
            decode=self.tokenizer.decode
        )

    def _encode(self, text: str) -> List[int]:
        return self.tokenizer.encode(
            text,
            max_length=2**32,
            truncation="do_not_truncate"
        )

    def _split_text(self, text: str) -> List[str]:
        """Split using tokenizer-based chunking"""
        return split_text_on_tokens(text=text, tokenizer=self.tokenizer_wrapper)

    def execute(self, data: Data[str]) -> Data[List[str]]:
        """Splits input text into token-based chunks"""
        content = data.data
        try:
            chunks = self._split_text(content)
            return Data(chunks)
        except Exception as e:
            self.logger.error(f"TokenTextSplitter error: {e}")
        return Data([])
