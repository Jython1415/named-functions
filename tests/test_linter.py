#!/usr/bin/env python3
"""
Comprehensive test suite for FormulaLinter.

This test suite validates the linter rules and ensures they catch
invalid formula patterns while allowing valid ones.

Test organization:
1. TestNoLeadingEqualsRule - validates no leading = character
2. TestNoTopLevelLambdaRule - validates no uninvoked LAMBDA at top level
3. TestFormulaLinter - validates main linter functionality
4. TestExistingFormulas - regression test for all formulas in repository
"""

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
import yaml
from lint_formulas import (
    FormulaLinter,
    NoLeadingEqualsRule,
    NoTopLevelLambdaRule,
    RequireParameterExamplesRule,
)


class TestNoLeadingEqualsRule:
    """Test the NoLeadingEqualsRule for detecting leading = character."""

    def setup_method(self):
        """Initialize rule before each test."""
        self.rule = NoLeadingEqualsRule()

    def test_formula_without_leading_equals_passes(self):
        """Test that a valid formula without = passes with no errors."""
        data = {"formula": "LET(x, 1, x)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_formula_with_leading_equals_fails(self):
        """Test that formula starting with = produces an error."""
        data = {"formula": "=SUM(A1:A10)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "starts with" in errors[0].lower()
        assert len(warnings) == 0

    def test_formula_with_whitespace_and_leading_equals_fails(self):
        """Test that formula with leading whitespace and = fails.

        Whitespace should be stripped before checking for =.
        """
        data = {"formula": "   =SUM(A1:A10)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert len(warnings) == 0

    def test_missing_formula_field_passes(self):
        """Test that missing formula field is silently skipped.

        Other validators (schema validation) will catch missing formula field.
        """
        data = {"name": "MYFUNCTION"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_non_string_formula_passes(self):
        """Test that non-string formula field is skipped.

        This is a data type issue that schema validation should catch.
        """
        data = {"formula": 123}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_formula_with_equals_in_middle_passes(self):
        """Test that = in the middle of formula is allowed.

        Only leading = is invalid. Comparisons like '=' are allowed.
        """
        data = {"formula": 'IF(x=5, "equal", "not equal")'}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_simple_function_passes(self):
        """Test that simple function call is valid."""
        data = {"formula": "SUM(A1:A10)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0


class TestNoTopLevelLambdaRule:
    """Test the NoTopLevelLambdaRule for detecting uninvoked LAMBDA."""

    def setup_method(self):
        """Initialize rule before each test."""
        self.rule = NoTopLevelLambdaRule()

    def test_normal_formula_passes(self):
        """Test that normal formula without LAMBDA passes."""
        data = {"formula": "LET(x, 1, x)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_uninvoked_lambda_fails(self):
        """Test that LAMBDA(x, x+1) without invocation produces error.

        Uninvoked LAMBDA is invalid because Google Sheets adds the wrapper
        automatically when you define parameters.
        """
        data = {"formula": "LAMBDA(x, x+1)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "uninvoked" in errors[0].lower()
        assert len(warnings) == 0

    def test_self_executing_lambda_warns(self):
        """Test that self-executing LAMBDA produces warning, not error.

        LAMBDA(x, x+1)(0) is technically valid but unnecessary.
        """
        data = {"formula": "LAMBDA(x, x+1)(0)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 1
        assert "self-executing" in warnings[0].lower()

    def test_nested_lambda_inside_let_passes(self):
        """Test that LAMBDA nested in LET is allowed.

        Only top-level uninvoked LAMBDA is invalid. LAMBDA inside LET
        or as argument is fine.
        """
        data = {"formula": "LET(f, LAMBDA(x, x+1), f(5))"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_lambda_lowercase_fails(self):
        """Test that lowercase 'lambda' also fails (case-insensitive check)."""
        data = {"formula": "lambda(x, x+1)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "uninvoked" in errors[0].lower()

    def test_missing_formula_field_passes(self):
        """Test that missing formula field is skipped."""
        data = {"name": "MYFUNCTION"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_non_string_formula_passes(self):
        """Test that non-string formula field is skipped."""
        data = {"formula": 123}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_lambda_as_argument_passes(self):
        """Test that LAMBDA as an argument (not top-level) is allowed.

        BYROW(range, LAMBDA(r, ...)) is valid because the LAMBDA
        is an argument, not the top-level formula.
        """
        data = {"formula": "BYROW(range, LAMBDA(r, COUNTA(r)))"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_whitespace_before_lambda_fails(self):
        """Test that leading whitespace is ignored before checking LAMBDA."""
        data = {"formula": "  LAMBDA(x, x+1)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert len(warnings) == 0

    def test_self_executing_lambda_with_multiple_args_warns(self):
        """Test self-executing LAMBDA with multiple arguments warns."""
        data = {"formula": "LAMBDA(x, y, x+y)(1, 2)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 1

    def test_self_executing_lambda_with_whitespace_warns(self):
        """Test self-executing LAMBDA with whitespace between definition and call."""
        data = {"formula": "LAMBDA(x, x+1) (5)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 1


class TestRequireParameterExamplesRule:
    """Test the RequireParameterExamplesRule for parameter example validation."""

    def setup_method(self):
        """Initialize rule before each test."""
        self.rule = RequireParameterExamplesRule()

    def test_parameter_with_non_empty_example_passes(self):
        """Test that parameter with non-empty example passes."""
        data = {
            "parameters": [{"name": "input", "description": "Test parameter", "example": "A1:B10"}]
        }
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_parameter_with_empty_example_fails(self):
        """Test that parameter with empty example produces error."""
        data = {
            "parameters": [
                {"name": "replacement", "description": "Replacement value", "example": ""}
            ]
        }
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "empty example" in errors[0].lower()
        assert "replacement" in errors[0].lower()
        assert len(warnings) == 0

    def test_parameter_missing_example_fails(self):
        """Test that parameter without example field produces error."""
        data = {"parameters": [{"name": "input", "description": "Missing example"}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "missing" in errors[0].lower()
        assert "example" in errors[0].lower()
        assert "input" in errors[0].lower()
        assert len(warnings) == 0

    def test_multiple_parameters_all_with_examples_passes(self):
        """Test that multiple parameters with examples pass."""
        data = {
            "parameters": [
                {"name": "range", "description": "Data range", "example": "A1:Z100"},
                {"name": "mode", "description": "Mode", "example": '"rows-any"'},
                {"name": "func", "description": "Callback", "example": "LAMBDA(x, SUM(x))"},
            ]
        }
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_multiple_parameters_one_empty_fails(self):
        """Test that multiple parameters with one empty example fails."""
        data = {
            "parameters": [
                {"name": "range", "description": "Data range", "example": "A1:Z100"},
                {"name": "value", "description": "Value", "example": ""},
                {"name": "func", "description": "Callback", "example": "LAMBDA(x, SUM(x))"},
            ]
        }
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "value" in errors[0].lower()
        assert "empty example" in errors[0].lower()

    def test_parameter_with_quoted_example_passes(self):
        """Test that parameter with quoted example passes."""
        data = {"parameters": [{"name": "mode", "description": "Mode", "example": '"rows-any"'}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0

    def test_parameter_with_blank_function_example_passes(self):
        """Test that parameter with BLANK() example passes."""
        data = {"parameters": [{"name": "fill", "description": "Fill value", "example": "BLANK()"}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0

    def test_parameter_with_numeric_example_passes(self):
        """Test that parameter with numeric example passes."""
        data = {"parameters": [{"name": "count", "description": "Count", "example": 10}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0

    def test_parameter_with_zero_example_passes(self):
        """Test that parameter with zero example passes (falsy but valid)."""
        data = {"parameters": [{"name": "offset", "description": "Offset", "example": 0}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0

    def test_missing_parameters_field_passes(self):
        """Test that missing parameters field is skipped."""
        data = {"name": "TEST_FUNC", "formula": "SUM(A1:A10)"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_non_list_parameters_field_passes(self):
        """Test that non-list parameters field is skipped."""
        data = {"parameters": "not a list"}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_parameter_with_quoted_empty_string_example_fails(self):
        """Test that parameter with '""' as example fails (literal empty string)."""
        data = {"parameters": [{"name": "replacement", "description": "Value", "example": ""}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 1
        assert "empty example" in errors[0].lower()

    def test_parameter_with_double_quoted_example_passes(self):
        """Test that parameter with double-quoted string example passes.

        When the YAML value is '"text"', it represents the string with quotes,
        which is a non-empty string, so it should pass.
        """
        data = {"parameters": [{"name": "text", "description": "Text", "example": '""'}]}
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        assert len(errors) == 0

    def test_non_dict_parameter_element_skipped(self):
        """Test that non-dict parameter elements are skipped."""
        data = {
            "parameters": [
                {"name": "param1", "description": "Valid", "example": "A1"},
                "invalid string element",
                {"name": "param2", "description": "Also valid", "example": "B1"},
            ]
        }
        errors, warnings = self.rule.check(Path("test.yaml"), data)

        # Should check the valid parameters but skip the string element
        assert len(errors) == 0

    def test_error_includes_file_path(self):
        """Test that error message includes the file path."""
        data = {"parameters": [{"name": "test", "description": "Test", "example": ""}]}
        errors, warnings = self.rule.check(Path("formulas/test.yaml"), data)

        assert len(errors) == 1
        assert "formulas/test.yaml" in errors[0]


class TestFormulaLinter:
    """Test the main FormulaLinter class."""

    def setup_method(self):
        """Initialize linter before each test."""
        self.linter = FormulaLinter()

    def test_linter_has_expected_rules(self):
        """Test that linter has all expected rules registered."""
        rule_names = {rule.name for rule in self.linter.rules}

        assert "no-leading-equals" in rule_names
        assert "no-top-level-lambda" in rule_names
        assert "require-parameter-examples" in rule_names
        assert "valid-formula-syntax" in rule_names
        assert len(self.linter.rules) == 4

    def test_lint_file_with_valid_yaml(self):
        """Test linting a valid YAML file with no linter errors."""
        # Create a temporary YAML file with valid formula
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"name": "TEST_FUNC", "formula": "LET(x, 1, x)"}, f)
            temp_path = Path(f.name)

        try:
            errors, warnings = self.linter.lint_file(temp_path)
            assert len(errors) == 0
            assert len(warnings) == 0
        finally:
            temp_path.unlink()

    def test_lint_file_with_leading_equals_error(self):
        """Test linting file with leading = produces error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"name": "TEST_FUNC", "formula": "=SUM(A1:A10)"}, f)
            temp_path = Path(f.name)

        try:
            errors, warnings = self.linter.lint_file(temp_path)
            assert len(errors) == 1
            assert "starts with" in errors[0].lower()
        finally:
            temp_path.unlink()

    def test_lint_file_with_uninvoked_lambda_error(self):
        """Test linting file with uninvoked LAMBDA produces error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"name": "TEST_FUNC", "formula": "LAMBDA(x, x+1)"}, f)
            temp_path = Path(f.name)

        try:
            errors, warnings = self.linter.lint_file(temp_path)
            assert len(errors) == 1
            assert "uninvoked" in errors[0].lower()
        finally:
            temp_path.unlink()

    def test_lint_file_with_self_executing_lambda_warning(self):
        """Test linting file with self-executing LAMBDA produces error and warning.

        Self-executing LAMBDAs produce:
        - 1 error from ValidFormulaSyntaxRule (invalid syntax per pyparsing grammar)
        - 1 warning from NoTopLevelLambdaRule (unnecessary self-executing pattern)
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"name": "TEST_FUNC", "formula": "LAMBDA(x, x+1)(0)"}, f)
            temp_path = Path(f.name)

        try:
            errors, warnings = self.linter.lint_file(temp_path)
            assert len(errors) == 1
            assert "syntax" in errors[0].lower()
            assert len(warnings) == 1
            assert "self-executing" in warnings[0].lower()
        finally:
            temp_path.unlink()

    def test_lint_file_with_yaml_parse_error(self):
        """Test linting file with invalid YAML produces error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Write invalid YAML
            f.write("invalid: yaml: content: without: proper: structure")
            temp_path = Path(f.name)

        try:
            errors, warnings = self.linter.lint_file(temp_path)
            assert len(errors) == 1
            assert "parsing error" in errors[0].lower() or "yaml" in errors[0].lower()
        finally:
            temp_path.unlink()

    def test_lint_file_with_non_dict_yaml(self):
        """Test linting file where YAML parses to non-dict raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Write YAML that parses as a list, not a dict
            f.write("- item1\n- item2\n")
            temp_path = Path(f.name)

        try:
            errors, warnings = self.linter.lint_file(temp_path)
            assert len(errors) == 1
            assert "invalid yaml structure" in errors[0].lower()
        finally:
            temp_path.unlink()

    def test_lint_all_returns_file_count(self):
        """Test that lint_all returns correct file count."""
        # Create temporary directory with formula files
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create 3 valid formula files
            for i in range(3):
                with open(tmpdir_path / f"formula{i}.yaml", "w") as f:
                    yaml.dump({"name": f"FUNC{i}", "formula": "LET(x, 1, x)"}, f)

            files_checked, error_count, warning_count, errors, warnings = self.linter.lint_all(
                tmpdir_path
            )

            assert files_checked == 3
            assert error_count == 0
            assert warning_count == 0

    def test_lint_all_counts_errors(self):
        """Test that lint_all correctly counts errors from multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create one valid and one invalid file
            with open(tmpdir_path / "valid.yaml", "w") as f:
                yaml.dump({"name": "VALID", "formula": "LET(x, 1, x)"}, f)

            with open(tmpdir_path / "invalid.yaml", "w") as f:
                yaml.dump({"name": "INVALID", "formula": "=SUM(A1:A10)"}, f)

            files_checked, error_count, warning_count, errors, warnings = self.linter.lint_all(
                tmpdir_path
            )

            assert files_checked == 2
            assert error_count == 1
            assert len(errors) == 1

    def test_lint_all_counts_warnings(self):
        """Test that lint_all correctly counts warnings from multiple files.

        Self-executing LAMBDAs produce both an error (syntax) and a warning (pattern).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create file with warning (self-executing LAMBDA)
            with open(tmpdir_path / "warning.yaml", "w") as f:
                yaml.dump({"name": "WARNING_FUNC", "formula": "LAMBDA(x, x+1)(0)"}, f)

            files_checked, error_count, warning_count, errors, warnings = self.linter.lint_all(
                tmpdir_path
            )

            assert files_checked == 1
            assert error_count == 1  # From ValidFormulaSyntaxRule
            assert warning_count == 1  # From NoTopLevelLambdaRule
            assert len(errors) == 1
            assert len(warnings) == 1

    def test_lint_all_with_empty_directory(self):
        """Test lint_all on directory with no YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            files_checked, error_count, warning_count, errors, warnings = self.linter.lint_all(
                tmpdir_path
            )

            assert files_checked == 0
            assert error_count == 0
            assert warning_count == 0


class TestExistingFormulas:
    """Regression test: All existing formulas in the repository must pass linting."""

    def test_all_existing_formulas_pass_lint(self):
        """Test that all formulas in formulas/ directory pass linting."""
        # Find the formulas directory relative to the project root
        project_root = Path(__file__).parent.parent
        formulas_dir = project_root / "formulas"

        # Skip test if formulas directory doesn't exist
        if not formulas_dir.exists():
            pytest.skip("formulas/ directory not found")

        linter = FormulaLinter()
        files_checked, error_count, warning_count, errors, warnings = linter.lint_all(formulas_dir)

        # All errors should be reported in assertion message for debugging
        if errors:
            error_messages = "\n".join(errors)
            pytest.fail(f"Found {error_count} linting error(s):\n{error_messages}")

        # Check that we actually found and validated some formulas
        assert files_checked > 0, "No formula files found in formulas/ directory"
        assert error_count == 0, f"Expected no errors, found {error_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
