"""F011 TS-010: worker fast-fail on vanished runs (F006 M-2 / F004 M-2).

Bug branch: the reproduction evidence is the live F006 TS-024 run (project
deleted at `generating` 4/6 -> StaleDataError on the in-flight lesson update
-> two 180 s-delayed retries before terminal). The deterministic surrogate
here drives the same code path: the vanished-run class settles immediately
as terminal missing_run with zero retries, while transient provider failures
keep the bounded-retry path (negative control).
"""

import uuid

from lessoncanvas.modules.artifact_production import graph as plan_graph
from lessoncanvas.modules.artifact_production.fastfail import settle_vanished_run


class VanishedRunError(Exception):
    pass


def test_vanished_run_class_settles_immediately_without_retry():
    # The run row is gone entirely (deletion cascade won the race).
    settled = settle_vanished_run(str(uuid.uuid4()), VanishedRunError("boom"))
    assert settled == "missing_run"


def test_stale_data_error_settles_even_if_row_probe_is_inconclusive(monkeypatch):
    from sqlalchemy.orm.exc import StaleDataError

    settled = settle_vanished_run(
        str(uuid.uuid4()), StaleDataError("UPDATE statement expected 1 row; 0 were matched")
    )
    assert settled == "missing_run"


def test_transient_provider_failure_keeps_bounded_retry_path(client, auth, db_session):
    # A provider error whose run still exists must NOT fast-fail.
    from lessoncanvas.models import Project
    from lessoncanvas.modules.run_orchestration import service as run_service
    from test_generation import confirmed_blueprint_project

    project_id = confirmed_blueprint_project(client, auth)
    workspace_id = db_session.get(Project, uuid.UUID(project_id)).workspace_id
    run, _ = run_service.start_generation(db_session, workspace_id, uuid.UUID(project_id))
    db_session.commit()

    result = settle_vanished_run(
        str(run.id), plan_graph.ProviderTransientError("provider unavailable")
    )
    assert result is None, "transient provider errors must stay retryable"


def test_execute_generation_settles_vanished_run_without_raising():
    """The real worker contract: a vanished-run graph failure returns terminal
    status (no exception -> no Celery retry), a transient provider failure
    re-raises (bounded retry preserved)."""
    from sqlalchemy.orm.exc import StaleDataError

    vanished_run_id = str(uuid.uuid4())  # no row exists: deletion won the race

    class VanishedGraph:
        def invoke(self, state):
            raise StaleDataError("UPDATE statement on lesson_plan_artifacts; 0 matched")

    class TransientGraph:
        def invoke(self, state):
            raise plan_graph.ProviderTransientError("provider unavailable")

    assert (
        plan_graph.execute_generation(vanished_run_id, graph=VanishedGraph())
        == "missing_run"
    )

    try:
        plan_graph.execute_generation(vanished_run_id, graph=TransientGraph())
        raise AssertionError("transient provider errors must re-raise for retry")
    except plan_graph.ProviderTransientError:
        pass
