# src/core/embedding/text_preprocessor.py
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel


class TextPreprocessor:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.fixed_dimension = 128  # Fixed dimension for the embedding vectors

    def generate_embedding_with_sliding_window(self, text: str, max_length=512, stride=256):
        """
        Generate an embedding for the given text using a sliding window approach.
        """
        # Tokenize the input text with sliding windows
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            stride=stride,
            return_overflowing_tokens=True,
            padding="max_length",
            return_tensors="pt"
        )

        embeddings = []
        with torch.no_grad():
            for input_ids in inputs["input_ids"]:
                # Forward pass through the model
                output = self.model(input_ids.unsqueeze(0))

                # Mean pooling to obtain the embedding
                embedding = output.last_hidden_state.mean(dim=1).squeeze()
                embeddings.append(embedding)

        # Aggregate embeddings (e.g., mean pooling across all windows)
        aggregated_embedding = torch.stack(embeddings).mean(dim=0)

        # Adjust the aggregated embedding to match the fixed dimension
        if aggregated_embedding.size(0) > self.fixed_dimension:
            aggregated_embedding = aggregated_embedding[:self.fixed_dimension]  # Truncate if larger
        elif aggregated_embedding.size(0) < self.fixed_dimension:
            # Pad with zeros if smaller
            padding = torch.zeros(
                self.fixed_dimension - aggregated_embedding.size(0), device=aggregated_embedding.device
            )
            aggregated_embedding = torch.cat((aggregated_embedding, padding))

        # Return the embedding as a float32 PyTorch Tensor
        return aggregated_embedding.to(dtype=torch.float32)

    def generate_embedding(self, text: str):
        """
        Generate a fixed-dimension embedding for the given text using the model.
        """
        # Tokenize the input text for the model
        inputs = self.tokenizer(text, return_tensors='pt')

        # Generate embeddings using the model
        with torch.no_grad():
            outputs = self.model(**inputs)

            # Pooling strategy (mean pooling)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()

        # Ensure the embedding has the correct fixed dimension
        if embedding.size(0) > self.fixed_dimension:
            embedding = embedding[:self.fixed_dimension]  # Truncate if larger
        elif embedding.size(0) < self.fixed_dimension:
            # Pad with zeros if smaller
            padding = torch.zeros(self.fixed_dimension - embedding.size(0), device=embedding.device)
            embedding = torch.cat((embedding, padding))

        # Return the embedding as a float32 PyTorch Tensor
        return embedding.to(dtype=torch.float32)

