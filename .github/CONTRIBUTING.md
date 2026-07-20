# Contributing to sqlfluff-plugin-legibility

## Development setup

Install the package and test dependencies:

```console
uv sync --extra test
```

Run the checks used by CI:

```console
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

## Changes

- Keep behavior focused on comment legibility.
- Prefer existing SQLFluff rules when they already cover a concern.
- Add passing and failing fixtures for rule changes.
- Update the README when configuration or behavior changes.

## Pull requests

Keep pull requests narrowly scoped and include the commands used for verification.
