"""F014 vector retrieval over embedded source chunks (Spec AC-002, D3/D4/D7).

Similarity top-k with rank-order budget trim replaces full-corpus truncation.
Chunks without usable embeddings are excluded with explicit disclosure
(count + reasons); zero relevance surfaces as an honest ungrounded state.
Retrieved text always leaves this module as plain data for labeled user
payloads — never as prompt authority.
"""

from sqlalchemy import text as sql_text

from lessoncanvas.adapters.embedding import (
    EmbeddingProviderError,
    get_embedding_adapter,
)
from lessoncanvas.settings import get_settings


def retrieve(
    session,
    project_id,
    query: str,
    *,
    top_k: int | None = None,
    budget_chars: int | None = None,
) -> dict:
    """Retrieve the most similar ready-source chunks for one query.

    Deterministic order: similarity desc, position asc, chunk id asc.
    Returns a self-describing result dict consumed by call sites, trace
    events, and the citation builder — cited chunks always come from the
    captured hit list of the same retrieval.
    """

    settings = get_settings()
    top_k = top_k or settings.retrieval_top_k
    budget_chars = budget_chars or settings.retrieval_budget_chars

    excluded = session.execute(
        sql_text(
            "SELECT count(*) AS n, coalesce(array_agg(DISTINCT left(embedding_error, 120)) "
            "FILTER (WHERE embedding_error IS NOT NULL), ARRAY[]::text[]) AS reasons "
            "FROM source_chunks c JOIN sources s ON s.id = c.source_id "
            "WHERE s.project_id = :pid AND s.status = 'ready' "
            "AND (c.embedding_status <> 'ok' OR c.embedding IS NULL)"
        ),
        {"pid": str(project_id)},
    ).mappings().first()

    result = {
        "query": query,
        "hits": [],
        "excluded_count": int(excluded["n"]) if excluded else 0,
        "excluded_reasons": (list(excluded["reasons"] or [])[:5]) if excluded else [],
        "budget_chars": budget_chars,
        "used_chars": 0,
        "grounding_state": "none",
        "error": None,
    }
    if not query.strip():
        return result

    try:
        (query_vector,) = get_embedding_adapter().embed_texts([query])
    except EmbeddingProviderError as error:
        result["error"] = f"query embedding failed: {error}"
        return result

    rows = session.execute(
        sql_text(
            "SELECT c.id::text AS chunk_id, c.source_id::text AS source_id, "
            "s.filename, c.position, c.text, c.text_sha256, "
            "1 - (c.embedding <=> (:q)::vector) AS similarity "
            "FROM source_chunks c JOIN sources s ON s.id = c.source_id "
            "WHERE s.project_id = :pid AND s.status = 'ready' "
            "AND c.embedding_status = 'ok' AND c.embedding IS NOT NULL "
            "ORDER BY c.embedding <=> (:q)::vector, c.position, c.id "
            "LIMIT :limit"
        ),
        {
            "pid": str(project_id),
            "q": "[" + ", ".join(repr(float(v)) for v in query_vector) + "]",
            "limit": top_k * 4,
        },
    ).mappings().all()

    candidates = [
        row for row in rows if float(row["similarity"]) >= settings.retrieval_similarity_threshold
    ][:top_k]

    hits = []
    used = 0
    for row in candidates:
        separator = 1 if used else 0
        remaining = budget_chars - used - separator
        if remaining <= 0:
            break  # budget exhausted; remaining lower-ranked hits drop
        chunk_text = row["text"][:remaining]
        if not chunk_text.strip():
            break
        used += separator + len(chunk_text)
        hits.append(
            {
                "chunk_id": row["chunk_id"],
                "source_id": row["source_id"],
                "filename": row["filename"],
                "position": int(row["position"]),
                "text": chunk_text,
                "text_sha256": row["text_sha256"],
                "similarity": round(float(row["similarity"]), 4),
            }
        )

    result["hits"] = hits
    result["used_chars"] = min(used, budget_chars)
    if hits:
        result["grounding_state"] = "retrieved"
    return result


def corpus_excerpt(result: dict) -> str:
    """Rank-ordered retrieved text for labeled user payloads.

    Kept as the payload key the planning flow already exposes to the model
    (`corpus_excerpt`); content is now retrieval-selected, never a
    full-corpus truncation.
    """

    return "\n".join(hit["text"] for hit in result["hits"])


def retrieved_source_entries(result: dict) -> list[dict]:
    """Compact provenance list for payloads and citations."""

    return [
        {
            "source_id": hit["source_id"],
            "filename": hit["filename"],
            "position": hit["position"],
            "similarity": hit["similarity"],
        }
        for hit in result["hits"]
    ]


def citation_objects(result: dict, limit: int | None = None) -> list[dict]:
    """Server-injected chunk citations from one retrieval's captured hits.

    Every citation binds to this retrieval's own hit list (Spec AC-003);
    callers never trust citations arriving inside model payloads.
    """

    settings = get_settings()
    hits = result["hits"][: limit or settings.citation_top_chunks]
    return [
        {
            "type": "source",
            "source_id": hit["source_id"],
            "filename": hit["filename"],
            "chunk_position": hit["position"],
            "text_sha256": hit["text_sha256"],
            "excerpt": hit["text"][: settings.citation_excerpt_chars],
        }
        for hit in hits
    ]


def trace_payload(result: dict, *, family: str, purpose: str, lesson_index: int | None = None,
                  item_kind: str | None = None, item_id: str | None = None) -> dict:
    """Trace-event payload for one retrieval (Spec AC-002)."""

    payload = {
        "family": family,
        "purpose": purpose,
        "query": result["query"],
        "hits": retrieved_source_entries(result),
        "hit_count": len(result["hits"]),
        "excluded_count": result["excluded_count"],
        "excluded_reasons": result["excluded_reasons"],
        "budget_chars": result["budget_chars"],
        "used_chars": result["used_chars"],
        "grounding_state": result["grounding_state"],
    }
    if result["error"]:
        payload["error"] = result["error"]
    if lesson_index is not None:
        payload["lesson_index"] = lesson_index
    if item_kind is not None:
        payload["item_kind"] = item_kind
        payload["item_id"] = item_id
    return payload
