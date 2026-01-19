# Named Functions Project

## Project Overview

This repository contains a collection of named Google Sheets formulas using LET and LAMBDA functions. Formulas are defined in YAML files and the README is automatically generated from these definitions.

The project emphasizes **robustness**, **comprehensive testing**, and **fail-fast validation** to ensure all formulas are syntactically correct and fully expandable.

## Project Structure

```
named-functions/
├── .github/
│   └── workflows/
│       ├── generate-readme.yml    # README generation and linting
│       ├── test.yml               # Test suite, coverage, and validation
│       └── claude.yml             # Claude Code integration
├── formulas/
│   └── *.yaml                     # Individual formula definitions (33 formulas)
├── scripts/
│   ├── generate_readme.py         # README generator with formula parser/expander
│   ├── lint_formulas.py           # Extensible YAML linter
│   └── test_zero_arg_functions.py # Specialized zero-arg function tests
├── tests/
│   ├── test_formula_parser.py     # Comprehensive parser tests (86 tests)
│   ├── test_generate_readme_integration.py  # End-to-end integration tests
│   └── CLAUDE.md                  # Testing philosophy and guidelines
├── pytest.ini                     # pytest configuration with markers
├── .readme-template.md            # Template for README generation
├── README.md                      # Auto-generated documentation
└── LICENSE                        # Project license
```

## Formula YAML Schema

Each formula is defined in a `.yaml` file in the `formulas/` directory with the following structure:

### Required Fields

- **name** (string): The formula name (e.g., "UNPIVOT")
- **version** (string/number): Version number (e.g., "1.0.0")
- **description** (string): Brief description of what the formula does
- **parameters** (list): Array of parameter objects, each containing:
  - `name` (string): Parameter name
  - `description` (string): Parameter description
  - `example` (optional, example value recommended): Example value if applicable
- **formula** (string): The actual Google Sheets formula using LET and LAMBDA

### Example Structure

```yaml
name: FUNCTION_NAME
version: 1.0.0

description: >
  Brief description of what the function does.

parameters:
  - name: param1
    description: Description of first parameter
    example: "A1:B10"

  - name: param2
    description: Description of second parameter
    example: 2

formula: |
  LET(
    variable, expression,
    result
  )
```

### Important Notes

- **No leading `=`**: Formulas in YAML should NOT start with `=` (automatically added during generation)
- **Comments supported**: You can use `/* */` block comments and `//` line comments in YAML formulas (automatically stripped for Google Sheets compatibility)
- **Composition allowed**: Formulas can call other named functions - they will be automatically expanded

## Development Workflow

### Adding a New Formula

1. Create a new `.yaml` file in the `formulas/` directory following the schema above
2. **Run linter**: `uv run scripts/lint_formulas.py` to check for style violations
3. **Run generator**: `uv run scripts/generate_readme.py` to validate and update README
4. **Run tests**: `pytest tests/ -v` to ensure nothing broke
5. **Verify README updated**: `git diff README.md` should show your new formula
6. **Commit both files**: The `.yaml` file AND updated `README.md`

### Pre-Commit Checklist

Before committing formula changes, run these commands in order:

```bash
# 1. Lint formulas (checks style rules)
uv run scripts/lint_formulas.py

# 2. Generate README (validates and expands formulas)
uv run scripts/generate_readme.py

# 3. Run test suite (ensures nothing broke)
pytest tests/ -v

# 4. Verify README is current
git diff README.md  # Should only show your intended changes
```

All four steps must succeed for CI to pass.

### CI/CD Workflows

The project has three GitHub Actions workflows:

#### 1. Test Workflow (`.github/workflows/test.yml`)
**Triggers**: Push/PR to main, manual dispatch
**Purpose**: Primary quality gate
**Steps**:
- Install dependencies (pytest, pytest-cov, pyyaml, pyparsing)
- Run full test suite with coverage: `pytest tests/ -v --cov=scripts --cov-report=term-missing`
- Run linter: `uv run scripts/lint_formulas.py`
- Run README generation: `uv run scripts/generate_readme.py`
- **Verify README is up to date** (fails if out of sync)

**Important**: Formula expansion failures will **block PR merges**. All formulas must expand to valid Google Sheets syntax.

