from __future__ import annotations

import ast
import json
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any


class StructuredOutputDslError(ValueError):
    def __init__(self, errors: str | list[str] | tuple[str, ...]) -> None:
        normalized = (errors,) if isinstance(errors, str) else tuple(errors)
        self.errors: tuple[str, ...] = normalized or ("Blueprint failed to compile.",)
        if len(self.errors) == 1:
            message = self.errors[0]
        else:
            message = f"{self.errors[0]} (+{len(self.errors) - 1} more)"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CompiledStructuredOutputSchema:
    name: str
    schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BlueprintTypeInfo:
    name: str
    category: str
    arguments: tuple[str, ...]
    summary: str


_NUMBER_ARGUMENTS = ("min", "max", "exclusive_min", "exclusive_max", "multiple_of")
_STRING_ARGUMENTS = ("min", "max")
_LIST_ARGUMENTS = ("min", "max")

BLUEPRINT_DECLARATION_KEYWORDS: tuple[str, ...] = ("Schema", "Return")

BLUEPRINT_TYPE_REGISTRY: tuple[BlueprintTypeInfo, ...] = (
    BlueprintTypeInfo("String", "primitive", _STRING_ARGUMENTS, "Text. min/max constrain length."),
    BlueprintTypeInfo("Integer", "primitive", _NUMBER_ARGUMENTS, "Whole number."),
    BlueprintTypeInfo("Float", "primitive", _NUMBER_ARGUMENTS, "Decimal number."),
    BlueprintTypeInfo("Boolean", "primitive", (), "True or false."),
    BlueprintTypeInfo("None", "keyword", (), "Null. Combine in unions for nullable values."),
    BlueprintTypeInfo("Date", "format", _STRING_ARGUMENTS, "Calendar date string."),
    BlueprintTypeInfo("Time", "format", _STRING_ARGUMENTS, "Time-of-day string."),
    BlueprintTypeInfo("Datetime", "format", _STRING_ARGUMENTS, "Date-time string."),
    BlueprintTypeInfo("Duration", "format", _STRING_ARGUMENTS, "Duration string."),
    BlueprintTypeInfo("Email", "format", _STRING_ARGUMENTS, "Email address string."),
    BlueprintTypeInfo("Hostname", "format", _STRING_ARGUMENTS, "Hostname string."),
    BlueprintTypeInfo("IPv4", "format", _STRING_ARGUMENTS, "IPv4 address string."),
    BlueprintTypeInfo("IPv6", "format", _STRING_ARGUMENTS, "IPv6 address string."),
    BlueprintTypeInfo("Uuid", "format", _STRING_ARGUMENTS, "UUID string."),
    BlueprintTypeInfo(
        "List",
        "container",
        _LIST_ARGUMENTS,
        "Array of a type. min/max constrain item count.",
    ),
    BlueprintTypeInfo(
        "Enum",
        "container",
        (),
        "Fixed set of literals: all strings, all numbers, or all booleans.",
    ),
    BlueprintTypeInfo("Optional", "container", (), "Shorthand for `Type | None`."),
)

_TYPE_ARGUMENTS_BY_NAME: dict[str, frozenset[str]] = {
    info.name: frozenset(info.arguments) for info in BLUEPRINT_TYPE_REGISTRY
}

_STRING_FORMAT_TYPES: dict[str, str] = {
    "Datetime": "date-time",
    "Date": "date",
    "Time": "time",
    "Duration": "duration",
    "Email": "email",
    "Hostname": "hostname",
    "IPv4": "ipv4",
    "IPv6": "ipv6",
    "Uuid": "uuid",
}

_TYPE_SUGGESTIONS: dict[str, str | None] = {
    "str": "String",
    "string": "String",
    "int": "Integer",
    "integer": "Integer",
    "float": "Float",
    "number": "Float",
    "double": "Float",
    "bool": "Boolean",
    "boolean": "Boolean",
    "list": "List",
    "array": "List",
    "enum": "Enum",
    "optional": "Optional",
    "none": "None",
    "null": "None",
    "Null": "None",
    "date": "Date",
    "time": "Time",
    "datetime": "Datetime",
    "email": "Email",
    "uuid": "Uuid",
    "UUID": "Uuid",
    "dict": None,
    "Dict": None,
    "map": None,
    "Map": None,
    "object": None,
    "Object": None,
}


def blueprint_editor_metadata() -> dict[str, list[str]]:
    return {
        "declarations": list(BLUEPRINT_DECLARATION_KEYWORDS),
        "types": [info.name for info in BLUEPRINT_TYPE_REGISTRY],
    }


