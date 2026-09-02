"""F012 sample pointer API: tells the web `/sample` view which project the
designated demo workspace owns. Read-only pointer only — all content reads go
through the normal project endpoints under the sample-read rule.
"""

from fastapi import APIRouter
from sqlalchemy import select

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError
from lessoncanvas.models import Project, Workspace
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/sample", tags=["sample"])


@router.get("")
def sample_pointer(session: SessionDep, workspace=WorkspaceDep) -> dict:
    settings = get_settings()
    demo_workspace = session.scalar(
        select(Workspace).where(Workspace.subject == settings.demo_owner_subject)
    )
    project = None
    if demo_workspace is not None:
        project = session.scalar(
            select(Project).where(
                Project.workspace_id == demo_workspace.id, Project.status == "active"
            )
        )
    if project is None:
        raise NotFoundError("sample not seeded")
    return {"project_id": str(project.id), "name": project.name}
