#!/usr/bin/env python3
"""
Formula YAML Linter

Validates formula YAML files against defined rules to ensure consistency
and correctness. Designed to be extensible for future validation rules.

Usage:
    uv run lint_formulas.py

Exit codes:
    0: All checks passed
    1: One or more lint errors found
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import yaml


class LintRule:
    """Base class for lint rules."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def check(self, file_path: Path, data: Dict[str, Any]) -> List[str]:
        """
        Check the rule against a YAML file.

        Args:
            file_path: Path to the YAML file
            data: Parsed YAML data

        Returns:
            List of error messages (empty if no errors)
        """
        raise NotImplementedError("Subclasses must implement check()")


class NoLeadingEqualsRule(LintRule):
    """Rule: Formula field must not start with '=' character."""

    def __init__(self):
        super().__init__(
            name="no-leading-equals",
            description="Formula field must not start with '=' character"
        )

    def check(self, file_path: Path, data: Dict[str, Any]) -> List[str]:
        errors = []

        if 'formula' not in data:
            return errors  # Skip if no formula field (will be caught by schema validation)

        formula = data['formula']
        if not isinstance(formula, str):
            return errors  # Skip if formula is not a string

        # Check if formula starts with '=' (ignoring leading whitespace)
        stripped = formula.lstrip()
        if stripped.startswith('='):
            errors.append(
                f"{file_path}: Formula starts with '=' character. "
                f"Remove the leading '=' from the formula field."
            )

        return errors


class FormulaLinter:
    """Main linter class that runs all validation rules."""

    def __init__(self):
        self.rules: List[LintRule] = [
            NoLeadingEqualsRule(),
            # Add more rules here as needed
        ]

    def lint_file(self, file_path: Path) -> List[str]:
        """
        Lint a single YAML file.

        Args:
            file_path: Path to the YAML file to lint

        Returns:
            List of error messages
        """
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                errors.append(f"{file_path}: Invalid YAML structure (expected dictionary)")
                return errors

            # Run all rules
            for rule in self.rules:
                rule_errors = rule.check(file_path, data)
                errors.extend(rule_errors)

        except yaml.YAMLError as e:
            errors.append(f"{file_path}: YAML parsing error: {e}")
        except Exception as e:
            errors.append(f"{file_path}: Unexpected error: {e}")

        return errors

    def lint_all(self, directory: Path = None) -> Tuple[int, int, List[str]]:
        """
        Lint all YAML files in the formulas directory.

        Args:
            directory: Directory to search for YAML files (defaults to formulas/ subdirectory)

        Returns:
            Tuple of (files_checked, error_count, error_messages)
        """
        if directory is None:
            directory = Path.cwd() / 'formulas'

        # Find all .yaml files in the formulas directory
        yaml_files = sorted(directory.glob('*.yaml'))

        all_errors = []
        files_checked = 0

        for yaml_file in yaml_files:
            files_checked += 1
            errors = self.lint_file(yaml_file)
            all_errors.extend(errors)

        return files_checked, len(all_errors), all_errors


def main():
    """Main entry point for the linter."""
    print("🔍 Linting formula YAML files...")
    print()

    linter = FormulaLinter()

    # Print registered rules
    print(f"Running {len(linter.rules)} lint rule(s):")
    for rule in linter.rules:
        print(f"  • {rule.name}: {rule.description}")
    print()

    # Run linter
    files_checked, error_count, errors = linter.lint_all()

    # Report results
    if error_count == 0:
        print(f"✅ All {files_checked} file(s) passed lint checks!")
        return 0
    else:
        print(f"❌ Found {error_count} error(s) in {files_checked} file(s):")
        print()
        for error in errors:
            print(f"  {error}")
        print()
        print("Please fix the errors above and run the linter again.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