def blueprint_types_by_category() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for info in BLUEPRINT_TYPE_REGISTRY:
        grouped.setdefault(info.category, []).append(info.name)
    return grouped


BLUEPRINT_SPEC_EXAMPLE = """Schema Friend:
  name: String(min=1)
  ranking: Float(min=0.0, max=1.0)  # closeness, 1.0 is closest

Return Person:
  name: String(min=1)
  age: Optional[Integer]  # null when unknown
  address:
    street: String
    city: String
  tags: List[String]
  status: Enum["draft", "final"]
  friends: List[Friend]"""


def blueprint_spec_card() -> str:
    grouped = blueprint_types_by_category()
    primitives = ", ".join(grouped.get("primitive", []))
    keywords = ", ".join(grouped.get("keyword", []))
    formats = ", ".join(grouped.get("format", []))
    string_args = ", ".join(f"{name}=" for name in _STRING_ARGUMENTS)
    number_args = ", ".join(f"{name}=" for name in _NUMBER_ARGUMENTS)
    list_args = ", ".join(f"{name}=" for name in _LIST_ARGUMENTS)
    lines = (
        "Blueprint defines the exact JSON object a model must return. "
        "It compiles to strict JSON Schema.",
        "",
        "RULES",
        "- Exactly one `Return Name:` block declares the output object. Optional "
        "`Schema Name:` blocks declare reusable shapes referenced by name.",
        "- Fields are `name: Type`, indented exactly two spaces per nesting level.",
        "- A trailing `# comment` on a field or declaration becomes its description; "
        "the model reads it. Full-line comments are ignored.",
        "- A bare `name:` opens an inline object block. `name: List:` or "
        "`name: List(min=1):` opens an inline list of objects.",
        "- Every declared field is always present in the output. `Optional[T]` "
        "(or `T | None`) means the value may be null, never omitted.",
        "",
        "TYPES",
        f"- Primitives: {primitives}. `{keywords}` is the null type for unions.",
        f"- Formatted strings: {formats}.",
        "- Containers: `List[T]`, `Enum[...]`, `Optional[T]`; unions with `A | B`.",
        f"- Constraints: `String({string_args})` for length; `Integer({number_args})` "
        f"and `Float(...)` for value bounds; `List[T]({list_args})` for item count.",
        '- Enum values are literals of one type: `Enum["draft", "final"]`, '
        "`Enum[1, 2, 3]`, or `Enum[True, False]`.",
        "",
        "AVOID",
        "- Python type names (`str`, `int`, `bool`, `dict`): use `String`, `Integer`, "
        "`Boolean`. There is no map/dict type; use an inline block or a Schema.",
        "- Regex: there is no `pattern` argument. Use a format type or a description.",
        "- Tabs or four-space indents: exactly two spaces per level.",
        "- Trailing commas, empty union branches, duplicate union branches.",
        "",
        "EXAMPLE",
        BLUEPRINT_SPEC_EXAMPLE,
    )
    return "\n".join(lines)


@dataclass(slots=True)
class FieldNode:
    name: str
    line_number: int
    kind: str  # "leaf" | "object" | "list_object"
    expression: str = ""
    description: str = ""
    list_arguments: str = ""
    children: list[FieldNode] = field(default_factory=list)


@dataclass(slots=True)
class SchemaDefinition:
    kind: str  # "Schema" | "Return"
    name: str
    line_number: int
    fields: list[FieldNode] = field(default_factory=list)
    expression: str = ""
    description: str = ""


@dataclass(slots=True)
class _Frame:
    indent: int
    fields: list[FieldNode]
    opener_line: int
    opener_name: str
    is_inline: bool


_MAX_ERRORS = 25

# Provider limits mirror OpenAI strict structured outputs, Blueprint's primary target.
# They are conservative for other services routed through OpenRouter.
_MAX_SCHEMA_PROPERTIES = 5000
_MAX_SCHEMA_DEPTH = 10
_MAX_SCHEMA_STRING_LENGTH = 120_000
_MAX_SCHEMA_ENUM_VALUES = 1000
_MAX_LARGE_ENUM_VALUES = 250
_MAX_LARGE_ENUM_STRING_LENGTH = 15_000

_BLOCK_DECLARATION_RE = re.compile(r"^(Schema|Return)\s+([A-Za-z][A-Za-z0-9_]*)\s*:$")
_RETURN_EXPRESSION_RE = re.compile(r"^Return\s+(.+)$")
_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
_LIST_BLOCK_RE = re.compile(r"^List(\(.*\))?:$")
_TYPE_NAME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\s*(.*)$")
_ARGUMENT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _ErrorCollector:
    __slots__ = ("errors",)

    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        if len(self.errors) < _MAX_ERRORS:
            self.errors.append(message)

    def extend(self, messages: tuple[str, ...] | list[str]) -> None:
        for message in messages:
            self.add(message)

    def raise_if_any(self) -> None:
        if self.errors:
            raise StructuredOutputDslError(self.errors)


