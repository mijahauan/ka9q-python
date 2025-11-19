# Testing Guide for Channel Operations

**Purpose:** Verify that ka9q-python can successfully create channels AND tune existing channels.

---

## The Problem

You reported that the package had issues:
1. ❌ Tuning an established channel to a different frequency didn't work
2. ❌ Raising or lowering the volume (gain) didn't work

These are **critical functional issues** that must be fixed before the package is production-ready.

---

## What We've Created

### 1. Comprehensive Test Script

**`test_channel_operations.py`** - Tests the exact scenarios you described:

```bash
python3 test_channel_operations.py radiod.local
```

**What it tests:**
1. ✅ **Create new channel** - Creates channel at 14.074 MHz
2. ✅ **Re-tune frequency** - Changes to 14.076 MHz (2 kHz higher)
3. ✅ **Change gain** - Adjusts volume from 0 dB to 10 dB
4. ✅ **Re-tune again** - Changes to 14.070 MHz (4 kHz lower)

**Output:**
- Detailed status for each operation
- Field-by-field verification
- Pass/fail for each test
- Diagnostic information if tests fail

### 2. Diagnostic Guide

**`CHANNEL_TUNING_DIAGNOSTICS.md`** - Complete troubleshooting guide:

- Common issues and solutions
- Step-by-step diagnostic procedures
- Code examples for each scenario
- radiod configuration checks
- Known limitations

### 3. Integration Tests

**`tests/test_integration.py`** - Automated tests (already existed):

```bash
pytest tests/test_integration.py -v --radiod-host=radiod.local
```

Tests:
- Frequency tuning
- Gain changes
- AGC enable/disable
- Multiple channels
- Re-tuning existing channels

---

## How to Test

### Quick Test (Recommended First)

```bash
cd /home/mjh/git/ka9q-python
python3 test_channel_operations.py radiod.local
```

**Expected output if working:**
```
✓ TEST 1: PASSED - Channel created successfully
✓ TEST 2: PASSED - Frequency re-tuning works
✓ TEST 3: PASSED - Gain adjustment works
✓ BONUS TEST: PASSED

🎉 ALL TESTS PASSED!
```

**If tests fail:**
See detailed diagnostics in output and consult `CHANNEL_TUNING_DIAGNOSTICS.md`

### Detailed Integration Tests

```bash
# Run all integration tests
pytest tests/test_integration.py -v --radiod-host=radiod.local

# Run specific test class
pytest tests/test_integration.py::TestIntegrationTuneFrequency -v --radiod-host=radiod.local
pytest tests/test_integration.py::TestIntegrationTuneGain -v --radiod-host=radiod.local
```

---

## What Could Be Wrong

### Possibility 1: Code Bug (Python Package)

If tests fail consistently, there may be a bug in how `tune()` works.

**Check for:**
- Commands not being sent correctly
- Response matching issues
- Parameter encoding problems

**Action:** Run with debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Then run your tune() calls
```

### Possibility 2: radiod Configuration

radiod may not support parameter changes for certain configurations.

**Check:**
```bash
# Test with native ka9q-radio tune utility
tune -r radiod.local -s 99999999 -f 14.074M -m usb -v

# Try changing frequency
tune -r radiod.local -s 99999999 -f 14.076M -m usb -v

# Try changing gain
tune -r radiod.local -s 99999999 -g 10 -v
```

If native `tune` doesn't work either, it's a radiod issue, not the Python package.

### Possibility 3: Network/Multicast Issues

Status responses may not be reaching the client.

**Check:**
```bash
# Test multicast connectivity
ping -c 3 239.251.200.193  # Or your multicast address

# Check routing
ip route | grep 224
```

### Possibility 4: SSRC Conflicts

Using an SSRC that's already in use by another process.

**Check:**
```bash
control -v radiod.local
```

Look for duplicate SSRCs.

---

## Code Examples

### Creating a New Channel (Should Work)

```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")

# Create new channel
status = control.tune(
    ssrc=12345678,
    frequency_hz=14.074e6,
    preset='usb',
    sample_rate=12000,
    timeout=10.0
)

