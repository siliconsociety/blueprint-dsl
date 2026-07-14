# Blueprint DSL — agent guide

Blueprint is a narrow, feature-complete structured-output language. The compiler in
`src/blueprint_dsl/compiler.py`, its public exports, and the tests are one contract.

## Gate

```bash
./gate.sh
```

Green means lint, static analysis, tests, coverage, wheel/sdist build, and package metadata
all passed. Never lower the coverage floor or weaken a language assertion.

## Compatibility

- Support Python 3.12 through 3.14.
- Keep the runtime standard-library-only.
- Preserve strict JSON Schema semantics and line-oriented diagnostics.
- Treat `blueprint/1` as stable language behavior. Bug fixes require regression tests.
- Keep `compile_blueprint` and its established compatibility aliases public.

## Release boundary

Building and checking distributions is normal verification. Publishing to PyPI is a
separate external action and always requires explicit approval.
