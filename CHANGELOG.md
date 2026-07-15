# Changelog

## 0.2.0 — 2026-07-15

- Render decoded JSON results as presentation-only Blueprint instance views.
- Expose framework-neutral syntax tokens and a pretty JSON companion view from
  `blueprint_dsl.render`.
- Preserve the `blueprint/1` language, compiler behavior, diagnostics, and public compatibility
  aliases unchanged.

## 0.1.0 — 2026-07-14

- Extract the complete, production-used Blueprint compiler from Today.
- Compile reusable schemas, inline objects, root arrays, lists, typed enums, optionals,
  unions, constrained primitives, and formatted strings to strict JSON Schema.
- Preserve line-oriented diagnostics, editor metadata, compact specification output, and
  provider schema-limit validation.
- Establish `blueprint/1` as the stable language version.
- Support Python 3.12 through 3.14 with no runtime dependencies.
