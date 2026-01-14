# KA9Q-RADIO COMPATIBILITY ANALYSIS

**Analysis Date:** January 13, 2026  
**ka9q-python Version:** 3.2.7  
**ka9q-radio Source:** /Users/mjh/Sync/GitHub/ka9q-radio

## Executive Summary

The ka9q-python library has **12 missing StatusType values** and **encoding type discrepancies** compared to the current ka9q-radio source code. These need to be addressed to ensure full compatibility with radiod.

### Critical Findings

1. **No Breaking Changes** - All existing StatusType values match correctly (no value mismatches)
2. **Missing Features** - 12 new StatusType values added to radiod are not exposed in Python
3. **Encoding Updates** - Encoding enum has been expanded with endian-specific variants and OPUS_VOIP

## Detailed Analysis

### 1. StatusType Enum Comparison

**Status:** ⚠️ **12 missing values, 7 obsolete placeholders**

#### Missing in Python (Present in C status.h):

| Name | Value | Description |
|------|-------|-------------|
| `BIN_BYTE_DATA` | 9 | Vector of 1-byte spectrum analyzer data |
| `SPECTRUM_BASE` | 11 | Base level of 1-byte analyzer data, dB |
| `SPECTRUM_AVG` | 12 | Number of FFTs averaged into each spectrum response |
| `WINDOW_TYPE` | 14 | Window type for FFT analyzer |
| `NOISE_BW` | 15 | Noise bandwidth of FFT spectrum bin, in bins |
| `SPECTRUM_SHAPE` | 91 | Parameter for spectrum analysis window (e.g., Kaiser beta) |
| `RESOLUTION_BW` | 93 | Bandwidth (Hz) of noncoherent integration bin |
| `OPUS_DTX` | 111 | Opus encoder discontinuous transmission enable/disable |
| `OPUS_APPLICATION` | 112 | Opus encoder application voice/audio/etc |
| `OPUS_BANDWIDTH` | 113 | Opus encoder audio bandwidth limitation |
| `OPUS_FEC` | 114 | Opus encoder forward error correction loss rate, % |
| `SPECTRUM_STEP` | 115 | Size of byte spectrum data level step, dB |

#### Obsolete in Python (Should be replaced):

| Name | Value | Should Be |
|------|-------|-----------|
| `UNUSED4` | 9 | `BIN_BYTE_DATA` |
| `UNUSED6` | 11 | `SPECTRUM_BASE` |
| `UNUSED7` | 12 | `SPECTRUM_AVG` |
| `UNUSED8` | 14 | `WINDOW_TYPE` |
| `UNUSED9` | 15 | `NOISE_BW` |
| `SPECTRUM_KAISER_BETA` | 91 | `SPECTRUM_SHAPE` |
| `NONCOHERENT_BIN_BW` | 93 | `RESOLUTION_BW` |

**Note:** The Python library used placeholder names (UNUSED4-9) for values 9, 11-12, 14-15. These positions now have proper names in the C code. Additionally, `SPECTRUM_KAISER_BETA` was renamed to `SPECTRUM_SHAPE` and `NONCOHERENT_BIN_BW` was renamed to `RESOLUTION_BW`.

### 2. Encoding Enum Comparison

**Status:** ⚠️ **Endian-specific variants and OPUS_VOIP missing**

#### C rtp.h enum encoding:

```c
enum encoding {
  NO_ENCODING = 0,
  S16LE,        // 1
  S16BE,        // 2
  OPUS,         // 3
  F32LE,        // 4
  AX25,         // 5
  F16LE,        // 6
  OPUS_VOIP,    // 7 - Opus with APPLICATION_VOIP
  F32BE,        // 8
  F16BE,        // 9
  UNUSED_ENCODING, // 10 - Sentinel, not used
};
```

#### Python types.py Encoding class:

```python
class Encoding:
    NO_ENCODING = 0
    S16LE = 1
    S16BE = 2
    OPUS = 3
    F32 = 4      # Should be F32LE
    AX25 = 5
    F16 = 6      # Should be F16LE
```

#### Issues:

1. **Missing endian variants:** `F32LE`, `F16LE`, `F32BE`, `F16BE`
2. **Missing OPUS variant:** `OPUS_VOIP` (value 7)
3. **Ambiguous names:** `F32` and `F16` should be `F32LE` and `F16LE` for clarity
4. **Missing sentinel:** `UNUSED_ENCODING` (value 10)

### 3. Impact Assessment

#### High Priority - Spectrum Analysis Features

The missing spectrum-related StatusType values indicate that radiod has expanded spectrum analysis capabilities:

- **BIN_BYTE_DATA** (9) - Compact 1-byte spectrum data format
- **SPECTRUM_BASE** (11) - Base level for byte data
- **SPECTRUM_AVG** (12) - Averaging control
- **WINDOW_TYPE** (14) - Window function selection
- **NOISE_BW** (15) - Noise bandwidth measurement
- **SPECTRUM_SHAPE** (91) - Window shaping parameter
- **RESOLUTION_BW** (93) - Resolution bandwidth
- **SPECTRUM_STEP** (115) - Level step size

