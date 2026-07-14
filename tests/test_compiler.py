from __future__ import annotations

import pytest

from blueprint_dsl import StructuredOutputDslError, compile_structured_output_dsl


def test_compile_structured_output_dsl_builds_strict_schema() -> None:
    compiled = compile_structured_output_dsl(
        """
        Schema Friend:
          name: String(min=1)
          ranking: Float(min=0.0, max=1.0)
          email: Email

        Return Person:
          name: String(min=1)
          age: Integer | None
          active: Boolean
          tags: List[String]
          status: Enum["draft", "final"]
          friends: List[Friend]
        """
    )

    assert compiled.name == "person"
    assert compiled.schema["additionalProperties"] is False
    assert compiled.schema["required"] == [
        "name",
        "age",
        "active",
        "tags",
        "status",
        "friends",
    ]
    assert compiled.schema["properties"]["name"] == {"type": "string", "minLength": 1}
    assert compiled.schema["properties"]["age"] == {
        "anyOf": [{"type": "integer"}, {"type": "null"}]
    }
    assert compiled.schema["properties"]["status"] == {
        "type": "string",
        "enum": ["draft", "final"],
    }
    assert compiled.schema["properties"]["friends"] == {
        "type": "array",
        "items": {"$ref": "#/$defs/Friend"},
    }
    assert compiled.schema["$defs"]["Friend"] == {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "ranking": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["name", "ranking", "email"],
        "additionalProperties": False,
    }


def test_compile_structured_output_dsl_supports_return_schema_alias() -> None:
    compiled = compile_structured_output_dsl(
        """
        Schema Person:
          name: String

        Return Person
        """
    )

    assert compiled.name == "person"
    assert compiled.schema["type"] == "object"
    assert compiled.schema["properties"] == {"name": {"type": "string"}}
    assert compiled.schema["required"] == ["name"]
    assert compiled.schema["additionalProperties"] is False
    # The aliased schema is inlined at the root, so no duplicate copy ships in $defs.
    assert "$defs" not in compiled.schema


def test_compile_structured_output_dsl_supports_root_array_return_expression() -> None:
    compiled = compile_structured_output_dsl(
        """
        Schema Person:
          name: String

        Return List[Person]
        """
    )

    assert compiled.name == "list_person"
    assert compiled.schema["type"] == "array"
    assert compiled.schema["items"] == {"$ref": "#/$defs/Person"}
    assert compiled.schema["$defs"]["Person"] == {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }


def test_compile_structured_output_dsl_supports_string_formats_and_list_bounds() -> None:
    compiled = compile_structured_output_dsl(
        """
        Return Event:
          id: Uuid
          starts_at: Datetime
          guests: List[Email](min=1, max=4)
        """
    )

    assert compiled.schema["properties"]["id"] == {"type": "string", "format": "uuid"}
    assert compiled.schema["properties"]["starts_at"] == {
        "type": "string",
        "format": "date-time",
    }
    assert compiled.schema["properties"]["guests"] == {
        "type": "array",
        "items": {"type": "string", "format": "email"},
        "minItems": 1,
        "maxItems": 4,
    }


def test_compile_structured_output_dsl_rejects_unknown_types() -> None:
    with pytest.raises(StructuredOutputDslError, match="unknown type Address"):
        compile_structured_output_dsl(
            """
            Return Contact:
              address: Address
            """
        )


def test_compile_structured_output_dsl_requires_exactly_one_return() -> None:
    with pytest.raises(StructuredOutputDslError, match="one Return"):
        compile_structured_output_dsl(
            """
            Schema Person:
              name: String
            """
        )

    with pytest.raises(StructuredOutputDslError, match="only one Return"):
        compile_structured_output_dsl(
            """
            Return Person:
              name: String

            Return Animal:
              name: String
            """
        )


def test_compile_structured_output_dsl_rejects_duplicate_fields() -> None:
    with pytest.raises(StructuredOutputDslError, match="declared more than once"):
        compile_structured_output_dsl(
            """
            Return Person:
              name: String
              name: String
            """
        )


