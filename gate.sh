#!/usr/bin/env bash
set -euo pipefail

uv run ruff check .
uv run pyright
uv run pytest --cov=blueprint_dsl --cov-report=term-missing
rm -rf dist
uv build
uv run twine check dist/*
