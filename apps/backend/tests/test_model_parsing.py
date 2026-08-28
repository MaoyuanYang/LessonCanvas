import pytest

from lessoncanvas.adapters.model import parse_model_json


def test_plain_json_object():
    assert parse_model_json('{"questions": []}') == {"questions": []}


def test_markdown_fenced_json():
    assert parse_model_json('```json\n{"questions": [{"field": "a"}]}\n```') == {
        "questions": [{"field": "a"}]
    }


def test_bare_fence_json():
    assert parse_model_json('```\n{"draft": {}}\n```') == {"draft": {}}


def test_json_wrapped_in_prose():
    assert parse_model_json('好的，以下是结果：\n{"a": {"b": 2}}\n希望有帮助') == {"a": {"b": 2}}


def test_nested_braces_survive_substring_extraction():
    assert parse_model_json('前言 {"outer": {"inner": [1, 2]}} 后记') == {
        "outer": {"inner": [1, 2]}
    }


def test_invalid_payload_raises():
    with pytest.raises(ValueError):
        parse_model_json("完全没有 JSON 的回复")