def compile_structured_output_dsl(source: str) -> CompiledStructuredOutputSchema:
    errors = _ErrorCollector()
    definitions = _parse_definitions(source, errors)

    return_definitions = [definition for definition in definitions if definition.kind == "Return"]
    if not return_definitions:
        errors.add("Blueprint must include one Return declaration.")
        errors.raise_if_any()
    return_definition = return_definitions[0]

    schema_definitions = {
        definition.name: definition for definition in definitions if definition.kind == "Schema"
    }

    root_schema = _compile_return_schema(return_definition, schema_definitions, errors)
    compiled_defs = {
        name: _compile_object_schema(definition, schema_definitions, errors)
        for name, definition in schema_definitions.items()
    }
    errors.raise_if_any()

    reachable_defs = _collect_reachable_defs(root_schema, compiled_defs)
    if reachable_defs:
        root_schema["$defs"] = reachable_defs

    errors.extend(_validate_provider_schema_limits(root_schema))
    errors.raise_if_any()

    return CompiledStructuredOutputSchema(
        name=_schema_response_name(return_definition.name),
        schema=root_schema,
    )


def _parse_definitions(source: str, errors: _ErrorCollector) -> list[SchemaDefinition]:
    if not str(source or "").strip():
        errors.add("Blueprint is blank.")
        errors.raise_if_any()

    definitions: list[SchemaDefinition] = []
    current: SchemaDefinition | None = None
    frames: list[_Frame] = []
    schema_names: set[str] = set()
    return_count = 0

    def close_frames_deeper_than(indent: int) -> None:
        while frames and frames[-1].indent > indent:
            frame = frames.pop()
            if frame.is_inline and not frame.fields:
                errors.add(
                    f"Line {frame.opener_line} inline block {frame.opener_name} has no fields."
                )

    def flush_current() -> None:
        nonlocal current
        close_frames_deeper_than(-1)
        frames.clear()
        if current is None:
            return
        if not current.expression and not current.fields:
            errors.add(
                f"{current.kind} {current.name} on line {current.line_number} has no fields."
            )
        definitions.append(current)
        current = None

    for line_number, raw_line in enumerate(textwrap.dedent(source).splitlines(), start=1):
        code, comment = _split_line_comment(raw_line)
        stripped = code.strip()
        description = comment.strip() if comment is not None else ""
        if not stripped:
            # Blank lines and full-line comments are non-semantic.
            continue

        leading = code[: len(code) - len(code.lstrip(" \t"))]
        if "\t" in leading:
            errors.add(f"Line {line_number} uses a tab for indentation.")
            continue
        if comment is not None and not description:
            errors.add(f"Line {line_number} has an empty trailing comment.")

        indent = len(leading)
        block_match = _BLOCK_DECLARATION_RE.match(stripped)
        return_match = _RETURN_EXPRESSION_RE.match(stripped)

        if indent == 0:
            if block_match:
                flush_current()
                kind, name = block_match.group(1), block_match.group(2)
                if kind == "Schema":
                    if name in schema_names:
                        errors.add(f"{name} is declared more than once.")
                    schema_names.add(name)
                else:
                    return_count += 1
                    if return_count > 1:
                        errors.add("Blueprint may include only one Return declaration.")
                    if name in schema_names:
                        errors.add(
                            f"Return {name}: conflicts with Schema {name}. "
                            f"Use Return {name} to alias that schema."
                        )
                current = SchemaDefinition(
                    kind=kind,
                    name=name,
                    line_number=line_number,
                    description=description,
                )
                frames.append(
                    _Frame(
                        indent=2,
                        fields=current.fields,
                        opener_line=line_number,
                        opener_name=name,
                        is_inline=False,
                    )
                )
                continue

            if return_match:
                flush_current()
                return_count += 1
                if return_count > 1:
                    errors.add("Blueprint may include only one Return declaration.")
                expression = return_match.group(1).strip()
                if expression.endswith(":"):
                    errors.add(
                        f"Line {line_number} Return type expressions must not end with a colon."
                    )
                    expression = expression.rstrip(":").strip()
                definitions.append(
                    SchemaDefinition(
                        kind="Return",
                        name=_return_expression_name(expression),
                        line_number=line_number,
                        expression=expression,
                        description=description,
                    )
                )
                continue

            errors.add(f"Line {line_number} is not a Schema or Return declaration.")
            continue

        if current is None:
            errors.add(f"Line {line_number} has a field before any declaration.")
            continue

        if indent % 2 != 0:
            errors.add(f"Line {line_number} must be indented in steps of two spaces.")
            continue

        close_frames_deeper_than(indent)
        if not frames or frames[-1].indent != indent:
            errors.add(f"Line {line_number} has unexpected indentation.")
            continue

        match = _FIELD_RE.match(stripped)
        if not match:
            errors.add(f"Line {line_number} is not a valid field definition.")
            continue

        field_name = match.group(1)
        rest = match.group(2).strip()
        parent_fields = frames[-1].fields
        if any(existing.name == field_name for existing in parent_fields):
            owner = frames[-1].opener_name
            errors.add(f"Field {field_name} is declared more than once in {owner}.")
            continue

        if not rest:
            node = FieldNode(
                name=field_name,
                line_number=line_number,
                kind="object",
                description=description,
            )
            parent_fields.append(node)
            frames.append(
                _Frame(
                    indent=indent + 2,
                    fields=node.children,
                    opener_line=line_number,
                    opener_name=field_name,
                    is_inline=True,
                )
            )
            continue

        if rest.endswith(":"):
            list_match = _LIST_BLOCK_RE.match(rest)
            if not list_match:
                errors.add(
                    f"Line {line_number} only a bare field name or List(...) "
                    "may open an inline block."
                )
                continue
            node = FieldNode(
                name=field_name,
                line_number=line_number,
                kind="list_object",
                description=description,
                list_arguments=list_match.group(1) or "",
            )
            parent_fields.append(node)
            frames.append(
                _Frame(
                    indent=indent + 2,
                    fields=node.children,
                    opener_line=line_number,
                    opener_name=field_name,
                    is_inline=True,
                )
            )
            continue

        parent_fields.append(
            FieldNode(
                name=field_name,
                line_number=line_number,
                kind="leaf",
                expression=rest,
                description=description,
            )
        )

    flush_current()
    return definitions


