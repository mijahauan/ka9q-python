# Troubleshooting Checklist: Tune Commands Not Taking Effect

Use this checklist if your application runs without errors but tune commands don't seem to take effect (frequency doesn't change, volume doesn't change, etc.).

## Quick Diagnosis

Run this command first to diagnose the issue:

```bash
python tests/test_tune_debug.py radiod.local
```

Replace `radiod.local` with your radiod hostname or IP.

This will show you:
1. Whether commands are being sent
2. Whether status responses are received
3. Whether reported values match requested values

## Symptom: Commands Sent But Nothing Happens

### Checklist Item 1: Verify Radiod is Actually Receiving Commands

**Test:**
```bash
# On the radiod host, monitor network traffic
sudo tcpdump -i any -n port 5006
```

**Expected:** You should see UDP packets when tune commands are sent.

**If you don't see packets:**
- Check firewall rules
- Verify radiod control port (default 5006)
- Check network routing

### Checklist Item 2: Verify Radiod is Processing Commands

**Test:**
Check radiod logs for command processing:

```bash
# On radiod host
journalctl -u radiod -f
# or
tail -f /var/log/radiod.log
```

**Expected:** Log entries when commands are received:
```
Received command for SSRC 99999999
Tuning to 14.074 MHz
```

**If you don't see log entries:**
- Radiod may not be receiving packets
- Radiod may be ignoring the SSRC
- Command packet format might be incorrect

### Checklist Item 3: Verify Radiod Has Working Hardware

**Test:**
Use radiod's built-in tune command:

```bash
# On radiod host
tune -r localhost -s 99999999 -f 14.074M -m usb -v
```

**Expected:** Should show status with requested frequency.

**If this doesn't work:**
- Radiod hardware configuration is wrong
- SDR device is not connected/working
- Issue is with radiod, not ka9q-python

**If this DOES work but ka9q-python doesn't:**
- Command encoding difference (file a bug)
- Network/multicast issue
- Timing issue

### Checklist Item 4: Check Status Response is Being Received

**Test:**
Add debug output to your application:

```python
from ka9q import RadiodControl

control = RadiodControl('radiod.local')

# Add timeout handler
import logging
logging.basicConfig(level=logging.DEBUG)

try:
    status = control.tune(
        ssrc=99999999,
        frequency_hz=14.074e6,
        preset='usb',
        timeout=10.0  # Longer timeout
    )
    print(f"Status received: {status}")
except TimeoutError as e:
    print(f"Timeout: {e}")
    print("Status response was not received")
```

**Expected:** Status dict with frequency, ssrc, etc.

**If timeout occurs:**
- Multicast not working
- Status address wrong
- Firewall blocking
- Radiod not sending status

### Checklist Item 5: Verify Requested vs Reported Values

**Test:**
Run the debug tool and check the "verification" sections:

```bash
python tests/test_tune_debug.py radiod.local
```

Look for:
```
Frequency verification:
  Requested: 14.074000 MHz
  Reported:  14.074000 MHz
  Diff:      0.0 Hz
  ✓ Frequency match!
```

**If values don't match:**
- Command is being sent but not applied
- Radiod is applying it differently
- Hardware limitations
- Preset overrides settings

### Checklist Item 6: Check Command Encoding

**Test:**
Add debugging to see what's being sent:

```python
# In ka9q/control.py, in the tune() method, add:
def tune(self, ssrc, **kwargs):
    # ... existing code ...
    
    # Right before sending command
    print(f"DEBUG: Sending command buffer: {cmd_buffer.hex()}")
    print(f"DEBUG: Buffer length: {len(cmd_buffer)}")
    print(f"DEBUG: Target: {self.control_address}:{self.control_port}")
    
    self.control_sock.sendto(bytes(cmd_buffer), 
                             (self.control_address, self.control_port))
```

**Expected:** Should see hex dump of command packet.

**Compare with working tune.c:**
```bash
# Capture packets from working tune.c
sudo tcpdump -i any -n port 5006 -w working.pcap

# Run tune.c
tune -r radiod.local -s 99999999 -f 14.074M -m usb

# Analyze with wireshark or tcpdump
tcpdump -r working.pcap -X
```

### Checklist Item 7: Verify SSRC is Valid

**Problem:** Some radiod configurations restrict which SSRCs are allowed.

**Test:**
Check radiod.conf for SSRC restrictions:

```bash
# On radiod host
grep -i ssrc /etc/radio/radiod.conf
```

**Solutions:**
- Use SSRC that matches hardware (check config)
- Try different SSRC values (1-4294967295)
- Check if SSRC range is reserved

### Checklist Item 8: Check Multicast Group Membership

**Test:**
Verify your application joins the status multicast group:

```python
# Add to your application
import socket
import struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', 5006))

# Join multicast group (239.1.2.3 is common for radiod status)
mreq = struct.pack('4sL', socket.inet_aton('239.1.2.3'), socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

print("Joined multicast group, waiting for packets...")
while True:
    data, addr = sock.recvfrom(8192)
    print(f"Received {len(data)} bytes from {addr}")
```

