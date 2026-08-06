"""Embedding service: text -> 384-dim vector, using ONE model everywhere.

Two subtleties that matter for retrieval quality with bge-small-en-v1.5:

1. Asymmetry: the model was trained so a short *query* gets a small instruction
   prefix, while stored *passages* do not. Using the right one on each side
   measurably improves retrieval. So we expose embed_query vs embed_passage.
2. Normalisation: we L2-normalise vectors so cosine similarity behaves cleanly —
   for unit vectors it is just a dot product, which is what makes the ranking in
   `app.ai.vectors` and the scoring in `app.ai.match` a single matrix multiply.

The model (~130 MB) downloads once on first use and is cached on disk.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings

# Recommended query instruction for bge-*-en-v1.5 retrieval.
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""
    return SentenceTransformer(settings.embedding_model)


def embed_passage(text: str) -> list[float]:
    """Embed a stored document (a KB chunk). No instruction prefix."""
    vec = _model().encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a search query (or a job description). With instruction prefix."""
    vec = _model().encode(_QUERY_INSTRUCTION + text, normalize_embeddings=True)
    return vec.tolist()
