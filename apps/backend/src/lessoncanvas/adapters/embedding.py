"""Thin embedding adapter (F014, ADR-0007).

One embedding model behind one adapter. The deterministic fake keeps CI and
E2E free of real weights; the fastembed implementation runs bge-small-zh-v1.5
in-process in deployed environments. A model or dimension change requires a
superseding ADR.
"""

import hashlib
import math
from functools import lru_cache

from lessoncanvas.settings import get_settings

EMBEDDING_DIM = 512


class EmbeddingProviderError(Exception):
    """Embedding computation failed; callers record the message per chunk."""


def _ngrams(value: str) -> list[str]:
    """Character 1- and 2-grams generated within whitespace-separated tokens.

    Grams never span (or consist of) whitespace, so two texts sharing no
    lexical material stay near-orthogonal apart from bounded hash-bucket
    noise — that bound is what the similarity threshold rides on.
    """

    grams: list[str] = []
    for token in value.lower().split():
        grams.extend(token)
        grams.extend(token[i : i + 2] for i in range(len(token) - 1))
    return grams


def _dim_index(gram: str) -> int:
    digest = hashlib.md5(gram.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % EMBEDDING_DIM


class FakeEmbeddingAdapter:
    """Deterministic hashed bag-of-n-grams vectors for tests and E2E.

    Cosine similarity tracks lexical overlap (character 1- and 2-grams), so
    constructed corpora exhibit the ranking behavior tests assert without
    any model weights; identical inputs always produce identical vectors.
    """

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for gram in _ngrams(text):
            vector[_dim_index(gram)] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


def _import_fastembed():
    from fastembed import TextEmbedding

    return TextEmbedding


class FastEmbedAdapter:
    """In-process fastembed provider (deployed environments, ADR-0007).

    The model loads once on first use; any import/load/inference failure
    surfaces as EmbeddingProviderError with the underlying reason so the
    write path can record per-chunk failure states.
    """

    def __init__(self) -> None:
        self._model = None

    def _load(self):
        settings = get_settings()
        try:
            text_embedding = _import_fastembed()
            self._model = text_embedding(model_name=settings.embedding_model)
        except Exception as error:
            raise EmbeddingProviderError(
                f"embedding model unavailable: {error}"
            ) from error

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            self._load()
        try:
            vectors = [vector.tolist() for vector in self._model.embed(texts)]
        except Exception as error:
            raise EmbeddingProviderError(f"embedding inference failed: {error}") from error
        settings = get_settings()
        for vector in vectors:
            if len(vector) != settings.embedding_dim:
                raise EmbeddingProviderError(
                    f"embedding dimension mismatch: got {len(vector)}, "
                    f"expected {settings.embedding_dim}"
                )
        return vectors


@lru_cache
def get_embedding_adapter():
    if get_settings().embedding_adapter == "fastembed":
        return FastEmbedAdapter()
    return FakeEmbeddingAdapter()
