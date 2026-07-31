from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=4)
def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name)