#### 2. Generate README Workflow (`.github/workflows/generate-readme.yml`)
**Triggers**: Push/PR with changes to `formulas/`, `.readme-template.md`, or `scripts/`
**Purpose**: Automated README generation and validation
**Steps**:
- Run linter and generator
- Auto-commit on push to main
- Comment on PRs if README needs regeneration

#### 3. Claude Workflow (`.github/workflows/claude.yml`)
**Triggers**: `@claude` mentions in issues/PRs/comments
**Purpose**: Claude Code integration
**Restrictions**: Limited to git, uv, and python commands only

## Testing

### Test Infrastructure

- **Framework**: pytest with integration-first approach
- **Location**: `tests/` directory (97 test functions across multiple test files)
- **Coverage**: 98.4%+ of scripts (tracked with pytest-cov)
- **Philosophy**: Test public APIs and expected behavior, not internal implementation details

### Running Tests

```bash
# Install test dependencies (if not already installed)
uv venv
source .venv/bin/activate
uv pip install pytest pytest-cov pyyaml pyparsing

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=scripts --cov-report=term-missing

# Run specific test file
pytest tests/test_formula_parser.py -v

# Run specific test class
pytest tests/test_formula_parser.py::TestBasicParsing -v

# Run specific test function
pytest tests/test_formula_parser.py::TestBasicParsing::test_simple_function_call -v
```

### Test Organization

#### test_formula_parser.py (86 tests)
Comprehensive parser tests organized into 11 test classes:
- **TestBasicParsing**: Simple function calls
- **TestLETAndLAMBDA**: Complex Google Sheets structures
- **TestStringHandling**: Quote handling and escaping
- **TestArraysAndRanges**: Spreadsheet-specific syntax
- **TestOperators**: Arithmetic, concatenation, comparison, logical
- **TestEdgeCases**: Multiple calls, whitespace, deep nesting
- **TestRealWorldPatterns**: Actual formulas from repository
- **TestParserMechanics**: Parser internals and reconstruction
- **TestNegativeCases**: Invalid syntax that should be rejected
- **TestValidEdgeCases**: Surprising but valid syntax (e.g., `IF(,,)`)
- **TestGrammarRuleCoverage**: Comprehensive grammar boundary tests

#### test_generate_readme_integration.py (11 tests)
End-to-end integration tests:
- **TestReadmeGeneration**: Full README generation workflow
- **TestFormulaValidation**: YAML schema validation
- **TestExistingFormulas**: Validates all 33 production formulas

### Testing Philosophy

The project uses **integration tests** rather than unit tests:
- Test public APIs and expected behavior, not internal implementation
- Allows internal refactoring without breaking tests
- Focuses on real-world usage patterns from actual formulas
- See `tests/CLAUDE.md` for detailed testing context and rationale

### Adding New Tests

When fixing bugs or adding features:

1. **Add test(s) first** (TDD approach when possible)
2. **Use integration-level tests** - Test public APIs, not internals
3. **Test real-world scenarios** - Use actual formula patterns from `formulas/` directory
4. **Include comprehensive docstrings** - Explain what's being validated and why
5. **For known issues** - Use `@pytest.mark.xfail(reason="issue #XXX")`
6. **Add negative tests** - Ensure invalid syntax is properly rejected with `ParseException`

Example test structure:
```python
class TestNewFeature:
    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_feature_works(self):
        """Test that new feature parses correctly.

        Detailed explanation of what's being tested and why.
        """
        formula = 'MYFUNCTION(arg1, arg2)'
        result = self.parser.parse(formula)
        # Assertions...
```

### Known Testing Gaps

