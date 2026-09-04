"""Pydantic projections for generation run state and the SSE event envelope.

These schemas are the frozen F003 contract between API/SSE and the Web client
(Spec API Behavior; ux-ui.md Frontend/Backend Contract).
"""

import uuid

from pydantic import BaseModel

TERMINAL_RUN_STATUSES = ("complete", "terminal_failure")
RESUMABLE_RUN_STATUSES = ("partial_failure", "capped_failure")
ACTIVE_RUN_STATUSES = ("queued", "generating", "validating")


class RetainedArtifactOut(BaseModel):
    id: str
    lesson_index: int
    source_brief_version: int | None = None
    source_blueprint_version: int | None = None
    source_run_id: str
    checksum: str | None = None
    download_available: bool = True


class CitationOut(BaseModel):
    """F014 U1: server-injected chunk citation (source + position + hash)."""

    type: str
    source_id: str | None = None
    filename: str | None = None
    chunk_position: int | None = None
    text_sha256: str | None = None
    excerpt: str | None = None
    section_id: str | None = None
    snapshot_version: str | None = None


class ReviewFindingOut(BaseModel):
    """F016 U3: one normalized review finding (latest round)."""

    dimension: str
    severity: str
    message: str
    reference: str | None = None


def _review_findings_of(artifact) -> list[ReviewFindingOut]:
    import json

    if not getattr(artifact, "review_findings_json", None):
        return []
    try:
        rows = json.loads(artifact.review_findings_json)
    except json.JSONDecodeError:
        return []
    return [ReviewFindingOut(**item) for item in rows if isinstance(item, dict)]


def _design_of(artifact) -> dict | None:
    import json

    if not getattr(artifact, "design_json", None):
        return None
    try:
        return json.loads(artifact.design_json)
    except json.JSONDecodeError:
        return None


class LessonArtifactOut(BaseModel):
    id: str
    lesson_index: int
    status: str
    language_mode: str
    failure_reason: str | None = None
    retry_count: int
    download_url: str | None = None
    # F014 U1/U2: chunk citations and the honest per-lesson grounding state.
    citations: list[CitationOut] = []
    grounding_state: str | None = None
    # F016 D4/U3: the validated design intermediate (plans only, read-only)
    # and the latest review round's findings/outcome (all families).
    design: dict | None = None
    review_findings: list[ReviewFindingOut] = []
    review_rounds: int = 0
    review_outcome: str | None = None


class GenerationSnapshot(BaseModel):
    run_id: str
    status: str
    brief_version: int
    blueprint_version: int
    language_mode: str
    scope_lesson_indexes: list[int] | None = None
    retained_artifacts: list[RetainedArtifactOut] = []
    model_calls: int
    model_call_cap: int
    artifacts: list[LessonArtifactOut]
    complete_count: int
    total_count: int


class DeckArtifactOut(BaseModel):
    id: str
    lesson_index: int
    status: str
    language_mode: str
    slide_count: int | None = None
    failure_reason: str | None = None
    retry_count: int
    download_url: str | None = None
    citations: list[CitationOut] = []
    grounding_state: str | None = None
    review_findings: list[ReviewFindingOut] = []
    review_rounds: int = 0
    review_outcome: str | None = None


class DeckGenerationSnapshot(BaseModel):
    run_id: str
    status: str
    brief_version: int
    blueprint_version: int
    language_mode: str
    scope_lesson_indexes: list[int] | None = None
    retained_artifacts: list[RetainedArtifactOut] = []
    model_calls: int
    model_call_cap: int
    artifacts: list[DeckArtifactOut]
    complete_count: int
    total_count: int


class ExerciseArtifactOut(BaseModel):
    id: str
    lesson_index: int
    status: str
    language_mode: str
    category_count: int | None = None
    item_count: int | None = None
    failure_reason: str | None = None
    retry_count: int
    exercise_download_url: str | None = None
    answer_download_url: str | None = None
    citations: list[CitationOut] = []
    grounding_state: str | None = None
    review_findings: list[ReviewFindingOut] = []
    review_rounds: int = 0
    review_outcome: str | None = None


class ExerciseGenerationSnapshot(BaseModel):
    run_id: str
    status: str
    brief_version: int
    blueprint_version: int
    language_mode: str
    scope_lesson_indexes: list[int] | None = None
    retained_artifacts: list[RetainedArtifactOut] = []
    difficulty: str | None = None
    model_calls: int
    model_call_cap: int
    artifacts: list[ExerciseArtifactOut]
    complete_count: int
    total_count: int


class RunEventOut(BaseModel):
    id: str
    run_id: str
    seq: int
    event_type: str
    payload: dict
    created_at: str


def _citations_of(artifact) -> list[CitationOut]:
    import json

    if not getattr(artifact, "citations_json", None):
        return []
    return [CitationOut(**item) for item in json.loads(artifact.citations_json)]


def artifact_out(artifact) -> LessonArtifactOut:
    return LessonArtifactOut(
        id=str(artifact.id),
        lesson_index=artifact.lesson_index,
        status=artifact.status,
        language_mode=artifact.language_mode,
        failure_reason=artifact.failure_reason,
        retry_count=artifact.retry_count,
        download_url=f"/projects/{artifact.project_id}/lesson-plans/{artifact.id}/download"
        if artifact.status == "complete"
        else None,
        citations=_citations_of(artifact),
        grounding_state=artifact.grounding_state,
        design=_design_of(artifact),
        review_findings=_review_findings_of(artifact),
        review_rounds=artifact.review_rounds,
        review_outcome=artifact.review_outcome,
    )


def deck_artifact_out(artifact) -> DeckArtifactOut:
    return DeckArtifactOut(
        id=str(artifact.id),
        lesson_index=artifact.lesson_index,
        status=artifact.status,
        language_mode=artifact.language_mode,
        slide_count=artifact.slide_count,
        failure_reason=artifact.failure_reason,
        retry_count=artifact.retry_count,
        download_url=f"/projects/{artifact.project_id}/slide-decks/{artifact.id}/download"
        if artifact.status == "complete"
        else None,
        citations=_citations_of(artifact),
        grounding_state=artifact.grounding_state,
        review_findings=_review_findings_of(artifact),
        review_rounds=artifact.review_rounds,
        review_outcome=artifact.review_outcome,
    )


def exercise_artifact_out(artifact) -> ExerciseArtifactOut:
    complete = artifact.status == "complete"
    return ExerciseArtifactOut(
        id=str(artifact.id),
        lesson_index=artifact.lesson_index,
        status=artifact.status,
        language_mode=artifact.language_mode,
        category_count=artifact.category_count,
        item_count=artifact.item_count,
        failure_reason=artifact.failure_reason,
        retry_count=artifact.retry_count,
        exercise_download_url=(
            f"/projects/{artifact.project_id}/exercises/{artifact.id}/download?file=exercise"
            if complete
            else None
        ),
        answer_download_url=(
            f"/projects/{artifact.project_id}/exercises/{artifact.id}/download?file=answer"
            if complete
            else None
        ),
        citations=_citations_of(artifact),
        grounding_state=artifact.grounding_state,
        review_findings=_review_findings_of(artifact),
        review_rounds=artifact.review_rounds,
        review_outcome=artifact.review_outcome,
    )


def event_out(event) -> RunEventOut:
    import json

    return RunEventOut(
        id=str(event.id),
        run_id=str(event.run_id),
        seq=event.seq,
        event_type=event.event_type,
        payload=json.loads(event.payload_json),
        created_at=event.created_at.isoformat(),
    )


def run_id_of(snapshot_run_id: uuid.UUID | str) -> str:
    return str(snapshot_run_id)
