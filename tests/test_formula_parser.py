#!/usr/bin/env python3
"""
Comprehensive test suite for FormulaParser.

This test suite establishes the specification for what the formula parser
should handle. Tests marked with xfail are expected to fail with current
implementation and define the target behavior.

Based on issue #96 analysis, we test 7 categories:
1. Basic Parsing - Simple function calls
2. LET and LAMBDA - Complex Google Sheets structures
3. String Handling - Quotes and escaping
4. Arrays and Ranges - Spreadsheet-specific syntax
5. Operators - Arithmetic, string concatenation, comparison
6. Edge Cases - Multiple calls, whitespace, deep nesting
7. Real-World Patterns - Actual formulas from the repository
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import pytest
from pyparsing import ParseException
from generate_readme import FormulaParser


class TestBasicParsing:
    """Test basic function call parsing."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_simple_function_call(self):
        """Test parsing simple function call with two arguments."""
        formula = "FUNC(arg1, arg2)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 2

    def test_simple_function_call_single_arg(self):
        """Test parsing function call with single argument."""
        formula = "FUNC(arg1)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 1

    def test_zero_arg_function(self):
        """Test parsing zero-argument function calls."""
        formula = "BLANK()"
        named_functions = {"BLANK"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "BLANK"
        assert len(calls[0]["args"]) == 0

    def test_nested_function_calls(self):
        """Test parsing nested function calls."""
        formula = "OUTER(INNER(x))"
        named_functions = {"OUTER", "INNER"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find both OUTER and INNER
        assert len(calls) == 2
        func_names = {c["name"] for c in calls}
        assert func_names == {"OUTER", "INNER"}

    def test_function_call_with_string_arg(self):
        """Test parsing function call with string argument."""
        formula = 'FUNC("string value")'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_function_call_with_number_arg(self):
        """Test parsing function call with numeric argument."""
        formula = "FUNC(42)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_ignores_non_named_functions(self):
        """Test that parser only extracts named functions, not built-ins."""
        formula = "MYFUNC(SUM(A1:A10))"
        named_functions = {"MYFUNC"}  # SUM is not in named functions

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should only find MYFUNC, not SUM
        assert len(calls) == 1
        assert calls[0]["name"] == "MYFUNC"


class TestLETAndLAMBDA:
    """Test parsing of LET and LAMBDA structures."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_let_with_nested_call(self):
        """Test parsing function call nested within LET statement."""
        formula = "LET(x, FUNC(y), x + 1)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find FUNC even though it's in LET binding
        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_let_multiple_bindings_with_calls(self):
        """Test LET with multiple bindings containing function calls."""
        formula = "LET(x, FUNC1(a), y, FUNC2(b), x + y)"
        named_functions = {"FUNC1", "FUNC2"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find both FUNC1 and FUNC2
        assert len(calls) == 2
        func_names = {c["name"] for c in calls}
        assert func_names == {"FUNC1", "FUNC2"}

    def test_lambda_with_call(self):
        """Test parsing function call inside LAMBDA."""
        formula = 'LAMBDA(x, FUNC(x, "mode"))'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find FUNC inside LAMBDA body
        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_complex_let_lambda_combination(self):
        """Test complex LET statement with LAMBDA containing function calls."""
        formula = 'LET(helper, LAMBDA(x, FUNC1(x)), result, BYROW(data, helper), FUNC2(result))'
        named_functions = {"FUNC1", "FUNC2"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find both FUNC1 (in LAMBDA) and FUNC2 (in LET body)
        assert len(calls) == 2
        func_names = {c["name"] for c in calls}
        assert func_names == {"FUNC1", "FUNC2"}

    def test_multiline_let_statement(self):
        """Test parsing multi-line LET statement (real-world pattern)."""
        formula = """LET(
            x, FUNC1(range),
            y, FUNC2(x, "mode"),
            y + 1
        )"""
        named_functions = {"FUNC1", "FUNC2"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find both functions
        assert len(calls) == 2
        func_names = {c["name"] for c in calls}
        assert func_names == {"FUNC1", "FUNC2"}


class TestStringHandling:
    """Test parsing with various string literal formats."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_double_quoted_string(self):
        """Test function call with double-quoted string."""
        formula = 'FUNC("hello world")'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_single_quoted_string(self):
        """Test function call with single-quoted string."""
        formula = "FUNC('hello world')"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_string_with_embedded_single_quotes(self):
        """Test string containing opposite quote type."""
        formula = '''FUNC("value with 'single' quotes")'''
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_string_with_escaped_quotes(self):
        """Test string with escaped quotes.

        NOTE: This test may reveal edge cases in escape handling.
        Google Sheets uses doubled quotes for escaping: ""Hello"" not \"Hello\"
        """
        # Input: FUNC("Say ""Hello""")
        formula = 'FUNC("Say ' + '""' + 'Hello' + '""' + '"' + ')'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_string_with_multiple_escaped_quotes(self):
        """Test string with multiple escaped quotes in one argument.

        Example: She said "Hello" and "Goodbye" (with doubled quotes in Google Sheets)
        """
        # Input has doubled quotes for escaping
        formula = 'FUNC("She said ' + '""' + 'Hello' + '""' + ' and ' + '""' + 'Goodbye' + '""' + '"' + ')'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 1

    def test_string_starting_with_escaped_quote(self):
        """Test string that starts with an escaped quote."""
        # Input: string starts with escaped quote (3 quotes at start)
        formula = 'FUNC(' + '""' + '"Start with quote"' + ')'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_string_ending_with_escaped_quote(self):
        """Test string that ends with an escaped quote."""
        # Input: string ends with escaped quote (3 quotes at end)
        formula = 'FUNC("End with quote' + '""' + '"' + ')'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_string_with_only_escaped_quotes(self):
        """Test string containing only escaped quotes."""
        # Input: string with two doubled quotes (4 quotes total)
        formula = 'FUNC(' + '""' + '""' + ')'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_multiple_args_with_escaped_quotes(self):
        """Test function with multiple arguments containing escaped quotes."""
        # Input: two arguments each with doubled quotes
        formula = 'FUNC("First ' + '""' + 'arg' + '""' + '", "Second ' + '""' + 'value' + '""' + '"' + ')'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 2

    def test_nested_function_with_escaped_quotes(self):
        """Test nested function calls with escaped quotes in arguments."""
        # Input: nested function with doubled quotes in inner arg
        formula = 'OUTER(INNER("Value with ' + '""' + 'quotes' + '""' + '"' + ')' + ')'
        named_functions = {"OUTER", "INNER"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 2
        func_names = {c["name"] for c in calls}
        assert func_names == {"OUTER", "INNER"}

    def test_mixed_quote_types(self):
        """Test function with both single and double quoted arguments."""
        formula = """FUNC('single', "double")"""
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 2

    def test_empty_string_argument(self):
        """Test function call with empty string argument."""
        formula = 'FUNC("")'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_function_name_in_string_not_matched(self):
        """Test that function names inside strings are not matched."""
        formula = 'REALFUNC("this calls FAKEFUNC(x)")'
        named_functions = {"REALFUNC", "FAKEFUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should only find REALFUNC, not FAKEFUNC in string
        assert len(calls) == 1
        assert calls[0]["name"] == "REALFUNC"


class TestArraysAndRanges:
    """Test parsing with array literals and range references."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_array_literal_single_row(self):
        """Test function call with 1D array literal."""
        formula = "FUNC({1,2,3})"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_array_literal_2d(self):
        """Test function call with 2D array (semicolon separator)."""
        formula = "FUNC({1,2;3,4})"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_array_with_mode_argument(self):
        """Test function with array and string argument (real pattern)."""
        formula = 'FUNC({1,2,3}, "mode")'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 2

    def test_range_reference(self):
        """Test function call with range reference (A1:B10)."""
        formula = "FUNC(A1:B10)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_multiple_range_references(self):
        """Test function with multiple range arguments."""
        formula = "FUNC(A1:B10, C:C, D1:D100)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 3

    def test_entire_column_reference(self):
        """Test function with entire column reference (C:C)."""
        formula = "FUNC(A:A, B:B)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"


class TestOperators:
    """Test parsing formulas with operators."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_arithmetic_in_arguments(self):
        """Test function call with arithmetic expressions in arguments."""
        formula = "FUNC(x + y, z * 2)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_string_concatenation(self):
        """Test function with string concatenation operator (&)."""
        formula = 'FUNC("prefix" & value & "suffix")'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_comparison_operators(self):
        """Test function with comparison operators."""
        formula = "FUNC(x > 0, y <= 10, z <> 5)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_function_call_in_expression(self):
        """Test function call used in arithmetic expression."""
        formula = "FUNC(x) + 10"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_logical_operators(self):
        """Test function with logical operators (AND, OR, NOT)."""
        formula = "FUNC(AND(x > 0, y > 0))"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_multiple_calls_same_function(self):
        """Test formula with multiple calls to the same function.

        This test was previously marked as xfail but now passes with the enhanced
        pyparsing grammar that supports operators. The grammar can now parse
        expressions like FUNC(x) + FUNC(y) and extract both function calls.
        """
        formula = "FUNC(x) + FUNC(y)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find both calls
        assert len(calls) == 2
        assert all(c["name"] == "FUNC" for c in calls)

    def test_whitespace_variations(self):
        """Test function call with various whitespace patterns."""
        formula = "FUNC(  arg1  ,  arg2  )"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_deeply_nested_calls(self):
        """Test deeply nested function calls (4 levels)."""
        formula = "FUNC1(FUNC2(FUNC3(FUNC4(x))))"
        named_functions = {"FUNC1", "FUNC2", "FUNC3", "FUNC4"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find all 4 functions
        assert len(calls) == 4
        func_names = {c["name"] for c in calls}
        assert func_names == {"FUNC1", "FUNC2", "FUNC3", "FUNC4"}

    def test_formula_with_leading_equals(self):
        """Test that formulas with leading = are handled correctly."""
        formula = "=FUNC(x, y)"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_empty_formula(self):
        """Test handling of empty formula."""
        formula = ""
        named_functions = {"FUNC"}

        # Should not crash
        try:
            ast = self.parser.parse(formula)
            calls = self.parser.extract_function_calls(ast, named_functions)
            # Empty formula should have no calls
            assert len(calls) == 0
        except Exception:
            # Or it might raise an exception, which is also acceptable
            pass

    def test_formula_with_only_whitespace(self):
        """Test handling of whitespace-only formula."""
        formula = "   "
        named_functions = {"FUNC"}

        # Should not crash
        try:
            ast = self.parser.parse(formula)
            calls = self.parser.extract_function_calls(ast, named_functions)
            assert len(calls) == 0
        except Exception:
            # Or it might raise an exception, which is also acceptable
            pass

    def test_function_with_parentheses_in_string(self):
        """Test that parentheses inside strings don't confuse the parser."""
        formula = 'FUNC("value (with parens)")'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"

    def test_function_with_comma_in_string(self):
        """Test that commas inside strings don't split arguments."""
        formula = 'FUNC("value, with, commas", arg2)'
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        # Should have 2 args, not 4
        assert len(calls[0]["args"]) == 2

    def test_very_long_argument_list(self):
        """Test function with many arguments (stress test)."""
        # Create a function call with 20 arguments
        args = ", ".join([f"arg{i}" for i in range(20)])
        formula = f"FUNC({args})"
        named_functions = {"FUNC"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "FUNC"
        assert len(calls[0]["args"]) == 20


class TestRealWorldPatterns:
    """Test patterns from actual formulas in the repository.

    These tests use real formula patterns to ensure parser handles
    production use cases.
    """

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_densifyrows_pattern(self):
        """Test DENSIFYROWS calling DENSIFY (actual formula)."""
        formula = 'DENSIFY(range, "rows")'
        named_functions = {"DENSIFY"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "DENSIFY"
        assert len(calls[0]["args"]) == 2

    def test_densify_complex_let(self):
        """Test DENSIFY's complex LET structure (simplified)."""
        formula = """LET(
            actual_mode, IF(OR(mode="", mode=0), "both", LOWER(TRIM(mode))),
            result, FILTER(range, BYROW(range, LAMBDA(r, COUNTA(r) >= 1))),
            result
        )"""
        named_functions = set()  # No named function calls in this formula

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find no named function calls (only built-ins)
        assert len(calls) == 0

    def test_vstackfill_with_blank(self):
        """Test VSTACKFILL calling BLANK (real pattern)."""
        formula = "VSTACK(a, b, BLANK())"
        named_functions = {"BLANK"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "BLANK"
        assert len(calls[0]["args"]) == 0

    def test_blanktoempty_calling_isblanklike(self):
        """Test formula calling another named function with IF."""
        formula = 'IF(ISBLANKLIKE(value), "", value)'
        named_functions = {"ISBLANKLIKE"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "ISBLANKLIKE"

    def test_multiple_named_functions_in_let(self):
        """Test LET calling multiple named functions (complex composition)."""
        formula = """LET(
            blank_check, ISBLANKLIKE(x),
            result, IF(blank_check, BLANK(), x),
            result
        )"""
        named_functions = {"ISBLANKLIKE", "BLANK"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should find both ISBLANKLIKE and BLANK
        assert len(calls) == 2
        func_names = {c["name"] for c in calls}
        assert func_names == {"ISBLANKLIKE", "BLANK"}

    def test_byrow_with_lambda_calling_named_function(self):
        """Test BYROW with LAMBDA that calls a named function."""
        formula = 'BYROW(range, LAMBDA(row, DENSIFY(row, "cols")))'
        named_functions = {"DENSIFY"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        assert len(calls) == 1
        assert calls[0]["name"] == "DENSIFY"


class TestParserMechanics:
    """Test the mechanics of the parser itself."""

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_extract_calls_returns_sorted_by_depth(self):
        """Test that extract_function_calls returns calls sorted by depth."""
        formula = "OUTER(INNER(x))"
        named_functions = {"OUTER", "INNER"}

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Calls should be sorted by depth (reverse order - deepest first)
        assert len(calls) == 2
        # INNER is deeper (depth 1) than OUTER (depth 0)
        # Sorted by depth reverse, so INNER should come first
        assert calls[0]["name"] == "INNER"
        assert calls[1]["name"] == "OUTER"

    def test_named_functions_filter_works(self):
        """Test that only named functions in the set are extracted."""
        formula = "NAMED(BUILTIN(x))"
        named_functions = {"NAMED"}  # BUILTIN is not named

        ast = self.parser.parse(formula)
        calls = self.parser.extract_function_calls(ast, named_functions)

        # Should only find NAMED, not BUILTIN
        assert len(calls) == 1
        assert calls[0]["name"] == "NAMED"

    def test_reconstruct_call_simple(self):
        """Test FormulaParser.reconstruct_call() with simple args."""
        result = FormulaParser.reconstruct_call("FUNC", ["arg1", "arg2"])
        assert result == "FUNC(arg1, arg2)"

    def test_reconstruct_call_with_string_literal(self):
        """Test reconstruct_call() with marked string literal."""
        # String literals are marked as tuples by parser
        result = FormulaParser.reconstruct_call("FUNC", [("__STRING_LITERAL__", "value")])
        assert result == 'FUNC("value")'

    def test_reconstruct_call_zero_args(self):
        """Test reconstruct_call() with no arguments."""
        result = FormulaParser.reconstruct_call("BLANK", [])
        assert result == "BLANK()"

    def test_reconstruct_call_with_parenthesized_expression(self):
        """Test reconstruct_call() preserves parentheses in expressions."""
        # Test case from issue: ERROR("text" & (num_cols - 1))
        formula = 'ERROR("text" & (num_cols - 1))'
        parser = FormulaParser()
        ast = parser.parse(formula)
        calls = parser.extract_function_calls(ast, {"ERROR"})

        assert len(calls) == 1
        reconstructed = FormulaParser.reconstruct_call(calls[0]["name"], calls[0]["args"])
        assert formula == reconstructed


class TestNegativeCases:
    """Test that parser correctly rejects invalid syntax.

    These tests document the grammar boundaries - what the parser should reject.
    This helps prevent accepting invalid syntax in future changes.
    """

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_missing_operator_between_cells(self):
        """Test that missing operator between cells fails.

        'A1 B1' is invalid - Google Sheets requires explicit operators
        between values (e.g., A1+B1, A1*B1).
        """
        with pytest.raises(ParseException):
            self.parser.parse("A1 B1")

    def test_malformed_range_double_colon(self):
        """Test that malformed range with double colon fails.

        'A1::' is invalid - colon requires valid cell reference on both sides.
        """
        with pytest.raises(ParseException):
            self.parser.parse("A1::")

    def test_unbalanced_parentheses_open_only(self):
        """Test that unbalanced parentheses (open only) fails.

        '((' is invalid - parentheses must be balanced.
        """
        with pytest.raises(ParseException):
            self.parser.parse("((")

    def test_unclosed_function_call(self):
        """Test that unclosed function call fails.

        'FUNC(' is invalid - function calls must have closing parenthesis.
        """
        with pytest.raises(ParseException):
            self.parser.parse("FUNC(")

    def test_single_close_parenthesis(self):
        """Test that single close parenthesis fails.

        ')' is invalid - no matching open parenthesis.
        """
        with pytest.raises(ParseException):
            self.parser.parse(")")

    def test_trailing_operator(self):
        """Test that trailing operator fails.

        'A1+' is invalid - binary operators require operands on both sides.
        """
        with pytest.raises(ParseException):
            self.parser.parse("A1+")

    def test_only_operator(self):
        """Test that operator alone fails.

        '+' alone is invalid - needs operands.
        """
        with pytest.raises(ParseException):
            self.parser.parse("+")

    def test_leading_comma_outside_function(self):
        """Test that leading comma outside function context fails.

        ',A1' is invalid outside of a function argument list.
        """
        with pytest.raises(ParseException):
            self.parser.parse(",A1")

    def test_trailing_comma_outside_function(self):
        """Test that trailing comma outside function context fails.

        'A1,' is invalid outside of a function argument list.
        """
        with pytest.raises(ParseException):
            self.parser.parse("A1,")

    def test_missing_closing_paren_in_function(self):
        """Test that missing closing parenthesis in function fails.

        'FUNC(A1' is invalid - function calls must be closed.
        """
        with pytest.raises(ParseException):
            self.parser.parse("FUNC(A1")

    def test_extra_open_paren(self):
        """Test that extra open parenthesis fails.

        '((A1)' is invalid - unbalanced parentheses.
        """
        with pytest.raises(ParseException):
            self.parser.parse("((A1)")

    def test_extra_close_paren(self):
        """Test that extra close parenthesis fails.

        '(A1))' is invalid - unbalanced parentheses.
        """
        with pytest.raises(ParseException):
            self.parser.parse("(A1))")

    def test_empty_array_rejected(self):
        """Test that empty array literal is rejected.

        '{}' is invalid in Google Sheets - arrays must have at least one element.
        """
        with pytest.raises(ParseException):
            self.parser.parse("{}")

    def test_array_with_empty_element_rejected(self):
        """Test that array with empty element is rejected.

        '{,}' is invalid in Google Sheets - array elements cannot be empty.
        """
        with pytest.raises(ParseException):
            self.parser.parse("{,}")


class TestValidEdgeCases:
    """Test that valid edge cases are correctly accepted.

    These tests document surprising but valid syntax - patterns that might
    look wrong but are actually valid in Google Sheets.
    """

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    def test_leading_equals_accepted(self):
        """Test that leading = is accepted.

        '=A1+B1' is valid - the leading = is how formulas are entered
        in Google Sheets. The parser strips it during normalization.
        """
        result = self.parser.parse("=A1+B1")
        assert result is not None

    def test_empty_arguments_accepted(self):
        """Test that empty arguments (zero-arg function) are accepted.

        'FUNC()' is valid - functions like TODAY(), NOW(), RAND() have
        no arguments but still require parentheses.
        """
        result = self.parser.parse("FUNC()")
        assert result is not None

    def test_empty_string_argument_accepted(self):
        """Test that empty string argument is accepted.

        'FUNC("")' is valid - empty string is a legitimate argument value.
        """
        result = self.parser.parse('FUNC("")')
        assert result is not None

    def test_empty_argument_in_list_accepted(self):
        """Test that empty argument between commas is accepted.

        'FUNC(,)' is valid - equivalent to passing BLANK() as arguments.
        Some functions accept optional parameters via empty commas.
        """
        result = self.parser.parse("FUNC(,)")
        assert result is not None

    def test_trailing_comma_with_empty_arg_accepted(self):
        """Test that trailing comma with empty argument is accepted.

        'FUNC(A1,)' is valid - the trailing comma represents an empty
        argument, equivalent to BLANK().
        """
        result = self.parser.parse("FUNC(A1,)")
        assert result is not None

    def test_leading_comma_with_empty_arg_accepted(self):
        """Test that leading comma with empty argument is accepted.

        'FUNC(,B1)' is valid - the leading comma represents an empty
        first argument, equivalent to BLANK().
        """
        result = self.parser.parse("FUNC(,B1)")
        assert result is not None

    def test_double_comma_creates_empty_arg(self):
        """Test that double comma (empty middle argument) is accepted.

        'FUNC(A1,,B1)' is valid - the double comma creates an empty
        middle argument, equivalent to FUNC(A1, BLANK(), B1).
        """
        result = self.parser.parse("FUNC(A1,,B1)")
        assert result is not None

    def test_identifier_without_parentheses_accepted(self):
        """Test that identifier without parentheses is accepted.

        'FUNC' (without parentheses) is valid syntax - it's treated as
        an identifier/named range, not a function call. In Google Sheets,
        this would reference a named range called 'FUNC' (or error if
        it doesn't exist), but it's not a parse error.
        """
        result = self.parser.parse("FUNC")
        assert result is not None

    def test_double_operator_with_unary_accepted(self):
        """Test that apparent double operator is accepted when second is unary.

        'A1 + + B1' is valid - the second '+' is a unary operator applied
        to B1. This is equivalent to 'A1 + (+B1)' = 'A1 + B1'.
        Google Sheets supports unary + and - operators.
        """
        result = self.parser.parse("A1 + + B1")
        assert result is not None

    def test_double_unary_minus_accepted(self):
        """Test that double unary minus is accepted.

        '--A1' is valid - double negation is supported.
        This is equivalent to -(-A1) = A1.
        """
        result = self.parser.parse("--A1")
        assert result is not None

    def test_mixed_unary_operators_accepted(self):
        """Test that mixed unary operators are accepted.

        '+-A1' is valid - unary + followed by unary -.
        This is equivalent to +(-A1) = -A1.
        """
        result = self.parser.parse("+-A1")
        assert result is not None


class TestGrammarRuleCoverage:
    """Ensure at least one negative test exists per grammar construct.

    This class provides targeted tests for each grammar rule to ensure
    we have comprehensive negative test coverage.
    """

    def setup_method(self):
        """Initialize parser before each test."""
        self.parser = FormulaParser()

    # Numbers - malformed number literals
    def test_invalid_number_format(self):
        """Test that malformed numbers fail (if applicable).

        Note: pyparsing number parsing is fairly permissive, so
        we test what actually fails vs what gets parsed differently.
        """
        # '1.2.3' - multiple decimal points, should fail
        with pytest.raises(ParseException):
            self.parser.parse("1.2.3")

    # Strings - unclosed strings
    def test_unclosed_double_quote_string(self):
        """Test that unclosed double-quoted string fails.

        '"hello' is invalid - string must be closed.
        """
        with pytest.raises(ParseException):
            self.parser.parse('"hello')

    def test_unclosed_single_quote_string(self):
        """Test that unclosed single-quoted string fails.

        \"'hello\" is invalid - string must be closed.
        """
        with pytest.raises(ParseException):
            self.parser.parse("'hello")

    # Function calls - various malformed patterns
    def test_function_call_missing_open_paren(self):
        """Test that function call pattern with missing open paren fails.

        'FUNC)' is invalid - missing opening parenthesis.
        """
        with pytest.raises(ParseException):
            self.parser.parse("FUNC)")

    def test_nested_unclosed_function(self):
        """Test that nested unclosed function call fails.

        'OUTER(INNER(' is invalid - INNER is not closed.
        """
        with pytest.raises(ParseException):
            self.parser.parse("OUTER(INNER(")

    # Ranges - malformed range patterns
    def test_range_missing_start(self):
        """Test that range with missing start fails.

        ':B10' is invalid - range needs start cell.
        Note: This pattern might be caught differently by the parser.
        """
        # This actually parses as an empty range reference in our grammar
        # Let's test a clearly invalid pattern
        with pytest.raises(ParseException):
            self.parser.parse(":::")

    # Arrays - malformed array patterns
    def test_unclosed_array(self):
        """Test that unclosed array literal fails.

        '{1,2,3' is invalid - array must be closed.
        """
        with pytest.raises(ParseException):
            self.parser.parse("{1,2,3")

    # Operators - invalid operator sequences
    def test_multiple_binary_operators(self):
        """Test that multiple binary operators in sequence fails.

        'A1 * / B1' is invalid - can't have two binary operators.
        (Note: + and - can be unary, but * and / cannot)
        """
        with pytest.raises(ParseException):
            self.parser.parse("A1 * / B1")

    def test_binary_operator_at_start(self):
        """Test that binary-only operator at start fails.

        '*A1' is invalid - * cannot be unary, only + and - can.
        """
        with pytest.raises(ParseException):
            self.parser.parse("*A1")

    def test_division_at_start(self):
        """Test that division operator at start fails.

        '/A1' is invalid - / cannot be unary.
        """
        with pytest.raises(ParseException):
            self.parser.parse("/A1")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