def test_compile_structured_output_dsl_rejects_unsupported_arguments() -> None:
    with pytest.raises(StructuredOutputDslError, match="does not accept arguments"):
        compile_structured_output_dsl(
            """
            Return Person:
              active: Boolean(min=1)
            """
        )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            """
            Return Person:
              name: String(min=5, max=2)
            """,
            "String min cannot be greater than max",
        ),
        (
            """
            Return Person:
              scores: List[Integer](min=3, max=1)
            """,
            "List min cannot be greater than max",
        ),
        (
            """
            Return Person:
              rating: Float(min=10, exclusive_max=10)
            """,
            "Float min must be less than exclusive_max",
        ),
        (
            """
            Return Person:
              count: Integer(multiple_of=0)
            """,
            "Integer multiple_of must be greater than zero",
        ),
    ],
)
def test_compile_structured_output_dsl_rejects_unsatisfiable_constraints(
    source: str,
    message: str,
) -> None:
    with pytest.raises(StructuredOutputDslError, match=message):
        compile_structured_output_dsl(source)


def test_compile_structured_output_dsl_rejects_provider_property_limit() -> None:
    fields = "\n".join(f"  field_{index}: String" for index in range(5001))

    with pytest.raises(StructuredOutputDslError, match="5,000 total object properties"):
        compile_structured_output_dsl(f"Return Large:\n{fields}")


def test_compile_structured_output_dsl_rejects_provider_enum_limit() -> None:
    values = ", ".join(f'"value_{index}"' for index in range(1001))

    with pytest.raises(StructuredOutputDslError, match="1,000 total enum values"):
        compile_structured_output_dsl(
            f"""
            Return Large:
              status: Enum[{values}]
            """
        )


def test_compile_structured_output_dsl_rejects_provider_depth_limit() -> None:
    expression = "String"
    for _ in range(10):
        expression = f"List[{expression}]"

    with pytest.raises(StructuredOutputDslError, match="10 nesting levels"):
        compile_structured_output_dsl(
            f"""
            Return Deep:
              value: {expression}
            """
        )


def test_compile_structured_output_dsl_rejects_large_enum_string_limit() -> None:
    values = ", ".join(f'"value_{index:03d}_{"x" * 52}"' for index in range(251))

    with pytest.raises(StructuredOutputDslError, match="enum string length"):
        compile_structured_output_dsl(
            f"""
            Return Large:
              status: Enum[{values}]
            """
        )


def test_compile_structured_output_dsl_compiles_trailing_comments_to_descriptions() -> None:
    compiled = compile_structured_output_dsl(
        """
        # Full-line comments stay non-semantic.
        Schema Friend:  # a person in the friends list
          name: String  # display name

        Return Person:  # the primary output object
          name: String(min=1)  # legal name
          friend: Friend  # closest friend
          plain: String
        """
    )

    assert compiled.schema["description"] == "the primary output object"
    assert compiled.schema["properties"]["name"] == {
        "type": "string",
        "minLength": 1,
        "description": "legal name",
    }
    assert compiled.schema["properties"]["friend"] == {
        "$ref": "#/$defs/Friend",
        "description": "closest friend",
    }
    assert "description" not in compiled.schema["properties"]["plain"]
    assert compiled.schema["$defs"]["Friend"]["description"] == "a person in the friends list"
    assert compiled.schema["$defs"]["Friend"]["properties"]["name"]["description"] == (
        "display name"
    )


def test_compile_structured_output_dsl_rejects_empty_trailing_comment() -> None:
    with pytest.raises(StructuredOutputDslError, match="empty trailing comment"):
        compile_structured_output_dsl(
            """
            Return Person:
              name: String  #
            """
        )


def test_compile_structured_output_dsl_supports_inline_object_blocks() -> None:
    compiled = compile_structured_output_dsl(
        """
        Return Order:
          id: Uuid
          customer:  # buyer details
            name: String(min=1)
            email: Email
          items: List(min=1):
            sku: String
            qty: Integer(min=1)
        """
    )

    customer = compiled.schema["properties"]["customer"]
    assert customer["type"] == "object"
    assert customer["description"] == "buyer details"
    assert customer["properties"]["email"] == {"type": "string", "format": "email"}
    assert customer["required"] == ["name", "email"]
    assert customer["additionalProperties"] is False

    items = compiled.schema["properties"]["items"]
    assert items["type"] == "array"
    assert items["minItems"] == 1
    assert items["items"]["properties"]["qty"] == {"type": "integer", "minimum": 1}
    assert items["items"]["required"] == ["sku", "qty"]


