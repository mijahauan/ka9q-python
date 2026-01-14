# Release Notes - Version 3.4.0

**Release Date:** January 13, 2026

## Summary

This release brings **full compatibility** with the latest ka9q-radio source code by Phil Karn (KA9Q). All protocol definitions have been synchronized, and new features for spectrum analysis and Opus encoder control are now available.

## What's New

### 🎯 Full ka9q-radio Protocol Synchronization

- **116/116 StatusType values** synchronized with ka9q-radio/src/status.h
- **11/11 Encoding types** synchronized with ka9q-radio/src/rtp.h
- All placeholder names replaced with actual protocol values

### 🎵 Enhanced Opus Encoder Control

Four new methods for fine-tuning Opus encoding:

- **`set_opus_dtx(ssrc, enable)`** - Discontinuous Transmission for bandwidth savings
- **`set_opus_application(ssrc, application)`** - Optimize for VOIP/AUDIO/LOWDELAY
- **`set_opus_bandwidth(ssrc, bandwidth)`** - Limit audio bandwidth (4-20 kHz)
- **`set_opus_fec(ssrc, loss_percent)`** - Forward Error Correction configuration

### 📊 Spectrum Analysis Support

New StatusType values for advanced spectrum analysis:

- `BIN_BYTE_DATA` - Compact 1-byte spectrum data format
- `SPECTRUM_BASE` - Base level for byte spectrum data
- `SPECTRUM_AVG` - FFT averaging control
- `WINDOW_TYPE` - Window function selection
- `NOISE_BW` - Noise bandwidth measurement
- `SPECTRUM_SHAPE` - Window shaping parameter
- `RESOLUTION_BW` - Resolution bandwidth
- `SPECTRUM_STEP` - Level step size

### 🔧 Encoding Type Enhancements

New encoding types for precise format control:

- `Encoding.F32LE` - 32-bit float little-endian (explicit)
- `Encoding.F16LE` - 16-bit float little-endian (explicit)
- `Encoding.OPUS_VOIP` - Opus optimized for voice
- `Encoding.F32BE` - 32-bit float big-endian
- `Encoding.F16BE` - 16-bit float big-endian

**Backward compatibility:** `Encoding.F32` and `Encoding.F16` continue to work as aliases to `F32LE` and `F16LE`.

## Changes

### Updated Files

- **`ka9q/types.py`**
  - Replaced 7 placeholder names with actual protocol values
  - Added 5 new StatusType values (111-115)
  - Expanded Encoding class with 6 new values
  - Maintained backward compatibility with aliases

- **`ka9q/control.py`**
  - Updated references to renamed StatusType values
  - Added 4 new Opus encoder control methods
  - Enhanced documentation

- **Version files**
  - Updated to 3.4.0 in `pyproject.toml` and `setup.py`

### New Documentation

- `COMPATIBILITY_ANALYSIS.md` - Detailed protocol comparison
- `COMPATIBILITY_UPDATE_SUMMARY.md` - Complete update summary
- `compare_status_types.py` - Verification script for StatusType
- `compare_encodings.py` - Verification script for Encoding

## Compatibility

✅ **100% Backward Compatible** - No breaking changes

- All existing code continues to work without modification
- All existing tests pass
- Encoding aliases maintain compatibility with previous versions

## Example Usage

### Optimized Opus Voice Channel

```python
from ka9q import RadiodControl, Encoding

control = RadiodControl("radiod.local")

# Create VOIP-optimized Opus channel
info = control.ensure_channel(
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    encoding=Encoding.OPUS_VOIP
)

# Optimize for voice communication
control.set_opus_application(info.ssrc, 2048)  # VOIP mode
control.set_opus_bandwidth(info.ssrc, 1103)    # Wideband (8 kHz)
control.set_opus_dtx(info.ssrc, True)          # Enable DTX
control.set_opus_fec(info.ssrc, 5)             # 5% expected loss
```

### Explicit Endianness

```python
# Request big-endian float format
control.ensure_channel(
    frequency_hz=10.0e6,
    preset="iq",
    sample_rate=16000,
    encoding=Encoding.F32BE  # Big-endian 32-bit float
)
```

## Testing

All existing tests pass:
- ✅ Protocol encoding/decoding tests
- ✅ SSRC allocation tests
- ✅ Channel encoding tests

## Verification

Run the included verification scripts to confirm synchronization:

```bash
python3 compare_status_types.py  # Should show ✅ in sync
python3 compare_encodings.py     # Should show ✅ in sync
```

## Upgrade Instructions

Simply upgrade via pip:

```bash
pip install --upgrade ka9q-python
```

No code changes required - all updates are backward compatible.

## Credits

- **Protocol Analysis:** Synchronized with ka9q-radio by Phil Karn (KA9Q)
- **Implementation:** Michael Hauan (AC0G)

## Links

- **GitHub:** https://github.com/mijahauan/ka9q-python
- **PyPI:** https://pypi.org/project/ka9q-python/
- **ka9q-radio:** https://github.com/ka9q/ka9q-radio