def _split_line_comment(line: str) -> tuple[str, str | None]:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
            continue
        if character == "#":
            return line[:index], line[index + 1 :]
    return line, None


def _attach_description(schema: dict[str, Any], description: str) -> dict[str, Any]:
    if description:
        schema["description"] = description
    return schema


def _compile_return_schema(
    definition: SchemaDefinition,
    schema_definitions: dict[str, SchemaDefinition],
    errors: _ErrorCollector,
) -> dict[str, Any]:
    if not definition.expression:
        return _compile_object_schema(definition, schema_definitions, errors)
    if definition.expression in schema_definitions:
        schema = _compile_object_schema(
            schema_definitions[definition.expression],
            schema_definitions,
            errors,
        )
        return _attach_description(schema, definition.description)
    try:
        schema = _compile_type_expression(
            definition.expression,
            schema_definitions,
            definition.line_number,
        )
    except StructuredOutputDslError as error:
        errors.extend(error.errors)
        schema = {"type": "object", "properties": {}, "additionalProperties": False}
    return _attach_description(schema, definition.description)


def _compile_object_schema(
    definition: SchemaDefinition,
    schema_definitions: dict[str, SchemaDefinition],
    errors: _ErrorCollector,
) -> dict[str, Any]:
    schema = _compile_fields_schema(definition.fields, schema_definitions, errors)
    return _attach_description(schema, definition.description)


