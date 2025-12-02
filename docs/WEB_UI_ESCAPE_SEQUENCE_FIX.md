# Web UI Escape Sequence Fix

## Problem
The web UI dropdown was displaying literal escape sequences (e.g., `\032`, `\064`) instead of properly decoded characters. This made service names difficult to read.

### Example of Issue
**Before:**
```
ACO G\032\064EM38ww\032with\032SAS2 (239.251.200.193)
```

**After:**
```
ACO G @EM38ww with SAS2 (239.251.200.193)
```

## Root Cause
The `discover_radiod_services()` function in `/ka9q/discovery.py` was parsing output from `avahi-browse` which contains **decimal** ASCII escape sequences (e.g., `\032` = ASCII 32 = space, `\064` = ASCII 64 = '@'). These escape sequences were being passed through to the web UI without being decoded.

## Solution
Added a new function `_decode_escape_sequences()` that:
1. Converts **decimal** escape sequences (like `\032`, `\064`) to their actual characters using base-10 interpretation
2. Replaces control characters (ASCII < 32 or == 127) with spaces for readability
3. Handles other common escape sequences (`\n`, `\t`, `\\`)

**Important:** avahi-browse uses **decimal** ASCII values, not octal! `\064` = ASCII 64 = '@', not '4'.

## Changes Made

### `/ka9q/discovery.py`
- **Added:** `_decode_escape_sequences()` function (lines 416-441)
- **Modified:** `discover_radiod_services()` to decode service names (line 467)

### `/tests/test_native_discovery.py`
- **Added:** Comprehensive test coverage for escape sequence decoding:
  - `test_decode_escape_sequences_decimal()` - Tests basic decimal decoding
  - `test_decode_escape_sequences_real_world()` - Tests with actual service names
  - `test_decode_escape_sequences_no_escapes()` - Tests strings without escapes
  - `test_decode_escape_sequences_control_chars()` - Tests control character replacement

## Technical Details

### Escape Sequence Types Handled
- **Decimal sequences:** `\032` (space, ASCII 32), `\064` ('@', ASCII 64), etc.
- **Control characters:** ASCII values < 32 or == 127 are replaced with spaces
- **Common escapes:** `\n`, `\t`, `\\`

### Data Flow
1. `avahi-browse` outputs service names with escape sequences
2. `discover_radiod_services()` parses the output and decodes the names
3. Web API (`/api/discover`) returns decoded names
4. JavaScript displays properly formatted names in the dropdown

## Testing
All tests pass:
```bash
python3 -m unittest tests.test_native_discovery.TestNativeDiscovery.test_decode_escape_sequences_decimal
python3 -m unittest tests.test_native_discovery.TestNativeDiscovery.test_decode_escape_sequences_real_world
python3 -m unittest tests.test_native_discovery.TestNativeDiscovery.test_decode_escape_sequences_no_escapes
python3 -m unittest tests.test_native_discovery.TestNativeDiscovery.test_decode_escape_sequences_control_chars
```

### Verification Examples
- `\032` → ` ` (space, ASCII 32)
- `\064` → `@` (at sign, ASCII 64)
- `ACO G\032\064EM38ww\032with\032SAS2` → `ACO G @EM38ww with SAS2`
- `ACO G\032\064EM38ww\032with\032airspy` → `ACO G @EM38ww with airspy`

## Impact
- **Web UI:** Service names now display correctly in the dropdown with proper @ symbols
- **API:** `/api/discover` endpoint returns human-readable service names
- **Backward Compatibility:** No breaking changes - only affects display format
- **Performance:** Minimal impact - regex-based decoding is fast

## Future Considerations
- The function could be extended to handle additional escape sequences if needed
- Currently assumes UTF-8 encoding for the service names
- All escape sequences are interpreted as decimal ASCII values per avahi-browse convention
