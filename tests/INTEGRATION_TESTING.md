# Integration Testing for Ka9q-Python

This document explains how to run integration tests that verify tune commands actually take effect on a live radiod instance.

## Overview

**Unit tests** (in `test_*.py` files) verify that the code structure is correct using mocks.

**Integration tests** (in `test_integration.py`) verify that commands actually affect radiod:
- Frequency changes take effect
- Gain/volume changes work
- Preset/mode changes apply
- Filter edges update
- Multiple channels coexist

## Prerequisites

1. **Running radiod instance** - You need access to a working radiod server
2. **Network connectivity** - Multicast must work between your machine and radiod
3. **Hardware** - radiod must have a working SDR hardware interface

## Quick Start

### 1. Run Debug Tool First

Before running full integration tests, use the debug tool to verify basic connectivity:

```bash
# Run debug tool
python tests/test_tune_debug.py radiod.local

# Or with your specific radiod hostname
python tests/test_tune_debug.py 192.168.1.100
```

The debug tool will:
- ✓ Connect to radiod
- ✓ Send tune commands with detailed output
- ✓ Show exactly what was requested vs what was reported
- ✓ Highlight any mismatches

**Expected output if working:**
```
======================================================================
Connecting to radiod at radiod.local
======================================================================
✓ Connected successfully
  Status address: 239.1.2.3
  Control address: radiod.local:5006

======================================================================
TEST 1: Basic Frequency Tune
======================================================================

Sending tune command:
  SSRC:      99999001 (0x05f5e0c9)
  Frequency: 14.074 MHz
  Preset:    usb
  Timeout:   5.0 seconds

✓ Tune command succeeded

Status fields received:
  frequency           : 14.074000 MHz (14074000.0 Hz)
  preset              : usb
  ssrc                : 99999001 (0x05f5e0c9)
  ...

Frequency verification:
  Requested: 14.074000 MHz
  Reported:  14.074000 MHz
  Diff:      0.0 Hz
  ✓ Frequency match!
```

### 2. Run Integration Tests

```bash
# Run all integration tests
pytest tests/test_integration.py -v --radiod-host=radiod.local

# Run specific test class
pytest tests/test_integration.py::TestIntegrationTuneFrequency -v --radiod-host=radiod.local

# Run with detailed output
pytest tests/test_integration.py -v -s --radiod-host=radiod.local
```

### 3. Set Environment Variable (Optional)

```bash
# Set default radiod host
export RADIOD_HOST=radiod.local

# Now you can omit --radiod-host
pytest tests/test_integration.py -v

# Skip integration tests (useful for CI/CD)
export SKIP_INTEGRATION=1
pytest tests/ -v  # Will skip integration tests
```

## Integration Test Categories

### Basic Connectivity Tests

Verifies you can connect to radiod:

```bash
pytest tests/test_integration.py::TestIntegrationBasic -v --radiod-host=radiod.local
```

Tests:
- Can connect to radiod
- Control socket exists

### Frequency Tuning Tests

Verifies frequency changes actually occur:

```bash
pytest tests/test_integration.py::TestIntegrationTuneFrequency -v --radiod-host=radiod.local
```

Tests:
- Tuning to different frequencies
- Frequency changes are applied
- Various bands (80m, 40m, 20m, etc.)

### Gain/Volume Tests

Verifies gain changes take effect:

```bash
pytest tests/test_integration.py::TestIntegrationTuneGain -v --radiod-host=radiod.local
```

Tests:
- Manual gain changes work
- AGC enable/disable
- Gain values are reported correctly

### Preset/Mode Tests

Verifies preset changes work:

```bash
pytest tests/test_integration.py::TestIntegrationTunePresets -v --radiod-host=radiod.local
```

Tests:
- USB, LSB, IQ mode changes
- Preset names are reported

### Sample Rate Tests

Verifies sample rate changes:

