from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer


class CharacterSplitter:
    """
    A text splitter that divides text into overlapping chunks by characters.

    This is a pure algorithm class (L3) that doesn't depend on any SAGE operators.
    For use as a SAGE operator, wrap this class in sage-middleware.

    Config:
        - chunk_size: Number of characters per chunk (default: 512).
        - overlap: Number of overlapping characters (default: 128).
        - separator: Optional separator for splitting (default: None, splits by character).
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 128, separator: str | None = None):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separator = separator

    def split(self, text: str) -> list[str]:
        """
        Split text into chunks.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        if self.separator:
            return [chunk for chunk in text.split(self.separator) if chunk.strip()]

        # Character-level split
        tokens = list(text)
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


class SentenceTransformersTokenTextSplitter:
    """
    A text splitter that divides text into token-based chunks using SentenceTransformer.

    This is a pure algorithm class (L3) that doesn't depend on any SAGE operators.
    For use as a SAGE operator, wrap this class in sage-middleware.

    Config:
        - chunk_size: Number of tokens per chunk (default: 512).
        - chunk_overlap: Number of overlapping tokens (default: 50).
        - model_name: SentenceTransformer model name (default: "sentence-transformers/all-mpnet-base-v2").
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> None:
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

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

    def split(self, text: str) -> list[str]:
        """
        Split text into token-based chunks.

        Args:
            text: The text to split

        Returns:
            List of token-based text chunks
        """
        input_ids = self.tokenizer.encode(text, truncation=True, padding=False)
        splits: list[str] = []
        start_idx = 0

        while start_idx < len(input_ids):
            cur_idx = min(start_idx + self.chunk_size, len(input_ids))
            chunk_ids = input_ids[start_idx:cur_idx]
            splits.append(self.tokenizer.decode(chunk_ids, skip_special_tokens=True))
            start_idx = cur_idx - self.chunk_overlap
            if cur_idx == len(input_ids):
                break

        return splits
