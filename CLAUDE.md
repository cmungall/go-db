# GO-DB Project Commands and Guidelines

## Commands
- Build: `poetry install`, `make all`
- Run: `poetry run go-db [args]`
- Lint: `tox -e lint`, `tox -e lint-fix`, `tox -e codespell`, `tox -e codespell-write`
- Test: `poetry run pytest` (all), `poetry run pytest tests/test_main.py::test_name` (single)
- Note: `make test` runs both pytest and doctests but doctests may fail

## Code Style
- Formatting: Black with 120 line length
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