def test_compile_structured_output_dsl_rejects_empty_inline_block() -> None:
    with pytest.raises(StructuredOutputDslError, match="inline block address has no fields"):
        compile_structured_output_dsl(
            """
            Return Person:
              address:
              name: String
            """
        )


def test_compile_structured_output_dsl_rejects_non_list_inline_block_openers() -> None:
    with pytest.raises(StructuredOutputDslError, match="only a bare field name or List"):
        compile_structured_output_dsl(
            """
            Return Person:
              address: Optional:
                street: String
            """
        )


def test_compile_structured_output_dsl_rejects_bad_indentation() -> None:
    with pytest.raises(StructuredOutputDslError, match="steps of two spaces"):
        compile_structured_output_dsl("Return Person:\n   name: String")

    with pytest.raises(StructuredOutputDslError, match="unexpected indentation"):
        compile_structured_output_dsl("Return Person:\n  name: String\n    extra: String")


def test_compile_structured_output_dsl_supports_optional() -> None:
    compiled = compile_structured_output_dsl(
        """
        Return Person:
          age: Optional[Integer]
          nickname: Optional[String(min=1)]
        """
    )

    assert compiled.schema["properties"]["age"] == {
        "anyOf": [{"type": "integer"}, {"type": "null"}]
    }
    assert compiled.schema["properties"]["nickname"] == {
        "anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]
    }


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("Optional[Integer | None]", "already nullable"),
        ("Optional[Optional[Integer]]", "already nullable"),
        ("Optional[None]", "redundant"),
        ("Optional", "requires a wrapped type"),
    ],
)
def test_compile_structured_output_dsl_rejects_redundant_optional(
    expression: str,
    message: str,
) -> None:
    with pytest.raises(StructuredOutputDslError, match=message):
        compile_structured_output_dsl(f"Return Person:\n  age: {expression}")


def test_compile_structured_output_dsl_supports_typed_enums() -> None:
    compiled = compile_structured_output_dsl(
        """
        Return Rating:
          stars: Enum[1, 2, 3, 4, 5]
          weight: Enum[0.5, 1.0]
          flagged: Enum[True, False]
        """
    )

    assert compiled.schema["properties"]["stars"] == {
        "type": "integer",
        "enum": [1, 2, 3, 4, 5],
    }
    assert compiled.schema["properties"]["weight"] == {"type": "number", "enum": [0.5, 1.0]}
    assert compiled.schema["properties"]["flagged"] == {
        "type": "boolean",
        "enum": [True, False],
    }


def test_compile_structured_output_dsl_rejects_mixed_enum_types() -> None:
    with pytest.raises(StructuredOutputDslError, match="all be strings, all numbers"):
        compile_structured_output_dsl(
            """
            Return Rating:
              value: Enum["low", 2]
            """
        )


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("String | | None", "empty union branch"),
        ("String | String", "duplicate union branch"),
        ("Optional[Integer] | None", "duplicate union branch"),
        ('Enum["a", , "b"]', "empty value"),
        ("String(min=1,, max=3)", "extra comma"),
    ],
)
def test_compile_structured_output_dsl_rejects_sloppy_syntax(
    expression: str,
    message: str,
) -> None:
    with pytest.raises(StructuredOutputDslError, match=message):
        compile_structured_output_dsl(f"Return Person:\n  value: {expression}")


@pytest.mark.parametrize(
    ("type_name", "hint"),
    [
        ("str", "Did you mean String"),
        ("int", "Did you mean Integer"),
        ("bool", "Did you mean Boolean"),
        ("dict", "does not support map types"),
    ],
)
def test_compile_structured_output_dsl_hints_for_common_type_typos(
    type_name: str,
    hint: str,
) -> None:
    with pytest.raises(StructuredOutputDslError, match=hint):
        compile_structured_output_dsl(f"Return Person:\n  value: {type_name}")


