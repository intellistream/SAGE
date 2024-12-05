# src/core/embedding/text_preprocessor.py
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel


class TextPreprocessor:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.fixed_dimension = 128  # Fixed dimension for the embedding vectors

    def generate_embedding(self, text: str):
        inputs = self.tokenizer(text, return_tensors='pt')
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Pooling strategy (mean pooling)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
        # Ensure the embedding has the correct fixed dimension
        if embedding.size(0) > self.fixed_dimension:
            embedding = embedding[:self.fixed_dimension]  # Truncate if larger
        elif embedding.size(0) < self.fixed_dimension:
            padding = torch.zeros(self.fixed_dimension - embedding.size(0))
            embedding = torch.cat((embedding, padding))  # Pad if smaller
        return embedding.numpy().astype(np.float32)  # Convert to float32
