#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyyaml>=6.0",
#   "pyparsing>=3.0",
# ]
# ///
"""
Test zero-argument function parsing and expansion.

This test verifies that:
1. Zero-argument function calls (like BLANK()) are parsed correctly
2. Formulas with nested zero-argument calls expand properly
3. VSTACKBLANK and HSTACKBLANK expand to their full definitions
"""

import sys
from pathlib import Path

# Add parent directory to path to import generate_readme
sys.path.insert(0, str(Path(__file__).parent))

from generate_readme import FormulaParser, expand_formula, ValidationError
import yaml


def test_zero_arg_parsing():
    """Test that zero-argument functions are parsed correctly."""
    print("Test 1: Parsing zero-argument function calls...")

    parser = FormulaParser()

    # Test BLANK() can be parsed
    try:
        ast = parser.parse("BLANK()")
        print("  ✓ BLANK() parsed successfully")
    except Exception as e:
        print(f"  ✗ BLANK() parsing failed: {e}")
        return False

    # Test nested zero-arg calls
    try:
        ast = parser.parse("VSTACKFILL(array1, array2, BLANK())")
        print("  ✓ VSTACKFILL(array1, array2, BLANK()) parsed successfully")
    except Exception as e:
        print(f"  ✗ Nested zero-arg call parsing failed: {e}")
        return False

    return True


def test_vstackblank_expansion():
    """Test that VSTACKBLANK expands properly."""
    print("\nTest 2: VSTACKBLANK expansion...")

    root_dir = Path(__file__).parent.parent

    # Load BLANK formula
    blank_path = root_dir / 'formulas' / 'blank.yaml'
    with open(blank_path) as f:
        blank_data = yaml.safe_load(f)

    # Load VSTACKFILL formula
    vstackfill_path = root_dir / 'formulas' / 'vstackfill.yaml'
    with open(vstackfill_path) as f:
        vstackfill_data = yaml.safe_load(f)

    # Load VSTACKBLANK formula
    vstackblank_path = root_dir / 'formulas' / 'vstackblank.yaml'
    with open(vstackblank_path) as f:
        vstackblank_data = yaml.safe_load(f)

    # Create formula dict
    all_formulas = {
        'BLANK': blank_data,
        'VSTACKFILL': vstackfill_data,
        'VSTACKBLANK': vstackblank_data
    }

    parser = FormulaParser()
    expanded_cache = {}

    try:
        # Expand VSTACKBLANK
        expanded = expand_formula(vstackblank_data, all_formulas, parser, expanded_cache)

        # Verify it was actually expanded (not just the original formula)
        original = vstackblank_data['formula'].strip()
        if expanded.strip() == original:
            print(f"  ✗ VSTACKBLANK was not expanded")
            return False

        # Verify BLANK() was expanded to IF(,,)
        if 'IF(,,)' not in expanded:
            print(f"  ✗ BLANK() was not expanded to IF(,,)")
            print(f"     Expanded formula: {expanded[:100]}...")
            return False

        # Verify VSTACKFILL was expanded (should contain VSTACK)
        if 'VSTACK' not in expanded:
            print(f"  ✗ VSTACKFILL was not expanded (missing VSTACK)")
            print(f"     Expanded formula: {expanded[:100]}...")
            return False

        print("  ✓ VSTACKBLANK expanded successfully")
        print(f"     Contains IF(,,): ✓")
        print(f"     Contains VSTACK: ✓")

    except ValidationError as e:
        print(f"  ✗ VSTACKBLANK expansion failed with validation error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ VSTACKBLANK expansion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_hstackblank_expansion():
    """Test that HSTACKBLANK expands properly."""
    print("\nTest 3: HSTACKBLANK expansion...")

    root_dir = Path(__file__).parent.parent

    # Load BLANK formula
    blank_path = root_dir / 'formulas' / 'blank.yaml'
    with open(blank_path) as f:
        blank_data = yaml.safe_load(f)

    # Load HSTACKFILL formula
    hstackfill_path = root_dir / 'formulas' / 'hstackfill.yaml'
    with open(hstackfill_path) as f:
        hstackfill_data = yaml.safe_load(f)

    # Load HSTACKBLANK formula
    hstackblank_path = root_dir / 'formulas' / 'hstackblank.yaml'
    with open(hstackblank_path) as f:
        hstackblank_data = yaml.safe_load(f)

    # Create formula dict
    all_formulas = {
        'BLANK': blank_data,
        'HSTACKFILL': hstackfill_data,
        'HSTACKBLANK': hstackblank_data
    }

    parser = FormulaParser()
    expanded_cache = {}

    try:
        # Expand HSTACKBLANK
        expanded = expand_formula(hstackblank_data, all_formulas, parser, expanded_cache)

        # Verify it was actually expanded
        original = hstackblank_data['formula'].strip()
        if expanded.strip() == original:
            print(f"  ✗ HSTACKBLANK was not expanded")
            return False

        # Verify BLANK() was expanded to IF(,,)
        if 'IF(,,)' not in expanded:
            print(f"  ✗ BLANK() was not expanded to IF(,,)")
            return False

        # Verify HSTACKFILL was expanded (should contain HSTACK)
        if 'HSTACK' not in expanded:
            print(f"  ✗ HSTACKFILL was not expanded (missing HSTACK)")
            return False

        print("  ✓ HSTACKBLANK expanded successfully")
        print(f"     Contains IF(,,): ✓")
        print(f"     Contains HSTACK: ✓")

    except ValidationError as e:
        print(f"  ✗ HSTACKBLANK expansion failed with validation error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ HSTACKBLANK expansion failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Zero-Argument Function Parsing and Expansion")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Zero-arg parsing", test_zero_arg_parsing()))
    results.append(("VSTACKBLANK expansion", test_vstackblank_expansion()))
    results.append(("HSTACKBLANK expansion", test_hstackblank_expansion()))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    # Exit with appropriate code
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