**Expected:** Should receive status packets periodically.

**If no packets:**
- Multicast not configured on network
- Wrong multicast address
- Firewall blocking multicast
- Not on same subnet as radiod

### Checklist Item 9: Timing Issues

**Problem:** Commands sent too quickly may be lost.

**Test:**
Add delays between commands:

```python
import time

status1 = control.tune(ssrc=12345, frequency_hz=14.074e6, preset='usb')
time.sleep(1.0)  # Wait 1 second

status2 = control.tune(ssrc=12345, frequency_hz=14.076e6, preset='usb')
```

**If this helps:**
- Radiod processing delay
- Network latency
- Need to wait for hardware settling

### Checklist Item 10: Parameter Conflicts

**Problem:** Some parameters override others.

**Test scenarios:**

1. **AGC overrides gain:**
   ```python
   # This may not work as expected
   status = control.tune(ssrc=12345, frequency_hz=14.074e6, 
                        gain=10.0, agc_enable=True)  # Conflict!
   ```
   
2. **Preset overrides filter edges:**
   ```python
   # Preset 'usb' may ignore custom filter edges
   status = control.tune(ssrc=12345, frequency_hz=14.074e6,
                        preset='usb', low_edge=100, high_edge=5000)
   ```
   
3. **Try minimal parameters first:**
   ```python
   # Start with just these
   status = control.tune(ssrc=12345, frequency_hz=14.074e6, preset='usb')
   ```

## Common Issues and Solutions

### Issue: "Everything seems to work but frequency doesn't change"

**Solution Path:**

1. Run: `python tests/test_tune_debug.py radiod.local`
2. Check "Frequency verification" section
3. If diff > 1 Hz, command not being applied
4. Check radiod logs: `journalctl -u radiod -f`
5. Try with tune.c: `tune -r localhost -s 12345 -f 14.074M -m usb`
6. If tune.c works, compare packet encoding
7. If tune.c doesn't work, fix radiod configuration

### Issue: "Volume/gain changes don't work"

**Solution Path:**

1. Run debug tool, check "Gain verification" section
2. Verify AGC is disabled when setting manual gain
3. Check if hardware supports gain control
4. Some SDRs have fixed gain in certain modes
5. Try: `status = control.tune(ssrc=12345, gain=10.0, agc_enable=False)`

### Issue: "Commands work sometimes but not others"

**Possible causes:**

1. **Race condition:** Add `time.sleep(0.5)` between commands
2. **SSRC conflict:** Use unique SSRC for each channel
3. **Network congestion:** Increase timeout
4. **Radiod overload:** Reduce command rate

### Issue: "First command works, subsequent ones don't"

**Solution:**

```python
# Re-tune existing channel (same SSRC)
status1 = control.tune(ssrc=12345, frequency_hz=14.074e6, preset='usb')
time.sleep(0.5)

# Change frequency on same SSRC
status2 = control.tune(ssrc=12345, frequency_hz=14.076e6, preset='usb')
# Should update, not create new channel
```

If this doesn't work:
- Radiod may not support channel updates
- Try using different SSRC for each tune

## Testing Matrix

Run these tests to isolate the problem:

| Test | Command | What It Tests |
|------|---------|---------------|
| 1. Debug tool | `python tests/test_tune_debug.py radiod.local` | End-to-end with diagnostics |
| 2. Basic connectivity | `pytest tests/test_integration.py::TestIntegrationBasic -v` | Can connect to radiod |
| 3. Frequency change | `pytest tests/test_integration.py::TestIntegrationTuneFrequency -v` | Frequency commands work |
| 4. Gain change | `pytest tests/test_integration.py::TestIntegrationTuneGain -v` | Gain commands work |
| 5. Native tune.c | `tune -r radiod.local -s 12345 -f 14M -m usb` | Radiod itself works |

## Getting Help

When reporting issues, include:

1. **Debug tool output:**
   ```bash
   python tests/test_tune_debug.py radiod.local > debug_output.txt 2>&1
   ```

2. **Radiod logs during command:**
   ```bash
   # Start logging
   journalctl -u radiod -f > radiod_logs.txt
   # Run your application
   # Stop logging (Ctrl+C)
   ```

3. **Radiod configuration:**
   ```bash
   cat /etc/radio/radiod.conf
   ```

4. **Network test results:**
   ```bash
   # Multicast test
   ip route | grep 224
   # Packet capture
   sudo tcpdump -i any -n port 5006 -c 10
   ```

5. **Python version and dependencies:**
   ```bash
   python --version
   pip list | grep ka9q
   ```

6. **What works with tune.c vs ka9q-python:**
   - Does tune.c work? (yes/no)
   - Does ka9q-python connect? (yes/no)
   - Does ka9q-python get status? (yes/no)
   - Do values match? (yes/no)

This information will help diagnose whether the issue is:
- Network/multicast configuration
- Radiod setup
- Hardware compatibility
- Ka9q-python bug
- Application integration issue
