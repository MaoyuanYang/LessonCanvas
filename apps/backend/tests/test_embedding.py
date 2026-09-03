"""F014 TS-001: embedding adapter contract (deterministic fake, guarded real)."""

import math

import pytest

from lessoncanvas.adapters import embedding as embedding_adapter_module
from lessoncanvas.adapters.embedding import (
    EMBEDDING_DIM,
    EmbeddingProviderError,
    FakeEmbeddingAdapter,
    FastEmbedAdapter,
    get_embedding_adapter,
)


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)


def test_fake_adapter_is_deterministic_and_dimensioned():
    adapter = FakeEmbeddingAdapter()
    first = adapter.embed_texts(["自然灾害与应对", "reading strategies"])[0]
    second = adapter.embed_texts(["自然灾害与应对", "other text"])[0]
    assert len(first) == EMBEDDING_DIM == 512
    assert first == second


def test_fake_adapter_distinguishes_texts_and_normalizes():
    adapter = FakeEmbeddingAdapter()
    chinese, english = adapter.embed_texts(["人与自然主题阅读", "the quick brown fox"])[0:2]
    assert chinese != english
    assert math.isclose(sum(value * value for value in chinese), 1.0, abs_tol=1e-9)
    assert math.isclose(sum(value * value for value in english), 1.0, abs_tol=1e-9)


def test_fake_adapter_empty_text_yields_zero_vector():
    (vector,) = FakeEmbeddingAdapter().embed_texts(["   "])
    assert vector == [0.0] * EMBEDDING_DIM


def test_fake_similarity_ranks_relevant_chunk_above_irrelevant():
    adapter = FakeEmbeddingAdapter()
    query, relevant, irrelevant = adapter.embed_texts(
        [
            "自然灾害 单元 阅读 与 表达 应对",
            "本单元围绕自然灾害展开，训练灾害应对的阅读与表达能力",
            "the quick brown fox jumps over the lazy dog far away",
        ]
    )
    assert cosine(query, relevant) > cosine(query, irrelevant)


def test_fake_similarity_disjoint_scripts_stay_below_threshold():
    adapter = FakeEmbeddingAdapter()
    chinese_query, latin_corpus = adapter.embed_texts(
        ["中华传统节日文化与习俗", "completely unrelated latin vocabulary only here"]
    )
    assert cosine(chinese_query, latin_corpus) < 0.1


def test_fastembed_import_failure_maps_to_provider_error(monkeypatch):
    def broken_import():
        raise ImportError("no fastembed in this environment")

    monkeypatch.setattr(embedding_adapter_module, "_import_fastembed", broken_import)
    adapter = FastEmbedAdapter()
    with pytest.raises(EmbeddingProviderError) as excinfo:
        adapter.embed_texts(["anything"])
    assert "embedding model unavailable" in str(excinfo.value)


def test_adapter_selection_follows_settings(monkeypatch):
    from lessoncanvas.settings import get_settings

    get_settings.cache_clear()
    get_embedding_adapter.cache_clear()
    monkeypatch.setenv("LESSONCANVAS_EMBEDDING_ADAPTER", "fastembed")
    try:
        assert isinstance(get_embedding_adapter(), FastEmbedAdapter)
    finally:
        monkeypatch.delenv("LESSONCANVAS_EMBEDDING_ADAPTER")
        get_settings.cache_clear()
        get_embedding_adapter.cache_clear()
    assert isinstance(get_embedding_adapter(), FakeEmbeddingAdapter)