print(f"Created: {status.get('frequency')/1e6:.6f} MHz")
```

### Re-tuning Existing Channel (This is what was failing)

```python
# Change frequency of existing channel
status = control.tune(
    ssrc=12345678,  # SAME SSRC as above
    frequency_hz=14.076e6,  # NEW frequency
    preset='usb',
    timeout=10.0
)

print(f"Re-tuned to: {status.get('frequency')/1e6:.6f} MHz")

# Verify it changed
if abs(status.get('frequency') - 14.076e6) < 1.0:
    print("✓ Re-tuning worked!")
else:
    print("✗ Re-tuning failed - still at old frequency")
```

### Changing Gain (This is what was failing)

```python
# Change gain on existing channel
status = control.tune(
    ssrc=12345678,
    frequency_hz=14.076e6,
    preset='usb',
    gain=15.0,  # NEW gain
    timeout=10.0
)

print(f"Gain: {status.get('gain')} dB")
print(f"AGC: {status.get('agc_enable')}")

# Verify
if abs(status.get('gain', 0) - 15.0) < 0.5:
    print("✓ Gain change worked!")
else:
    print("✗ Gain change failed")
```

---

## Expected Behavior

### For New Channels
✅ `tune()` should create the channel with specified parameters  
✅ Status response should match requested values  
✅ Channel should appear in `control -v` output  

### For Existing Channels
✅ `tune()` should update the channel parameters  
✅ Status response should show NEW values  
✅ Channel should actually operate at new frequency/gain  
✅ Previous settings should be replaced (not accumulate)  

---

## Next Steps

### 1. Run the Test Script

```bash
python3 test_channel_operations.py radiod.local
```

This will tell us exactly what's working and what's not.

### 2. Based on Results

**If all tests pass:**
- ✅ Package is working correctly
- Previous issues may have been configuration/usage errors
- Document correct usage patterns

**If tests fail:**
- 📋 Review detailed diagnostics
- 🔍 Check radiod logs: `journalctl -u radiod -f`
- 🐛 File bug report with test output
- 🛠️ May need code fixes

### 3. Document Findings

Create a summary of:
- What works
- What doesn't work
- Under what conditions
- Error messages and logs

---

## Performance vs Functionality

**Important Note:**

The performance fixes we just applied improve:
- ✅ Speed (exponential backoff, socket reuse)
- ✅ Resource usage (less CPU, fewer sockets)
- ✅ Scalability (can handle more channels)

But they don't change **functional behavior**:
- If tuning didn't work before, it still won't work
- If tuning worked before, it should still work (and be faster)

**So we need to test functionality separately from performance.**

---

## Files Reference

| File | Purpose |
|------|---------|
| `test_channel_operations.py` | Comprehensive functional test script |
| `CHANNEL_TUNING_DIAGNOSTICS.md` | Troubleshooting guide |
| `tests/test_integration.py` | Automated integration tests |
| `test_performance_fixes.py` | Performance improvement verification |

---

## Getting Help

If tests reveal bugs:

1. **Collect diagnostics:**
   ```bash
   python3 test_channel_operations.py radiod.local > test_output.log 2>&1
   journalctl -u radiod -n 200 > radiod.log
   ```

2. **Try native tune:**
   ```bash
   tune -r radiod.local -s 99999999 -f 14.074M -m usb -v
   ```

3. **Check packet flow:**
   ```bash
   tcpdump -i any multicast and port 5006
   ```

4. **File issue with:**
   - Test output
   - radiod logs
   - Network diagnostics
   - radiod version/config

---

## Summary

You reported critical issues with channel tuning. We've created:

1. ✅ Comprehensive test script to verify functionality
2. ✅ Detailed diagnostic guide
3. ✅ Integration tests for automated checking
4. ✅ Code examples showing correct usage

**Next step: Run the test script and see what happens.**

```bash
python3 test_channel_operations.py radiod.local
```

This will tell us if the package works correctly or if there are bugs to fix.
