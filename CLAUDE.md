# GO-DB Project Commands and Guidelines

## Commands
- Build: `uv sync`, `make all`
- Run: `uv run go-db [args]`
- Lint: `uv run tox -e lint`, `uv run tox -e lint-fix`, `uv run tox -e codespell`, `uv run tox -e codespell-write`
- Test: `uv run pytest` (all), `uv run pytest tests/test_main.py::test_name` (single)
- Note: `make test` runs both pytest and doctests but doctests may fail

## Code Style
- Formatting: Ruff format with 120 line length
- Linting: Ruff with rules B, D, E, F, I, S, W
- Imports: Sorted with isort (via Ruff)
- Types: Use type annotations consistently
- Naming: snake_case for functions/variables, CamelCase for classes
- Documentation: Required docstrings (enforced)
- Error handling: Use descriptive error messages and appropriate exceptions
- Version: Follow PEP-440 versioning style

## SQL Style
- Use uppercase for SQL keywords
- Prefer descriptive view/table names with readable indentation
- Follow GO rule naming conventions for violations views (GORULE_XXXXXXX_violations)
