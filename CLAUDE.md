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
- **README.md is auto-generated**: Edit `.readme-template.md` for static content changes
- **Use `uv` not `pip`**: The project uses `uv` for dependency management
- **Formula composition**: Formulas can reference other named functions - the system will automatically expand them
- **GitHub API access**: If `gh` CLI is unavailable, use the patterns documented in the "GitHub API Operations" section below.

## GitHub API Operations

When the `gh` CLI is unavailable, you can interact with GitHub using `curl` and the `$GITHUB_TOKEN` environment variable. This section documents tested patterns for common operations.

### Checking for GitHub Token Availability

Verify the token is available before attempting API calls:

```bash
[ -n "$GITHUB_TOKEN" ] && echo "✓ Available" || echo "✗ Not available"
```

### Authentication Format

Use the `-u "token:$GITHUB_TOKEN"` format for basic authentication with curl:

```bash
curl -s -u "token:$GITHUB_TOKEN" https://api.github.com/repos/OWNER/REPO/issues
```

**Important**: Use the `-u` flag format shown above, NOT the Authorization header format. This is essential for proper authentication.

### Creating Issues

Create a new GitHub issue with title and body:

```bash
curl -s -u "token:$GITHUB_TOKEN" \
  -X POST \
  https://api.github.com/repos/OWNER/REPO/issues \
  -H "Content-Type: application/json" \
  -d @- <<'EOF' | jq -r '.number'
{
  "title": "Issue title",
  "body": "Issue body with markdown support"
}
EOF
```

The `jq -r '.number'` extracts the issue number from the response.

### Creating Pull Requests

Create a new pull request:

```bash
curl -s -u "token:$GITHUB_TOKEN" \
  -X POST \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -H "Content-Type: application/json" \
  -d '{
    "title": "PR title",
    "body": "PR description with markdown",
    "head": "feature-branch",
    "base": "main"
  }' | jq -r '.number'
```

### Monitoring CI Status

Two complementary approaches exist for checking CI/workflow status:

#### Commit Status API (Combined Status)

Get the overall combined status for a commit:

```bash
curl -s -u "token:$GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/commits/SHA/status" | \
  jq -r '.state'
```

Returns: "success", "failure", "pending", or "error"

#### Check Runs API (Detailed Per-Job)

Get detailed information about individual workflow jobs:

```bash
curl -s -u "token:$GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/commits/SHA/check-runs" | \
  jq -r '.check_runs[] | "\(.name): \(.status) - \(.conclusion // "in_progress")"'
```

This shows each job's status and conclusion (e.g., "test: completed - success").

### Polling for CI Completion

When waiting for CI to complete, use a polling loop with the check-runs API:

```bash
for i in {1..24}; do
  sleep 10
  status=$(curl -s -u "token:$GITHUB_TOKEN" \
    "https://api.github.com/repos/OWNER/REPO/commits/SHA/check-runs" | \
    jq -r '.check_runs[] | select(.name == "test") | .conclusion')

  if [ "$status" = "success" ] || [ "$status" = "failure" ]; then
    echo "CI completed with status: $status"
    break
  fi
done
```

This polls every 10 seconds for up to 4 minutes. Adjust the sleep duration and loop count as needed.

### Key Insights and Gotchas

1. **Commit Status API Limitations**: The commit status API can show "pending" even when individual check-runs have completed. Use the check-runs API for more reliable status information.

2. **Always Use `-s` Flag**: Include `-s` (silent) with curl to suppress progress output, which is important when parsing JSON responses.

3. **JSON Parsing with jq**: Always use `jq` to parse JSON responses. Avoid manual string parsing which is error-prone.

4. **Heredocs for Multiline Bodies**: Use heredocs with `-d @-` for multiline JSON bodies:
   ```bash
   -d @- <<'EOF'
   { ... }
   EOF
   ```

5. **Check Token Format**: If authentication fails, verify the token format is exactly `-u "token:$GITHUB_TOKEN"` (not other header-based formats).

6. **Rate Limiting**: GitHub API has rate limits. For frequent polling, be aware of the limits and add appropriate delays between requests.

7. **Commit SHA**: Use full commit SHA for API calls, or `HEAD` when on a branch:
   ```bash
   git rev-parse HEAD
   ```
