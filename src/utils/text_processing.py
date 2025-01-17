import torch
import numpy as np
import logging
from src.core.embedding.text_preprocessor import TextPreprocessor

def process_text_to_embedding(text, max_length=512, stride=256):
    """
    Process a long text into a single embedding using chunking and aggregation.
    :param text: Input text to process.
    :param max_length: Maximum token length for each chunk.
    :param stride: Overlap between consecutive chunks.
    :return: Aggregated embedding as a PyTorch tensor.
    """
    logger = logging.getLogger(__name__)
    text_preprocessor = TextPreprocessor()

    try:
        """
            待修复，最大仅支持512个token不太够用!！
        """
        # Tokenize the text to check its length
        tokens = text_preprocessor.tokenizer.tokenize(text)
        if len(tokens) > max_length:
            logger.warning(f"Input text length ({len(tokens)}) exceeds model's max length ({max_length}). Truncating text.")
            text = text_preprocessor.tokenizer.decode(text_preprocessor.tokenizer.encode(text, max_length=max_length, truncation=True))

        # Tokenize with truncation, stride, and overlapping chunks
        tokens = text_preprocessor.tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            stride=stride,
            return_overflowing_tokens=True,
            padding="max_length",
            return_tensors="pt"
        )

        embeddings = []
        for chunk in tokens["input_ids"]:
            # Generate embedding for each chunk
            chunk_text = text_preprocessor.tokenizer.decode(chunk, skip_special_tokens=True)
            embedding = text_preprocessor.generate_embedding(chunk_text)  # Returns a tensor
            embeddings.append(embedding)

        # Aggregate embeddings (mean pooling)
        if embeddings:
            aggregated_embedding = torch.stack(embeddings).mean(dim=0)
            logger.info(f"Processed text into embedding of shape: {aggregated_embedding.shape}")
            return aggregated_embedding.to(dtype=torch.float32)  # Ensure float32 tensor
        else:
            raise ValueError("No embeddings generated. The input text might be empty.")
    except Exception as e:
        logger.error(f"Error processing text to embedding: {str(e)}")
        raise RuntimeError(f"Text processing failed: {str(e)}")


def process_session_text_to_embedding(session_texts):
    """
    Process session texts into a single embedding using parallel processing.
    """
    # TODO: can be parallelized for optimization
    session_embedding = torch.mean(torch.stack([process_text_to_embedding(text) for text in session_texts]), dim=0)
    return session_embedding