from __future__ import annotations

import json

import pytest

from blueprint_dsl.render import (
    BlueprintOutputToken,
    BlueprintOutputView,
    BlueprintRenderError,
    render_blueprint_output,
)


def test_render_blueprint_output_builds_a_general_instance_view() -> None:
    value = {
        "summary": "A dragon story",
        "legible": True,
        "confidence": 0.8,
        "flags": ["creative", False, None],
        "details": {"pages": 2, "notes": []},
        "reviews": [{"score": 4}, {"score": 5}],
        "metadata": {},
    }

    view = render_blueprint_output(value, name="PageReview")

    assert isinstance(view, BlueprintOutputView)
    assert view.text == (
        "PageReview:\n"
        "  summary: A dragon story\n"
        "  legible: true\n"
        "  confidence: 0.8\n"
        "  flags:\n"
        "    - creative\n"
        "    - false\n"
        "    - null\n"
        "  details:\n"
        "    pages: 2\n"
        "    notes: []\n"
        "  reviews:\n"
        "    -\n"
        "      score: 4\n"
        "    -\n"
        "      score: 5\n"
        "  metadata: {}\n"
    )
    assert json.loads(view.json_text) == value
    assert "A dragon story" in view.json_text


def test_render_blueprint_output_exposes_framework_neutral_syntax_tokens() -> None:
    view = render_blueprint_output({"count": 3, "ready": True}, name="Status")

    assert view.text == "".join(token.text for token in view.tokens)
    assert all(isinstance(token, BlueprintOutputToken) for token in view.tokens)
    assert [(token.kind, token.text) for token in view.tokens if token.kind != "whitespace"] == [
        ("name", "Status"),
        ("punctuation", ":"),
        ("key", "count"),
        ("punctuation", ":"),
        ("number", "3"),
        ("key", "ready"),
        ("punctuation", ":"),
        ("constant", "true"),
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([1, "two"], "Result:\n  - 1\n  - two\n"),
        ("plain text", "Result: plain text\n"),
        (None, "Result: null\n"),
        ({}, "Result: {}\n"),
        ([], "Result: []\n"),
    ],
)
def test_render_blueprint_output_supports_every_json_root(
    value: object,
    expected: str,
) -> None:
    assert render_blueprint_output(value).text == expected


def test_render_blueprint_output_preserves_multiline_unicode_and_json_looking_strings() -> None:
    value = {
        "transcription": "Kid\nspeling! 🐉",
        "payload": '{"looks":"like json"}',
        "": "empty key",
        "not-a-field": "quoted key",
    }

    view = render_blueprint_output(value, name="Document")

    assert "transcription: Kid\nspeling! 🐉\n" in view.text
    assert 'payload: {"looks":"like json"}\n' in view.text
    assert '  "": empty key\n' in view.text
    assert '  "not-a-field": quoted key\n' in view.text
    assert "🐉" in view.json_text


@pytest.mark.parametrize("name", ["", "two words", "9Result", "Result:", "Result\n", None])
def test_render_blueprint_output_rejects_invalid_names(name: object) -> None:
    with pytest.raises(BlueprintRenderError, match="name must start with a letter"):
        render_blueprint_output({}, name=name)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [("tuple",), {"bad": {1, 2}}, object()])
def test_render_blueprint_output_rejects_non_json_values(value: object) -> None:
    with pytest.raises(BlueprintRenderError, match="must be decoded JSON"):
        render_blueprint_output(value)


def test_render_blueprint_output_rejects_non_string_object_keys() -> None:
    with pytest.raises(BlueprintRenderError, match="non-string key"):
        render_blueprint_output({1: "not JSON"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_render_blueprint_output_rejects_nonfinite_numbers(value: float) -> None:
    with pytest.raises(BlueprintRenderError, match="must be finite JSON"):
        render_blueprint_output({"value": value})


def test_render_blueprint_output_rejects_circular_references() -> None:
    value: list[object] = []
    value.append(value)

    with pytest.raises(BlueprintRenderError, match=r"circular reference at \$\[0\]"):
        render_blueprint_output(value)


def test_render_blueprint_output_allows_repeated_noncyclic_collections() -> None:
    child = {"name": "shared"}

    view = render_blueprint_output({"first": child, "second": child})

    assert view.text.count("name: shared") == 2
