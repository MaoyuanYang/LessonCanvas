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
        if "fail" in data.get("scenario", ""):
            raise ModelProviderError("model provider unavailable")
        return ModelResponse(text=json.dumps({}), latency_ms=1)


@lru_cache
def get_model_adapter():
    settings = get_settings()
    if settings.model_adapter == "fake":
        return FakeModelAdapter()
    return DeepSeekAdapter()
