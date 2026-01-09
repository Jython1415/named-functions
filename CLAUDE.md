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
├── .readme-template.md            # Template for README generation
├── generate_readme.py             # Python script to generate README from YAML files
├── lint_formulas.py               # Python script to lint formula YAML files
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

1. Create a new `.yaml` file in the `formulas/` directory (e.g., `formulas/myformula.yaml`)
2. Follow the YAML schema structure above
3. Ensure all required fields are present and valid
4. Run `uv run lint_formulas.py` to check for style violations
5. Run `uv run generate_readme.py` locally to:
   - Validate the YAML file
   - Update README.md with the new formula
6. Commit both the `.yaml` file and the updated `README.md`
7. Push to GitHub

### Linting Formula Files

Before committing, run the linter to check for style violations:

```bash
uv run lint_formulas.py
```

This will:
- Scan all `.yaml` files in the `formulas/` directory
- Check each file against lint rules (e.g., no leading `=` in formulas)
- Report any violations with clear error messages
- Exit with error code if violations are found

The linter is extensible and new rules can be added by creating new `LintRule` subclasses in `lint_formulas.py`.

### Testing README Generation

Before committing, test the README generation locally:

```bash
uv run generate_readme.py
```

This will:
- Scan all `.yaml` files in the `formulas/` directory
- Validate each file against the schema
- Generate/update `README.md` from `.readme-template.md`
- Report any validation errors

### GitHub Actions Automation

The repository uses GitHub Actions to automatically validate and regenerate the README:

- **On push to main**: If any `.yaml` files or related files are modified, the workflow:
  1. Runs `lint_formulas.py` to check for style violations (fails if violations found)
  2. Runs `generate_readme.py` to regenerate README
  3. Commits and pushes updated `README.md` if changed

- **On pull requests**: If README needs regeneration, the workflow adds a comment to the PR requesting the author to regenerate locally

## Important Files

### lint_formulas.py

Python script that lints formula YAML files:
- Discovers all `.yaml` files in the `formulas/` directory
- Runs extensible lint rules against each file
- Reports style violations with clear error messages
- Exits with error code if violations are found

**Current lint rules:**
- **no-leading-equals**: Formulas must not start with `=` character (the equals sign is added automatically during README generation)

**Adding new rules:**
Create a new subclass of `LintRule` and add it to the `FormulaLinter.rules` list.

### generate_readme.py

Python script that:
- Discovers all `.yaml` files in the `formulas/` directory
- Validates them against the formula schema
- Generates formula list in markdown format
- Updates README.md by replacing content between `<!-- AUTO-GENERATED CONTENT START -->` and `<!-- AUTO-GENERATED CONTENT END -->` markers

### .readme-template.md

Template file for README generation. Contains:
- Static content (project description, contributing guide, license)
- Auto-generation markers where formula list is inserted

### Validation Rules

The generate_readme.py script validates:
- All required fields are present and non-empty
- Field types are correct (strings, lists, dicts)
- Parameters have required `name` and `description` fields
- YAML syntax is valid

## Common Tasks

### Add a new formula
1. Create `formulas/newformula.yaml` following the schema
2. Run `uv run lint_formulas.py` to check for style violations
3. Run `uv run generate_readme.py` to validate and update README
4. Commit both the `.yaml` file and updated `README.md`

### Update an existing formula
1. Edit the `.yaml` file in `formulas/` directory
2. Increment the version number
3. Run `uv run lint_formulas.py` to check for style violations
4. Run `uv run generate_readme.py` to regenerate README
5. Commit changes

### Modify README static content
1. Edit `.readme-template.md` (not README.md directly)
2. Run `uv run generate_readme.py` to regenerate README
3. Commit both files

### Add a new lint rule
1. Open `lint_formulas.py`
2. Create a new subclass of `LintRule` with your validation logic
3. Add an instance of your rule to the `FormulaLinter.rules` list
4. Test by running `uv run lint_formulas.py`
5. Commit the updated linter

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

- **Always run the linter first**: Use `uv run lint_formulas.py` after creating/modifying YAML files
- **Always validate YAML files**: Run `uv run generate_readme.py` after creation/modification
- **Formula files location**: All formula YAML files are in the `formulas/` directory, not the root
- **No leading equals signs**: Formulas must NOT start with `=` character (enforced by linter)
- **README.md is auto-generated**: Edit `.readme-template.md` for static content changes
- **Use `uv` not `pip`**: The project uses `uv` for dependency management
- **Document formulas well**: Include clear parameter descriptions and examples
- **Semantic versioning**: Version numbers should follow semantic versioning principles
- **Formula composition**: Formulas can reference other named functions - the system will automatically expand them
