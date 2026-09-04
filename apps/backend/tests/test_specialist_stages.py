"""F016 T0: formula caps (TS-014 formula part) and fake-adapter stage scripting.

The specialist stage kinds and fault markers defined here are the deterministic
contract the T1-T3 slices build against: source analysis (filename markers),
lesson design (title markers + design_invalid eval fault), review findings
(title markers + review_severe_twice eval fault), and revise outputs reusing
the family draft builders.
"""

import json

import pytest

from lessoncanvas.adapters.model import FakeModelAdapter, ModelProviderError
from lessoncanvas.modules.run_orchestration.caps import compute_model_call_cap
from lessoncanvas.settings import get_settings


def _complete(payload: dict) -> dict:
    response = FakeModelAdapter().complete(
        system="你是测试专用系统提示", user=json.dumps(payload, ensure_ascii=False)
    )
    return json.loads(response.text)


# --- TS-014 (formula part): per-run cap computation ---


def test_cap_formula_plans_family():
    # 5 stages x 4 lessons + slack 2 = 22, above the flat floor of 20.
    assert compute_model_call_cap("plans", 4) == 22
    assert compute_model_call_cap("plans", 8) == 42


def test_cap_formula_floor_wins_for_small_units():
    # 4x3+2 = 14 and 4x2+2 = 10 stay at the pre-F016 flat cap of 20.
    assert compute_model_call_cap("decks", 3) == 20
    assert compute_model_call_cap("exercises", 2) == 20
    assert compute_model_call_cap("plans", 1) == 20


def test_cap_formula_uses_at_least_one_lesson():
    assert compute_model_call_cap("plans", 0) == 20


def test_cap_formula_rejects_unknown_family():
    with pytest.raises(ValueError):
        compute_model_call_cap("workbooks", 4)


def test_cap_formula_settings_driven(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "model_call_cap_plans_per_lesson", 6, raising=False)
    monkeypatch.setattr(settings, "model_call_cap_slack", 0, raising=False)
    assert compute_model_call_cap("plans", 4) == 24


# --- Fake adapter stage scripting contracts ---


def test_fake_source_analysis_default_and_faults():
    payload = {
        "kind": "source_analysis",
        "filename": "unit-reader.txt",
        "chunks": [
            {"position": 1, "excerpt": "语篇摘录一"},
            {"position": 2, "excerpt": "语篇摘录二"},
        ],
    }
    analysis = _complete(payload)["analysis"]
    assert analysis["suitability"]["recommended"] is True
    assert analysis["key_passages"][0]["chunk_position"] == 1

    with pytest.raises(ModelProviderError):
        _complete({**payload, "filename": "ANALYSIS_FAIL.txt"})

    injected = _complete({**payload, "filename": "ANALYSIS_INJECT.txt"})["analysis"]
    assert any("IGNORE ALL PREVIOUS INSTRUCTIONS" in t for t in injected["topics"])


def test_fake_lesson_design_default_invalid_and_inject():
    payload = {
        "kind": "generation_design_lesson",
        "lesson": {
            "lesson_index": 2,
            "lesson_title": "阅读与表达",
            "objective_ids": ["obj-1", "obj-2"],
        },
        "retrieved": [{"position": 3, "text": "语篇"}],
    }
    design = _complete(payload)["design"]
    assert design["objective_ids"] == ["obj-1", "obj-2"]
    assert design["evidence_references"] == [{"chunk_position": 3}]
    assert all(5 <= a["timing_minutes"] <= 60 for a in design["activities"])

    invalid = _complete(
        {
            **payload,
            "lesson": {**payload["lesson"], "lesson_title": "DESIGN_INVALID 阅读"},
        }
    )["design"]
    assert invalid["objective_ids"] == ["obj-bogus-999"]

    injected = _complete(
        {
            **payload,
            "lesson": {**payload["lesson"], "lesson_title": "DESIGN_INJECT 阅读"},
        }
    )["design"]
    assert any(
        "IGNORE ALL PREVIOUS INSTRUCTIONS" in a["description"] for a in injected["activities"]
    )

    with pytest.raises(ModelProviderError):
        _complete(
            {
                **payload,
                "lesson": {**payload["lesson"], "lesson_title": "DESIGN_FAIL 阅读"},
            }
        )


