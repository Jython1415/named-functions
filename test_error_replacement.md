# Error Replacement Investigation

## Issue Description
User reports that in `=DENSIFY(B2:K2000, "cols")`:
- Columns with #N/A errors ARE being kept (column not removed)
- BUT #N/A values within those columns are replaced with "" (empty string)
- This happens in non-strict mode

## Test Case - Minimal Reproducible Example

### Test Data
```
| A | B | C | D |
|---|---|---|---|
| 1 | 2 | 3 |   |
| 4 | #N/A | 6 |   |
| 7 | 8 | 9 |   |
```

### Expected Behavior
`=DENSIFY(A1:D3, "cols")`

Should return:
```
| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
| 4 | #N/A | 6 |
| 7 | 8 | 9 |
```

Column D removed (empty), columns A-C kept, #N/A preserved in B2.

### Actual Behavior (User Report)
#N/A is replaced with "" (empty string).

## Hypothesis - IFNA Wrapper Issue?

Looking at line 56 of densify.yaml:
```
IFNA(FILTER(transposed, BYROW(transposed, LAMBDA(c, COUNTA(c) >= threshold))), BLANK())
```

The IFNA wrapper is meant to catch FILTER failures (when no columns pass the threshold).

**Question**: Could IFNA be catching #N/A values WITHIN the filtered array, not just the FILTER error itself?

Let me test this theory...

## Potential Root Causes

1. **IFNA catching internal #N/A values?**
   - IFNA should only catch the top-level #N/A from FILTER failing
   - BUT maybe Google Sheets behavior is different?

2. **TRANSPOSE issue with errors?**
   - Does TRANSPOSE somehow convert errors to ""?
   - Unlikely, but worth checking

3. **FILTER issue with errors?**
   - Does FILTER replace errors with ""?
   - Unlikely - FILTER should preserve values

4. **BYROW + LAMBDA issue?**
   - Could BYROW be doing something with errors?
   - COUNTA should count errors correctly

## Next Steps

1. Create a simple Google Sheet test
2. Test: `=FILTER(A1:C3, BYROW(A1:C3, LAMBDA(c, COUNTA(c) >= 1)))`
3. Test: `=TRANSPOSE(A1:C3)` with errors
4. Test: `=IFNA(A1:C3, "REPLACED")` with errors
5. Identify which operation is replacing errors
