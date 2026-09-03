"""F014 write-path embedding (Spec AC-001, ADR-0007).

Every chunk gets a vector or an explicit failure state with a recorded
reason at write time; embeddings are never computed at read time.
"""

import hashlib

from lessoncanvas.adapters.embedding import (
    EMBEDDING_DIM,
    EmbeddingProviderError,
    get_embedding_adapter,
)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(chunk_texts: list[str]) -> str:
    """Content identity of a source: the parsed text as the pipeline saw it
    (chunk texts joined in position order)."""

    return hashlib.sha256("\n".join(chunk_texts).encode("utf-8")).hexdigest()


def embed_chunks(texts: list[str]) -> list[dict]:
    """Embed a batch, isolating provider failure into per-chunk states.

    Returns one {vector, status, error} per input; a provider failure marks
    every chunk in the batch failed with the reason (Spec D3: exclude-with-
    disclosure later; re-parse re-attempts).
    """

    if not texts:
        return []
    try:
        vectors = get_embedding_adapter().embed_texts(texts)
    except EmbeddingProviderError as error:
        reason = str(error)
        return [
            {"vector": None, "status": "failed", "error": reason} for _ in texts
        ]
    results = []
    for vector in vectors:
        if len(vector) != EMBEDDING_DIM:
            results.append(
                {
                    "vector": None,
                    "status": "failed",
                    "error": f"embedding dimension mismatch: {len(vector)}",
                }
            )
            continue
        results.append({"vector": vector, "status": "ok", "error": None})
    return results