def test_fake_review_severity_gating_by_round():
    base = {
        "kind": "generation_review_lesson",
        "lesson": {"lesson_index": 1, "lesson_title": "常规课"},
        "round": 1,
        "draft": {"lesson_plan": {}},
    }
    assert _complete(base)["review"]["findings"] == []

    minor = _complete({**base, "lesson": {**base["lesson"], "lesson_title": "REVIEW_MINOR 课"}})
    assert minor["review"]["findings"][0]["severity"] == "minor"

    severe_round1 = _complete(
        {**base, "lesson": {**base["lesson"], "lesson_title": "REVIEW_SEVERE 课"}}
    )
    assert severe_round1["review"]["findings"][0]["severity"] == "severe"
    # REVIEW_SEVERE (without TWICE) clears on the re-review round.
    assert _complete(
        {
            **base,
            "lesson": {**base["lesson"], "lesson_title": "REVIEW_SEVERE 课"},
            "round": 2,
        }
    )["review"]["findings"] == []

    twice = _complete(
        {
            **base,
            "lesson": {**base["lesson"], "lesson_title": "REVIEW_SEVERE_TWICE 课"},
            "round": 2,
        }
    )
    assert twice["review"]["findings"][0]["severity"] == "severe"

    with pytest.raises(ModelProviderError):
        _complete({**base, "lesson": {**base["lesson"], "lesson_title": "REVIEW_FAIL 课"}})

    parse_fail = FakeModelAdapter().complete(
        system="s",
        user=json.dumps(
            {**base, "lesson": {**base["lesson"], "lesson_title": "REVIEW_PARSE_FAIL 课"}}
        ),
    )
    with pytest.raises(json.JSONDecodeError):
        json.loads(parse_fail.text)


def test_fake_revise_reuses_family_draft_builders():
    payload = {
        "kind": "generation_revise_lesson",
        "lesson": {"lesson_index": 1, "lesson_title": "修订课", "unit_objectives": []},
        "draft": {"lesson_plan": {"title": "修订课"}},
        "findings": [
            {"dimension": "objective_coverage", "severity": "severe", "message": "补齐目标"}
        ],
    }
    revised = _complete(payload)
    assert revised["lesson_plan"]["title"] == "修订课"

    deck = _complete(
        {
            **payload,
            "kind": "generation_revise_deck",
            "lesson": {
                "lesson_index": 1,
                "lesson_title": "修订课",
                "lesson_plan": {"title": "修订课", "stages": []},
            },
        }
    )
    assert deck["slide_deck"]["title"] == "修订课"

    exercises = _complete(
        {
            **payload,
            "kind": "generation_revise_exercises",
            "lesson": {
                "lesson_index": 1,
                "lesson_title": "修订课",
                "lesson_plan": {"title": "修订课"},
                "confirmed_objectives": ["目标一"],
                "difficulty": "foundation",
            },
        }
    )
    assert exercises["exercise_set"]["title"] == "修订课"


def test_fake_design_and_review_eval_fault_modes(monkeypatch):
    # F009 harness scripting: design_invalid / review_severe_twice eval faults
    # are reachable only through the gated activate_eval_faults path.
    adapter = FakeModelAdapter()
    settings = get_settings()
    monkeypatch.setattr(settings, "eval_fault_profile", "enabled", raising=False)
    monkeypatch.setattr(settings, "model_adapter", "fake", raising=False)
    adapter.activate_eval_faults(
        {"generation_design_lesson": {"lesson_index": 1, "mode": "design_invalid"}}
    )
    design = _complete(
        {
            "kind": "generation_design_lesson",
            "lesson": {"lesson_index": 1, "lesson_title": "课", "objective_ids": ["obj-1"]},
        }
    )["design"]
    assert design["objective_ids"] == ["obj-bogus-999"]

    adapter.activate_eval_faults(
        {"generation_review_lesson": {"lesson_index": 1, "mode": "review_severe_twice"}}
    )
    findings = _complete(
        {
            "kind": "generation_review_lesson",
            "lesson": {"lesson_index": 1, "lesson_title": "课"},
            "round": 2,
        }
    )["review"]["findings"]
    assert findings[0]["severity"] == "severe"
    adapter.activate_eval_faults(None)
