#!/usr/bin/env python3
"""
Integration tests for generate_readme.py.

Tests the complete README generation workflow without testing
internal implementation details.
"""

import sys
from pathlib import Path
import tempfile
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import pytest


class TestReadmeGeneration:
    """Integration tests for README generation."""

    def test_generate_readme_runs_without_error(self):
        """Test that generate_readme.py can be imported and run."""
        import generate_readme

        # Should be able to load formulas
        root_dir = Path(__file__).parent.parent
        try:
            formulas = generate_readme.load_and_validate_formulas(root_dir)
            assert isinstance(formulas, list)
            assert len(formulas) > 0
        except generate_readme.ValidationError as e:
            pytest.fail(f"Formula validation failed: {e}")

    def test_formula_parser_can_be_created(self):
        """Test that FormulaParser can be instantiated."""
        from generate_readme import FormulaParser

        parser = FormulaParser()
        assert parser is not None

    def test_strip_comments_removes_comments(self):
        """Test that strip_comments removes /* */ and // comments."""
        from generate_readme import strip_comments

        formula_with_comments = """LET(
            /* Block comment */
            x, 5,  // Line comment
            x + 1
        )"""

        result = strip_comments(formula_with_comments)

        assert '/*' not in result
        assert '*/' not in result
        assert '//' not in result
        assert 'LET(' in result
        assert 'x, 5' in result

    def test_dependency_graph_construction(self):
        """Test building dependency graph from formulas."""
        from generate_readme import build_dependency_graph, FormulaParser

        formulas = [
            {'name': 'A', 'formula': 'B(x)'},
            {'name': 'B', 'formula': 'x + 1'},
            {'name': 'C', 'formula': 'A(y)'}
        ]

        parser = FormulaParser()
        graph = build_dependency_graph(formulas, parser)

        assert 'A' in graph
        assert 'B' in graph
        assert 'C' in graph

    def test_cycle_detection_finds_cycles(self):
        """Test that cycle detection works."""
        from generate_readme import detect_cycles

        # Graph with cycle: A -> B -> A
        graph_with_cycle = {
            'A': ['B'],
            'B': ['A']
        }

        cycles = detect_cycles(graph_with_cycle)
        assert len(cycles) > 0

        # Graph without cycle
        graph_without_cycle = {
            'A': ['B'],
            'B': ['C'],
            'C': []
        }

        cycles = detect_cycles(graph_without_cycle)
        assert len(cycles) == 0


class TestFormulaValidation:
    """Test formula YAML validation."""

    def test_valid_formula_passes_validation(self):
        """Test that a valid formula passes validation."""
        from generate_readme import validate_formula_yaml

        valid_data = {
            'name': 'TEST',
            'version': '1.0.0',
            'description': 'A test formula',
            'parameters': [
                {'name': 'x', 'description': 'Input value'}
            ],
            'formula': 'x + 1'
        }

        # Should not raise
        try:
            validate_formula_yaml(valid_data, 'test.yaml')
        except Exception as e:
            pytest.fail(f"Valid formula failed validation: {e}")

    def test_missing_name_fails_validation(self):
        """Test that missing name field fails validation."""
        from generate_readme import validate_formula_yaml, ValidationError

        invalid_data = {
            'version': '1.0.0',
            'description': 'Missing name',
            'parameters': [],
            'formula': 'x'
        }

        with pytest.raises(ValidationError, match="name"):
            validate_formula_yaml(invalid_data, 'test.yaml')

    def test_missing_formula_fails_validation(self):
        """Test that missing formula field fails validation."""
        from generate_readme import validate_formula_yaml, ValidationError

        invalid_data = {
            'name': 'TEST',
            'version': '1.0.0',
            'description': 'Missing formula',
            'parameters': []
        }

        with pytest.raises(ValidationError, match="formula"):
            validate_formula_yaml(invalid_data, 'test.yaml')

    def test_empty_description_fails_validation(self):
        """Test that empty description fails validation."""
        from generate_readme import validate_formula_yaml, ValidationError

        invalid_data = {
            'name': 'TEST',
            'version': '1.0.0',
            'description': '',  # Empty
            'parameters': [],
            'formula': 'x'
        }

        with pytest.raises(ValidationError, match="description"):
            validate_formula_yaml(invalid_data, 'test.yaml')


class TestExistingFormulas:
    """Test that existing formulas in the repository are valid."""

    def test_all_existing_formulas_are_valid(self):
        """Test that all existing formula files pass validation."""
        import generate_readme

        root_dir = Path(__file__).parent.parent
        formulas_dir = root_dir / 'formulas'

        if not formulas_dir.exists():
            pytest.skip("Formulas directory not found")

        yaml_files = list(formulas_dir.glob('*.yaml'))
        assert len(yaml_files) > 0, "No YAML files found"

        # Load and validate all formulas
        try:
            formulas = generate_readme.load_and_validate_formulas(root_dir)
            assert len(formulas) == len(yaml_files)
        except generate_readme.ValidationError as e:
            pytest.fail(f"Formula validation failed: {e}")

    def test_no_circular_dependencies_in_formulas(self):
        """Test that formulas don't have circular dependencies."""
        import generate_readme

        root_dir = Path(__file__).parent.parent

        try:
            formulas = generate_readme.load_and_validate_formulas(root_dir)

            # load_and_validate_formulas includes cycle detection
            # If we get here, there are no cycles
            assert len(formulas) > 0
        except generate_readme.ValidationError as e:
            if "Circular" in str(e):
                pytest.fail(f"Circular dependencies found: {e}")
            raise


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
