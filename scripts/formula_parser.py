#!/usr/bin/env python3
"""
Formula parser module for Google Sheets formulas.

This module provides:
- FormulaParser: A pyparsing-based parser for Google Sheets formula syntax
- strip_comments: Utility function to remove comments from formulas

The parser supports:
- Function calls with arguments (including nested and zero-argument calls)
- String literals with Google Sheets doubled-quote escaping
- Numbers, identifiers, cell references, and range references
- Array literals
- Operators (arithmetic, comparison, logical, string concatenation)
- Parenthesized expressions
- Empty arguments (e.g., IF(,,))
"""

import re
from typing import Any, Dict, List, Set

from pyparsing import (
    DelimitedList,
    Forward,
    Group,
    Literal,
    Optional,
    ParseResults,
    Word,
    ZeroOrMore,
    alphanums,
    alphas,
    pyparsing_common,
)


def strip_comments(formula: str) -> str:
    """
    Remove // and /* */ style comments from formula text.

    This ensures formulas copied from the README are valid Google Sheets
    formulas, as Google Sheets does not support comments in formulas.

    Args:
        formula: Formula text potentially containing comments

    Returns:
        Formula with comments removed
    """
    # Remove /* */ style block comments
    result = re.sub(r"/\*.*?\*/", "", formula, flags=re.DOTALL)
    # Remove // style line comments
    result = re.sub(r"//[^\n]*", "", result)
    return result


