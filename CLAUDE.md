# Named Functions Project

## Documentation Constraints

**CRITICAL**: This file must remain ≤250 lines to ensure it's maintainable and focused. Be prescriptive (how to work with this project), not descriptive (comprehensive documentation). Avoid:
- Specific counts (formulas, tests, lines) that become stale
- Detailed file listings discoverable via exploration
- Redundancy with tests/CLAUDE.md, README.md, or inline docs
- Troubleshooting details (errors are explicit and self-documenting)
- Historical context (use git history and issues)

## Project Overview

This repository contains named Google Sheets formulas using LET and LAMBDA functions. Formulas are defined in YAML files and the README is automatically generated from these definitions.

**Philosophy**: Robustness through fail-fast validation, comprehensive testing, and explicit failures over silent degradation.

## Project Structure

```
named-functions/
├── .github/workflows/*.yml    # CI/CD: test.yml (quality gate), generate-readme.yml, claude.yml
├── formulas/*.yaml            # Individual formula definitions
├── scripts/*.py               # generate_readme.py (parser/expander), lint_formulas.py
├── tests/                     # test_formula_parser.py, test_generate_readme_integration.py
│   └── CLAUDE.md              # Testing philosophy and guidelines
├── pytest.ini                 # Test configuration
├── .readme-template.md        # Template for README generation
└── README.md                  # Auto-generated (DO NOT EDIT DIRECTLY)
```

## Formula YAML Schema

Each `.yaml` file in `formulas/` has this structure:

```yaml
name: FUNCTION_NAME
version: 1.0.0
description: Brief description of what the function does
parameters:
  - name: param1
    description: Description of parameter
    example: "A1:B10"
formula: |
  LET(
    variable, expression,
    result
  )
```

**Key rules:**
- No leading `=` (added during generation)
- Comments supported: `/* block */` and `// line` (auto-stripped)
- Formulas can call other named functions (auto-expanded)

## Development Workflow

### Adding or Modifying Formulas

**CRITICAL 4-STEP PROCESS** (all must succeed for CI to pass):

```bash
# 1. Lint formulas
uv run scripts/lint_formulas.py

# 2. Generate README (validates and expands formulas)
uv run scripts/generate_readme.py

# 3. Run test suite
pytest tests/ -v

# 4. Verify README updated, then commit BOTH files
git diff README.md
git add formulas/your-formula.yaml README.md
git commit -m "Add/update YOUR_FORMULA"
```

**Always commit both**: The `.yaml` file AND the updated `README.md`

### CI/CD

- **test.yml**: Primary quality gate (runs tests, linter, generator, verifies README up-to-date)
- **generate-readme.yml**: Auto-commits README on main, comments on PRs if stale
- **claude.yml**: Claude Code integration (restricted to git, uv, python commands)

**Formula expansion failures block PR merges** - all formulas must be syntactically valid and fully expandable.

## Testing

**Location**: `tests/` directory with pytest

**Run tests:**
```bash
pytest tests/ -v                                    # All tests
pytest tests/ -v --cov=scripts --cov-report=term-missing  # With coverage
```

**Philosophy**: Integration-first approach testing public APIs and expected behavior, not implementation details.

**For details**: See `tests/CLAUDE.md` for testing philosophy, adding tests, and known gaps.

## Parser Architecture

**Design**: 100% pyparsing grammar (no regex fallbacks) supporting all Google Sheets formula constructs.

**Core principles:**
- **Fail-fast**: Invalid syntax blocks CI/CD with explicit `ParseException`
- **Single robust grammar**: No silent degradation or fallback mechanisms
- **Explicit failures**: Grammar gaps surface immediately as errors

**Supported**: Standard Google Sheets syntax including LET, LAMBDA, nested functions, empty arguments (`IF(,,)`), unary operators (`--condition`), arrays, ranges, operators.

**Known limitation**: Google Sheets doubled-quote escaping (`""`) not yet supported - use backslash escaping (`\"`).

**Implementation**: FormulaParser class in `scripts/generate_readme.py`

## Formula Composition

Formulas can call other named functions - the system automatically:
- Detects function calls and expands them recursively
- Substitutes parameters with arguments (word-boundary matching)
- Detects circular dependencies and reports errors
- Validates expansion succeeded (CI fails if formula unchanged)