```bash
pytest tests/test_integration.py::TestIntegrationTuneSampleRate -v --radiod-host=radiod.local
```

Tests:
- 12000 Hz, 24000 Hz, 48000 Hz
- Sample rate changes are applied

### Filter Edge Tests

Verifies filter settings work:

```bash
pytest tests/test_integration.py::TestIntegrationTuneFilterEdges -v --radiod-host=radiod.local
```

Tests:
- Low/high edge settings
- Filter changes take effect

### Encoding Tests

Verifies audio encoding changes:

```bash
pytest tests/test_integration.py::TestIntegrationTuneEncoding -v --radiod-host=radiod.local
```

Tests:
- S16BE, S16LE, F32 encodings
- Encoding changes are reported

### Multiple Channel Tests

Verifies multiple channels can coexist:

```bash
pytest tests/test_integration.py::TestIntegrationTuneMultipleChannels -v --radiod-host=radiod.local
```

Tests:
- Multiple SSRCs active simultaneously
- Each channel maintains independent state

### Re-tune Tests

Verifies existing channels can be re-tuned:

```bash
pytest tests/test_integration.py::TestIntegrationTuneRetune -v --radiod-host=radiod.local
```

Tests:
- Re-tuning frequency on existing channel
- Changing gain on existing channel
- Re-tune doesn't create duplicate channels

## Troubleshooting

### Problem: Tests Skip or Fail to Connect

**Symptoms:**
```
SKIPPED [1] test_integration.py:45: Cannot connect to radiod at radiod.local
```

**Solutions:**

1. **Check radiod is running:**
   ```bash
   # On radiod host
   systemctl status radiod
   # or
   ps aux | grep radiod
   ```

2. **Check network connectivity:**
   ```bash
   # Can you reach the host?
   ping radiod.local
   
   # Is radiod listening?
   nc -zv radiod.local 5006
   ```

3. **Check multicast:**
   ```bash
   # Verify multicast route exists
   ip route show | grep 224
   
   # Should see something like:
   # 224.0.0.0/4 dev eth0 scope link
   ```

4. **Try IP address instead of hostname:**
   ```bash
   pytest tests/test_integration.py -v --radiod-host=192.168.1.100
   ```

### Problem: Commands Don't Take Effect

**Symptoms:**
- Tests report "Frequency mismatch" or "Gain didn't change"
- Requested values don't match reported values
- No errors, but nothing happens

**Debug steps:**

1. **Run the debug tool:**
   ```bash
   python tests/test_tune_debug.py radiod.local
   ```
   
   Look for warnings like:
   ```
   ⚠ Frequency mismatch (diff > 1 Hz)
   ⚠ WARNING: Frequency appears unchanged from old value!
   ```

2. **Check radiod logs:**
   ```bash
   # On radiod host
   journalctl -u radiod -f
   # or
   tail -f /var/log/radiod.log
   ```
   
   Look for errors like:
   - "Invalid SSRC"
   - "No hardware available"
   - "Tuning failed"

3. **Verify radiod has hardware:**
   ```bash
   # On radiod host, check radiod config
   cat /etc/radio/radiod.conf
   
   # Should have [hardware] section with device configured
   ```

4. **Test with radiod's original tune command:**
   ```bash
   # On radiod host
   tune -r localhost -s 99999999 -f 14.074M -m usb -v
   ```
   
   If this doesn't work, the issue is with radiod, not ka9q-python.

5. **Check command packet is being sent:**
   
   Add debugging to `ka9q/control.py`:
   ```python
   # In tune() method, after building command
   print(f"Sending command: {len(cmd_buffer)} bytes")
   print(f"Command SSRC: {ssrc}, Tag: {command_tag}")
   ```

6. **Verify status responses are received:**
   
   Add debugging:
   ```python
   # In tune() method, in response loop
   print(f"Received status from SSRC {resp_ssrc}, tag {resp_tag}")
   ```

### Problem: Timeout Errors

