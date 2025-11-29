#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""
Generate README.md from formula YAML files.

This script:
1. Reads all .yaml files in the root directory
2. Validates them against the formula schema
3. Generates README.md with a list of formulas
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import yaml


class ValidationError(Exception):
    """Raised when a YAML file doesn't meet the schema requirements."""
    pass


def validate_formula_yaml(data: Dict[str, Any], filename: str) -> None:
    """
    Validate that a YAML file meets the formula schema.

    Required fields:
    - name: string
    - version: string
    - description: string
    - parameters: list
    - formula: string

    Optional fields:
    - notes: string

    Args:
        data: Parsed YAML data
        filename: Name of the file being validated (for error messages)

    Raises:
        ValidationError: If validation fails
    """
    required_fields = ['name', 'version', 'description', 'parameters', 'formula']
    optional_fields = ['notes']

    # Check required fields exist and are not empty
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"{filename}: Missing required field '{field}'")
        if data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            raise ValidationError(f"{filename}: Required field '{field}' is empty")

    # Validate field types
    if not isinstance(data['name'], str):
        raise ValidationError(f"{filename}: Field 'name' must be a string")

    if not isinstance(data['version'], (str, float, int)):
        raise ValidationError(f"{filename}: Field 'version' must be a string or number")

    if not isinstance(data['description'], str):
        raise ValidationError(f"{filename}: Field 'description' must be a string")

    if not isinstance(data['parameters'], list):
        raise ValidationError(f"{filename}: Field 'parameters' must be a list")

    if not isinstance(data['formula'], str):
        raise ValidationError(f"{filename}: Field 'formula' must be a string")

    # Validate parameters structure
    for i, param in enumerate(data['parameters']):
        if not isinstance(param, dict):
            raise ValidationError(f"{filename}: Parameter {i} must be a dictionary")
        if 'name' not in param:
            raise ValidationError(f"{filename}: Parameter {i} missing required field 'name'")
        if 'description' not in param:
            raise ValidationError(f"{filename}: Parameter {i} missing required field 'description'")

    # Check for unexpected fields
    all_allowed_fields = set(required_fields + optional_fields)
    unexpected_fields = set(data.keys()) - all_allowed_fields
    if unexpected_fields:
        print(f"Warning: {filename} contains unexpected fields: {', '.join(unexpected_fields)}")


def load_and_validate_formulas(root_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all .yaml files from root directory and validate them.

    Args:
        root_dir: Path to the repository root

    Returns:
        List of validated formula data dictionaries with 'filename' added

    Raises:
        ValidationError: If any file fails validation
    """
    formulas = []
    yaml_files = sorted(root_dir.glob('*.yaml'))

    if not yaml_files:
        print("Warning: No .yaml files found in root directory")
        return formulas

    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data is None:
                raise ValidationError(f"{yaml_file.name}: File is empty")

            validate_formula_yaml(data, yaml_file.name)

            # Add filename for linking
            data['filename'] = yaml_file.name
            formulas.append(data)

            print(f"✓ Validated {yaml_file.name}")

        except yaml.YAMLError as e:
            raise ValidationError(f"{yaml_file.name}: Invalid YAML syntax - {e}")
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"{yaml_file.name}: Error reading file - {e}")

    return formulas


def generate_formula_list(formulas: List[Dict[str, Any]]) -> str:
    """
    Generate markdown with formula summary list and detailed expandable sections.

    Args:
        formulas: List of validated formula dictionaries

    Returns:
        Markdown string with formula list and detailed sections
    """
    if not formulas:
        return "_No formulas available yet._\n"

    sorted_formulas = sorted(formulas, key=lambda f: f['name'].lower())

    # Generate summary list
    lines = ["### Quick Reference\n"]
    for formula in sorted_formulas:
        name = formula['name']
        filename = formula['filename']
        description = formula['description'].strip()
        description_clean = ' '.join(description.split())
        lines.append(f"- **[{name}]({filename})** - {description_clean}")

    lines.append("")  # blank line
    lines.append("### Detailed Formulas\n")

    # Generate detailed sections with copy-pastable content
    for formula in sorted_formulas:
        name = formula['name']
        filename = formula['filename']
        description = formula['description'].strip()
        description_clean = ' '.join(description.split())
        version = formula['version']
        parameters = formula.get('parameters', [])
        formula_text = formula['formula'].strip()
        notes = formula.get('notes', '')

        # Create expandable section
        lines.append(f"<details>")
        lines.append(f"<summary><strong>{name}</strong></summary>\n")

        # 1. Function name
        lines.append(f"### {name}\n")

        # 2. Description
        lines.append(f"**Description**\n")
        lines.append(f"```")
        lines.append(description_clean)
        lines.append(f"```\n")

        # 3. Argument placeholders (parameter names only)
        if parameters:
            lines.append(f"**Parameters**\n")
            lines.append(f"```")
            for i, param in enumerate(parameters, 1):
                lines.append(f"{i}. {param['name']}")
            lines.append(f"```\n")

        # 4. Formula definition
        lines.append(f"**Formula**\n")
        lines.append(f"```")
        lines.append(formula_text)
        lines.append(f"```\n")

        # 5. Argument description and examples
        if parameters:
            lines.append(f"**Parameter Details**\n\n")
            for param in parameters:
                param_name = param['name']
                param_desc = param['description'].strip()
                param_desc_clean = ' '.join(param_desc.split())
                param_example = param.get('example', '')

                # Use heading level 4 for parameter names for stronger visual hierarchy
                lines.append(f"#### {param_name}\n")
                lines.append(f"```")
                lines.append(param_desc_clean)
                lines.append(f"```\n")

                if param_example:
                    lines.append(f"**Example:**\n")
                    lines.append(f"```")
                    lines.append(f"{param_example}")
                    lines.append(f"```\n")

        if notes:
            notes_clean = ' '.join(notes.strip().split())
            lines.append(f"**Notes**\n")
            lines.append(f"```")
            lines.append(notes_clean)
            lines.append(f"```\n")

        lines.append(f"</details>\n")

    return '\n'.join(lines)


def generate_readme(template_path: Path, formulas: List[Dict[str, Any]]) -> str:
    """
    Generate README content by inserting formula list into template.

    Args:
        template_path: Path to the README template file
        formulas: List of validated formula dictionaries

    Returns:
        Complete README content
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    formula_list = generate_formula_list(formulas)

    # Replace content between markers
    start_marker = '<!-- AUTO-GENERATED CONTENT START -->'
    end_marker = '<!-- AUTO-GENERATED CONTENT END -->'

    if start_marker not in template or end_marker not in template:
        raise ValueError("Template missing AUTO-GENERATED CONTENT markers")

    before = template.split(start_marker)[0]
    after = template.split(end_marker)[1]

    readme = (
        f"{before}{start_marker}\n"
        f"<!-- This section is automatically generated by generate_readme.py -->\n\n"
        f"{formula_list}\n"
        f"{end_marker}{after}"
    )

    return readme


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent
    template_path = root_dir / '.readme-template.md'
    readme_path = root_dir / 'README.md'

    try:
        # Load and validate all formula YAML files
        print("Loading and validating formula files...")
        formulas = load_and_validate_formulas(root_dir)
        print(f"\nFound {len(formulas)} valid formula(s)")

        # Generate README
        print(f"\nGenerating README from template...")
        readme_content = generate_readme(template_path, formulas)

        # Write README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"✓ README.md generated successfully")
        return 0

    except ValidationError as e:
        print(f"❌ Validation Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
