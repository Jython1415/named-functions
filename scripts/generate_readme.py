#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyyaml>=6.0",
#   "pyparsing>=3.0",
# ]
# ///
"""
Generate README.md from formula YAML files.

This script:
1. Reads all .yaml files in the formulas directory
2. Validates them against the formula schema
3. Generates README.md with a list of formulas
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
import yaml
from pyparsing import (
    Forward, Word, alphas, alphanums, QuotedString,
    Literal, Group, DelimitedList, Optional, ParseException,
    ParseResults, pyparsing_common, MatchFirst, Empty, ZeroOrMore
)


class ValidationError(Exception):
    """Raised when a YAML file doesn't meet the schema requirements."""
    pass


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
    result = re.sub(r'/\*.*?\*/', '', formula, flags=re.DOTALL)
    # Remove // style line comments
    result = re.sub(r'//[^\n]*', '', result)
    return result


class FormulaParser:
    """Parser for Google Sheets formulas using pyparsing."""

    def __init__(self):
        """Initialize the parser with grammar definition."""
        # Define basic tokens
        identifier = Word(alphas + "_", alphanums + "_")
        lparen = Literal("(")
        rparen = Literal(")")
        lbrace = Literal("{")
        rbrace = Literal("}")
        comma = Literal(",")
        semicolon = Literal(";")

        # String literals (handle escaped quotes)
        # Wrap in a marker to preserve information that these were quoted
        string_literal = (
            (QuotedString('"', esc_char='\\') | QuotedString("'", esc_char='\\'))
            .set_parse_action(lambda t: ('__STRING_LITERAL__', t[0]))
        )

        # Numbers
        number = pyparsing_common.number()

        # Cell reference patterns: A1, $A$1, etc.
        # Include underscore to prevent partial matching of identifiers like header_rows
        cell_ref = Word(alphas + "$", alphanums + "$" + "_")

        # Range reference: A1:B10, A:A, 1:1, etc.
        # Use Regex for flexibility with sheet references and complex patterns
        from pyparsing import Regex
        range_ref = Regex(r'[A-Za-z$]*[0-9$]*:[A-Za-z$]*[0-9$]*')

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
            identifier("function") +
            lparen.suppress() +
            Group(args_list)("args") +
            rparen.suppress()
        )

        # Parse action to fix args structure
        def fix_function_call(tokens):
            # tokens[0] is a ParseResults for the function_call
            # tokens[0]['args'] contains the args list
            call = tokens[0]
            if 'args' in call:
                args = call['args']
                # If args is [[]] or [['__EMPTY__']], convert to []
                if len(args) == 1:
                    if args[0] == [] or args[0] == '__EMPTY__':
                        call['args'] = []
            return tokens

        function_call = function_call_raw.copy().set_parse_action(fix_function_call)

        # Array literal: {1,2,3} or {1,2;3,4}
        # Arrays can contain expressions separated by commas (columns) and semicolons (rows)
        # Use regex to match content inside braces, requiring at least one non-delimiter element
        # This rejects empty arrays {} and delimiter-only arrays {,} {;} which Google Sheets rejects
        from pyparsing import Regex
        array_literal = Regex(r'\{[^}]*[^,;\s}][^}]*\}')

        # Operators (all Google Sheets operators)
        # Arithmetic: +, -, *, /, ^
        # String concatenation: &
        # Comparison: =, <>, <, >, <=, >=
        # Logical: AND, OR (used as infix operators in some formulas)
        # Note: : is NOT an operator - it's handled by range_ref pattern
        # We define these but don't strictly parse operator precedence
        # We just need them recognized so parsing doesn't stop at them
        from pyparsing import one_of, CaselessKeyword
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
        term = parenthesized_expr | function_call | string_literal | array_literal | range_ref | number | cell_ref | identifier

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
            return [('__PARENTHESIZED__', tokens[0])]

        parenthesized_expr <<= (lparen.suppress() + expression + rparen.suppress()).set_parse_action(mark_parenthesized)

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
        normalized = formula.lstrip('=').strip()
        result = self.grammar.parse_string(normalized, parse_all=True)
        return result

    def extract_function_calls(self, ast: ParseResults, named_functions: Set[str]) -> List[Dict[str, Any]]:
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
                        calls.append({"name": func_name, "args": args, "depth": depth, "node": node})
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
                        calls.append({"name": func_name, "args": args, "depth": depth, "node": None})
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
            if arg == '__EMPTY__':
                return ""
            # Check if it's a marked parenthesized expression
            elif isinstance(arg, tuple) and len(arg) == 2 and arg[0] == '__PARENTHESIZED__':
                # It's a parenthesized expression, stringify the inner expression and wrap
                inner_expr = arg[1]
                # Convert ParseResults to list if needed
                if isinstance(inner_expr, ParseResults):
                    inner_expr = list(inner_expr)
                inner = stringify(inner_expr)
                return f"({inner})"
            # Check if it's a marked string literal
            elif isinstance(arg, tuple) and len(arg) == 2 and arg[0] == '__STRING_LITERAL__':
                # It's a quoted string literal, add quotes back
                return f'"{arg[1]}"'
            elif isinstance(arg, str):
                # It's an identifier or operator, return as-is
                return arg
            elif isinstance(arg, (int, float)):
                return str(arg)
            elif isinstance(arg, list):
                # Handle list arguments (from grouped expressions)
                # Recursively stringify each item
                # The list may contain operators interspersed with terms
                stringified_items = [stringify(item) for item in arg]

                # Special handling for parenthesized expressions
                # If the list is ['(', content, ')'], join without spaces around parens
                result_parts = []
                i = 0
                while i < len(stringified_items):
                    if i < len(stringified_items) - 2 and stringified_items[i] == '(':
                        # Find matching )
                        depth = 1
                        j = i + 1
                        while j < len(stringified_items) and depth > 0:
                            if stringified_items[j] == '(':
                                depth += 1
                            elif stringified_items[j] == ')':
                                depth -= 1
                            j += 1
                        # Join the parenthesized section without extra spaces
                        if depth == 0:
                            # Found matching ), join i to j-1 without spaces around parens
                            inner = " ".join(stringified_items[i+1:j-1])
                            result_parts.append(f"({inner})")
                            i = j
                            continue
                    result_parts.append(stringified_items[i])
                    i += 1

                # Join with spaces - operators are already in the list
                return " ".join(result_parts)
            elif isinstance(arg, dict):
                # Handle dict representation from asDict()
                if 'function' in arg:
                    inner_func = arg['function']
                    inner_args = arg.get('args', [])
                    return FormulaParser.reconstruct_call(inner_func, inner_args)
                return str(arg)
            elif isinstance(arg, ParseResults):
                # If it's a ParseResults, convert it back to string
                if hasattr(arg, 'asDict'):
                    node_dict = arg.asDict()
                    if 'function' in node_dict:
                        # It's a function call
                        inner_func = node_dict['function']
                        inner_args = node_dict.get('args', [])
                        return FormulaParser.reconstruct_call(inner_func, inner_args)
                # Otherwise just convert to string
                return str(arg)
            else:
                return str(arg)

        # Join arguments with commas (no spaces for empty arguments)
        stringified_args = [stringify(arg) for arg in args]
        args_str = ",".join(stringified_args)
        # Add spaces around commas only if arguments are non-empty
        # This handles IF(,,) correctly instead of IF(, , )
        args_str_with_spaces = ""
        for i, arg_str in enumerate(stringified_args):
            if i > 0:
                args_str_with_spaces += ", " if arg_str else ","
            args_str_with_spaces += arg_str
        return f"{func_name}({args_str_with_spaces})"


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


