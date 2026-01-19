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
from typing import Any, Dict, List, Tuple

import yaml
from formula_parser import FormulaParser, strip_comments
from pyparsing import ParseException


class LintRule:
    """Base class for lint rules."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def check(self, file_path: Path, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Check the rule against a YAML file.

        Args:
            file_path: Path to the YAML file
            data: Parsed YAML data

        Returns:
            Tuple of (errors, warnings) - both are lists of messages
        """
        raise NotImplementedError("Subclasses must implement check()")


class NoLeadingEqualsRule(LintRule):
    """Rule: Formula field must not start with '=' character."""

    def __init__(self):
        super().__init__(
            name="no-leading-equals", description="Formula field must not start with '=' character"
        )

    def check(self, file_path: Path, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        errors = []
        warnings = []

        if "formula" not in data:
            return (
                errors,
                warnings,
            )  # Skip if no formula field (will be caught by schema validation)

        formula = data["formula"]
        if not isinstance(formula, str):
            return errors, warnings  # Skip if formula is not a string

        # Check if formula starts with '=' (ignoring leading whitespace)
        stripped = formula.lstrip()
        if stripped.startswith("="):
            errors.append(
                f"{file_path}: Formula starts with '=' character. "
                f"Remove the leading '=' from the formula field."
            )

        return errors, warnings


class NoTopLevelLambdaRule(LintRule):
    """Rule: Formula field must not start with uninvoked LAMBDA wrapper."""

    def __init__(self):
        super().__init__(
            name="no-top-level-lambda",
            description="Formula field must not start with uninvoked LAMBDA wrapper (Google Sheets adds this automatically)",
        )

    def check(self, file_path: Path, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        errors = []
        warnings = []

        if "formula" not in data:
            return errors, warnings  # Skip if no formula field

        formula = data["formula"]
        if not isinstance(formula, str):
            return errors, warnings  # Skip if formula is not a string

        # Check if formula starts with LAMBDA (ignoring leading whitespace and trailing whitespace)
        stripped = formula.strip()
        if stripped.upper().startswith("LAMBDA("):
            # Check if it's a self-executing LAMBDA (ends with invocation like )(0) or )(args))
            # Pattern: LAMBDA(...)(...)

            # Count parentheses to find where the LAMBDA definition ends
            paren_count = 0
            in_string = False
            escape_next = False
            lambda_end = -1

            for i, char in enumerate(stripped):
                if escape_next:
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == "(":
                        paren_count += 1
                    elif char == ")":
                        paren_count -= 1
                        if paren_count == 0:
                            lambda_end = i
                            break

            # Check if there's an immediate invocation after the LAMBDA
            if lambda_end >= 0 and lambda_end < len(stripped) - 1:
                after_lambda = stripped[lambda_end + 1 :].lstrip()
                if after_lambda.startswith("("):
                    # This is a self-executing LAMBDA - warn about it
                    # Investigation in issue #81 proved that LAMBDA(input, IF(,,))(0) and IF(,,)
                    # behave identically in all contexts. Self-executing LAMBDAs are unnecessary.
                    warnings.append(
                        f"{file_path}: Formula uses self-executing LAMBDA pattern. "
                        f"For parameterless functions, this is unnecessary (see issue #81). "
                        f"Consider simplifying by removing the LAMBDA wrapper."
                    )
                    return errors, warnings

            # This is an uninvoked LAMBDA - flag it as error
            errors.append(
                f"{file_path}: Formula starts with uninvoked LAMBDA wrapper. "
                f"Google Sheets adds the LAMBDA wrapper automatically when you define parameters. "
                f"Only include the formula body in the YAML file."
            )

        return errors, warnings


class RequireParameterExamplesRule(LintRule):
    """Rule: All parameters must have non-empty example values."""

    def __init__(self):
        super().__init__(
            name="require-parameter-examples",
            description="All parameters must have non-empty example values",
        )

    def check(self, file_path: Path, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Check that all parameters have non-empty examples.

        Args:
            file_path: Path to the YAML file
            data: Parsed YAML data

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Skip if parameters field is missing
        if "parameters" not in data:
            return errors, warnings

        parameters = data["parameters"]
        if not isinstance(parameters, list):
            return errors, warnings

        # Check each parameter for example field
        for i, param in enumerate(parameters):
            if not isinstance(param, dict):
                continue

            param_name = param.get("name", f"parameter-{i}")

            # Check if example field exists
            if "example" not in param:
                errors.append(
                    f"{file_path}: Parameter '{param_name}' is missing 'example' field. "
                    f"Provide a concrete example value (e.g., '\"A1:B10\"', '0', 'BLANK()', etc.)"
                )
            else:
                # Check if example is empty string
                example = param.get("example")
                if isinstance(example, str) and example == "":
                    errors.append(
                        f"{file_path}: Parameter '{param_name}' has empty example. "
                        f"Provide a concrete example value (e.g., '\"A1:B10\"', '0', '\"\"', 'BLANK()', etc.)"
                    )

        return errors, warnings


class ValidFormulaSyntaxRule(LintRule):
    """Rule: Formula must be parseable by the pyparsing grammar."""

    def __init__(self):
        super().__init__(
            name="valid-formula-syntax",
            description="Formula must be parseable by the pyparsing grammar",
        )
        self.parser = FormulaParser()

    def check(self, file_path: Path, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Check that the formula can be parsed by the pyparsing grammar.

        Args:
            file_path: Path to the YAML file
            data: Parsed YAML data

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Skip if formula field is missing or not a string
        if "formula" not in data:
            return errors, warnings

        formula = data["formula"]
        if not isinstance(formula, str):
            return errors, warnings

        # Strip comments before parsing (matches generator behavior)
        cleaned_formula = strip_comments(formula)

        try:
            # Attempt to parse the formula
            self.parser.parse(cleaned_formula)
        except ParseException as e:
            # Format error message with position information
            error_msg = f"{file_path}: Formula syntax error"

            # Add position info if available
            if hasattr(e, "loc"):
                error_msg += f" at position {e.loc}"
            if hasattr(e, "msg"):
                error_msg += f": {e.msg}"

            # Add line/column context if available
            if hasattr(e, "line") and hasattr(e, "col"):
                error_msg += f"\n  Line: {e.line}\n  Location: {' ' * (e.col - 1)}^"

            errors.append(error_msg)
        except Exception as e:
            # Catch any other parsing errors
            errors.append(f"{file_path}: Unexpected error while parsing formula: {e}")

        return errors, warnings


class FormulaLinter:
    """Main linter class that runs all validation rules."""

    def __init__(self):
        self.rules: List[LintRule] = [
            NoLeadingEqualsRule(),
            NoTopLevelLambdaRule(),
            RequireParameterExamplesRule(),
            ValidFormulaSyntaxRule(),
            # Add more rules here as needed
        ]

    def lint_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Lint a single YAML file.

        Args:
            file_path: Path to the YAML file to lint

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                errors.append(f"{file_path}: Invalid YAML structure (expected dictionary)")
                return errors, warnings

            # Run all rules
            for rule in self.rules:
                rule_errors, rule_warnings = rule.check(file_path, data)
                errors.extend(rule_errors)
                warnings.extend(rule_warnings)

        except yaml.YAMLError as e:
            errors.append(f"{file_path}: YAML parsing error: {e}")
        except Exception as e:
            errors.append(f"{file_path}: Unexpected error: {e}")

        return errors, warnings

    def lint_all(self, directory: Path = None) -> Tuple[int, int, int, List[str], List[str]]:
        """
        Lint all YAML files in the formulas directory.

        Args:
            directory: Directory to search for YAML files (defaults to formulas/ subdirectory)

        Returns:
            Tuple of (files_checked, error_count, warning_count, errors, warnings)
        """
        if directory is None:
            directory = Path.cwd() / "formulas"

        # Find all .yaml files in the formulas directory
        yaml_files = sorted(directory.glob("*.yaml"))

        all_errors = []
        all_warnings = []
        files_checked = 0

        for yaml_file in yaml_files:
            files_checked += 1
            errors, warnings = self.lint_file(yaml_file)
            all_errors.extend(errors)
            all_warnings.extend(warnings)

        return files_checked, len(all_errors), len(all_warnings), all_errors, all_warnings


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
    files_checked, error_count, warning_count, errors, warnings = linter.lint_all()

    # Report warnings
    if warning_count > 0:
        print(f"⚠️  Found {warning_count} warning(s):")
        print()
        for warning in warnings:
            print(f"  {warning}")
        print()

    # Report results
    if error_count == 0:
        if warning_count > 0:
            print(f"✅ All {files_checked} file(s) passed lint checks (with warnings above)")
        else:
            print(f"✅ All {files_checked} file(s) passed lint checks!")
        return 0
    print(f"❌ Found {error_count} error(s) in {files_checked} file(s):")
    print()
    for error in errors:
        print(f"  {error}")
    print()
    print("Please fix the errors above and run the linter again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
