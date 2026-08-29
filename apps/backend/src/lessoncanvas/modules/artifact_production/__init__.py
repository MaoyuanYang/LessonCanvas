"""Artifact production: DOCX lesson-plan generation (F003)."""

from lessoncanvas.modules.artifact_production.docx_tools import (
    RENDER_TOOL_DEFINITION,
    REQUIRED_SECTIONS,
    VALIDATE_TOOL_DEFINITION,
    execute_docx_tool,
    render_lesson_plan_docx,
    validate_lesson_plan_docx,
)
from lessoncanvas.modules.artifact_production.graph import (
    CapExhaustedError,
    ProviderTransientError,
    artifact_key,
    build_graph,
    execute_generation,
    mark_provider_exhausted,
)

__all__ = [
    "RENDER_TOOL_DEFINITION",
    "REQUIRED_SECTIONS",
    "VALIDATE_TOOL_DEFINITION",
    "CapExhaustedError",
    "ProviderTransientError",
    "artifact_key",
    "build_graph",
    "execute_docx_tool",
    "execute_generation",
    "mark_provider_exhausted",
    "render_lesson_plan_docx",
    "validate_lesson_plan_docx",
]
