# Named Functions Project

## Project Overview

This repository contains a collection of named Google Sheets formulas using LET and LAMBDA functions. Formulas are defined in YAML files and the README is automatically generated from these definitions.

## Project Structure

```
named-functions/
├── .github/
│   └── workflows/
│       └── generate-readme.yml    # GitHub Actions workflow for auto-generating README
├── formulas/
│   └── *.yaml                     # Individual formula definitions (e.g., unpivot.yaml)
├── scripts/
│   ├── generate_readme.py         # Python script to generate README from YAML files
│   └── lint_formulas.py           # Python script to lint formula YAML files
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

## Development Workflow

### Adding a New Formula

1. Create a new `.yaml` file in the `formulas/` directory following the schema above
2. Run `uv run scripts/lint_formulas.py` to check for style violations
3. Run `uv run scripts/generate_readme.py` to validate and update README
4. Commit both the `.yaml` file and updated `README.md`

### CI/CD

The GitHub Actions workflow (`.github/workflows/generate-readme.yml`) automatically runs linting and README generation on push/PR. See the workflow file for details.

## Linter

The linter (`scripts/lint_formulas.py`) validates formula YAML files against style rules. It's extensible - new rules can be added easily.

### Adding a New Lint Rule

1. Open `scripts/lint_formulas.py`
2. Create a new subclass of `LintRule` with your validation logic
3. Add an instance to the `FormulaLinter.rules` list
4. Test by running `uv run scripts/lint_formulas.py`


## Formula Composition

Formulas can call other named functions, enabling powerful composition patterns. The system automatically:
- Parses formulas to detect function calls
- Expands references to other formulas with proper argument substitution
- Detects circular dependencies and reports errors
- Generates fully expanded formulas in the README

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
2. **Automatic expansion**: The parser detects calls to named functions and expands them
3. **Argument substitution**: Parameters are replaced with the provided arguments
4. **No circular dependencies**: The system detects cycles and reports errors before generation

### Example: DENSIFYROWS

**Input YAML:**
```yaml
formula: |
  DENSIFY(range, "rows-any")
```

**Generated README (expanded):**
The README will show DENSIFY's complete ~65-line formula with all occurrences of the `mode` parameter replaced by `"rows-any"` and the `range` parameter preserved.

### Implementation Details

The composition system uses pyparsing to:
- Parse Google Sheets formulas (including LAMBDA, LET, nested functions)
- Build a dependency graph of formula references
- Detect circular dependencies using DFS with cycle detection
- Expand formulas recursively, innermost-first
- Preserve string literals, function calls, and whitespace

## Dependencies

- **Python**: 3.8 or higher
- **uv**: Package manager (used for running scripts)
- **PyYAML**: 6.0 or higher (automatically handled by uv inline script metadata)
- **pyparsing**: 3.0 or higher (for formula parsing and composition)

## Notes for Claude Code

- **Always run linter and generator**: Use `uv run scripts/lint_formulas.py` then `uv run scripts/generate_readme.py` after creating/modifying YAML files
- **Formula files location**: All formula YAML files are in the `formulas/` directory
- **No leading equals signs**: Formulas must NOT start with `=` character (enforced by linter)
- **README.md is auto-generated**: Edit `.readme-template.md` for static content changes
- **Use `uv` not `pip`**: The project uses `uv` for dependency management
- **Formula composition**: Formulas can reference other named functions - the system will automatically expand them