def _compile_fields_schema(
    fields: list[FieldNode],
    schema_definitions: dict[str, SchemaDefinition],
    errors: _ErrorCollector,
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for node in fields:
        try:
            properties[node.name] = _compile_field(node, schema_definitions, errors)
        except StructuredOutputDslError as error:
            errors.extend(error.errors)
            properties[node.name] = {"type": "string"}
    return {
        "type": "object",
        "properties": properties,
        "required": [node.name for node in fields],
        "additionalProperties": False,
    }


def _compile_field(
    node: FieldNode,
    schema_definitions: dict[str, SchemaDefinition],
    errors: _ErrorCollector,
) -> dict[str, Any]:
    if node.kind == "object":
        schema = _compile_fields_schema(node.children, schema_definitions, errors)
        return _attach_description(schema, node.description)

    if node.kind == "list_object":
        items = _compile_fields_schema(node.children, schema_definitions, errors)
        schema = {"type": "array", "items": items}
        arguments = _parse_optional_arguments(node.list_arguments, node.line_number)
        schema = _apply_list_arguments(schema, arguments, "List", node.line_number)
        return _attach_description(schema, node.description)

    schema = _compile_type_expression(node.expression, schema_definitions, node.line_number)
    return _attach_description(schema, node.description)


def _flatten_union_branches(schema: dict[str, Any]) -> list[dict[str, Any]]:
    if set(schema.keys()) == {"anyOf"} and isinstance(schema.get("anyOf"), list):
        return list(schema["anyOf"])
    return [schema]


def _build_union(branches: list[dict[str, Any]], line_number: int) -> dict[str, Any]:
    seen: set[str] = set()
    for branch in branches:
        key = json.dumps(branch, sort_keys=True)
        if key in seen:
            raise StructuredOutputDslError(f"Line {line_number} has a duplicate union branch.")
        seen.add(key)
    return {"anyOf": branches}


def _compile_type_expression(
    expression: str,
    schema_definitions: dict[str, SchemaDefinition],
    line_number: int,
) -> dict[str, Any]:
    parts = _split_top_level(expression, "|")
    if len(parts) > 1:
        branches: list[dict[str, Any]] = []
        for part in parts:
            if not part:
                raise StructuredOutputDslError(f"Line {line_number} has an empty union branch.")
            branches.extend(
                _flatten_union_branches(_compile_single_type(part, schema_definitions, line_number))
            )
        return _build_union(branches, line_number)
    if not parts or not parts[0]:
        raise StructuredOutputDslError(f"Line {line_number} has a blank type expression.")
    return _compile_single_type(parts[0], schema_definitions, line_number)


def _compile_single_type(
    expression: str,
    schema_definitions: dict[str, SchemaDefinition],
    line_number: int,
) -> dict[str, Any]:
    if not expression:
        raise StructuredOutputDslError(f"Line {line_number} has a blank type expression.")
    if expression == "None":
        return {"type": "null"}
    if expression.startswith("List["):
        return _compile_list_type(expression, schema_definitions, line_number)
    if expression.startswith("Enum["):
        return _compile_enum_type(expression, line_number)
    if expression.startswith("Optional["):
        return _compile_optional_type(expression, schema_definitions, line_number)

    match = _TYPE_NAME_RE.match(expression)
    if not match:
        raise StructuredOutputDslError(f"Line {line_number} has an invalid type expression.")
    type_name = match.group(1)
    suffix = match.group(2).strip()

    if type_name in {"List", "Enum", "Optional"} and suffix.startswith("["):
        raise StructuredOutputDslError(
            f"Line {line_number} has a space before [ in {type_name}[...]; remove the space."
        )
    if type_name == "Optional":
        raise StructuredOutputDslError(
            f"Line {line_number} Optional requires a wrapped type, like Optional[String]."
        )

    arguments = _parse_optional_arguments(suffix, line_number)

    if type_name == "Boolean":
        _reject_arguments(type_name, arguments, line_number)
        return {"type": "boolean"}
    if type_name == "Integer":
        return _apply_number_arguments({"type": "integer"}, arguments, type_name, line_number)
    if type_name == "Float":
        return _apply_number_arguments({"type": "number"}, arguments, type_name, line_number)
    if type_name == "String":
        return _apply_string_arguments({"type": "string"}, arguments, type_name, line_number)
    if type_name in _STRING_FORMAT_TYPES:
        schema: dict[str, Any] = {"type": "string", "format": _STRING_FORMAT_TYPES[type_name]}
        return _apply_string_arguments(schema, arguments, type_name, line_number)
    if type_name in schema_definitions:
        _reject_arguments(type_name, arguments, line_number)
        return {"$ref": f"#/$defs/{type_name}"}

    suggestion = _TYPE_SUGGESTIONS.get(type_name, "")
    if suggestion is None:
        raise StructuredOutputDslError(
            f"Line {line_number} uses unknown type {type_name}. Blueprint does not support "
            "map types; use an inline block or a Schema."
        )
    if suggestion:
        raise StructuredOutputDslError(
            f"Line {line_number} uses unknown type {type_name}. Did you mean {suggestion}?"
        )
    raise StructuredOutputDslError(f"Line {line_number} uses unknown type {type_name}.")


def _compile_optional_type(
    expression: str,
    schema_definitions: dict[str, SchemaDefinition],
    line_number: int,
) -> dict[str, Any]:
    inner, suffix = _read_bracket_body(expression, "Optional", line_number)
    if suffix:
        raise StructuredOutputDslError(f"Line {line_number} Optional does not accept arguments.")
    if inner == "None":
        raise StructuredOutputDslError(f"Line {line_number} Optional[None] is redundant; use None.")

    compiled = _compile_type_expression(inner, schema_definitions, line_number)
    branches = _flatten_union_branches(compiled)
    if any(branch == {"type": "null"} for branch in branches):
        raise StructuredOutputDslError(
            f"Line {line_number} Optional wraps a type that is already nullable."
        )
    branches.append({"type": "null"})
    return _build_union(branches, line_number)


def _compile_list_type(
    expression: str,
    schema_definitions: dict[str, SchemaDefinition],
    line_number: int,
) -> dict[str, Any]:
    inner, suffix = _read_bracket_body(expression, "List", line_number)
    arguments = _parse_optional_arguments(suffix, line_number)
    schema: dict[str, Any] = {
        "type": "array",
        "items": _compile_type_expression(inner, schema_definitions, line_number),
    }
    return _apply_list_arguments(schema, arguments, "List", line_number)


def _compile_enum_type(expression: str, line_number: int) -> dict[str, Any]:
    inner, suffix = _read_bracket_body(expression, "Enum", line_number)
    arguments = _parse_optional_arguments(suffix, line_number)
    _reject_arguments("Enum", arguments, line_number)

    values: list[Any] = []
    for item in _split_top_level(inner, ","):
        if not item:
            raise StructuredOutputDslError(
                f"Line {line_number} Enum has an empty value; remove the extra comma."
            )
        value = _parse_literal(item, line_number)
        if not isinstance(value, str | int | float | bool):
            raise StructuredOutputDslError(
                f"Line {line_number} Enum values must be strings, numbers, or booleans."
            )
        values.append(value)

    if not values:
        raise StructuredOutputDslError(f"Line {line_number} Enum must include at least one value.")
    if len(values) != len(set(values)):
        raise StructuredOutputDslError(f"Line {line_number} Enum values must be unique.")

    if all(isinstance(value, bool) for value in values):
        enum_type = "boolean"
    elif all(isinstance(value, str) for value in values):
        enum_type = "string"
    elif all(isinstance(value, int | float) and not isinstance(value, bool) for value in values):
        enum_type = "integer" if all(isinstance(value, int) for value in values) else "number"
    else:
        raise StructuredOutputDslError(
            f"Line {line_number} Enum values must all be strings, all numbers, or all booleans."
        )
    return {"type": enum_type, "enum": values}


def _read_bracket_body(expression: str, type_name: str, line_number: int) -> tuple[str, str]:
    prefix = f"{type_name}["
    if not expression.startswith(prefix):
        raise StructuredOutputDslError(f"Line {line_number} has an invalid {type_name} expression.")

    depth = 0
    quote: str | None = None
    escaped = False
    for index, character in enumerate(expression[len(type_name) :], start=len(type_name)):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
            continue
        if character == "[":
            depth += 1
            continue
        if character == "]":
            depth -= 1
            if depth == 0:
                inner = expression[len(prefix) : index]
                suffix = expression[index + 1 :].strip()
                if not inner.strip():
                    raise StructuredOutputDslError(f"Line {line_number} {type_name} body is blank.")
                return inner.strip(), suffix
    raise StructuredOutputDslError(f"Line {line_number} has an unclosed {type_name} bracket.")


def _parse_optional_arguments(suffix: str, line_number: int) -> dict[str, Any]:
    if not suffix:
        return {}
    if not suffix.startswith("(") or not suffix.endswith(")"):
        raise StructuredOutputDslError(f"Line {line_number} has an invalid type argument list.")
    argument_body = suffix[1:-1].strip()
    if not argument_body:
        return {}

    arguments: dict[str, Any] = {}
    for item in _split_top_level(argument_body, ","):
        if not item:
            raise StructuredOutputDslError(
                f"Line {line_number} has an extra comma in the argument list."
            )
        if "=" not in item:
            raise StructuredOutputDslError(f"Line {line_number} type arguments must use key=value.")
        name, raw_value = item.split("=", 1)
        argument_name = name.strip()
        if not _ARGUMENT_NAME_RE.match(argument_name):
            raise StructuredOutputDslError(
                f"Line {line_number} has invalid argument {argument_name}."
            )
        if argument_name in arguments:
            raise StructuredOutputDslError(f"Line {line_number} repeats argument {argument_name}.")
        arguments[argument_name] = _parse_literal(raw_value.strip(), line_number)
    return arguments


def _parse_literal(value: str, line_number: int) -> Any:
    if not value:
        raise StructuredOutputDslError(f"Line {line_number} has a blank literal.")
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        pass

    try:
        if any(character in value for character in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError as error:
        raise StructuredOutputDslError(
            f"Line {line_number} has invalid literal {value}."
        ) from error


def _apply_string_arguments(
    schema: dict[str, Any],
    arguments: dict[str, Any],
    type_name: str,
    line_number: int,
) -> dict[str, Any]:
    _reject_unknown_arguments(
        type_name,
        arguments,
        set(_TYPE_ARGUMENTS_BY_NAME.get(type_name, frozenset(_STRING_ARGUMENTS))),
        line_number,
    )
    if "min" in arguments:
        schema["minLength"] = _read_nonnegative_int_argument(arguments["min"], "min", line_number)
    if "max" in arguments:
        schema["maxLength"] = _read_nonnegative_int_argument(arguments["max"], "max", line_number)
    if (
        "minLength" in schema
        and "maxLength" in schema
        and schema["minLength"] > schema["maxLength"]
    ):
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} min cannot be greater than max."
        )
    return schema


