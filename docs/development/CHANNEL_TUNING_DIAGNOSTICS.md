# Channel Tuning Diagnostics Guide

**Problem:** Tuning existing channels to different frequencies or changing gain/volume isn't working.

This guide helps diagnose and fix issues with channel creation and tuning.

---

## Quick Test

Run the comprehensive test script:

```bash
python3 test_channel_operations.py radiod.local
```

This will test:
1. ✅ Creating a new channel
2. ✅ Re-tuning to a different frequency
3. ✅ Changing gain/volume
4. ✅ Multiple frequency changes

---

## Common Issues and Solutions

### Issue 1: Commands Send But Don't Take Effect

**Symptoms:**
- `tune()` returns successfully (no timeout)
- But radiod doesn't actually change frequency/gain
- Channel stays at old settings

**Likely Causes:**

#### A. radiod Not Accepting Parameter Changes

Some radiod configurations may lock certain parameters. Check radiod logs:

```bash
journalctl -u radiod -f
```

Look for messages like:
- "Parameter locked"
- "Invalid parameter"
- "Channel preset prevents changes"

#### B. Preset Conflicts

Some presets don't support all parameters:
- **IQ mode**: May not support gain control
- **FM mode**: May have different gain behavior
- **Locked presets**: May prevent frequency changes

**Solution:** Specify the preset explicitly in every tune() call:

```python
# Instead of:
control.tune(ssrc=123, frequency_hz=14.076e6)

# Do this:
control.tune(ssrc=123, frequency_hz=14.076e6, preset='usb')
```

#### C. AGC Interfering with Gain

If AGC is enabled, manual gain changes may be ignored.

**Solution:** Explicitly disable AGC when setting gain:

```python
# This sets gain AND disables AGC
status = control.tune(
    ssrc=123,
    frequency_hz=14.074e6,
    preset='usb',
    gain=10.0  # This automatically sets AGC_ENABLE=0
)
```

---

### Issue 2: Timeout When Tuning

**Symptoms:**
- `TimeoutError` exception
- "No status response received for SSRC"

**Likely Causes:**

#### A. Wrong SSRC

radiod may not be sending status for that SSRC.

**Diagnosis:**
```bash
# List all active channels
control -v radiod.local
```

Check if your SSRC appears in the list.

**Solution:** Use an SSRC that matches an existing channel, or create a new unique one.

#### B. Multicast Issues

Status responses aren't reaching the client.

**Diagnosis:**
```bash
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Try tuning
control.tune(ssrc=123, frequency_hz=14e6, timeout=10)
```

Look for:
- "Sent tune command with tag X" ← Command sent
- "Received N bytes from..." ← Status received
- "Response not for us: ssrc=Y, tag=Z" ← Wrong response

**Solution:** Check multicast routing and firewall.

#### C. radiod Not Responding

radiod may be busy or crashed.

**Diagnosis:**
```bash
systemctl status radiod
journalctl -u radiod -n 50
```

**Solution:** Restart radiod or check its configuration.

---

### Issue 3: Frequency Changes But Returns to Old Value

**Symptoms:**
- `tune()` succeeds
- Status shows correct new frequency
- But channel actually plays old frequency

**Likely Cause:** Multiple clients controlling same SSRC

**Diagnosis:**
```bash
# Check for other processes using radiod
control -v radiod.local
# Look for same SSRC being managed elsewhere
```

**Solution:** Use unique SSRCs for your application.

---

### Issue 4: Gain Changes Have No Effect

**Symptoms:**
- `tune()` succeeds with new gain value
- Status shows gain changed
- But audio volume doesn't change

**Likely Causes:**

#### A. Wrong Preset Mode

Some modes don't support gain:
- **IQ mode**: Gain is in receiver, not demod
- **FM mode**: Uses different gain model

**Solution:** Use preset that supports gain:

```python
control.tune(ssrc=123, frequency_hz=14e6, preset='usb', gain=10.0)
# USB, LSB, AM typically support gain
```

#### B. AGC Still Enabled

If AGC is on, it overrides manual gain.

**Check:**
```python
status = control.tune(ssrc=123, gain=10.0)
print(f"AGC enabled: {status.get('agc_enable')}")
```

Should print: `AGC enabled: False`

If it prints `True`, there's a problem.

**Solution:** File a bug report - gain setting should disable AGC automatically.

#### C. Output Level vs Gain

radiod has both `GAIN` (demod gain) and `OUTPUT_LEVEL` (output scaling).

**Try:**
```python
# Set output level instead
control.set_output_level(ssrc=123, level=1.0)
```

---

## Detailed Diagnostic Steps

### Step 1: Verify Basic Connectivity

```python
from ka9q import RadiodControl, discover_channels

control = RadiodControl("radiod.local")
print(f"Connected to: {control.status_mcast_addr}")
print(f"Destination: {control.dest_addr}")

# List channels
channels = discover_channels("radiod.local")
print(f"Found {len(channels)} channels")
for ssrc, info in channels.items():
    print(f"  {ssrc}: {info.frequency/1e6:.3f} MHz, {info.preset}")
```

**Expected:** Should list active channels without errors.

### Step 2: Test Creating New Channel

```python
import logging
logging.basicConfig(level=logging.DEBUG)

test_ssrc = 99999999
status = control.tune(
    ssrc=test_ssrc,
    frequency_hz=14.074e6,
    preset='usb',
    sample_rate=12000,
    timeout=10.0
)

print(f"Created channel:")
print(f"  SSRC: {status.get('ssrc')}")
print(f"  Frequency: {status.get('frequency')/1e6:.6f} MHz")
print(f"  Preset: {status.get('preset')}")
```

