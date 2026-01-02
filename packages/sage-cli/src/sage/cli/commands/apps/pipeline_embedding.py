"""
Enhanced Pipeline Builder Templates with EmbeddingService Integration

这个模块提供增强的 pipeline 模板，完全集成了新的 EmbeddingService。
"""

from typing import Any


class EmbeddingPipelineTemplates:
    """Embedding-focused pipeline templates using EmbeddingService."""

    @staticmethod
    def rag_with_embedding_service(
        embedding_method: str = "hf",
        embedding_model: str | None = None,
        use_vllm: bool = False,
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """RAG Pipeline with dedicated EmbeddingService.

        Args:
            embedding_method: Embedding method (hf, openai, jina, vllm, etc.)
            embedding_model: Specific embedding model name
            use_vllm: Whether to use vLLM backend for embedding
            llm_model: LLM model for generation
            **kwargs: Additional config options

        Returns:
            Complete pipeline configuration
        """
        # Default models for each method
        default_models = {
            "hf": "BAAI/bge-small-zh-v1.5",
            "openai": "text-embedding-3-small",
            "jina": "jina-embeddings-v3",
            "zhipu": "embedding-3",
            "vllm": "BAAI/bge-base-en-v1.5",
        }

        embedding_model = embedding_model or default_models.get(
            embedding_method, "BAAI/bge-small-zh-v1.5"
        )

        config = {
            "pipeline": {
                "name": "rag_with_embedding_service",
                "description": f"RAG pipeline with {embedding_method} embedding service",
                "version": "2.0.0",
                "type": "local",
            },
            "services": {},
        }

        # Configure embedding service
        if use_vllm or embedding_method == "vllm":
            # Use vLLM backend
            config["services"]["vllm"] = {  # type: ignore[index]
                "class": "sage.llm.VLLMService",
                "config": {
                    "model_id": llm_model,
                    "embedding_model_id": embedding_model,
                    "auto_download": True,
                    "engine": {
                        "dtype": "auto",
                        "tensor_parallel_size": 1,
                        "gpu_memory_utilization": 0.9,
                    },
                },
            }

            config["services"]["embedding"] = {  # type: ignore[index]
                "class": "sage.common.components.sage_embedding.EmbeddingService",
                "config": {
                    "method": "vllm",
                    "vllm_service_name": "vllm",
                    "batch_size": 128,
                    "normalize": True,
                    "cache_enabled": True,
                    "cache_size": 10000,
                },
            }
        else:
            # Use standard embedding method
            embedding_config = {
                "method": embedding_method,
                "model": embedding_model,
                "batch_size": 32,
                "normalize": True,
                "cache_enabled": kwargs.get("cache_enabled", True),
                "cache_size": kwargs.get("cache_size", 5000),
            }

            # Add API key if needed
            if embedding_method in ["openai", "jina", "zhipu", "cohere"]:
                embedding_config["api_key"] = f"${{{embedding_method.upper()}_API_KEY}}"

            config["services"]["embedding"] = {  # type: ignore[index]
                "class": "sage.common.components.sage_embedding.EmbeddingService",
                "config": embedding_config,
            }

        # Add vector database service
        config["services"]["vector_db"] = {  # type: ignore[index]
            "class": "sage.middleware.components.sage_db.service.SageDBService",
            "config": {
                "dimension": kwargs.get("dimension", 768),
                "index_type": kwargs.get("index_type", "AUTO"),
            },
        }

        # Add operators
        config["operators"] = [  # type: ignore[assignment]
            {
                "name": "load_query",
                "type": "input_operator",
                "config": {"source": "stdin"},
            },
            {
                "name": "embed_query",
                "type": "embedding_operator",
                "config": {
                    "embedding_service": "embedding",
                    "input_field": "query",
                    "output_field": "query_vector",
                },
            },
            {
                "name": "retrieve_documents",
                "type": "vector_search_operator",
                "config": {
                    "db_service": "vector_db",
                    "query_field": "query_vector",
                    "top_k": kwargs.get("top_k", 5),
                },
            },
            {
                "name": "generate_answer",
                "type": "llm_generate_operator",
                "config": {
                    "llm_service": "vllm" if use_vllm else "llm",
                    "prompt_template": """Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:""",
                    "max_tokens": 512,
                },
            },
        ]

        return config

    @staticmethod
    def knowledge_base_builder(
        embedding_method: str = "hf",
        embedding_model: str | None = None,
        use_vllm: bool = False,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs,
    ) -> dict[str, Any]:
        """Knowledge base building pipeline with EmbeddingService.

        Args:
            embedding_method: Embedding method
            embedding_model: Model name
            use_vllm: Use vLLM for high-throughput processing
            chunk_size: Text chunk size
            chunk_overlap: Overlap between chunks
        """
        default_models = {
            "hf": "BAAI/bge-base-zh-v1.5",
            "openai": "text-embedding-3-large",
            "vllm": "BAAI/bge-large-en-v1.5",
        }

        embedding_model = embedding_model or default_models.get(embedding_method)

        config = {
            "pipeline": {
                "name": "knowledge_base_builder",
                "description": "Build knowledge base with embedding service",
                "version": "2.0.0",
                "type": "local",
            },
            "services": {},
        }

        # Configure services based on method
        if use_vllm or embedding_method == "vllm":
            config["services"]["vllm"] = {  # type: ignore[index]
                "class": "sage.llm.VLLMService",
                "config": {
                    "model_id": embedding_model,
                    "embedding_model_id": embedding_model,
                    "auto_download": True,
                },
            }

            config["services"]["embedding"] = {  # type: ignore[index]
                "class": "sage.common.components.sage_embedding.EmbeddingService",
                "config": {
                    "method": "vllm",
                    "vllm_service_name": "vllm",
                    "batch_size": 256,  # Large batch for indexing
                    "normalize": True,
                    "cache_enabled": False,  # No cache needed for one-time indexing
                },
            }
        else:
            embedding_config = {
                "method": embedding_method,
                "model": embedding_model,
                "batch_size": 64,
                "normalize": True,
                "cache_enabled": False,
            }

            if embedding_method in ["openai", "jina", "zhipu"]:
                embedding_config["api_key"] = f"${{{embedding_method.upper()}_API_KEY}}"

            config["services"]["embedding"] = {  # type: ignore[index]
                "class": "sage.common.components.sage_embedding.EmbeddingService",
                "config": embedding_config,
            }

        config["services"]["vector_db"] = {  # type: ignore[index]
            "class": "sage.middleware.components.sage_db.service.SageDBService",
            "config": {
                "dimension": kwargs.get("dimension", 768),
                "index_type": "HNSW",  # Better for large-scale indexing
            },
        }

        config["operators"] = [  # type: ignore[assignment]
            {
                "name": "load_documents",
                "type": "document_loader",
                "config": {
                    "source_path": kwargs.get("source_path", "data/documents/"),
                    "file_types": ["txt", "md", "pdf", "docx"],
                },
            },
            {
                "name": "chunk_documents",
                "type": "text_chunker",
                "config": {
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "strategy": "sentence_aware",
                },
            },
            {
                "name": "embed_chunks",
                "type": "batch_embedding_operator",
                "config": {
                    "embedding_service": "embedding",
                    "input_field": "chunks",
                    "output_field": "embeddings",
                    "batch_size": 256,
                    "show_progress": True,
                },
            },
            {
                "name": "index_vectors",
                "type": "vector_indexing_operator",
                "config": {
                    "db_service": "vector_db",
                    "vector_field": "embeddings",
                    "metadata_fields": ["doc_id", "chunk_id", "text", "source"],
                    "show_progress": True,
                },
            },
            {
                "name": "save_index",
                "type": "index_saver",
                "config": {"output_path": kwargs.get("output_path", "data/index/")},
            },
        ]

        return config

    @staticmethod
    def hybrid_search_pipeline(
        dense_method: str = "hf",
        sparse_method: str = "bm25s",
        dense_model: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Hybrid search pipeline with dense + sparse embeddings."""
        config = {
            "pipeline": {
                "name": "hybrid_search",
                "description": "Hybrid search with dense and sparse embeddings",
                "version": "2.0.0",
                "type": "local",
            },
            "services": {
                # Dense embedding service
                "embedding_dense": {
                    "class": "sage.common.components.sage_embedding.EmbeddingService",
                    "config": {
                        "method": dense_method,
                        "model": dense_model or "BAAI/bge-base-en-v1.5",
                        "batch_size": 32,
                        "normalize": True,
                        "cache_enabled": True,
                    },
                },
                # Sparse embedding service
                "embedding_sparse": {
                    "class": "sage.common.components.sage_embedding.EmbeddingService",
                    "config": {
                        "method": sparse_method,
                        "normalize": False,
                        "cache_enabled": True,
                    },
                },
                # Two vector databases
                "vector_db_dense": {
                    "class": "sage.middleware.components.sage_db.service.SageDBService",
                    "config": {"dimension": 768, "index_type": "HNSW"},
                },
                "vector_db_sparse": {
                    "class": "sage.middleware.components.sage_db.service.SageDBService",
                    "config": {"dimension": 10000, "index_type": "FLAT"},
                },
            },
            "operators": [
                {
                    "name": "embed_dense",
                    "type": "embedding_operator",
                    "config": {
                        "embedding_service": "embedding_dense",
                        "input_field": "query",
                        "output_field": "dense_vector",
                    },
                },
                {
                    "name": "embed_sparse",
                    "type": "embedding_operator",
                    "config": {
                        "embedding_service": "embedding_sparse",
                        "input_field": "query",
                        "output_field": "sparse_vector",
                    },
                },
                {
                    "name": "search_dense",
                    "type": "vector_search_operator",
                    "config": {
                        "db_service": "vector_db_dense",
                        "query_field": "dense_vector",
                        "top_k": 20,
                        "output_field": "dense_results",
                    },
                },
                {
                    "name": "search_sparse",
                    "type": "vector_search_operator",
                    "config": {
                        "db_service": "vector_db_sparse",
                        "query_field": "sparse_vector",
                        "top_k": 20,
                        "output_field": "sparse_results",
                    },
                },
                {
                    "name": "fuse_results",
                    "type": "hybrid_fusion_operator",
                    "config": {
                        "fusion_method": "reciprocal_rank",
                        "weights": {
                            "dense": kwargs.get("dense_weight", 0.6),
                            "sparse": kwargs.get("sparse_weight", 0.4),
                        },
                        "final_top_k": kwargs.get("top_k", 5),
                    },
                },
            ],
        }

        return config

    @staticmethod
    def multi_embedding_strategy(
        query_method: str = "hf",
        doc_method: str = "openai",
        batch_method: str = "vllm",
        **kwargs,
    ) -> dict[str, Any]:
        """Multi-embedding strategy: different methods for different use cases."""
        config = {
            "pipeline": {
                "name": "multi_embedding_strategy",
                "description": "Different embedding methods for different scenarios",
                "version": "2.0.0",
                "type": "local",
            },
            "services": {
                # Fast local for queries
                "embedding_fast": {
                    "class": "sage.common.components.sage_embedding.EmbeddingService",
                    "config": {
                        "method": query_method,
                        "model": "BAAI/bge-small-zh-v1.5",
                        "batch_size": 16,
                        "normalize": True,
                        "cache_enabled": True,
                        "cache_size": 10000,
                    },
                },
                # High quality for important documents
                "embedding_quality": {
                    "class": "sage.common.components.sage_embedding.EmbeddingService",
                    "config": {
                        "method": doc_method,
                        "model": "text-embedding-3-large",
                        "api_key": "${OPENAI_API_KEY}",
                        "batch_size": 100,
                        "normalize": True,
                    },
                },
                # vLLM for batch processing
                "vllm": {
                    "class": "sage.llm.VLLMService",
                    "config": {
                        "model_id": "BAAI/bge-large-en-v1.5",
                        "embedding_model_id": "BAAI/bge-large-en-v1.5",
                    },
                },
                "embedding_batch": {
                    "class": "sage.common.components.sage_embedding.EmbeddingService",
                    "config": {
                        "method": "vllm",
                        "vllm_service_name": "vllm",
                        "batch_size": 512,
                        "normalize": True,
                    },
                },
            },
            "operators": [
                {
                    "name": "route_by_size",
                    "type": "router_operator",
                    "config": {
                        "routes": [
                            {
                                "condition": "len(payload['texts']) < 10",
                                "embedding_service": "embedding_fast",
                            },
                            {
                                "condition": "len(payload['texts']) > 1000",
                                "embedding_service": "embedding_batch",
                            },
                            {
                                "condition": "payload.get('high_quality', False)",
                                "embedding_service": "embedding_quality",
                            },
                        ],
                        "default_service": "embedding_fast",
                    },
                }
            ],
        }

        return config


def generate_embedding_pipeline(use_case: str, **kwargs) -> dict[str, Any]:
    """Generate embedding pipeline based on use case.

    Args:
        use_case: One of: rag, knowledge_base, hybrid_search, multi_strategy
        **kwargs: Additional configuration options

    Returns:
        Complete pipeline configuration
    """
    templates = EmbeddingPipelineTemplates()

    use_case_map = {
        "rag": templates.rag_with_embedding_service,
        "knowledge_base": templates.knowledge_base_builder,
        "hybrid_search": templates.hybrid_search_pipeline,
        "multi_strategy": templates.multi_embedding_strategy,
    }

    if use_case not in use_case_map:
        raise ValueError(
            f"Unknown use case: {use_case}. Available: {', '.join(use_case_map.keys())}"
        )

    return use_case_map[use_case](**kwargs)  # type: ignore[operator]


__all__ = [
    "EmbeddingPipelineTemplates",
    "generate_embedding_pipeline",
]
