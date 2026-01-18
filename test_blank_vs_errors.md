# DENSIFY Error Preservation - BLANK() vs Error Testing

## Implementation Strategy

To distinguish between FILTER failing vs FILTER returning data with errors, we use:

```
LET(
  result, FILTER(...),
  IF(ISNA(ROWS(result)), BLANK(), result)
)
```

### How It Works

1. **FILTER fails (no matches)**:
   - `result = #N/A` (single error value, not an array)
   - `ROWS(#N/A) = #N/A` (ROWS can't count rows of an error)
   - `ISNA(#N/A) = TRUE`
   - Returns `BLANK()`

2. **FILTER succeeds with #N/A in data**:
   - `result = array` (e.g., 3 rows × 4 cols with some #N/A cells)
   - `ROWS(array) = 3` (a number)
   - `ISNA(3) = FALSE`
   - Returns `result` (with all #N/A values preserved)

## Test Cases

### Test 1: Empty Data (FILTER Fails)
**Data**:
```
| A | B | C |
|---|---|---|
|   |   |   |
|   |   |   |
```

**Formula**: `=DENSIFY(A1:C2, "cols")`

**Expected**: `BLANK()` (all columns empty, FILTER finds nothing)

**Logic**:
- FILTER returns #N/A (no columns have content)
- ROWS(#N/A) = #N/A
- ISNA(#N/A) = TRUE
- Result: BLANK() ✓

### Test 2: Data with #N/A Errors (FILTER Succeeds)
**Data**:
```
| A | B | C | D |
|---|---|---|---|
| 1 | 2 | 3 |   |
| 4 | #N/A | 6 |   |
| 7 | 8 | 9 |   |
```

**Formula**: `=DENSIFY(A1:D3, "cols")`

**Expected**: Columns A, B, C (with #N/A preserved in B2)

**Logic**:
- FILTER returns 3-column array (A, B, C have content)
- B column contains: 2, #N/A, 8
- ROWS(3-col array) = 3
- ISNA(3) = FALSE
- Result: Array with #N/A preserved ✓

### Test 3: Column with Only #N/A (FILTER Succeeds)
**Data**:
```
| A | B | C |
|---|---|---|
| 1 | #N/A |   |
| 2 | #N/A |   |
| 3 | #N/A |   |
```

**Formula**: `=DENSIFY(A1:C3, "cols")`

**Expected**: Columns A, B (both kept, #N/A values preserved)

**Logic**:
- Column B has content (errors count as non-empty)
- COUNTA(#N/A) = 1 (errors counted)
- FILTER returns 2-column array (A and B)
- ROWS(2-col array) = 3
- ISNA(3) = FALSE
- Result: Both columns with all #N/A preserved ✓

### Test 4: Mixed Error Types
**Data**:
```
| A | B | C | D |
|---|---|---|---|
| 1 | #DIV/0! | 3 |   |
| 4 | #VALUE! | 6 |   |
| 7 | #N/A | 9 |   |
```

**Formula**: `=DENSIFY(A1:D3, "cols")`

**Expected**: Columns A, B, C (all errors preserved)

**Logic**:
- FILTER returns 3-column array
- ROWS(array) = 3
- ISNA(3) = FALSE
- Result: All error types preserved (#DIV/0!, #VALUE!, #N/A) ✓

### Test 5: Strict Mode with Incomplete Row
**Data**:
```
| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
| 4 |   | 6 |
|   |   |   |
```

**Formula**: `=DENSIFY(A1:C3, "rows-any-strict")`

**Expected**: Only row 1 (row 2 is incomplete, row 3 is empty)

**Logic**:
- Row 1: 3/3 cells have content → keep
- Row 2: 2/3 cells have content → remove (need all for -any)
- Row 3: 0/3 cells have content → remove
- FILTER returns 1-row array
- ROWS(1-row array) = 1
- ISNA(1) = FALSE
- Result: Row 1 only ✓

### Test 6: Strict Mode - All Rows Filtered
**Data**:
```
| A | B | C |
|---|---|---|
| 1 |   | 3 |
| 4 |   | 6 |
```

**Formula**: `=DENSIFY(A1:C2, "rows-any-strict")`

**Expected**: `BLANK()` (no rows are complete)

**Logic**:
- Row 1: 2/3 cells → remove
- Row 2: 2/3 cells → remove
- FILTER returns #N/A (no rows pass)
- ROWS(#N/A) = #N/A
- ISNA(#N/A) = TRUE
- Result: BLANK() ✓

## Why This Works

The key insight: **ROWS() behaves differently on errors vs arrays**

- `ROWS(error)` → propagates the error → `#N/A`
- `ROWS(array)` → returns a number → `3`, `5`, etc.

This allows us to detect FILTER failure (returns error) vs FILTER success (returns array), even when the array contains errors.

## Edge Cases Covered

✅ Empty data → BLANK()
✅ Data with #N/A → #N/A preserved
✅ Data with only errors → Errors preserved
✅ Mixed error types → All preserved
✅ Strict mode filtering all rows → BLANK()
✅ Non-strict mode with errors → Errors preserved

## Column Filtering Note

For column filtering, we apply the same logic to the transposed result:

```
LET(
  transposed, TRANSPOSE(rows_filtered),
  result, FILTER(transposed, ...),
  IF(ISNA(ROWS(result)), BLANK(), TRANSPOSE(result))
)
```

The TRANSPOSE at the end converts the filtered columns back to the original orientation.
