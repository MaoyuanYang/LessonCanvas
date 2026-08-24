import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class StandardsSection:
    id: str
    title: str
    text: str


@dataclass(frozen=True)
class StandardsSnapshot:
    snapshot_version: str
    title: str
    publisher: str
    sections: tuple[StandardsSection, ...]


@lru_cache
def load_snapshot() -> StandardsSnapshot:
    raw = (
        resources.files("lessoncanvas.data")
        .joinpath("standards_snapshot_v1.json")
        .read_text(encoding="utf-8")
    )
    data = json.loads(raw)
    sections = tuple(
        StandardsSection(id=s["id"], title=s["title"], text=s["text"])
        for s in data["sections"]
    )
    return StandardsSnapshot(
        snapshot_version=data["snapshot_version"],
        title=data["title"],
        publisher=data["publisher"],
        sections=sections,
    )


STANDARDS_TOOL_DEFINITION = {
    "name": "search_curriculum_standards",
    "description": (
        "Search the curated senior-high English curriculum standards snapshot "
        "for grounding evidence. Returns matching sections with the snapshot version."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "keywords to search for"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
}


def _score(query: str, section: StandardsSection) -> int:
    tokens = [t for t in query.lower().split() if t]
    haystack = (section.title + section.text).lower()
    return sum(1 for token in tokens if token in haystack)


def search_standards(query: str, limit: int = 5) -> list[dict]:
    snapshot = load_snapshot()
    ranked = sorted(
        (s for s in snapshot.sections if _score(query, s) > 0),
        key=lambda s: _score(query, s),
        reverse=True,
    )
    return [
        {
            "section_id": s.id,
            "title": s.title,
            "text": s.text,
            "snapshot_version": snapshot.snapshot_version,
        }
        for s in ranked[:limit]
    ]


def execute_tool(name: str, arguments: dict) -> list[dict]:
    if name != STANDARDS_TOOL_DEFINITION["name"]:
        raise KeyError(f"unknown tool: {name}")
    return search_standards(arguments.get("query", ""), int(arguments.get("limit", 5)))