def test_compile_structured_output_dsl_hints_for_space_before_bracket() -> None:
    with pytest.raises(StructuredOutputDslError, match="space before"):
        compile_structured_output_dsl("Return Person:\n  tags: List [String]")


def test_compile_structured_output_dsl_rejects_pattern_with_hint() -> None:
    with pytest.raises(StructuredOutputDslError, match="no longer supports pattern"):
        compile_structured_output_dsl(
            """
            Return Person:
              code: String(pattern="^[A-Z]+$")
            """
        )


def test_compile_structured_output_dsl_aggregates_errors() -> None:
    with pytest.raises(StructuredOutputDslError) as exc_info:
        compile_structured_output_dsl(
            """
            Return Person:
              first: str
              second: Address
              third: String | String
            """
        )

    assert len(exc_info.value.errors) == 3
    assert "Did you mean String" in exc_info.value.errors[0]
    assert "unknown type Address" in exc_info.value.errors[1]
    assert "duplicate union branch" in exc_info.value.errors[2]
    assert "(+2 more)" in str(exc_info.value)


def test_compile_structured_output_dsl_prunes_unused_schemas() -> None:
    compiled = compile_structured_output_dsl(
        """
        Schema Used:
          name: String

        Schema Unused:
          name: String

        Return Person:
          friend: Used
        """
    )

    assert set(compiled.schema["$defs"]) == {"Used"}


def test_compile_structured_output_dsl_keeps_recursive_schema_defs() -> None:
    compiled = compile_structured_output_dsl(
        """
        Schema Node:
          label: String
          children: List[Node]

        Return Node
        """
    )

    assert compiled.schema["properties"]["children"]["items"] == {"$ref": "#/$defs/Node"}
    assert compiled.schema["$defs"]["Node"]["properties"]["label"] == {"type": "string"}


def test_compile_structured_output_dsl_counts_descriptions_toward_string_budget() -> None:
    long_description = "d" * 120_001
    with pytest.raises(StructuredOutputDslError, match="schema string characters"):
        compile_structured_output_dsl(f"Return Person:\n  name: String  # {long_description}")


def test_blueprint_type_registry_matches_editor_metadata() -> None:
    from blueprint_dsl import (
        BLUEPRINT_TYPE_REGISTRY,
        blueprint_editor_metadata,
        blueprint_types_by_category,
    )

    metadata = blueprint_editor_metadata()
    assert metadata["declarations"] == ["Schema", "Return"]
    assert metadata["types"] == [info.name for info in BLUEPRINT_TYPE_REGISTRY]

    grouped = blueprint_types_by_category()
    assert set(grouped) == {"primitive", "keyword", "format", "container"}
    assert "Optional" in grouped["container"]


def test_spec_doc_mentions_every_registry_type() -> None:
    from pathlib import Path

    from blueprint_dsl import BLUEPRINT_TYPE_REGISTRY

    doc_path = Path("docs/blueprint.html")
    assert doc_path.exists(), "tracked Blueprint spec doc is missing"
    doc = doc_path.read_text(encoding="utf-8")
    for info in BLUEPRINT_TYPE_REGISTRY:
        assert info.name in doc, f"spec doc is missing type {info.name}"
    assert "pattern=" not in doc, "spec doc still documents the removed pattern argument"


def test_blueprint_spec_card_covers_registry_and_example_compiles() -> None:
    from blueprint_dsl import (
        BLUEPRINT_SPEC_EXAMPLE,
        BLUEPRINT_TYPE_REGISTRY,
        blueprint_spec_card,
    )

    card = blueprint_spec_card()
    for info in BLUEPRINT_TYPE_REGISTRY:
        assert info.name in card, f"spec card is missing type {info.name}"
    assert BLUEPRINT_SPEC_EXAMPLE in card
    assert "RULES" in card and "AVOID" in card

    compiled = compile_structured_output_dsl(BLUEPRINT_SPEC_EXAMPLE)
    assert compiled.name == "person"
