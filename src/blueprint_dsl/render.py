"""Render decoded JSON values as human-readable Blueprint output views."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Literal

type BlueprintOutputTokenKind = Literal[
    "name",
    "key",
    "string",
    "number",
    "constant",
    "punctuation",
    "whitespace",
]


class BlueprintRenderError(ValueError):
    """The supplied name or value cannot be rendered as Blueprint output."""


@dataclass(frozen=True, slots=True)
class BlueprintOutputToken:
    kind: BlueprintOutputTokenKind
    text: str


@dataclass(frozen=True, slots=True)
class BlueprintOutputView:
    text: str
    tokens: tuple[BlueprintOutputToken, ...]
    json_text: str


_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _Renderer:
    __slots__ = ("tokens",)

    def __init__(self) -> None:
        self.tokens: list[BlueprintOutputToken] = []

    def add(self, kind: BlueprintOutputTokenKind, text: str) -> None:
        self.tokens.append(BlueprintOutputToken(kind=kind, text=text))

    def render_value(
        self,
        value: object,
        *,
        depth: int,
        path: str,
        active_collections: set[int],
    ) -> None:
        if isinstance(value, dict):
            self._render_object(
                value,
                depth=depth,
                path=path,
                active_collections=active_collections,
            )
            return
        if isinstance(value, list):
            self._render_list(
                value,
                depth=depth,
                path=path,
                active_collections=active_collections,
            )
            return
        self._render_scalar(value, path=path)

    def _render_object(
        self,
        value: dict[object, object],
        *,
        depth: int,
        path: str,
        active_collections: set[int],
    ) -> None:
        if not value:
            self.add("punctuation", "{}")
            return
        collection_id = _enter_collection(value, path, active_collections)
        try:
            for key, child in value.items():
                if not isinstance(key, str):
                    raise BlueprintRenderError(
                        f"Blueprint output object at {path} has a non-string key."
                    )
                child_path = _object_path(path, key)
                self._indent(depth)
                self.add("key", _display_key(key))
                self.add("punctuation", ":")
                if _is_nonempty_collection(child):
                    self.add("whitespace", "\n")
                    self.render_value(
                        child,
                        depth=depth + 1,
                        path=child_path,
                        active_collections=active_collections,
                    )
                else:
                    self.add("whitespace", " ")
                    self.render_value(
                        child,
                        depth=depth,
                        path=child_path,
                        active_collections=active_collections,
                    )
                    self.add("whitespace", "\n")
        finally:
            active_collections.remove(collection_id)

    def _render_list(
        self,
        value: list[object],
        *,
        depth: int,
        path: str,
        active_collections: set[int],
    ) -> None:
        if not value:
            self.add("punctuation", "[]")
            return
        collection_id = _enter_collection(value, path, active_collections)
        try:
            for index, child in enumerate(value):
                child_path = f"{path}[{index}]"
                self._indent(depth)
                self.add("punctuation", "-")
                if _is_nonempty_collection(child):
                    self.add("whitespace", "\n")
                    self.render_value(
                        child,
                        depth=depth + 1,
                        path=child_path,
                        active_collections=active_collections,
                    )
                else:
                    self.add("whitespace", " ")
                    self.render_value(
                        child,
                        depth=depth,
                        path=child_path,
                        active_collections=active_collections,
                    )
                    self.add("whitespace", "\n")
        finally:
            active_collections.remove(collection_id)

    def _render_scalar(self, value: object, *, path: str) -> None:
        if isinstance(value, str):
            self.add("string", value)
            return
        if value is None:
            self.add("constant", "null")
            return
        if isinstance(value, bool):
            self.add("constant", "true" if value else "false")
            return
        if isinstance(value, int):
            self.add("number", str(value))
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise BlueprintRenderError(
                    f"Blueprint output number at {path} must be finite JSON."
                )
            self.add("number", json.dumps(value, allow_nan=False))
            return
        raise BlueprintRenderError(
            f"Blueprint output value at {path} must be decoded JSON; "
            f"got {type(value).__name__}."
        )

    def _indent(self, depth: int) -> None:
        self.add("whitespace", "  " * depth)


def render_blueprint_output(value: object, *, name: str = "Result") -> BlueprintOutputView:
    """Render a decoded JSON value as a presentation-only Blueprint instance view."""

    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise BlueprintRenderError(
            "Blueprint output name must start with a letter and contain only letters, "
            "numbers, and underscores."
        )

    renderer = _Renderer()
    renderer.add("name", name)
    renderer.add("punctuation", ":")
    if _is_nonempty_collection(value):
        renderer.add("whitespace", "\n")
        renderer.render_value(value, depth=1, path="$", active_collections=set())
    else:
        renderer.add("whitespace", " ")
        renderer.render_value(value, depth=0, path="$", active_collections=set())
        renderer.add("whitespace", "\n")

    tokens = tuple(renderer.tokens)
    return BlueprintOutputView(
        text="".join(token.text for token in tokens),
        tokens=tokens,
        json_text=json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False),
    )


def _is_nonempty_collection(value: object) -> bool:
    return isinstance(value, dict | list) and bool(value)


def _enter_collection(value: object, path: str, active_collections: set[int]) -> int:
    collection_id = id(value)
    if collection_id in active_collections:
        raise BlueprintRenderError(f"Blueprint output contains a circular reference at {path}.")
    active_collections.add(collection_id)
    return collection_id


def _display_key(key: str) -> str:
    if _FIELD_NAME_RE.fullmatch(key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _object_path(path: str, key: str) -> str:
    if _FIELD_NAME_RE.fullmatch(key):
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key, ensure_ascii=False)}]"


__all__ = [
    "BlueprintOutputToken",
    "BlueprintOutputTokenKind",
    "BlueprintOutputView",
    "BlueprintRenderError",
    "render_blueprint_output",
]