**Expected:** Should create channel and return status with matching values.

**If it fails:** Check radiod logs for errors.

### Step 3: Test Re-tuning Frequency

```python
# Use the channel created in Step 2
status = control.tune(
    ssrc=test_ssrc,
    frequency_hz=14.076e6,  # Change by 2 kHz
    preset='usb',
    timeout=10.0
)

print(f"Re-tuned to: {status.get('frequency')/1e6:.6f} MHz")

# Verify it changed
if abs(status.get('frequency') - 14.076e6) < 1.0:
    print("✓ Frequency change worked!")
else:
    print("✗ Frequency didn't change!")
```

**Expected:** Frequency should change to 14.076 MHz.

**If it fails:**
- Check if status has correct SSRC: `status.get('ssrc') == test_ssrc`
- Check if status has correct tag: `status.get('command_tag')`
- Enable DEBUG logging to see what radiod returns

### Step 4: Test Gain Change

```python
# Change gain on existing channel
status = control.tune(
    ssrc=test_ssrc,
    frequency_hz=14.076e6,
    preset='usb',
    gain=15.0,
    timeout=10.0
)

print(f"Gain: {status.get('gain')} dB")
print(f"AGC: {status.get('agc_enable')}")

# Verify
if abs(status.get('gain', 0) - 15.0) < 0.5:
    print("✓ Gain change worked!")
else:
    print("✗ Gain didn't change!")
```

**Expected:** Gain should be 15.0 dB, AGC should be False.

---

## Code Review Checklist

If tuning still doesn't work, check your code:

### ✅ Always Specify SSRC
```python
# Wrong - no SSRC specified
control.tune(frequency_hz=14e6)

# Right
control.tune(ssrc=12345678, frequency_hz=14e6)
```

### ✅ Use Consistent SSRC for Same Channel
```python
# Wrong - different SSRCs
control.tune(ssrc=123, frequency_hz=14.074e6, preset='usb')
control.tune(ssrc=456, frequency_hz=14.076e6)  # Creates NEW channel!

# Right - same SSRC
control.tune(ssrc=123, frequency_hz=14.074e6, preset='usb')
control.tune(ssrc=123, frequency_hz=14.076e6, preset='usb')  # Re-tunes existing
```

### ✅ Check Return Status
```python
# Wrong - not checking result
control.tune(ssrc=123, frequency_hz=14e6)

# Right - verify it worked
status = control.tune(ssrc=123, frequency_hz=14e6)
if abs(status.get('frequency', 0) - 14e6) > 1.0:
    print("WARNING: Frequency mismatch!")
```

### ✅ Handle Timeouts
```python
# Wrong - no error handling
status = control.tune(ssrc=123, frequency_hz=14e6)

# Right - catch timeouts
try:
    status = control.tune(ssrc=123, frequency_hz=14e6, timeout=10.0)
except TimeoutError:
    print("radiod not responding!")
    # Handle error
```

---

## radiod Configuration Issues

### Check radiod Settings

Some radiod configurations may prevent tuning:

```bash
# Check radiod config file
cat /etc/radiod.conf

# Look for:
# - Locked channels
# - Fixed frequencies
# - AGC force-enabled
# - Gain limits
```

### Check radiod Version

Older radiod versions may have bugs:

```bash
radiod --version
```

Ensure you're using a recent version.

### Test with Native tune Utility

Verify radiod itself works:

```bash
# Create channel with ka9q-radio's tune
tune -r radiod.local -s 99999999 -f 14.074M -m usb -v

# Try changing frequency
tune -r radiod.local -s 99999999 -f 14.076M -m usb -v

# Try changing gain
tune -r radiod.local -s 99999999 -f 14.076M -m usb -g 10 -v
```

If the native `tune` utility works but the Python package doesn't, it's a bug in ka9q-python.

---

## Known Limitations

### 1. Some Parameters May Be Ignored

Depending on radiod configuration and preset:
- IQ mode may ignore gain
- Some presets lock certain parameters
- Hardware limitations may prevent changes

### 2. AGC Behavior

When AGC is enabled:
- Manual gain changes may be overridden
- Gain may vary over time
- Set `gain` parameter to force AGC off

### 3. Multicast Timing

- Status responses are asynchronous
- May take 100-1000ms to receive
- Use longer timeouts if network is slow

---

## Getting Help

If tuning still doesn't work after following this guide:

1. **Run the diagnostic script:**
   ```bash
   python3 test_channel_operations.py radiod.local > diagnostics.log 2>&1
   ```

2. **Collect logs:**
   ```bash
   journalctl -u radiod -n 100 > radiod.log
   ```

3. **File an issue with:**
   - diagnostics.log
   - radiod.log  
   - Your code snippet
   - radiod version and config

---

## Quick Reference

### Create New Channel
```python
control.tune(
    ssrc=12345678,
    frequency_hz=14.074e6,
    preset='usb',
    sample_rate=12000,
    timeout=10.0
)
```

### Change Frequency
```python
control.tune(
    ssrc=12345678,  # Same SSRC
    frequency_hz=14.076e6,  # New frequency
    preset='usb',
    timeout=10.0
)
```

### Change Gain
```python
control.tune(
    ssrc=12345678,
    frequency_hz=14.074e6,
    preset='usb',
    gain=15.0,  # New gain (disables AGC)
    timeout=10.0
)
```

### Change Multiple Parameters
```python
control.tune(
    ssrc=12345678,
    frequency_hz=14.080e6,  # New frequency
    preset='usb',
    gain=20.0,  # New gain
    sample_rate=12000,
    timeout=10.0
)
```
