"""
Embedding methods and models for SAGE middleware.
"""

from .embedding_api import apply_embedding_model
from .embedding_model import EmbeddingModel

# Import specific embedding implementations
from . import hf
from . import ollama
from . import siliconcloud
from . import openai
from . import bedrock
from . import zhipu
from . import mockembedder
from . import _cohere
from . import nvidia_openai
from . import lollms
from . import jina

__all__ = [
    'apply_embedding_model',
    'EmbeddingModel',
    'hf',
    'ollama', 
    'siliconcloud',
    'openai',
    'bedrock',
    'zhipu',
    'mockembedder',
    '_cohere',
    'nvidia_openai',
    'lollms',
    'jina'
]
