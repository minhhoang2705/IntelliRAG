# CSV Bomb DoS Security Fix

## Overview
Fixed a critical security vulnerability in `app/services/preprocessing/csv_handler.py` that allowed CSV-bomb DoS attacks by loading entire CSV files into memory without limits.

## Changes Made

### 1. Added Security Limits (Lines 27-30)
```python
# Security limits to prevent CSV-bomb DoS attacks
MAX_ROWS = 100000  # Maximum number of data rows
MAX_COLUMNS = 1000  # Maximum number of columns
VALID_DELIMITERS = {',', ';', '\t', '|'}  # Valid CSV delimiters
```

### 2. Created CSVBombError Exception (Lines 14-16)
```python
class CSVBombError(Exception):
    """Exception raised when CSV file exceeds security limits."""
    pass
```

### 3. Updated `_detect_delimiter()` Method (Lines 57-91)
- Added delimiter validation against `VALID_DELIMITERS`
- Defaults to comma if invalid delimiter detected
- Consistent csv.Error handling

### 4. Updated `extract_text()` Method (Lines 93-185)
**Before:** Used `rows = list(reader)` - loads entire file into memory
**After:** 
- Validates column count BEFORE reading data
- Streams rows one at a time
- Stops and raises `CSVBombError` when `MAX_ROWS` exceeded
- Re-raises `CSVBombError` (doesn't swallow security exceptions)

### 5. Updated `_parse_csv_data()` Method (Lines 229-327)
**Before:** 
- Used `rows = list(reader)` 
- Checked limits AFTER loading all data
- Raised generic `ValueError`

**After:**
- Validates column count BEFORE reading any rows
- Streams rows in a loop with counter
- Raises `CSVBombError` immediately when limit exceeded
- Uses class constants instead of local variables

### 6. Updated `_parse_csv_with_text()` Method (Lines 329-431)
**Before:** Used `rows = list(reader)` - loads entire file
**After:**
- Validates column count first
- Streams rows and builds text representation incrementally
- Stops at `MAX_ROWS` limit
- Memory-efficient processing

### 7. Exported CSVBombError
Updated `app/services/preprocessing/__init__.py` to export `CSVBombError` for use in other modules.

## Security Improvements

### Protection Against CSV-Bomb DoS
1. **Column Limit**: Validates `fieldnames` count before reading any data
2. **Row Limit**: Streams rows with counter, stops at limit
3. **Streaming**: Never loads entire file into memory with `list()`
4. **Delimiter Validation**: Only allows safe, common delimiters
5. **Early Failure**: Raises exception immediately when limit exceeded

### Attack Scenarios Prevented
- ✅ Files with millions of rows
- ✅ Files with thousands of columns
- ✅ Files with unusual/malicious delimiters
- ✅ Memory exhaustion attacks

## Test Coverage

### New Tests Added (6 tests)
1. `test_csv_handler_rejects_too_many_rows` - Validates MAX_ROWS enforcement
2. `test_csv_handler_rejects_too_many_columns` - Validates MAX_COLUMNS enforcement
3. `test_csv_handler_validates_delimiter` - Tests valid delimiter handling
4. `test_csv_handler_handles_invalid_delimiter` - Tests fallback behavior
5. `test_csv_handler_streams_large_file` - Verifies streaming works correctly
6. `test_csv_handler_handles_csv_error` - Tests csv.Error handling

### Test Results
- **Total Tests**: 18 (12 existing + 6 new)
- **Status**: All PASSED ✅
- **No regressions**: All existing tests still pass

## Configuration

The limits can be adjusted by modifying the class constants:
```python
CSVHandler.MAX_ROWS = 50000      # Adjust as needed
CSVHandler.MAX_COLUMNS = 500     # Adjust as needed
```

## Usage Example

```python
from app.services.preprocessing import CSVHandler, CSVBombError

handler = CSVHandler()

try:
    result = handler.process(csv_file_path)
    # Process result...
except CSVBombError as e:
    # Handle CSV bomb attack
    logger.error(f"CSV file exceeds security limits: {e}")
```

## TDD Workflow Followed

1. ✅ **RED**: Wrote failing tests first
2. ✅ **GREEN**: Implemented minimal fix to pass tests
3. ✅ **REFACTOR**: Cleaned up code while keeping tests green

## Related Files
- `app/services/preprocessing/csv_handler.py` - Main implementation
- `tests/unit/test_preprocessing_csv.py` - Test suite
- `app/services/preprocessing/__init__.py` - Export CSVBombError

## Performance Impact
- **Positive**: Reduced memory footprint for large files
- **Neutral**: No performance degradation for normal-sized files
- **Security**: Prevents DoS attacks

## Compliance
- Follows project TDD methodology
- Maintains backward compatibility for valid CSV files
- No linting errors
- Proper error handling and logging