**Symptoms:**
```
TimeoutError: No status response received for SSRC 99999999
```

**Solutions:**

1. **Increase timeout:**
   ```python
   status = control.tune(ssrc=ssrc, frequency_hz=freq, timeout=10.0)  # 10 seconds
   ```

2. **Check multicast reception:**
   ```bash
   # Test multicast reception
   socat - UDP4-RECVFROM:5006,ip-add-membership=239.1.2.3:0.0.0.0,reuseaddr
   ```
   
   You should see binary status packets.

3. **Verify firewall isn't blocking:**
   ```bash
   # Check firewall rules
   iptables -L -n | grep 5006
   ```

4. **Check radiod is sending status:**
   ```bash
   # On radiod host, check config
   grep status /etc/radio/radiod.conf
   
   # Should have:
   # status = 239.1.2.3
   ```

### Problem: Wrong Values Reported

**Symptoms:**
- Frequency requested: 14.074 MHz
- Frequency reported: 14.000 MHz
- Difference is systematic

**Possible causes:**

1. **Radiod applying offset:**
   - Check radiod.conf for frequency offsets
   - Some SDRs have built-in offsets

2. **Hardware limitations:**
   - SDR may not support exact frequency
   - Check hardware documentation

3. **Preset limitations:**
   - Some presets override frequency settings
   - Try using 'iq' mode for exact frequency

4. **Filter edges affecting reported frequency:**
   - Filter center may differ from carrier frequency
   - This is normal for SSB modes

## Expected Test Results

### All Tests Pass

```
tests/test_integration.py::TestIntegrationBasic::test_can_connect_to_radiod PASSED
tests/test_integration.py::TestIntegrationTuneFrequency::test_tune_frequency_changes PASSED
tests/test_integration.py::TestIntegrationTuneGain::test_gain_changes_take_effect PASSED
...
======================== 15 passed in 12.34s =========================
```

This means:
- ✓ Commands are being sent correctly
- ✓ Commands are taking effect on radiod
- ✓ Status responses match requested values
- ✓ Your integration is working properly

### Some Tests Fail or Skip

Review the specific failures:

- **Skipped tests:** Radiod not accessible or feature not supported
- **Failed assertions:** Commands not taking effect (see troubleshooting above)
- **Timeouts:** Network or multicast issues

## Best Practices

1. **Use unique SSRCs for testing:**
   - Start at 99000000 to avoid conflicts
   - Each test uses different SSRC

2. **Add delays between commands:**
   ```python
   time.sleep(0.5)  # Give radiod time to process
   ```

3. **Clean up test channels:**
   - Integration tests use high SSRCs (99000000+)
   - These can be safely deleted on radiod

4. **Test one thing at a time:**
   - Run individual test classes first
   - Isolate which parameter isn't working

5. **Compare with original tune.c:**
   - If ka9q-python fails but tune.c works, file a bug
   - If both fail, issue is with radiod setup

## CI/CD Integration

To skip integration tests in automated testing:

```yaml
# .github/workflows/test.yml
env:
  SKIP_INTEGRATION: 1

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ -v
        # Integration tests will be skipped
```

For automated integration testing with radiod:

```yaml
services:
  radiod:
    image: your-radiod-image
    ports:
      - 5006:5006

steps:
  - run: pytest tests/test_integration.py -v --radiod-host=radiod
```

## Getting Help

If integration tests fail:

1. Run debug tool and save output
2. Check radiod logs
3. Try original tune.c to verify radiod works
4. Compare command encoding with working tune.c
5. File issue with:
   - Debug tool output
   - radiod logs
   - radiod version and config
   - Network setup

## Summary

Integration tests verify that:
- ✓ Tune commands are sent correctly
- ✓ Radiod processes commands
- ✓ Changes actually take effect
- ✓ Status responses reflect reality

Run them regularly to catch regressions and verify your radiod setup works correctly.