def _apply_number_arguments(
    schema: dict[str, Any],
    arguments: dict[str, Any],
    type_name: str,
    line_number: int,
) -> dict[str, Any]:
    _reject_unknown_arguments(type_name, arguments, set(_NUMBER_ARGUMENTS), line_number)
    if "min" in arguments:
        schema["minimum"] = _read_number_argument(arguments["min"], "min", line_number)
    if "max" in arguments:
        schema["maximum"] = _read_number_argument(arguments["max"], "max", line_number)
    if "exclusive_min" in arguments:
        schema["exclusiveMinimum"] = _read_number_argument(
            arguments["exclusive_min"],
            "exclusive_min",
            line_number,
        )
    if "exclusive_max" in arguments:
        schema["exclusiveMaximum"] = _read_number_argument(
            arguments["exclusive_max"],
            "exclusive_max",
            line_number,
        )
    if "multiple_of" in arguments:
        multiple_of = _read_number_argument(
            arguments["multiple_of"],
            "multiple_of",
            line_number,
        )
        if multiple_of <= 0:
            raise StructuredOutputDslError(
                f"Line {line_number} {type_name} multiple_of must be greater than zero."
            )
        schema["multipleOf"] = multiple_of
    _validate_number_bounds(schema, type_name, line_number)
    return schema


