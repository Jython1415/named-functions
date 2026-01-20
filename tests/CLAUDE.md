# Testing Infrastructure

This directory contains the test suite for the named-functions project scripts.

## Context for Claude Code

When working with this repository, understand that:

1. **Testing Philosophy**: We use integration tests rather than unit tests. The scripts (`generate_readme.py`, `lint_formulas.py`) are treated as black boxes - we test their public APIs and expected behavior, not internal implementation details.

2. **Why Integration Tests**: The formula parsing and expansion logic is complex and has gone through several iterations. Internal implementation may change (pyparsing vs regex, depth filtering, etc.), but the external contract (valid formulas expand correctly, invalid formulas error) should remain stable.

3. **Test Coverage Priorities**:
   - All existing formulas must validate and expand successfully
   - Dependency graph construction and cycle detection must work
   - Formula YAML schema validation must catch malformed files
   - Edge cases from issues #95 and #96 should be added as tests when implementing fixes

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_generate_readme_integration.py -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=term-missing
```

## Test Organization

### `test_generate_readme_integration.py`
Integration tests for `scripts/generate_readme.py`:
- **TestReadmeGeneration**: Tests that the generator runs, parses formulas, builds dependency graphs, and detects cycles
- **TestFormulaValidation**: Tests YAML schema validation (required fields, data types, etc.)
- **TestExistingFormulas**: Validates that all current formulas in `formulas/` directory pass validation and have no circular dependencies

**Important**: These tests run against the actual `formulas/*.yaml` files in the repository. If formulas are added/modified, these tests will automatically validate them.

## Adding New Tests

When fixing bugs or adding features to `scripts/generate_readme.py` or `scripts/lint_formulas.py`:

1. **Add tests for the bug/feature first** (TDD approach when possible)
2. **Use integration-level tests** - test the public API, not internals
3. **Test real-world scenarios** - use actual formula patterns from the `formulas/` directory
4. **Consider edge cases** - especially for parsing (see issue #96 for known edge cases)

Example test pattern:
```python
def test_feature_name(self):
    """Test that [specific behavior] works correctly."""
    import generate_readme

    # Setup: Create test data
    formulas = [...]

    # Execute: Call the public API
    result = generate_readme.some_function(formulas)

    # Assert: Verify expected behavior
    assert result meets_expectations
```

## CI Integration

Tests run automatically on every push and PR via `.github/workflows/ci.yml`:
- Installs pytest, pyyaml, pyparsing
- Runs pytest test suite
- Runs linter on all formulas
- Runs README generation and verifies it's up to date

If tests fail in CI, the PR cannot be merged.

## Known Testing Gaps

Based on issues #95 and #96, future work should add tests for:

1. **Formula expansion failures** (issue #95):
   - Test that expansion failures cause the script to exit with non-zero code
   - Test that partially expanded formulas are detected and rejected

2. **Parsing edge cases** (issue #96):
   - Escaped quotes in strings: `"Say \"Hello\""`
   - Complex nested LET/LAMBDA structures
   - String concatenation with `&` operator
   - Array formulas with `;` separators
   - Range operators in arguments
   - Multiple calls to same function

3. **Linter rules**:
   - Test each linter rule individually (see `test_linter.py` for comprehensive examples)
   - Test that invalid formulas are caught
   - Test that valid formulas pass
   - Parameter examples rule (`require-parameter-examples`): All parameters must have non-empty `example` fields; test edge cases like zero (`0`), falsy values, quoted strings (`'""'`), and function calls (`BLANK()`)

## Dependencies

Tests require:
- `pytest` - Test runner
- `pyyaml` - For reading formula YAML files
- `pyparsing` - For formula parsing (used by generate_readme.py)

These are automatically installed by CI. For local development:
```bash
uv pip install --system pytest pyyaml pyparsing
```
