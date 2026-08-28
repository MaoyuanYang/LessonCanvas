import json
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx

from lessoncanvas.settings import get_settings


@dataclass
class ModelResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class ModelProviderError(Exception):
    pass


class DeepSeekAdapter:
    def complete(self, system: str, user: str) -> ModelResponse:
        settings = get_settings()
        started = time.monotonic()
        try:
            response = httpx.post(
                f"{settings.deepseek_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={
                    "model": settings.deepseek_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                },
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, KeyError) as error:
            raise ModelProviderError("model provider unavailable") from error
        choice = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        latency = int((time.monotonic() - started) * 1000)
        return ModelResponse(
            text=choice,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cost_usd=0.0,
            latency_ms=latency,
        )

    def stream(self, system: str, user: str):
        settings = get_settings()
        with httpx.stream(
            "POST",
            f"{settings.deepseek_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "stream": True,
            },
            timeout=60,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload_text = line[len("data:") :].strip()
                if payload_text == "[DONE]":
                    break
                try:
                    payload = json.loads(payload_text)
                except json.JSONDecodeError:
                    continue
                delta = payload.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content")
                if token:
                    yield token


class FakeModelAdapter:
    def complete(self, system: str, user: str) -> ModelResponse:
        data = json.loads(user)
        kind = data.get("kind")
        if kind == "gap_analysis":
            known = set(data.get("known_fields", []))
            required = data.get("required_fields", [])
            missing = [f for f in required if f not in known]
            questions = [
                {"field": m, "question": f"请补充：{m} 的具体内容是什么？"} for m in missing[:3]
            ]
            return ModelResponse(text=json.dumps({"questions": questions}), latency_ms=1)
        if kind == "build_draft":
            fields = data.get("fields", {})
            draft = {}
            for required_field in data.get("required_fields", []):
                value = fields.get(required_field)
                draft[required_field] = {
                    "value": value,
                    "grounding": "teacher-stated" if value else None,
                    "unresolved": not value,
                }
            return ModelResponse(text=json.dumps({"draft": draft}), latency_ms=1)
        if kind == "planning_gap_analysis":
            if "课时分配" in data.get("corpus_excerpt", ""):
                return ModelResponse(text=json.dumps({"questions": []}), latency_ms=1)
            known = set(data.get("known_fields", []))
            gaps = data.get("planning_gaps", [])
            missing = [g for g in gaps if g not in known]
            questions = [{"field": m, "question": f"请说明规划缺口：{m}"} for m in missing[:3]]
            return ModelResponse(text=json.dumps({"questions": questions}), latency_ms=1)
        if kind == "planning_build_draft":
            return ModelResponse(text=json.dumps(_fake_planning_blueprint(data)), latency_ms=1)
        if "fail" in data.get("scenario", ""):
            raise ModelProviderError("model provider unavailable")
        return ModelResponse(text=json.dumps({}), latency_ms=1)

    def stream(self, system: str, user: str):
        data = json.loads(user)
        text = data.get("narration", "这是叙述文本。")
        yield from (text[i : i + 4] for i in range(0, len(text), 4))


def _fake_planning_blueprint(data: dict) -> dict:
    import re

    brief = data.get("brief", {})
    known = data.get("known", {})
    corpus = data.get("corpus_excerpt", "")
    standards = data.get("standards", [])

    raw_count = str(brief.get("lesson_count") or "")
    match = re.search(r"\d+", raw_count)
    lesson_count = int(match.group()) if match else 1

    objectives_text = str(brief.get("teaching_objectives") or "")
    objective_texts = [t.strip() for t in re.split(r"[；;，,]", objectives_text) if t.strip()]
    if not objective_texts:
        objective_texts = [brief.get("unit_theme") or "理解单元主题"]

    objectives = [
        {"id": f"obj-{i}", "text": text} for i, text in enumerate(objective_texts, start=1)
    ]

    period_plan = known.get("period_plan") or ""
    period_match = re.search(r"\d+", period_plan)
    per_lesson_periods = None
    if period_match:
        per_lesson_periods = max(1, int(period_match.group()) // max(1, lesson_count))

    lessons = []
    for index in range(1, lesson_count + 1):
        lessons.append(
            {
                "index": index,
                "title": f"第{index}课 {brief.get('unit_theme') or '单元'}",
                "objective_ids": [objectives[(index - 1) % len(objectives)]["id"]],
                "assessment_intent": brief.get("assessment_orientation") or "形成性评价",
                "period_count": per_lesson_periods,
                "activity_outline": None,
                "material_notes": None,
            }
        )

    findings = []
    if "冲突" in corpus:
        findings.append(
            {
                "kind": "source_conflict",
                "message": "来源材料之间存在内容冲突",
                "evidence": "来源内容标记了冲突",
            }
        )
    if not standards:
        findings.append(
            {
                "kind": "standards_warning",
                "message": "课标快照中未检索到与单元主题直接对应的条目",
                "evidence": None,
            }
        )
    if not period_plan and lesson_count > 1:
        findings.append(
            {
                "kind": "period_warning",
                "message": "未提供课时分配意图，课时分布可能不合理",
                "evidence": None,
            }
        )

    return {
        "blueprint": {
            "unit": {
                "title": brief.get("unit_theme") or "未命名单元",
                "objectives": objectives,
                "assessment_intent": brief.get("assessment_orientation"),
            },
            "lessons": lessons,
            "findings": findings,
        }
    }


@lru_cache
def get_model_adapter():
    settings = get_settings()
    if settings.model_adapter == "fake":
        return FakeModelAdapter()
    return DeepSeekAdapter()
