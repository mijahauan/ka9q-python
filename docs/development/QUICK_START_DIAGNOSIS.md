# Quick Start: Diagnosing "Commands Don't Take Effect"

## Your Situation

Your application runs without errors, but tune commands don't seem to work:
- Changing frequency doesn't change the frequency
- Changing volume/gain doesn't change the volume
- Commands are sent but nothing happens

## Step 1: Run the Debug Tool (2 minutes)

```bash
cd /path/to/ka9q-python
python tests/test_tune_debug.py radiod.local
```

Replace `radiod.local` with your radiod hostname or IP address.

### What to Look For

**If working correctly**, you'll see:
```
✓ Connected successfully
✓ Tune command succeeded

Frequency verification:
  Requested: 14.074000 MHz
  Reported:  14.074000 MHz
  Diff:      0.0 Hz
  ✓ Frequency match!

Gain verification:
  Requested: 10.00 dB
  Reported:  10.00 dB
  Diff:      0.00 dB
  ✓ Gain match!
```

**If NOT working**, you'll see warnings like:
```
⚠ Frequency mismatch (diff > 1 Hz)
⚠ WARNING: Frequency appears unchanged from old value!
⚠ Gain mismatch (diff > 0.1 dB)
```

## Step 2: Interpret Results

### Scenario A: Connection Failed

**Error message:**
```
✗ Connection failed: [Errno -2] Name or service not known
```

**Solutions:**
1. Check radiod hostname/IP is correct
2. Verify radiod is running: `systemctl status radiod` (on radiod host)
3. Test network: `ping radiod.local`
4. Try IP instead of hostname: `python tests/test_tune_debug.py 192.168.1.100`

### Scenario B: Timeout Receiving Status

**Error message:**
```
✗ Tune command failed: No status response received
```

**Solutions:**
1. Multicast not working - check: `ip route | grep 224`
2. Firewall blocking - temporarily disable to test
3. Wrong network interface - check `ifconfig` or `ip addr`
4. Radiod not sending status - check radiod logs

### Scenario C: Values Don't Match

**Debug output shows:**
```
Frequency verification:
  Requested: 14.074000 MHz
  Reported:  14.000000 MHz
  Diff:      74000.0 Hz
  ⚠ Frequency mismatch (diff > 1 Hz)
```

**This means:** Commands are being sent and received, but not applied!

**Solutions:**
1. **Check radiod logs** (MOST IMPORTANT):
   ```bash
   # On radiod host
   journalctl -u radiod -f
   # or
   tail -f /var/log/radiod.log
   ```
   
   Look for errors like:
   - "No hardware available"
   - "Tuning failed"
   - "Invalid parameter"

2. **Test with native tune.c**:
   ```bash
   # On radiod host
   tune -r localhost -s 99999999 -f 14.074M -m usb -v
   ```
   
   - If this WORKS → ka9q-python bug (report it)
   - If this FAILS → radiod configuration problem

3. **Check radiod hardware config**:
   ```bash
   cat /etc/radio/radiod.conf
   ```
   
   Should have [hardware] section:
   ```
   [hardware]
   device = rtlsdr://0
   # or
   device = airspy://0
   ```

4. **Verify hardware is connected**:
   ```bash
   lsusb  # Should show SDR device
   ```

## Step 3: Run Integration Tests

Once debug tool shows values match, run full integration tests:

```bash
# Test frequency changes
pytest tests/test_integration.py::TestIntegrationTuneFrequency -v --radiod-host=radiod.local

# Test gain changes
pytest tests/test_integration.py::TestIntegrationTuneGain -v --radiod-host=radiod.local

# Test all
pytest tests/test_integration.py -v --radiod-host=radiod.local
```

## Step 4: Test Your Application

Add debug output to your application:

```python
from ka9q import RadiodControl

control = RadiodControl('radiod.local')

# Send tune command
print("Requesting frequency: 14.074 MHz, gain: 10 dB")
status = control.tune(
    ssrc=12345,
    frequency_hz=14.074e6,
    preset='usb',
    gain=10.0,
    timeout=5.0
)

# Check what was reported
print(f"Reported frequency: {status.get('frequency', 0)/1e6:.3f} MHz")
print(f"Reported gain: {status.get('gain', 0):.1f} dB")

# Compare
requested_freq = 14.074e6
reported_freq = status.get('frequency', 0)
freq_diff = abs(requested_freq - reported_freq)

if freq_diff < 1.0:
    print("✓ Frequency matches!")
else:
    print(f"⚠ Frequency mismatch: diff = {freq_diff} Hz")
```

## Common Issues and Quick Fixes

### Issue: "Commands work in examples but not my app"

**Check:**
1. Are you using the same radiod hostname?
2. Are you waiting for status response (not timing out)?
3. Are you checking status dict for values?
4. Are you reusing the same SSRC correctly?

**Add to your app:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show debug output from ka9q-python.

### Issue: "First command works, rest don't"

**Problem:** Likely re-tuning existing channel incorrectly.

**Solution:** Use same SSRC to update channel:
```python
ssrc = 12345

# Create channel
status1 = control.tune(ssrc=ssrc, frequency_hz=14.074e6, preset='usb')

# Update same channel (use same SSRC)
status2 = control.tune(ssrc=ssrc, frequency_hz=14.076e6, preset='usb')
```

### Issue: "Gain changes don't work"

**Check AGC setting:**
```python
# This may not work (AGC overrides gain)
status = control.tune(ssrc=12345, gain=10.0, agc_enable=True)

# Try this instead
status = control.tune(ssrc=12345, gain=10.0)
# AGC will be disabled automatically when gain is set
```

### Issue: "Works sometimes, not others"

**Add delays:**
```python
import time

status1 = control.tune(ssrc=12345, frequency_hz=14.074e6, preset='usb')
time.sleep(0.5)  # Wait for radiod to process

status2 = control.tune(ssrc=12345, frequency_hz=14.076e6, preset='usb')
```

## Getting More Help

If the debug tool shows mismatches and radiod logs show errors, you need to:

1. Fix radiod configuration
2. Check hardware connections
3. Verify SDR device works

If the debug tool shows matches but your app doesn't work:

1. Add debug output to your app (see above)
2. Compare what your app sends vs what debug tool sends
3. Check for timing issues
4. Verify you're reading status correctly

## Full Troubleshooting Guide

See `tests/TROUBLESHOOTING_CHECKLIST.md` for complete diagnosis steps.

See `tests/INTEGRATION_TESTING.md` for detailed integration testing guide.

## Example Session

Here's what a successful diagnosis looks like:

```bash
$ python tests/test_tune_debug.py radiod.local
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
  command_tag         : 12345
  frequency           : 14.074000 MHz (14074000.0 Hz)
  gain                : 0.00 dB
  preset              : usb
  samprate            : 12000 Hz
  ssrc                : 99999001 (0x05f5e0c9)

Frequency verification:
  Requested: 14.074000 MHz
  Reported:  14.074000 MHz
  Diff:      0.0 Hz
  ✓ Frequency match!

======================================================================
TEST 2: Gain Change
======================================================================
...
✓ Gain match!

======================================================================
TEST 3: Frequency Change
======================================================================
...
✓ Frequency changed successfully!

======================================================================
SUMMARY
======================================================================
✓ All debug tests completed
```

This means your radiod is working and commands are taking effect!

If you see this, then any issues in your application are likely related to:
- How you're calling tune()
- How you're interpreting the status response
- Timing of commands

Not a problem with ka9q-python or radiod itself.