**Impact:** Applications using spectrum analysis features cannot access these new capabilities.

#### Medium Priority - Opus Encoder Enhancements

New Opus encoder controls have been added:

- **OPUS_DTX** (111) - Discontinuous transmission (saves bandwidth)
- **OPUS_APPLICATION** (112) - Application type (voice/audio/restricted-lowdelay)
- **OPUS_BANDWIDTH** (113) - Audio bandwidth limiting
- **OPUS_FEC** (114) - Forward error correction

**Impact:** Applications using Opus encoding cannot optimize encoder settings.

#### Medium Priority - Encoding Type Precision

The encoding enum now distinguishes between little-endian and big-endian float formats:

- **F32LE/F32BE** - 32-bit float, endian-specific
- **F16LE/F16BE** - 16-bit float, endian-specific
- **OPUS_VOIP** - Opus optimized for voice

**Impact:** Applications may not be able to request specific endianness or use VOIP-optimized Opus.

### 4. Compatibility Status

#### ✅ No Breaking Changes

All existing StatusType enum values have **correct mappings** - no value mismatches were found. This means:

- Existing code will continue to work
- No protocol incompatibilities with current radiod versions
- Backward compatibility is maintained

#### ⚠️ Missing Functionality

The library cannot:

1. Access new spectrum analysis features
2. Configure advanced Opus encoder settings
3. Request specific endianness for float encodings
4. Use VOIP-optimized Opus encoding

### 5. Recommended Actions

#### Immediate (Required for Full Compatibility):

1. **Update `types.py` StatusType class:**
   - Replace `UNUSED4` → `BIN_BYTE_DATA`
   - Replace `UNUSED6` → `SPECTRUM_BASE`
   - Replace `UNUSED7` → `SPECTRUM_AVG`
   - Replace `UNUSED8` → `WINDOW_TYPE`
   - Replace `UNUSED9` → `NOISE_BW`
   - Replace `SPECTRUM_KAISER_BETA` → `SPECTRUM_SHAPE`
   - Replace `NONCOHERENT_BIN_BW` → `RESOLUTION_BW`
   - Add `OPUS_DTX = 111`
   - Add `OPUS_APPLICATION = 112`
   - Add `OPUS_BANDWIDTH = 113`
   - Add `OPUS_FEC = 114`
   - Add `SPECTRUM_STEP = 115`

2. **Update `types.py` Encoding class:**
   - Rename `F32` → `F32LE` (keep value 4)
   - Rename `F16` → `F16LE` (keep value 6)
   - Add `OPUS_VOIP = 7`
   - Add `F32BE = 8`
   - Add `F16BE = 9`
   - Add `UNUSED_ENCODING = 10`
   - Add backward compatibility aliases: `F32 = F32LE`, `F16 = F16LE`

3. **Update `control.py`:**
   - Add setter methods for new Opus parameters
   - Add getter methods for spectrum analysis parameters
   - Update documentation strings

4. **Add tests:**
   - Test new StatusType values
   - Test new Encoding values
   - Verify backward compatibility

#### Future Enhancements:

1. **Spectrum Analysis API:**
   - Create high-level spectrum analyzer interface
   - Add example showing spectrum analysis usage

2. **Opus Configuration API:**
   - Add convenience methods for Opus tuning
   - Document Opus parameter interactions

3. **Documentation:**
   - Update API reference with new parameters
   - Add migration guide for encoding changes
   - Document spectrum analysis features

## Verification Commands

```bash
# Run comparison scripts
cd /Users/mjh/Sync/GitHub/ka9q-python
python3 compare_status_types.py
python3 compare_encodings.py

# After fixes, verify
python3 compare_status_types.py && echo "✅ StatusType in sync"
python3 compare_encodings.py && echo "✅ Encoding in sync"
```

## References

- **ka9q-radio status.h:** `/Users/mjh/Sync/GitHub/ka9q-radio/src/status.h`
- **ka9q-radio rtp.h:** `/Users/mjh/Sync/GitHub/ka9q-radio/src/rtp.h`
- **ka9q-python types.py:** `/Users/mjh/Sync/GitHub/ka9q-python/ka9q/types.py`
- **ka9q-python control.py:** `/Users/mjh/Sync/GitHub/ka9q-python/ka9q/control.py`

## Conclusion

The ka9q-python library is **functionally compatible** with radiod but is **missing access to newer features** added by Phil Karn. No breaking changes were found, so existing code will continue to work. However, to provide full access to radiod's capabilities, the library should be updated with the 12 missing StatusType values and the expanded Encoding enum.

The updates are **low-risk** since they only add new capabilities without changing existing behavior.
