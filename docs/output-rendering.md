# Rendering Blueprint output

Blueprint covers both sides of a structured-output interaction:

1. Blueprint source declares the exact value a model must return.
2. `compile_blueprint()` turns that declaration into strict JSON Schema.
3. `render_blueprint_output()` turns the decoded JSON result into a readable Blueprint view.

The rendering API is general-purpose. It knows nothing about OCR, classification, extraction,
or any other application domain.

## Example

```python
from blueprint_dsl.render import render_blueprint_output

value = {
    "summary": "A dragon story",
    "legible": True,
    "flags": ["creative", "unclear"],
}

view = render_blueprint_output(value, name="PageReview")
print(view.text)
```

```text
PageReview:
  summary: A dragon story
  legible: true
  flags:
    - creative
    - unclear
```

`name` is a presentation label. It defaults to `Result` and has no effect on compilation,
validation, schema identity, or the JSON value.

## A view, not another serialization format

Blueprint output is intentionally presentation-only. It resembles Blueprint source so people can
read the contract and its result in the same visual language, but it is not valid Blueprint source
and cannot be parsed back into JSON. Strings are displayed as their values rather than as quoted
JSON literals, including when they contain line breaks.

JSON remains the canonical machine representation. Every `BlueprintOutputView` therefore includes:

- `text`: the human-readable Blueprint view;
- `tokens`: the same view divided into semantic syntax tokens;
- `json_text`: an indented, Unicode-preserving JSON representation of the decoded value.

## Syntax-aware interfaces

`view.tokens` lets a terminal, editor, server-rendered page, or other interface add syntax styling
without Blueprint depending on an application framework. Each frozen `BlueprintOutputToken` has a
`kind` and `text`. Token kinds are `name`, `key`, `string`, `number`, `constant`, `punctuation`, and
`whitespace`.

Consumers must escape token text when inserting it into HTML. Blueprint returns data, not trusted
markup, CSS, or JavaScript.

## Accepted values

The renderer accepts decoded JSON values: objects with string keys, arrays, strings, finite numbers,
booleans, and null. It rejects non-JSON Python values, non-string object keys, non-finite floats, and
circular references with `BlueprintRenderError`.

Object ordering is preserved. Keys that are valid Blueprint field names are displayed directly;
other JSON keys are quoted so the view remains readable. Empty objects and arrays are displayed as
`{}` and `[]`.

The renderer does not validate a value against compiled JSON Schema. Validation belongs to the
provider boundary or application using the contract and would require behavior beyond Blueprint's
standard-library-only runtime.

## Compatibility

Rendering is additive package behavior and does not change the `blueprint/1` grammar, compiler,
diagnostics, compiled JSON Schema, or established imports. Applications that only compile Blueprint
source are unaffected. Applications can adopt `blueprint_dsl.render` independently of how they
store, validate, or display structured results.
