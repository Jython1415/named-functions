# Tests

This directory contains the test suite for the named-functions project.

## Running Tests

### Run all tests

```bash
pytest tests/ -v
```

### Run specific test file

```bash
pytest tests/test_generate_readme_integration.py -v
```

### Run with coverage

```bash
pytest tests/ --cov=scripts --cov-report=term-missing
```

## Test Organization

- `test_generate_readme_integration.py` - Integration tests for README generation
  - Tests formula validation
  - Tests dependency graph construction
  - Tests cycle detection
  - Tests that all existing formulas are valid

## Adding New Tests

When adding new functionality to `scripts/generate_readme.py` or `scripts/lint_formulas.py`:

1. Add integration tests that verify the complete workflow
2. Focus on testing public APIs and expected behavior
3. Ensure tests work with the current codebase
4. Use pytest fixtures and parametrization where appropriate

## CI Integration

Tests are automatically run on every push and pull request via GitHub Actions.
See `.github/workflows/test.yml` for the CI configuration.

## Dependencies

Tests require:
- pytest
- pyyaml
- pyparsing

These are automatically installed by the CI workflow.
