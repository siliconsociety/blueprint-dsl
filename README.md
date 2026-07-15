# Blueprint DSL

Blueprint is a small language for declaring the exact JSON object an AI model must return.
It compiles to strict JSON Schema and fails with line-oriented diagnostics when a contract is
invalid or exceeds common structured-output provider limits.

```text
Schema Friend:
  name: String(min=1)
  closeness: Float(min=0.0, max=1.0)

Return Person:
  name: String(min=1)
  age: Optional[Integer]
  address:
    street: String
    city: String
  tags: List[String]
  status: Enum["draft", "final"]
  friends: List[Friend]
```

```python
from blueprint_dsl import compile_blueprint

compiled = compile_blueprint(source)
print(compiled.name)
print(compiled.schema)
```

## Language

A Blueprint contains exactly one `Return Name:` declaration and may contain reusable
`Schema Name:` declarations. Every declared field is required. `Optional[T]` means the
field value may be null; it does not make the field absent.

Supported primitives are `String`, `Integer`, `Float`, and `Boolean`. `None` is available
for nullable unions. Formatted strings include `Date`, `Time`, `Datetime`, `Duration`,
`Email`, `Hostname`, `IPv4`, `IPv6`, and `Uuid`. Containers include `List[T]`, `Enum[...]`,
`Optional[T]`, and unions such as `String | None`.

String and formatted-string `min`/`max` arguments constrain length. Numeric types support
`min`, `max`, `exclusive_min`, `exclusive_max`, and `multiple_of`. Lists support `min` and
`max` item counts. Two-space-indented bare fields create inline objects; `List:` creates an
inline list of objects. Trailing comments become schema descriptions.

`blueprint_spec_card()` returns the complete compact language reference used by Blueprint
editors. `blueprint_editor_metadata()` and `blueprint_types_by_category()` expose the same
canonical type registry for UI tooling.

## Stability

Blueprint is intentionally narrow and feature complete. Version `0.1.0` establishes the
public package API and `blueprint/1` language semantics. Future releases are expected to be
bug fixes unless an actual language defect requires a documented change.

An additive catalog of reusable, versioned output contracts is being considered for a future
release. See [Standard output schemas](docs/standard-output-schemas.md) for the working design.

## Development

Blueprint supports Python 3.12 through 3.14 and has no runtime dependencies.

```bash
./gate.sh
```

The gate runs linting, static analysis, the complete compiler suite with branch coverage,
and a distribution build. PyPI publication is a separate, deliberate release action.

## License

MIT
