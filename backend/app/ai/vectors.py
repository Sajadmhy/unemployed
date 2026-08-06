"""Cosine similarity over stored embeddings, in numpy.

This used to be pgvector's `<=>` operator inside an ORDER BY. It moved into
Python when the database became SQLite, and the move costs nothing here: both
call sites rank the *knowledge base*, which is one person's career — tens of
rows, not millions. The original schema said as much, declining to build a
vector index because "with a personal KB (tens of chunks) an exact scan is
fine". An exact scan is exactly what this is; it just happens in numpy now.

The scoring engine (`app.ai.match`) already worked this way for the same
reason, so this is one shared implementation rather than a second one.

Every vector the app stores is L2-normalised at write time by
`app.ai.embeddings`, which is what lets similarity be a plain dot product.
"""
import numpy as np

# Vectors are unit-length, so a dot product is already the cosine similarity and
# cosine distance is 1 - that. Keeping both makes call sites read the way they
# did when the database was doing this.


def similarities(query: list[float], vectors: list[list[float]]) -> np.ndarray:
    """Cosine similarity of `query` against each row of `vectors`."""
    if not vectors:
        return np.empty(0, dtype=np.float32)
    matrix = np.asarray(vectors, dtype=np.float32)
    return matrix @ np.asarray(query, dtype=np.float32)


def rank(query: list[float], items: list, embedding_of=lambda item: item.embedding):
    """`items` ordered by similarity to `query`, closest first.

    Returns `(item, similarity)` pairs so a caller that needs to show the score -
    the KB search endpoint does - gets it without recomputing.
    """
    if not items:
        return []
    sims = similarities(query, [embedding_of(item) for item in items])
    order = np.argsort(sims)[::-1]
    return [(items[i], float(sims[i])) for i in order]
