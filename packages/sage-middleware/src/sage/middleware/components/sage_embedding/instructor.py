import numpy as np
from sentence_transformers import SentenceTransformer


async def instructor_embed(
    texts: [str], model: str = "hkunlp/instructor-large"
) -> [np.array]:
    _model = SentenceTransformer(model)
    return _model.encode(texts)
