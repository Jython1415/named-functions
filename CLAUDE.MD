# Named Functions Project

## Project Overview

This repository contains a collection of named Google Sheets formulas using LET and LAMBDA functions. Formulas are defined in YAML files and the README is automatically generated from these definitions.

## Project Structure

```
named-functions/
├── .github/
│   └── workflows/
│       └── generate-readme.yml    # GitHub Actions workflow for auto-generating README
├── .readme-template.md            # Template for README generation
├── generate_readme.py             # Python script to generate README from YAML files
├── README.md                      # Auto-generated documentation
├── LICENSE                        # Project license
└── *.yaml                         # Individual formula definitions (e.g., unpivot.yaml)
```

## Formula YAML Schema

Each formula is defined in a `.yaml` file in the root directory with the following structure:

### Required Fields

- **name** (string): The formula name (e.g., "UNPIVOT")
- **version** (string/number): Version number (e.g., "1.0.0")
- **description** (string): Brief description of what the formula does
- **parameters** (list): Array of parameter objects, each containing:
  - `name` (string): Parameter name
  - `description` (string): Parameter description
  - `default` (optional, no default value required): Default value if applicable
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
    default: 1
    example: 2

formula: |
  LET(
    variable, expression,
    result
  )
```

## Development Workflow

### Adding a New Formula

1. Create a new `.yaml` file in the root directory (e.g., `myformula.yaml`)
2. Follow the YAML schema structure above
3. Ensure all required fields are present and valid
4. Run `uv run generate_readme.py` locally to:
   - Validate the YAML file
   - Update README.md with the new formula
5. Commit both the `.yaml` file and the updated `README.md`
6. Push to GitHub

### Testing README Generation

Before committing, test the README generation locally:

```bash
uv run generate_readme.py
```

This will:
- Scan all `.yaml` files in the root directory
- Validate each file against the schema
- Generate/update `README.md` from `.readme-template.md`
- Report any validation errors

### GitHub Actions Automation

The repository uses GitHub Actions to automatically regenerate the README:

- **On push to main**: If any `.yaml` files or related files are modified, the workflow:
  1. Runs `generate_readme.py`
  2. Commits and pushes updated `README.md` if changed

- **On pull requests**: If README needs regeneration, the workflow adds a comment to the PR requesting the author to regenerate locally

## Important Files

### generate_readme.py

Python script that:
- Discovers all `.yaml` files in the root directory
- Validates them against the formula schema
- Generates formula list in markdown format
- Updates README.md by replacing content between `<!-- AUTO-GENERATED CONTENT START -->` and `<!-- AUTO-GENERATED CONTENT END -->` markers

### .readme-template.md

Template file for README generation. Contains:
- Static content (project description, contributing guide, license)
- Auto-generation markers where formula list is inserted

### Validation Rules

The script validates:
- All required fields are present and non-empty
- Field types are correct (strings, lists, dicts)
- Parameters have required `name` and `description` fields
- YAML syntax is valid

## Common Tasks

### Add a new formula
1. Create `newformula.yaml` following the schema
2. Run `uv run generate_readme.py` to validate and update README
3. Commit both files

### Update an existing formula
1. Edit the `.yaml` file
2. Increment the version number
3. Run `uv run generate_readme.py`
4. Commit changes

### Modify README static content
1. Edit `.readme-template.md` (not README.md directly)
2. Run `uv run generate_readme.py` to regenerate README
3. Commit both files

## Dependencies

- **Python**: 3.8 or higher
- **uv**: Package manager (used for running scripts)
- **PyYAML**: 6.0 or higher (automatically handled by uv inline script metadata)

## Google Sheets Function Reference

This project uses advanced Google Sheets functions:

- **LET**: Define variables within formulas for better readability and performance
- **LAMBDA**: Create custom reusable functions
- **MAKEARRAY**: Generate arrays dynamically
- **FILTER**: Filter data based on conditions
- **INDEX**: Retrieve values from arrays
- **MATCH**: Find position of values
- And other standard spreadsheet functions