def _apply_list_arguments(
    schema: dict[str, Any],
    arguments: dict[str, Any],
    type_name: str,
    line_number: int,
) -> dict[str, Any]:
    _reject_unknown_arguments(type_name, arguments, set(_LIST_ARGUMENTS), line_number)
    if "min" in arguments:
        schema["minItems"] = _read_nonnegative_int_argument(arguments["min"], "min", line_number)
    if "max" in arguments:
        schema["maxItems"] = _read_nonnegative_int_argument(arguments["max"], "max", line_number)
    if "minItems" in schema and "maxItems" in schema and schema["minItems"] > schema["maxItems"]:
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} min cannot be greater than max."
        )
    return schema


def _validate_number_bounds(
    schema: dict[str, Any],
    type_name: str,
    line_number: int,
) -> None:
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    exclusive_minimum = schema.get("exclusiveMinimum")
    exclusive_maximum = schema.get("exclusiveMaximum")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} min cannot be greater than max."
        )
    if exclusive_minimum is not None and maximum is not None and exclusive_minimum >= maximum:
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} exclusive_min must be less than max."
        )
    if minimum is not None and exclusive_maximum is not None and minimum >= exclusive_maximum:
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} min must be less than exclusive_max."
        )
    if (
        exclusive_minimum is not None
        and exclusive_maximum is not None
        and exclusive_minimum >= exclusive_maximum
    ):
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} exclusive_min must be less than exclusive_max."
        )


def _reject_arguments(
    type_name: str,
    arguments: dict[str, Any],
    line_number: int,
) -> None:
    if arguments:
        argument_names = ", ".join(sorted(arguments))
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} does not accept arguments: {argument_names}."
        )


def _reject_unknown_arguments(
    type_name: str,
    arguments: dict[str, Any],
    allowed: set[str],
    line_number: int,
) -> None:
    unknown = sorted(set(arguments) - allowed)
    if not unknown:
        return
    if "pattern" in unknown:
        raise StructuredOutputDslError(
            f"Line {line_number} {type_name} no longer supports pattern; use a format "
            "type or a trailing # description instead."
        )
    raise StructuredOutputDslError(
        f"Line {line_number} {type_name} does not accept arguments: {', '.join(unknown)}."
    )