- **Google Sheets doubled-quote escaping**: `""` syntax not yet supported (tracked in #103, marked as `xfail`)
- See open issues for other known limitations

## Parser Architecture

### Overview

The formula parser uses **pyparsing exclusively** to parse Google Sheets formulas. As of PR #111, all regex fallback code has been removed (~97-103 lines eliminated).

### Design Philosophy

- **Single robust grammar**: One comprehensive pyparsing grammar for all formulas (no regex fallbacks)
- **Explicit failures**: Grammar gaps surface immediately as `ParseException` instead of silently degrading
- **Fail fast**: Invalid syntax blocks CI/CD rather than producing incorrect output
- **100% pyparsing**: The grammar handles ALL Google Sheets constructs natively

### Supported Constructs

The parser supports the full range of Google Sheets formula syntax:

**Operators:**
- Arithmetic: `+`, `-`, `*`, `/`, `^`
- String concatenation: `&`
- Comparison: `=`, `<>`, `<`, `>`, `<=`, `>=`
- Logical: `AND`, `OR` (case-insensitive)
- Unary: `+`, `-` (including `--` idiom for boolean-to-number conversion)

**Data Types:**
- Numbers: Integers and floats
- Strings: Single and double quotes with escape sequences
- Arrays: `{1,2,3}` and `{1,2;3,4}` (semicolon for row separation)
- Ranges: `A1:B10`, `C:C`, `1:1`, `$A$1:$B$10`
- Cell references: `A1`, `$A$1`, `A$1`, `$A1`

**Functions:**
- Standard function calls: `SUM(A1:A10)`
- LET expressions: `LET(x, 1, y, 2, x + y)`
- LAMBDA expressions: `LAMBDA(x, x * 2)`
- Nested functions: `IF(SUM(A1:A10) > 0, "Positive", "Zero")`
- Zero-argument functions: `TODAY()`, `BLANK()`
- Empty arguments: `IF(,,)`, `IF(A1,,B1)` (creates empty/blank arguments)

**Structural:**
- Parenthesized expressions: `(expr)`, `((nested))`
- Multiple arguments: `FUNCTION(arg1, arg2, arg3)`
- Deep nesting: Unlimited nesting depth

### Special Features

#### Empty Argument Support
The parser correctly handles Google Sheets' empty argument syntax:
```
IF(,,)           → IF with three empty arguments
IF(A1,,B1)       → IF with empty middle argument
LAMBDA(x,)(0)    → LAMBDA with empty body (edge case)
```

This is distinct from zero-argument functions like `BLANK()`.

#### Comment Stripping
Comments are automatically removed before parsing (Google Sheets doesn't support comments):
```yaml
formula: |
  /* This is a comment */
  LET(
    x, 1,  // Inline comment
    x + 2
  )
```
Becomes: `LET(x, 1, x + 2)`

#### Parenthesized Expression Preservation
Parentheses around expressions are preserved for accurate string replacement during expansion:
```
(A1 + B1)    → Marked as parenthesized expression
((A1 + B1))  → Nested parentheses preserved
```

#### Unary Operator Support
Supports Google Sheets unary operator patterns:
```
-A1          → Negation
--condition  → Boolean-to-number conversion (Google Sheets idiom)
+A1          → Positive sign (identity operation)
```

### Parser Validation Rules

The parser **rejects invalid syntax** that Google Sheets doesn't support:

- **Empty arrays**: `{}` is invalid (arrays must have at least one element)
- **Delimiter-only arrays**: `{,}` and `{;}` are invalid
- **Unclosed strings**: `"hello` without closing quote
- **Unclosed functions**: `SUM(A1:A10` without closing paren
- **Unclosed arrays**: `{1,2,3` without closing brace
- **Invalid operator sequences**: `A1 + + B1` (double operators except `--`)

### Known Limitations

- **Google Sheets doubled-quote escaping**: `"He said ""hello"""` not yet supported (tracked in #103)
- Use backslash escaping instead: `"He said \"hello\""`

### Parser Implementation Details

**Location**: `scripts/generate_readme.py` (FormulaParser class, lines 28-355)

**Key Methods:**
- `parse(formula: str)` → Parses formula and returns AST (ParseResults)
- `extract_function_calls(ast, named_functions)` → Extracts calls to named functions
- `reconstruct_call(func_name, args)` → Reconstructs exact function call text for string replacement

**Internal Markers:**
The parser uses tuple markers to preserve semantic information through transformations:
- `(__STRING_LITERAL__, "value")` → Marks quoted strings
- `(__PARENTHESIZED__, expr)` → Marks parenthesized expressions
- `__EMPTY__` → Marks omitted function arguments (e.g., in `IF(,,)`)

These markers guide reconstruction and expansion.

## Formula Composition

Formulas can call other named functions, enabling powerful composition patterns. The system automatically:
- Parses formulas to detect function calls
- Expands references to other formulas with proper argument substitution
- Detects circular dependencies and reports errors
- Generates fully expanded formulas in the README
- **Validates expansion succeeded** (fails CI if expansion produces no change)

### Writing Composable Formulas

Simply call other named functions naturally in your formula:

```yaml
name: DENSIFYROWS
version: 1.0.0
description: Removes incomplete rows (convenience wrapper)
parameters:
  - name: range
    description: Data range to process
    example: "A1:Z100"
formula: |
  DENSIFY(range, "rows-any")
```

The README will show the fully expanded formula with `DENSIFY`'s definition inlined and arguments substituted.

### Composition Rules

1. **Natural syntax**: Write `DENSIFY(range, "rows-any")` directly - no special syntax needed
2. **Automatic expansion**: The parser detects calls to named functions and expands them recursively
3. **Argument substitution**: Parameters are replaced with the provided arguments using word-boundary matching
4. **No circular dependencies**: The system detects cycles and reports errors before generation
5. **Expansion validation**: If expansion fails to modify the formula, an error is raised and CI fails

### Example: DENSIFYROWS

**Input YAML:**
```yaml
formula: |
  DENSIFY(range, "rows-any")
```

**Generated README (expanded):**
The README will show DENSIFY's complete ~65-line formula with all occurrences of the `mode` parameter replaced by `"rows-any"` and the `range` parameter preserved.

### Implementation Details

The composition system uses pyparsing and recursive expansion:

**Phase 1: Dependency Analysis**
- Parse each formula to extract calls to other named functions
- Build dependency graph: `formula_name → [dependencies]`
- Detect circular dependencies using DFS with cycle detection
- Report cycles like: `A → B → C → A`

**Phase 2: Recursive Expansion**
- Process function calls deepest-first (bottom-up)
- For each call:
  1. Recursively expand arguments (handles nested compositions like `OUTER(INNER(x))`)
  2. Recursively expand the called function's definition
  3. Substitute parameters with arguments (using word-boundary regex to avoid partial matches)
  4. Replace call text with expanded definition (wrapped in parentheses)
- Cache expanded formulas to avoid redundant work
- Validate that expansion actually modified the formula

**Phase 3: Validation**
- Verify all function calls were successfully expanded
- If formula text unchanged after expansion, raise `ValidationError`
- This catches parser bugs and unsupported syntax early (blocks CI)

**Key Functions** (in `scripts/generate_readme.py`):
- `build_dependency_graph()` (lines 421-451)
- `detect_cycles()` (lines 454-488)
- `substitute_arguments()` (lines 491-580)
- `expand_argument()` (lines 584-644)
- `expand_formula()` (lines 647-758)

## Linter

The linter (`scripts/lint_formulas.py`) validates formula YAML files against style rules. It's extensible - new rules can be added easily.

### Current Lint Rules

1. **No leading equals**: Formulas should not start with `=` (added during generation)
2. **Self-executing LAMBDA warning**: Warns about `LAMBDA(...)(args)` patterns (can often be simplified)

### Adding a New Lint Rule

1. Open `scripts/lint_formulas.py`
2. Create a new subclass of `LintRule` with your validation logic:
   ```python
   class MyNewRule(LintRule):
       def check(self, file_path, data):
           errors = []
           warnings = []
           # Your validation logic here
           return errors, warnings
   ```
3. Add an instance to the `FormulaLinter.rules` list (around line 260)
4. Test by running `uv run scripts/lint_formulas.py`

Rules automatically apply to all YAML files in `formulas/`.

## Best Practices

### Formula Development

1. **Test in Google Sheets first**: Validate your formula works before adding to repository
2. **Use composition**: Leverage existing formulas instead of duplicating logic
3. **Follow the schema**: Ensure all required fields are present and properly formatted
4. **Add clear examples**: Provide realistic parameter examples that demonstrate usage
5. **Validate locally**: Run linter, generator, and tests before pushing
6. **Commit both files**: Always commit both `.yaml` and updated `README.md`

### Parser Issues and Grammar Improvements

If you encounter parser errors:

1. **Run parser tests**: `pytest tests/test_formula_parser.py -v` to identify the issue
2. **Check test suite**: See if similar syntax is already tested (may be in negative tests as unsupported)
3. **Improve grammar**: Fix the pyparsing grammar in `scripts/generate_readme.py` (FormulaParser class)
4. **Add tests**: Add test cases for the new syntax (both positive and negative)
5. **Never add fallbacks**: Improve the grammar instead of working around it (project philosophy)

### Testing

1. **Add tests for new features**: Every new formula construct needs corresponding tests
2. **Include negative tests**: Test that invalid syntax is properly rejected with `ParseException`
3. **Test edge cases**: Empty arguments, nested structures, special characters, whitespace
4. **Run full suite**: Always run all tests before committing (`pytest tests/ -v`)
5. **Check coverage**: Use `--cov` flag to ensure new code is tested

### Code Quality

1. **Follow Python conventions**: PEP 8 style (note: linters for Python code are planned, see #112)
2. **Document complex logic**: Add comments explaining non-obvious behavior
3. **Keep functions focused**: Each function should do one thing well
4. **Prefer integration tests**: Test public APIs, not implementation details

## Troubleshooting

### Formula Expansion Failures

**Symptom**: `generate_readme.py` fails with "Formula expansion did not modify the formula"

**Possible Causes:**
- Formula references a non-existent named function
- Parser failed to detect function call (grammar bug)
- Circular dependency between formulas
- Unsupported syntax in formula

**Solutions:**
1. Check for typos in function names (case-sensitive)
2. Verify all referenced functions exist in `formulas/`
3. Run dependency check: `uv run scripts/generate_readme.py` (will report cycles)
4. Run parser tests: `pytest tests/test_formula_parser.py -v`
5. Check formula syntax matches Google Sheets conventions
6. Look at CI logs for specific error messages

### Parser Errors

**Symptom**: `ParseException` when running `generate_readme.py`

**Possible Causes:**
- Formula uses unsupported syntax
- Unbalanced parentheses, brackets, or quotes
- Invalid operator sequences
- Empty arrays or invalid array syntax

**Solutions:**
1. Run parser tests to narrow down the issue: `pytest tests/test_formula_parser.py::TestStringHandling -v`
2. Check if your formula uses syntax in the "Known Limitations" section
3. Verify string literals use backslash escaping: `\"` not `""`
4. Check for balanced delimiters: matching `()`, `{}`, `""`
5. Review negative tests in `tests/test_formula_parser.py` to understand grammar boundaries
6. If legitimate Google Sheets syntax, file an issue to improve the grammar

### CI/CD Failures

**Symptom**: GitHub Actions workflow fails

**Common Causes and Solutions:**

1. **README not regenerated locally**
   - Run: `uv run scripts/generate_readme.py`
   - Commit updated `README.md`

2. **Linter errors**
   - Run: `uv run scripts/lint_formulas.py`
   - Fix reported style violations
   - Common: Remove leading `=` from formulas

3. **Test failures**
   - Run: `pytest tests/ -v`
   - Fix failing tests or update tests if behavior intentionally changed
   - Check for formula changes that break other formulas

4. **Formula expansion errors**
   - Check CI logs for specific formula that failed
   - Follow "Formula Expansion Failures" troubleshooting above
   - Ensure formula uses supported syntax

5. **Coverage regression**
   - Run: `pytest tests/ --cov=scripts --cov-report=term-missing`
   - Add tests for uncovered code paths

### Linter Warnings

**Symptom**: Linter reports warnings (but doesn't fail)

**Common Warnings:**

1. **Self-executing LAMBDA**: `LAMBDA(...)(args)` pattern detected
   - Not an error - LAMBDA wrappers behave identically to unwrapped code
   - Consider simplifying by removing unnecessary LAMBDA wrapper
   - See issue #81 for investigation details

### Test Failures

**Symptom**: Local tests pass but CI fails (or vice versa)

**Solutions:**
1. Ensure dependencies match: `uv pip install pytest pytest-cov pyyaml pyparsing`
2. Check Python version (3.8+ required)
3. Clear pytest cache: `rm -rf .pytest_cache`
4. Check for filesystem case sensitivity issues (rare)

## Dependencies

- **Python**: 3.8 or higher
- **uv**: Package manager (used for running scripts with inline dependencies)
- **PyYAML**: 6.0 or higher (for YAML parsing)
- **pyparsing**: 3.0 or higher (for formula parsing)
- **pytest**: 9.0 or higher (for testing)
- **pytest-cov**: Latest (for coverage reporting)

### Installing Dependencies

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install pytest pytest-cov pyyaml pyparsing
```

### Dependency Management

- Scripts use `uv` inline dependency declarations (no separate requirements.txt)
- CI workflows install dependencies explicitly
- `uv run` automatically handles dependencies when running scripts

## Notes for Claude Code

### Critical Requirements

- **Always run linter and generator**: Use `uv run scripts/lint_formulas.py` then `uv run scripts/generate_readme.py` after creating/modifying YAML files
- **Always run tests**: Use `pytest tests/ -v` to ensure changes don't break existing functionality
- **Commit both files**: The `.yaml` file AND updated `README.md` must be committed together
- **README.md is auto-generated**: Edit `.readme-template.md` for static content changes, not `README.md` directly

### Project Locations

- **Formula files**: `formulas/*.yaml` (33 production formulas)
- **Test files**: `tests/test_*.py`
- **Scripts**: `scripts/*.py`
- **Templates**: `.readme-template.md`
- **Config**: `pytest.ini`, `.github/workflows/*.yml`

### Development Tips

- **Use `uv` not `pip`**: The project uses `uv` for dependency management and script execution
- **Formula composition works**: Formulas can reference other named functions - the system will automatically expand them
- **Parser is pyparsing-only**: No regex fallbacks exist (intentionally removed)
- **Tests are integration-focused**: Test public APIs, not implementation details
- **Fail-fast philosophy**: Invalid syntax should be caught immediately, not silently tolerated

### GitHub API Operations

When `gh` CLI is unavailable, use `curl` with `$GITHUB_TOKEN`. Authentication format: `-u "token:$GITHUB_TOKEN"`

**Create Issue:**
```bash
curl -s -u "token:$GITHUB_TOKEN" -X POST \
  https://api.github.com/repos/OWNER/REPO/issues \
  -H "Content-Type: application/json" \
  -d '{"title": "Title", "body": "Body"}' | jq -r '.number'
```

**Create PR:**
```bash
curl -s -u "token:$GITHUB_TOKEN" -X POST \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -H "Content-Type: application/json" \
  -d '{"title": "Title", "body": "Body", "head": "branch", "base": "main"}' | jq -r '.number'
```

**Check CI Status:**
```bash
curl -s -u "token:$GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/commits/SHA/check-runs" | \
  jq -r '.check_runs[] | "\(.name): \(.conclusion // "in_progress")"'
```

**Poll for CI Completion:**
```bash
for i in {1..24}; do
  status=$(curl -s -u "token:$GITHUB_TOKEN" \
    "https://api.github.com/repos/OWNER/REPO/commits/SHA/check-runs" | \
    jq -r '.check_runs[0].conclusion')
  [ "$status" != "null" ] && break
  sleep 10
done
```

**Key Points:**
- Use `-s` flag with curl for clean output; parse with `jq` (never manual string parsing)
- Use heredocs `-d @- <<'EOF'` for multiline JSON
- Check-runs API is more reliable than commit status API

### Recent Project Evolution

The project has undergone significant maturation:

**Parser Improvements:**
- Eliminated regex fallback mechanism (PR #111)
- Added support for empty arguments, unary operators, logical operators
- Enhanced with comprehensive negative tests (PR #114)
- Fixed edge cases with zero-arg functions, nested calls, LET expressions

**Testing Infrastructure:**
- Created comprehensive test suite (86 parser tests + integration tests)
- Achieved 98.4%+ test coverage
- Added CI workflow with coverage tracking
- Established integration-first testing philosophy

**Quality Assurance:**
- Fail-fast validation: expansion failures block CI
- README staleness detection
- Automated comment stripping
- Strict grammar validation (no silent degradation)

**Documentation:**
- Enhanced CLAUDE.md with testing, parser architecture, troubleshooting
- Added tests/CLAUDE.md for testing philosophy
- Expanded GitHub API patterns

See issues #96, #97, #99, #100, #101, #102, #103, #110, #111, #114 for historical context.
