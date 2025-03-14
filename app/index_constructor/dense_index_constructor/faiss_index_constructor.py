import numpy as np
import faiss
import torch
import os
from tqdm import tqdm
from app.index_constructor.dense_index_constructor.dense_index_constructor import DenseIndexConstructor
from app.embedding_methods.encoder import Encoder
from app.embedding_methods.ste_encoder import STEncoder


class FaissIndexConstructor(DenseIndexConstructor):
    """A concrete class for building dense index using Faiss."""

    def __init__(
        self,
        corpus_path,
        save_dir,
        model_path,
        use_fp16,
        model_name,
        model_type="bert",
        pooling_method='mean',
        max_length=512,
        batch_size=256,
        faiss_type="Flat",
        faiss_gpu=False,
        corpus_name="corpus_test",
    ):
        super().__init__(
            corpus_path,
            save_dir,
            model_path,
            use_fp16,
            pooling_method,
            max_length,
            batch_size,
        )
        self.faiss_type = faiss_type
        self.faiss_gpu = faiss_gpu
        self.model_name = model_name
        self.model_type = model_type.lower()
        self.corpus_name = corpus_name

        # Initialize the encoder based on the model type
        if self.model_type == "sentence-transformer":
            self.encoder = STEncoder(
                model_name=self.model_name,
                model_path=self.model_path,
                max_length=self.max_length,
                use_fp16=self.use_fp16,
            )
        elif self.model_type == "bert":
            self.encoder = Encoder(
                model_name=self.model_name,
                model_path=self.model_path,
                pooling_method=self.pooling_method,
                max_length=self.max_length,
                use_fp16=self.use_fp16,
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    def encode_all(self):
        """Encode all documents using the specified encoder."""
        encode_data = [item["contents"] for item in self.corpus]
        if torch.cuda.device_count() > 1:
            print("Using multi-GPU for encoding!")
            self.batch_size = self.batch_size * torch.cuda.device_count()
            all_embeddings = self.encoder.multi_gpu_encode(encode_data, batch_size=self.batch_size, is_query=False)
        else:
            all_embeddings = self.encoder.encode(encode_data, batch_size=self.batch_size, is_query=False)

        return all_embeddings

    def save_index(self, all_embeddings, index_save_path):
        """Save the Faiss index to disk."""
        dim = all_embeddings.shape[-1]
        faiss_index = faiss.index_factory(dim, self.faiss_type, faiss.METRIC_INNER_PRODUCT)

        if self.faiss_gpu:
            co = faiss.GpuMultipleClonerOptions()
            co.useFloat16 = True
            co.shard = True
            faiss_index = faiss.index_cpu_to_all_gpus(faiss_index, co)
            if not faiss_index.is_trained:
                faiss_index.train(all_embeddings)
            faiss_index.add(all_embeddings)
            faiss_index = faiss.index_gpu_to_cpu(faiss_index)
        else:
            if not faiss_index.is_trained:
                faiss_index.train(all_embeddings)
            faiss_index.add(all_embeddings)

        faiss.write_index(faiss_index, index_save_path)

    def build_index(self):
        """Build the dense index using Faiss."""
        all_embeddings = self.encode_all()
        index_save_path = os.path.join(self.save_dir, f"{self.corpus_name}_{self.faiss_type}.index")
        self.save_index(all_embeddings, index_save_path)
        print(f"Faiss index saved to {index_save_path}")