def _read_nonnegative_int_argument(value: Any, name: str, line_number: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StructuredOutputDslError(
            f"Line {line_number} argument {name} must be a nonnegative integer."
        )
    return value


def _read_number_argument(value: Any, name: str, line_number: int) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise StructuredOutputDslError(f"Line {line_number} argument {name} must be a number.")
    return value


def _split_top_level(value: str, separator: str) -> list[str]:
    parts: list[str] = []
    start = 0
    bracket_depth = 0
    paren_depth = 0
    quote: str | None = None
    escaped = False

    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
            continue
        if character == "[":
            bracket_depth += 1
            continue
        if character == "]":
            bracket_depth -= 1
            continue
        if character == "(":
            paren_depth += 1
            continue
        if character == ")":
            paren_depth -= 1
            continue
        if character == separator and bracket_depth == 0 and paren_depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1

    parts.append(value[start:].strip())
    return parts


def _collect_reachable_defs(
    root_schema: dict[str, Any],
    compiled_defs: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    def collect_refs(node: Any, found: set[str]) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                found.add(ref.removeprefix("#/$defs/"))
            for value in node.values():
                collect_refs(value, found)
        elif isinstance(node, list):
            for item in node:
                collect_refs(item, found)

    reachable: set[str] = set()
    collect_refs(root_schema, reachable)
    pending = [name for name in reachable if name in compiled_defs]
    while pending:
        name = pending.pop()
        found: set[str] = set()
        collect_refs(compiled_defs[name], found)
        for candidate in found:
            if candidate not in reachable and candidate in compiled_defs:
                reachable.add(candidate)
                pending.append(candidate)

    return {name: schema for name, schema in compiled_defs.items() if name in reachable}


def _validate_provider_schema_limits(schema: dict[str, Any]) -> list[str]:
    stats = {
        "properties": 0,
        "string_length": 0,
        "enum_values": 0,
        "max_depth": 0,
    }
    limit_errors: list[str] = []

    def visit(node: Any, depth: int) -> None:
        if not isinstance(node, dict):
            return

        if "$defs" in node:
            defs = node.get("$defs")
            if isinstance(defs, dict):
                for name, definition in defs.items():
                    stats["string_length"] += len(str(name))
                    visit(definition, 1)

        description = node.get("description")
        if isinstance(description, str):
            stats["string_length"] += len(description)

        enum_values = node.get("enum")
        if isinstance(enum_values, list):
            stats["enum_values"] += len(enum_values)
            enum_string_length = sum(len(value) for value in enum_values if isinstance(value, str))
            stats["string_length"] += enum_string_length
            if (
                len(enum_values) > _MAX_LARGE_ENUM_VALUES
                and enum_string_length > _MAX_LARGE_ENUM_STRING_LENGTH
            ):
                limit_errors.append(
                    "Blueprint enum string length exceeds provider limit for large enums."
                )

        node_type = node.get("type")
        if node_type == "object" or "properties" in node:
            stats["max_depth"] = max(stats["max_depth"], depth)
            properties = node.get("properties")
            if isinstance(properties, dict):
                stats["properties"] += len(properties)
                for name, property_schema in properties.items():
                    stats["string_length"] += len(str(name))
                    visit(property_schema, depth + 1)

        if node_type == "array" or "items" in node:
            stats["max_depth"] = max(stats["max_depth"], depth)
            visit(node.get("items"), depth + 1)

        any_of = node.get("anyOf")
        if isinstance(any_of, list):
            for item in any_of:
                visit(item, depth + 1)

    visit(schema, 1)

    if stats["properties"] > _MAX_SCHEMA_PROPERTIES:
        limit_errors.append(
            "Blueprint schema exceeds provider limit of "
            f"{_MAX_SCHEMA_PROPERTIES:,} total object properties."
        )
    if stats["max_depth"] > _MAX_SCHEMA_DEPTH:
        limit_errors.append(
            f"Blueprint schema exceeds provider limit of {_MAX_SCHEMA_DEPTH} nesting levels."
        )
    if stats["string_length"] > _MAX_SCHEMA_STRING_LENGTH:
        limit_errors.append(
            "Blueprint schema exceeds provider limit of "
            f"{_MAX_SCHEMA_STRING_LENGTH:,} schema string characters."
        )
    if stats["enum_values"] > _MAX_SCHEMA_ENUM_VALUES:
        limit_errors.append(
            "Blueprint schema exceeds provider limit of "
            f"{_MAX_SCHEMA_ENUM_VALUES:,} total enum values."
        )
    return limit_errors


def _return_expression_name(expression: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]*|\d+", expression)
    if not words:
        return "structured_output"
    return "".join(word[:1].upper() + word[1:] for word in words)


def _schema_response_name(value: str) -> str:
    words = re.sub(r"(?<!^)([A-Z])", r"_\1", value).lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", words).strip("_")
    return normalized or "structured_output"