**Example**: `DENSIFY(range, "rows-any")` expands to DENSIFY's full definition with arguments substituted.

**Rule**: If expansion doesn't modify the formula, it's an error (catches parser bugs and missing dependencies).

## Linter

**Script**: `scripts/lint_formulas.py`

**Key rules enforced:**
- Formulas must not start with `=` (added during generation)
- Warns about self-executing LAMBDA patterns (can often be simplified)

**Extensible**: Add new rules by subclassing `LintRule` and registering in the linter.

## Best Practices

### Formula Development
1. Test in Google Sheets first before adding to repository
2. Use composition - call existing named functions instead of duplicating logic
3. Follow the 4-step workflow (lint → generate → test → commit both)
4. Provide realistic parameter examples in YAML

### Parser Improvements
1. Run parser tests first: `pytest tests/test_formula_parser.py -v`
2. Improve the pyparsing grammar - never add fallback mechanisms
3. Add tests for new syntax (both positive and negative cases)
4. Negative tests are critical - ensure invalid syntax is properly rejected

### Testing
1. Add integration-level tests for new features (test public APIs)
2. Include negative tests (invalid syntax should raise `ParseException`)
3. Check coverage: `pytest tests/ --cov=scripts --cov-report=term-missing`
4. For known issues: Use `@pytest.mark.xfail(reason="issue #XXX")`

### Code Quality
1. Follow PEP 8 conventions
2. Keep functions focused (single responsibility)
3. Prefer integration tests over unit tests
4. Document non-obvious behavior with comments

## Troubleshooting Quick Reference

**Formula expansion fails**: Check for typos in function names (case-sensitive), verify all referenced functions exist, check for circular dependencies

**Parser errors**: Verify balanced delimiters (`()`, `{}`, `""`), check syntax matches Google Sheets conventions, review negative tests in `tests/test_formula_parser.py` for grammar boundaries

**CI fails**: README not regenerated (run generator and commit), linter errors (fix violations), test failures (fix or update tests), expansion errors (check formula syntax)

**Local vs CI mismatch**: Ensure dependencies match (`uv pip install pytest pytest-cov pyyaml pyparsing`), clear pytest cache (`rm -rf .pytest_cache`)

## Dependencies

- **Python**: 3.8+
- **uv**: Package manager (used for running scripts)
- **Core**: PyYAML, pyparsing (parsing), pytest, pytest-cov (testing)

Scripts use `uv` inline dependency declarations (PEP 723). CI workflows install dependencies explicitly.

## Notes for Claude Code

### Critical Requirements

- **Always run linter and generator**: `uv run scripts/lint_formulas.py` then `uv run scripts/generate_readme.py`
- **Always run tests**: `pytest tests/ -v` before committing
- **Commit both files**: `.yaml` AND updated `README.md` together
- **README.md is auto-generated**: Edit `.readme-template.md` for template changes, not README.md directly

### Development Tips

- **Use `uv` not `pip`**: The project uses `uv` for dependency management and script execution
- **Parser is pyparsing-only**: No regex fallbacks exist (intentionally removed)
- **Fail-fast philosophy**: Invalid syntax should be caught immediately, not silently tolerated
- **Formula composition works**: Formulas can reference other named functions - the system automatically expands them
- **Tests are integration-focused**: Test public APIs, not implementation details

### GitHub API Patterns

When `gh` CLI unavailable, use `curl -u "token:$GITHUB_TOKEN"` with GitHub REST API:
- Create PR: `POST /repos/OWNER/REPO/pulls`
- Check CI: `GET /repos/OWNER/REPO/commits/SHA/check-runs`
- Use `-s` flag and parse with `jq` (never manual string parsing)

### Project Evolution Context

The project has matured significantly:
- Parser: Regex fallbacks eliminated, 100% pyparsing grammar
- Testing: Comprehensive test suite with high coverage, integration-first approach
- Quality: Fail-fast validation, README staleness detection, strict grammar validation
- CI/CD: Automated testing, linting, and README generation with merge blocking

For historical details, see issues and PRs in repository.
