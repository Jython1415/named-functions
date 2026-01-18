# DENSIFY Error Handling Test Cases

## Test Setup

Create a Google Sheet with this data:

| A | B | C | D |
|---|---|---|---|
| 1 | 2 | 3 | 4 |
| 5 | #DIV/0! | 7 | 8 |
| | | | |
| 9 | 10 | | 12 |
| | #N/A | | |

## Current Behavior Issues

### Test 1: Non-strict mode (rows)
**Formula**: `=DENSIFY(A1:D5, "rows")`
**Expected**: Keep rows 1, 2, 4; remove rows 3, 5 (empty). Preserve #DIV/0! error in B2.
**Actual (predicted)**: Likely works correctly - COUNTA counts errors as non-empty.

### Test 2: Strict mode (rows-any-strict)
**Formula**: `=DENSIFY(A1:D5, "rows-any-strict")`
**Expected**: Keep only row 1 (complete); keep row 2 with error preserved.
**Actual (predicted)**: **Returns BLANK()** - the #DIV/0! error causes SUMPRODUCT to fail, causing entire result to be erased.

### Test 3: Error-only row (rows)
**Formula**: `=DENSIFY(A1:D5, "rows")`
**Expected**: Keep row 5 (has #N/A error, which counts as non-empty).
**Actual (predicted)**: Works correctly with COUNTA.

## Root Cause

The issue is in strict mode's `LEN(TRIM(r))` logic:
- `LEN(TRIM(#ERROR))` propagates the error
- This causes `SUMPRODUCT` to fail
- Which causes `FILTER` to return #N/A
- Which gets replaced by `BLANK()` via `IFNA`

## Proposed Solution

Wrap error-prone operations with IFERROR to treat errors as non-empty:

```
SUMPRODUCT((IFERROR(LEN(TRIM(r)) > 0, TRUE)) * 1)
```

This ensures:
1. Errors are counted as non-empty (TRUE → 1 in SUMPRODUCT)
2. Rows with errors are preserved
3. Error values in cells remain unchanged (FILTER preserves original values)
