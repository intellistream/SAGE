import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer


async def instructor_embed(
    texts: list[str], model: str = "hkunlp/instructor-large"
) -> NDArray[np.float32]:  # type: ignore[return]
    _model = SentenceTransformer(model)
    return _model.encode(texts)  # type: ignore[return-value]
