# Formula Expansion Fix Summary

## Problem
8 formulas in the README contained unexpanded named function calls instead of being fully expanded to native Google Sheets formulas. This made them unusable in actual Google Sheets since users would need to manually define all the dependent named functions.

### Affected Formulas
- DATAROWS (called DROPROWS)
- DROP (called DROPROWS, DROPCOLS)
- DROPCOLS (called DROPROWS)
- HEADERS (called TAKEROWS)
- OMITCOLS (called OMITROWS)
- TAKE (called TAKEROWS, TAKECOLS)
- TAKECOLS (called TAKEROWS)
- UNPIVOT (called BLANKTOEMPTY)

## Root Cause

**Issue 1: Parser Failure on Complex Formulas**
The pyparsing-based parser failed to parse complex multi-line LET statements. When parsing failed, it fell back to regex detection which only found function names but didn't extract arguments, causing expansion to fail with "Parameter count mismatch" errors.

**Issue 2: Depth Filtering**
When pyparsing succeeded, it correctly identified function calls nested within LET statements but assigned them `depth > 0`. The expansion logic only processed `depth == 0` calls, skipping LET-nested calls entirely.

## Solution

### Fix 1: Enhanced Regex Argument Extraction
Added robust argument extraction to the regex fallback using balanced parenthesis matching:
- `_extract_args_from_formula()`: Finds matching closing parenthesis while tracking string literals
- `_split_arguments()`: Splits arguments on commas, respecting nested parentheses and quotes
- Now extracts actual arguments instead of returning empty list

### Fix 2: Process All Depths
Changed expansion logic to process calls at all depths, not just depth=0:
- Calls within LET value assignments are independent calls, not nested arguments
- They need direct expansion via string replacement
- Processing all depths handles both top-level and LET-nested calls correctly

## Testing
- All 33 formulas now expand successfully (verified by generation script output)
- README contains only native Google Sheets functions
- Formulas like DROP, HEADERS, TAKE now show full inline expansions (100+ lines)

## Files Modified
- `scripts/generate_readme.py`: Added argument extraction functions, removed depth filter
- `README.md`: Regenerated with all formulas fully expanded

## Impact
Users can now copy formulas directly from the README into Google Sheets without needing to define any dependencies. All formulas are self-contained and use only native Google Sheets functions.