class FormulaParser:
    """Parser for Google Sheets formulas using pyparsing."""

    def __init__(self):
        """Initialize the parser with grammar definition."""
        # Define basic tokens
        identifier = Word(alphas + "_", alphanums + "_")
        lparen = Literal("(")
        rparen = Literal(")")
        comma = Literal(",")

        # String literals (handle escaped quotes)
        # Google Sheets uses doubled-quote escaping: "" within a string represents a single "
        # Note: pyparsing's esc_quote parameter has a bug when """ is followed by , and then "
        # So we use a custom regex-based parser instead
        from pyparsing import Regex

        # Match double-quoted strings: opening ", content (with "" escapes), closing "
        # The content can be: any char except ", OR "" (escaped quote)
        # Pattern: " (?: [^"] | "" )* "
        double_quoted = Regex(r'"(?:[^"]|"")*"')

        # Match single-quoted strings: opening ', content (with '' escapes), closing '
        # Pattern: ' (?: [^'] | '' )* '
        single_quoted = Regex(r"'(?:[^']|'')*'")

        def process_string_literal(t):
            """Process a quoted string literal, unescaping doubled quotes."""
            s = t[0]
            # Remove opening and closing quotes
            content = s[1:-1]
            # Unescape doubled quotes
            if s[0] == '"':
                content = content.replace('""', '"')
            else:  # single quote
                content = content.replace("''", "'")
            return ("__STRING_LITERAL__", content)

        string_literal = (double_quoted | single_quoted).set_parse_action(process_string_literal)

        # Numbers
        number = pyparsing_common.number()

        # Cell reference patterns: A1, $A$1, etc.
        # Include underscore to prevent partial matching of identifiers like header_rows
        cell_ref = Word(alphas + "$", alphanums + "$" + "_")

        # Range reference: A1:B10, A:A, 1:1, etc.
        # Use Regex for flexibility with sheet references and complex patterns
        from pyparsing import Regex

        range_ref = Regex(r"[A-Za-z$]*[0-9$]*:[A-Za-z$]*[0-9$]*")

        # Forward declaration for recursive expressions
        expression = Forward()
        parenthesized_expr = Forward()

        # Function call: FUNC(arg1, arg2, ...)
        # Support for empty arguments in function calls (e.g., IF(,,))
        from pyparsing import FollowedBy

        # An argument can be an expression OR nothing (matched via lookahead)
        # The lookahead ensures empty args are only valid between/before commas or rparen
        empty_arg = (FollowedBy(comma | rparen)).set_parse_action(lambda: "__EMPTY__")

        # Allow expressions or empty args
        argument = expression | empty_arg

        # Use DelimitedList for comma-separated args
        args_list = Optional(DelimitedList(argument))

        # Create the function call and apply a parse action to fix spurious empty args
        function_call_raw = Group(
            identifier("function")
            + lparen.suppress()
            + Group(args_list)("args")
            + rparen.suppress()
        )

        # Parse action to fix args structure
        def fix_function_call(tokens):
            # tokens[0] is a ParseResults for the function_call
            # tokens[0]['args'] contains the args list
            call = tokens[0]
            if "args" in call:
                args = call["args"]
                # If args is [[]] or [['__EMPTY__']], convert to []
                if len(args) == 1 and (args[0] == [] or args[0] == "__EMPTY__"):
                    call["args"] = []
            return tokens

        function_call = function_call_raw.copy().set_parse_action(fix_function_call)

        # Array literal: {1,2,3} or {1,2;3,4}
        # Arrays can contain expressions separated by commas (columns) and semicolons (rows)
        # Use regex to match content inside braces, requiring at least one non-delimiter element
        # This rejects empty arrays {} and delimiter-only arrays {,} {;} which Google Sheets rejects
        from pyparsing import Regex

        array_literal = Regex(r"\{[^}]*[^,;\s}][^}]*\}")

        # Operators (all Google Sheets operators)
        # Arithmetic: +, -, *, /, ^
        # String concatenation: &
        # Comparison: =, <>, <, >, <=, >=
        # Logical: AND, OR (used as infix operators in some formulas)
        # Note: : is NOT an operator - it's handled by range_ref pattern
        # We define these but don't strictly parse operator precedence
        # We just need them recognized so parsing doesn't stop at them
        from pyparsing import CaselessKeyword, one_of

        # Use case-insensitive matching for AND and OR since they can appear in various cases
        and_op = CaselessKeyword("AND")
        or_op = CaselessKeyword("OR")
        # Regular operators with one_of (space-separated for case-sensitive matching)
        basic_operators = one_of("+ - * / ^ & = <> < > <= >=")
        operators = and_op | or_op | basic_operators

        # Unary operators (prefix operators like unary minus: -x, --x)
        # These are different from binary operators and can appear at the start of an expression
        unary_operators = one_of("+ -")

        # Basic term: can be a function call, string, number, array, range, or identifier
        # Order matters: more specific patterns first
        # parenthesized_expr must come first (highest precedence)
        # range_ref must come before cell_ref (because A1:B10 contains A1)
        # function_call must come before identifier (because FUNC is also an identifier)
        term = (
            parenthesized_expr
            | function_call
            | string_literal
            | array_literal
            | range_ref
            | number
            | cell_ref
            | identifier
        )

        # Allow zero or more unary operators before a term
        # This enables patterns like: -(expr), --(expr), +--(expr), etc.
        unary_term = ZeroOrMore(unary_operators) + term

        # Expression: one or more unary_terms, possibly separated by binary operators
        # We use ZeroOrMore to handle any number of operator-term pairs
        # This is permissive - we don't validate syntax, just extract function calls
        # Group the expression to prevent it from being flattened when used in DelimitedList
        # IMPORTANT: Don't suppress operators - we need them for reconstruction
        expression <<= Group(unary_term + ZeroOrMore(operators + unary_term))

        # Parenthesized expression: (expression)
        # This must be defined after expression is complete
        # Mark parenthesized expressions so we know to add parens back during reconstruction
        def mark_parenthesized(tokens):
            """Mark a parenthesized expression so it can be reconstructed with parens."""
            return [("__PARENTHESIZED__", tokens[0])]

        parenthesized_expr <<= (
            lparen.suppress() + expression + rparen.suppress()
        ).set_parse_action(mark_parenthesized)

        # For parsing the entire formula, we allow multiple expressions
        # This handles cases like: FUNC(x) + FUNC(y)
        self.grammar = expression

    def parse(self, formula: str) -> ParseResults:
        """
        Parse formula and return AST.

        Args:
            formula: Formula text to parse

        Returns:
            ParseResults object representing the AST

        Raises:
            ParseException: If formula cannot be parsed
        """
        # Normalize: strip leading = and whitespace
        normalized = formula.lstrip("=").strip()
        result = self.grammar.parse_string(normalized, parse_all=True)
        return result

    def extract_function_calls(
        self, ast: ParseResults, named_functions: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract function calls by walking the AST.

        Args:
            ast: ParseResults object from parsing
            named_functions: Set of named function names to look for

        Returns:
            List of function call dictionaries sorted by depth (deepest first)
        """
        calls = []

        def walk(node, depth=0):
            """Recursively walk AST to find function calls."""
            if isinstance(node, ParseResults):
                node_dict = node.asDict()
                # Check if it's a function call node
                if "function" in node_dict:
                    func_name = node_dict["function"]
                    if func_name in named_functions:
                        args = node_dict.get("args", [])
                        calls.append(
                            {"name": func_name, "args": args, "depth": depth, "node": node}
                        )
                    # Walk the args
                    if "args" in node_dict:
                        for arg in node_dict["args"]:
                            walk(arg, depth + 1)
                else:
                    # Not a function call, walk children
                    for item in node:
                        walk(item, depth)
            elif isinstance(node, dict):
                # Handle dict representation (from nested ParseResults converted to dict)
                if "function" in node:
                    func_name = node["function"]
                    if func_name in named_functions:
                        args = node.get("args", [])
                        calls.append(
                            {"name": func_name, "args": args, "depth": depth, "node": None}
                        )
                    # Walk the args
                    if "args" in node:
                        for arg in node["args"]:
                            walk(arg, depth + 1)
            elif isinstance(node, (list, tuple)):
                for item in node:
                    walk(item, depth)

        walk(ast)

        # Return calls sorted by depth (deepest first for bottom-up expansion)
        return sorted(calls, key=lambda c: c["depth"], reverse=True)

    @staticmethod
    def reconstruct_call(func_name: str, args: List) -> str:
        """
        Reconstruct the original function call text.

        Args:
            func_name: Name of the function
            args: List of arguments (can be strings, ParseResults, or lists)

        Returns:
            Reconstructed function call string
        """

        def stringify(arg):
            """Convert argument to string representation."""
            # Handle empty argument placeholder
            if arg == "__EMPTY__":
                return ""
            # Check if it's a marked parenthesized expression
            if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == "__PARENTHESIZED__":
                # It's a parenthesized expression, stringify the inner expression and wrap
                inner_expr = arg[1]
                # Convert ParseResults to list if needed
                if isinstance(inner_expr, ParseResults):
                    inner_expr = list(inner_expr)
                inner = stringify(inner_expr)
                return f"({inner})"
            # Check if it's a marked string literal
            if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == "__STRING_LITERAL__":
                # It's a quoted string literal, add quotes back
                return f'"{arg[1]}"'
            if isinstance(arg, str):
                # It's an identifier or operator, return as-is
                return arg
            if isinstance(arg, (int, float)):
                return str(arg)
            if isinstance(arg, list):
                # Handle list arguments (from grouped expressions)
                # Recursively stringify each item
                # The list may contain operators interspersed with terms
                stringified_items = [stringify(item) for item in arg]

                # Special handling for parenthesized expressions
                # If the list is ['(', content, ')'], join without spaces around parens
                result_parts = []
                i = 0
                while i < len(stringified_items):
                    if i < len(stringified_items) - 2 and stringified_items[i] == "(":
                        # Find matching )
                        depth = 1
                        j = i + 1
                        while j < len(stringified_items) and depth > 0:
                            if stringified_items[j] == "(":
                                depth += 1
                            elif stringified_items[j] == ")":
                                depth -= 1
                            j += 1
                        # Join the parenthesized section without extra spaces
                        if depth == 0:
                            # Found matching ), join i to j-1 without spaces around parens
                            inner = " ".join(stringified_items[i + 1 : j - 1])
                            result_parts.append(f"({inner})")
                            i = j
                            continue
                    result_parts.append(stringified_items[i])
                    i += 1

                # Join with spaces - operators are already in the list
                return " ".join(result_parts)
            if isinstance(arg, dict):
                # Handle dict representation from asDict()
                if "function" in arg:
                    inner_func = arg["function"]
                    inner_args = arg.get("args", [])
                    return FormulaParser.reconstruct_call(inner_func, inner_args)
                return str(arg)
            if isinstance(arg, ParseResults):
                # If it's a ParseResults, convert it back to string
                if hasattr(arg, "asDict"):
                    node_dict = arg.asDict()
                    if "function" in node_dict:
                        # It's a function call
                        inner_func = node_dict["function"]
                        inner_args = node_dict.get("args", [])
                        return FormulaParser.reconstruct_call(inner_func, inner_args)
                # Otherwise just convert to string
                return str(arg)
            return str(arg)

        # Join arguments with commas (no spaces for empty arguments)
        stringified_args = [stringify(arg) for arg in args]
        # Add spaces around commas only if arguments are non-empty
        # This handles IF(,,) correctly instead of IF(, , )
        args_str_with_spaces = ""
        for i, arg_str in enumerate(stringified_args):
            if i > 0:
                args_str_with_spaces += ", " if arg_str else ","
            args_str_with_spaces += arg_str
        return f"{func_name}({args_str_with_spaces})"