def build_dependency_graph(formulas: List[Dict[str, Any]], parser: FormulaParser) -> Dict[str, List[str]]:
    """
    Build dependency graph by parsing formulas and finding function calls.

    Args:
        formulas: List of formula dictionaries
        parser: FormulaParser instance

    Returns:
        Dict mapping formula names to list of dependencies (formulas they call)
    """
    graph = {}
    named_functions = {f['name'] for f in formulas}

    for formula in formulas:
        name = formula['name']
        formula_text = formula['formula']

        try:
            ast = parser.parse(formula_text)
            calls = parser.extract_function_calls(ast, named_functions)
            # Get unique dependencies
            dependencies = list({c['name'] for c in calls})
        except ParseException as e:
            # Formula doesn't parse or has no function calls
            print(f"  Note: {name} formula doesn't call other named functions")
            dependencies = []

        graph[name] = dependencies

    return graph


def detect_cycles(graph: Dict[str, List[str]]) -> List[str]:
    """
    Detect circular dependencies using DFS with color marking.

    Args:
        graph: Dependency graph

    Returns:
        List of cycle descriptions (empty if no cycles)
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    cycles = []

    def dfs(node: str, path: List[str]):
        """DFS helper function."""
        color[node] = GRAY
        path.append(node)

        for neighbor in graph.get(node, []):
            if color[neighbor] == GRAY:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(' → '.join(cycle))
            elif color[neighbor] == WHITE:
                dfs(neighbor, path[:])

        color[node] = BLACK

    for node in graph:
        if color[node] == WHITE:
            dfs(node, [])

    return cycles


def substitute_arguments(
    formula_text: str,
    parameters: List[Dict[str, Any]],
    arguments: List[Any]
) -> str:
    """
    Substitute parameters with argument values.

    Args:
        formula_text: The formula definition
        parameters: List of parameter dicts with 'name' field
        arguments: List of argument expressions

    Returns:
        Formula with parameters replaced by arguments
    """
    if len(parameters) != len(arguments):
        raise ValueError(
            f"Parameter count mismatch: expected {len(parameters)}, "
            f"got {len(arguments)}"
        )

    result = formula_text

    # Substitute each parameter
    for param, arg in zip(parameters, arguments):
        param_name = param['name']

        # Convert argument to string
        # Handle empty argument placeholder
        if arg == '__EMPTY__':
            arg_str = ""
        elif isinstance(arg, tuple) and len(arg) == 2 and arg[0] == '__STRING_LITERAL__':
            # It's a marked string literal, add quotes back
            arg_str = f'"{arg[1]}"'
        elif isinstance(arg, str):
            # It's an identifier or unquoted value, return as-is
            arg_str = arg
        elif isinstance(arg, (int, float)):
            arg_str = str(arg)
        elif isinstance(arg, list):
            # Handle list arguments (from grouped expressions)
            # Use the same stringify logic as reconstruct_call
            def stringify_item(item):
                if item == '__EMPTY__':
                    return ""
                elif isinstance(item, tuple) and len(item) == 2 and item[0] == '__PARENTHESIZED__':
                    # Parenthesized expression - stringify inner and wrap
                    inner_expr = item[1]
                    # Convert ParseResults to list if needed
                    if isinstance(inner_expr, ParseResults):
                        inner_expr = list(inner_expr)
                    inner = stringify_item(inner_expr)
                    return f"({inner})"
                elif isinstance(item, tuple) and len(item) == 2 and item[0] == '__STRING_LITERAL__':
                    return f'"{item[1]}"'
                elif isinstance(item, dict) and 'function' in item:
                    return FormulaParser.reconstruct_call(item['function'], item.get('args', []))
                elif isinstance(item, ParseResults):
                    if hasattr(item, 'asDict'):
                        d = item.asDict()
                        if 'function' in d:
                            return FormulaParser.reconstruct_call(d['function'], d.get('args', []))
                    return str(item)
                else:
                    return str(item)
            # Join with spaces - operators are now preserved in the list
            arg_str = " ".join(stringify_item(item) for item in arg)
        elif isinstance(arg, ParseResults):
            # Reconstruct from parse results
            if hasattr(arg, 'asDict'):
                node_dict = arg.asDict()
                if 'function' in node_dict:
                    arg_str = FormulaParser.reconstruct_call(
                        node_dict['function'],
                        node_dict.get('args', [])
                    )
                else:
                    arg_str = str(arg)
            else:
                arg_str = str(arg)
        else:
            arg_str = str(arg)

        # Use word boundaries to avoid partial replacements
        # Won't replace 'range' in 'input_range'
        pattern = r'\b' + re.escape(param_name) + r'\b'
        result = re.sub(pattern, arg_str, result)

    return result



def expand_argument(
    arg: Any,
    all_formulas: Dict[str, Dict[str, Any]],
    parser: FormulaParser,
    expanded_cache: Dict[str, str]
) -> str:
    if isinstance(arg, str):
        return arg
    if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == "__PARENTHESIZED__":
        # Parenthesized expression - expand the inner part and wrap
        inner_expr = arg[1]
        # Convert ParseResults to list if needed
        if isinstance(inner_expr, ParseResults):
            inner_expr = list(inner_expr)
        inner = expand_argument(inner_expr, all_formulas, parser, expanded_cache)
        return f"({inner})"
    if isinstance(arg, tuple) and len(arg) == 2 and arg[0] == "__STRING_LITERAL__":
        return f"{chr(34)}{arg[1]}{chr(34)}"
    if isinstance(arg, (int, float)):
        return str(arg)
    # Handle list arguments (from grouped expressions)
    if isinstance(arg, list):
        # Recursively expand each item in the list
        expanded_items = [expand_argument(item, all_formulas, parser, expanded_cache) for item in arg]
        return " ".join(expanded_items)
    # Handle dict representation (from nested ParseResults converted to dict)
    if isinstance(arg, dict) and "function" in arg:
        func_name = arg["function"]
        inner_args = arg.get("args", [])
        if func_name in all_formulas:
            func_def = all_formulas[func_name]
            func_expanded = expand_formula(func_def, all_formulas, parser, expanded_cache)
            func_expanded_stripped = func_expanded.lstrip("=").strip()
            # Recursively expand inner args
            expanded_inner_args = [expand_argument(a, all_formulas, parser, expanded_cache) for a in inner_args]
            substituted = substitute_arguments(
                func_expanded_stripped,
                func_def["parameters"],
                expanded_inner_args
            )
            return f"({substituted})"
        else:
            return FormulaParser.reconstruct_call(func_name, inner_args)
    if isinstance(arg, ParseResults) and hasattr(arg, "asDict"):
        node_dict = arg.asDict()
        if "function" in node_dict:
            func_name = node_dict["function"]
            inner_args = node_dict.get("args", [])
            if func_name in all_formulas:
                func_def = all_formulas[func_name]
                func_expanded = expand_formula(func_def, all_formulas, parser, expanded_cache)
                func_expanded_stripped = func_expanded.lstrip("=").strip()
                substituted = substitute_arguments(
                    func_expanded_stripped,
                    func_def["parameters"],
                    inner_args
                )
                return f"({substituted})"
            else:
                return FormulaParser.reconstruct_call(func_name, inner_args)
    return str(arg)


def expand_formula(
    formula_data: Dict[str, Any],
    all_formulas: Dict[str, Dict[str, Any]],
    parser: FormulaParser,
    expanded_cache: Dict[str, str]
) -> str:
    """
    Recursively expand formula by substituting function calls.

    Args:
        formula_data: Formula to expand
        all_formulas: Dict of all formulas by name
        parser: FormulaParser instance
        expanded_cache: Cache of already-expanded formulas

    Returns:
        Fully expanded formula text
    """
    name = formula_data['name']

    # Check cache
    if name in expanded_cache:
        return expanded_cache[name]

    # Strip comments from formula before processing
    formula_text = strip_comments(formula_data['formula']).strip()
    original_formula_text = formula_text  # Save for validation
    named_functions = set(all_formulas.keys())

    try:
        ast = parser.parse(formula_text)
        calls = parser.extract_function_calls(ast, named_functions)
    except ParseException:
        # No function calls or doesn't parse
        expanded_cache[name] = formula_text
        return formula_text

    # No calls to our functions
    if not calls:
        expanded_cache[name] = formula_text
        return formula_text

    # Process all function calls, including those nested within LET statements
    # Note: We process all depths because calls within LET assignments are not
    # nested arguments but independent calls that need expansion
    top_level_calls = calls

    # Expand each function call
    result = formula_text
    for call in top_level_calls:
        func_name = call['name']
        args = call['args']

        # Get function definition
        func_def = all_formulas[func_name]

        # First, expand all arguments that are function calls
        expanded_args = []
        for arg in args:
            expanded_arg = expand_argument(arg, all_formulas, parser, expanded_cache)
            expanded_args.append(expanded_arg)

        # Recursively expand the called function first
        func_expanded = expand_formula(func_def, all_formulas, parser, expanded_cache)

        # Strip leading = from the expanded formula (it will be inlined)
        func_expanded_stripped = func_expanded.lstrip('=').strip()

        # Map arguments to parameters
        substituted = substitute_arguments(
            func_expanded_stripped,
            func_def['parameters'],
            expanded_args
        )

        # Replace function call in result
        call_text = FormulaParser.reconstruct_call(func_name, args)
        # Wrap in parentheses to preserve structure
        result = result.replace(call_text, f"({substituted})")

    # If the original formula had = prefix, preserve it
    # Remove extra parentheses if the entire formula is just one substitution
    if result.startswith('(') and result.endswith(')') and result.count('(') == result.count(')'):
        # Check if it's just wrapped - try to unwrap
        inner = result[1:-1]
        # Simple heuristic: if no calls were made or if this was a complete replacement
        if formula_text == call_text:
            result = inner

    # Ensure = prefix for expanded formulas that need it
    # If the result starts with a formula function (LET, LAMBDA, etc.) and doesn't have =, add it
    if not result.startswith('='):
        # Check if it starts with a common formula function
        formula_starters = ['LET(', 'LAMBDA(', 'BYROW(', 'BYCOL(', 'MAKEARRAY(', 'FILTER(', 'DENSIFY(']
        if any(result.startswith(starter) for starter in formula_starters):
            result = '=' + result

    # Validation: If we had dependencies but the result equals the original formula,
    # the parser failed to expand the function calls
    if calls and result.lstrip('=').strip() == original_formula_text.lstrip('=').strip():
        func_names = ', '.join(sorted({c['name'] for c in calls}))
        raise ValidationError(
            f"{name}: Formula expansion failed - calls to {func_names} were not expanded.\n"
            f"  This indicates a parser bug. The formula may contain:\n"
            f"  - Zero-argument function calls (e.g., BLANK())\n"
            f"  - Complex nested structures\n"
            f"  - Unsupported syntax that the parser cannot handle\n"
            f"  Original formula: {original_formula_text[:100]}{'...' if len(original_formula_text) > 100 else ''}"
        )

    expanded_cache[name] = result
    return result


def load_and_validate_formulas(root_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all .yaml files from formulas directory and validate them.

    Args:
        root_dir: Path to the repository root

    Returns:
        List of validated formula data dictionaries with 'filename' added

    Raises:
        ValidationError: If any file fails validation
    """
    formulas = []
    formulas_dir = root_dir / 'formulas'
    yaml_files = sorted(formulas_dir.glob('*.yaml'))

    if not yaml_files:
        print("Warning: No .yaml files found in formulas directory")
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

    # Check for circular dependencies
    if formulas:
        print("\nChecking for circular dependencies...")
        parser = FormulaParser()
        graph = build_dependency_graph(formulas, parser)
        cycles = detect_cycles(graph)

        if cycles:
            cycle_desc = "\n".join(f"  - {cycle}" for cycle in cycles)
            raise ValidationError(
                f"Circular dependencies detected:\n{cycle_desc}"
            )

        print("✓ No circular dependencies found")

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

    # Expand formulas (replace function calls with definitions)
    print("\nExpanding formula compositions...")
    parser = FormulaParser()
    all_formulas = {f['name']: f for f in formulas}
    expanded_cache = {}
    expansion_failures = []

    for formula in sorted_formulas:
        try:
            expanded = expand_formula(formula, all_formulas, parser, expanded_cache)
            print(f"  ✓ Expanded {formula['name']}")
        except Exception as e:
            error_msg = f"{formula['name']}: {e}"
            expansion_failures.append(error_msg)
            print(f"  ✗ Failed to expand {formula['name']}: {e}", file=sys.stderr)
            # Use original formula if expansion fails (with comments stripped)
            expanded_cache[formula['name']] = strip_comments(formula['formula']).strip()

    # If any formulas failed to expand, raise an error to block the build
    if expansion_failures:
        failure_details = "\n  - ".join(expansion_failures)
        raise ValidationError(
            f"❌ Formula expansion failures detected ({len(expansion_failures)} formula(s)):\n"
            f"  - {failure_details}\n\n"
            f"These formulas must be fixed before the README can be generated.\n"
            f"Run the tests to help diagnose the issue: pytest tests/test_formula_parser.py -v"
        )

    # Generate summary list
    lines = ["### Quick Reference\n"]
    for formula in sorted_formulas:
        name = formula['name']
        filename = formula['filename']
        description = formula['description'].strip()
        description_clean = ' '.join(description.split())
        # Create anchor link to detailed section (GitHub auto-generates anchors from headers)
        anchor = name.lower().replace(' ', '-')
        lines.append(f"- **[{name}](#{anchor})** - {description_clean}")

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
        # Use expanded formula
        formula_text = expanded_cache.get(name, formula['formula'].strip())
        notes = formula.get('notes', '')

        # Create expandable section
        lines.append(f"<details>")
        lines.append(f"<summary><strong>{name}</strong></summary>\n")

        # 1. Function name
        lines.append(f"### {name}\n")

        # 2. Description with version
        lines.append(f"**Description**\n")
        lines.append(f"```")
        lines.append(f"v{version} {description_clean}")
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
            for param in parameters:
                param_name = param['name']
                param_desc = param['description'].strip()
                param_desc_clean = ' '.join(param_desc.split())
                param_example = param.get('example', '')

                # Use heading level 4 for parameter names for stronger visual hierarchy
                lines.append(f"#### {param_name}\n")
                lines.append(f"**Description:**\n")
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
    root_dir = Path(__file__).parent.parent
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
