"""F016 T7 (Spec D1/TS-024): idempotent deploy-time source-analysis backfill.

Analyzes every ready source that has no settled analysis row (pre-F016 rows
on the deployed stack, including the F009 seeded dataset sources so live
re-baseline passes run with analyses present). Safe to re-run: sources whose
analysis is ready or failed are skipped — a failed analysis is never silently
re-analyzed (the teacher-visible manual retry owns re-billing).

Runs inside the deployed image after `alembic upgrade head`:
    uv run python scripts/backfill_source_analyses.py
"""

import sys

from sqlalchemy import select

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Source, SourceAnalysis
from lessoncanvas.modules.sources_grounding.analysis import (
    AnalysisInProgressError,
    analyze_source,
)


def backfill(session) -> dict:
    stats = {"analyzed": 0, "skipped": 0, "failed": 0}
    settled = {
        row.source_id
        for row in session.scalars(select(SourceAnalysis)).all()
        if row.status in ("ready", "failed", "analyzing")
    }
    sources = session.scalars(
        select(Source).where(Source.status == "ready").order_by(Source.created_at)
    ).all()
    for source in sources:
        if source.id in settled:
            stats["skipped"] += 1
            continue
        try:
            row = analyze_source(session, source.id)
        except AnalysisInProgressError:
            stats["skipped"] += 1
            continue
        except ValueError:
            stats["skipped"] += 1
            continue
        session.commit()
        if row.status == "ready":
            stats["analyzed"] += 1
        else:
            stats["failed"] += 1
    return stats


def main() -> int:
    session = SessionLocal()
    try:
        stats = backfill(session)
        session.commit()
    finally:
        session.close()
    print(
        f"source-analysis backfill: {stats['analyzed']} analyzed, "
        f"{stats['failed']} failed (manual retry only), {stats['skipped']} skipped"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
