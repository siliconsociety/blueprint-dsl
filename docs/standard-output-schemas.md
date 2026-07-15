# Standard output schemas (working design)

Status: proposal for a future release. Names and public APIs in this document are not yet
commitments.

## The idea

Blueprint can ship a small catalog of useful output contracts alongside the compiler. Each
contract would be ordinary, valid Blueprint source: readable by a person, editable in an app,
and compiled by the same `compile_blueprint()` function as user-authored source.

The first candidates will come from repeated production needs. Faithful OCR is one concrete
example:

```text
Return OcrRead:
  transcription: String # Faithful text shown on the page; preserve spelling, capitalization, punctuation, and line breaks. Do not correct, explain, or add commentary.
```

This is deliberately not a new declaration type, import syntax, or hidden compiler mode. A
standard schema should be useful because its source has been carefully designed and tested,
not because the language treats it specially.

## Why it belongs in Blueprint

Writing a valid JSON shape is easy. Writing a durable model contract is harder. Field names,
descriptions, null behavior, constraints, and nesting all influence model behavior. Applications
otherwise repeat that work, drift apart, and lose the exact contract needed to reproduce a
finding.

A compact standard catalog could provide:

- human-readable starting points for common structured-output jobs;
- reviewed field descriptions and conservative provider-compatible constraints;
- stable identifiers for discussing the intended contract;
- exact Blueprint source that applications can display, edit, snapshot, and hash;
- tests against the real compiler and its provider-limit checks.

## Compatibility boundary

Standard schemas should be entirely additive.

- `blueprint/1` grammar and compiler behavior do not change.
- Existing imports and compiled JSON Schema remain unchanged.
- Every bundled contract must compile through the public compiler without privileged behavior.
- Applications may ignore the catalog and continue supplying source directly.
- Selecting a standard contract must never happen implicitly.

Adding the catalog therefore does not require `blueprint/2`. A language version should change
only when source semantics change.

## Source is the product

The primary artifact should be the Blueprint source, not an opaque precompiled JSON Schema.
Callers need to be able to show it to humans, customize it, store it beside a request, and
compile it under the version they actually deployed.

A packaged entry will likely need metadata similar to:

| Field | Purpose |
| --- | --- |
| `id` | Stable machine name, such as `ocr-read` |
| `version` | Contract version independent of the package version |
| `name` | Human-facing name |
| `summary` | Short statement of intended use |
| `source` | Exact Blueprint text |
| `sha256` | Digest for provenance and reproducibility |

The exact Python representation is undecided. A frozen descriptor returned from an explicit
module is preferable to discovery, entry points, or a plugin registry. A possible shape is:

```python
from blueprint_dsl.output_schemas import get_output_schema

contract = get_output_schema("ocr-read", version=1)
compiled = compile_blueprint(contract.source)
```

That example illustrates intent only; it does not reserve the module or function name.

## Versioning rules

A published contract is a reproducibility boundary.

- Cosmetic documentation outside `source` may improve in place.
- Changing field names, types, constraints, or descriptions creates a new contract version.
- Old contract versions remain importable after a new version ships.
- A defect in a contract is fixed by publishing a new version, not silently rewriting history.
- Package releases may add contracts or contract versions without changing the language version.

Applications should still persist the exact source and digest used for each model request. A
catalog identifier is useful provenance, but it is not a substitute for the evidence itself.

## Candidate scope

The initial catalog should stay deliberately small. Candidates should have multiple real uses,
a clear output boundary, and field descriptions that do not smuggle application policy into a
general-purpose package.

Likely early categories include:

- faithful transcription or OCR;
- classification with an explicit label and confidence;
- extraction with explicit uncertainty or null values;
- review output that separates observations from conclusions.

The actual first set remains to be chosen. Production contracts should graduate into the
catalog only after their semantics have been exercised by more than one workflow.

## Release criteria

Before any standard schema becomes public:

1. Its source compiles under `blueprint/1` and stays within provider limits.
2. Tests freeze the source, digest, identifier, version, and compiled JSON Schema.
3. The field descriptions are reviewed as model instructions, not merely documentation.
4. Examples show both direct use and copy-then-customize use.
5. The public API makes version selection explicit and has no discovery magic.
6. The changelog distinguishes additions to the catalog from changes to the language.

## Open questions

- Should the first release expose source constants only, or frozen descriptors with metadata?
- Should callers request `id` plus an integer version, or use a single identifier such as
  `ocr-read/1`?
- Does the catalog need a `list_output_schemas()` helper for editors, or is an exported tuple
  sufficient?
- Which production contracts are mature enough to become the first stable set?
- Should the first catalog API be marked experimental while the contracts themselves are
  versioned and immutable?
