# Native Channel Discovery Implementation

This document describes the native Python channel discovery feature that eliminates the dependency on the `control` executable from ka9q-radio.

## Overview

The ka9q-python package now includes a pure Python implementation for discovering active channels by listening directly to radiod's status multicast stream. This makes channel discovery work without requiring external executables.

## Implementation

### How It Works

1. **radiod broadcasts status packets** on a multicast address (e.g., `239.251.200.193:5006`)
2. **Each channel sends periodic updates** containing all channel parameters (SSRC, frequency, preset, sample rate, SNR, etc.)
3. **Native discovery listens** to this multicast stream for a configurable duration (default: 2 seconds)
4. **Packets are decoded** using the same TLV decoder used by the `tune()` method
5. **Channel information is collected** and returned as a dictionary

### Key Components

#### `discover_channels_native()` - Pure Python Discovery

Located in `ka9q/discovery.py`, this function:
- Creates a `RadiodControl` instance to set up multicast socket
- Joins the status multicast group
- Listens for status packets for a specified duration
- Decodes TLV-encoded status messages
- Extracts channel information (SSRC, frequency, preset, etc.)
- Returns dictionary of `{ssrc: ChannelInfo}` mappings

#### `discover_channels_via_control()` - Control Utility Fallback

The original implementation that invokes the external `control` utility. Renamed for clarity and kept as a fallback option.

#### `discover_channels()` - Smart Discovery

The main function that:
1. Tries native Python discovery first (default)
2. Falls back to control utility if native fails or finds no channels
3. Can be configured to force either method

## Usage

### Basic Discovery (Automatic)

```python
from ka9q import discover_channels

# Uses native Python by default, falls back if needed
channels = discover_channels("radiod.local")

for ssrc, info in channels.items():
    print(f"SSRC {ssrc}:")
    print(f"  Frequency: {info.frequency/1e6:.3f} MHz")
    print(f"  Preset: {info.preset}")
    print(f"  Sample Rate: {info.sample_rate} Hz")
    print(f"  SNR: {info.snr:.1f} dB")
```

### Native Python Only

```python
from ka9q import discover_channels_native

# Pure Python, no external dependencies
channels = discover_channels_native("radiod.local", listen_duration=3.0)
```

### Control Utility Only

```python
from ka9q import discover_channels_via_control

# Requires 'control' executable from ka9q-radio
channels = discover_channels_via_control("radiod.local")
```

### Force Method Selection

```python
from ka9q import discover_channels

# Force native (no fallback)
channels = discover_channels("radiod.local", use_native=True)

# Force control utility (skip native)
channels = discover_channels("radiod.local", use_native=False)
```

## Benefits

### No External Dependencies
- **Before**: Required `control` executable from ka9q-radio
- **After**: Pure Python implementation, no external tools needed

### Cross-Platform mDNS Resolution
The package uses a multi-tier approach for resolving .local hostnames:
1. **Linux**: `avahi-resolve` (if available)
2. **macOS**: `dns-sd` (if available)  
3. **Fallback**: Python's `getaddrinfo` (works everywhere)
4. **Direct IP**: Bypasses resolution entirely

This means it works on macOS, Linux, and Windows without requiring any external tools.

### Cross-Platform
- Works anywhere Python works
- No need to compile ka9q-radio tools

### Better Control
- Adjustable listen duration
- Direct access to decoded status data
- Can be integrated into async workflows

### Easier Debugging
- Python exceptions instead of subprocess errors
- Full logging of packet reception and decoding
- Can inspect raw status dictionaries

### More Reliable
- Direct protocol implementation
- No subprocess overhead
- Consistent behavior across platforms

## Technical Details

### Protocol Compatibility

Uses the same TLV decoding as the `tune()` method:
- Status packets have type byte = 0
- Fields are decoded according to `StatusType` enum
- Handles variable-length integers, floats, doubles, strings, and sockets

### Socket Configuration

- Joins multicast group using `IP_ADD_MEMBERSHIP`
- Uses `select()` for non-blocking packet reception
- Configurable timeout (default: 100ms poll interval)
- Properly closes sockets after discovery

### Decoded Fields

Each `ChannelInfo` contains:
- `ssrc` - Channel SSRC identifier
- `frequency` - Radio frequency in Hz
- `preset` - Mode/preset name (e.g., "usb", "iq")
- `sample_rate` - Sample rate in Hz
- `snr` - Signal-to-noise ratio in dB
- `multicast_address` - Output destination address
- `port` - Output destination port

### Performance

- Default 2-second listen captures most channels
- Channels broadcast status ~1-2 times per second
- Minimal CPU usage (event-driven with select)
- Memory efficient (processes packets as received)

## Configuration

### Listen Duration

```python
# Quick scan (may miss some channels)
channels = discover_channels("radiod.local", listen_duration=1.0)

# Longer scan (more thorough)
channels = discover_channels("radiod.local", listen_duration=5.0)

# Custom duration
channels = discover_channels_native("radiod.local", listen_duration=10.0)
```

### Fallback Behavior

```python
# Default: try native, fall back to control
channels = discover_channels("radiod.local")

# Native only: raise exception if it fails
try:
    channels = discover_channels_native("radiod.local")
except Exception as e:
    print(f"Discovery failed: {e}")

# Control only: skip native completely
channels = discover_channels("radiod.local", use_native=False)
```

## Example Output

```
INFO: Discovering channels via native Python listener from radiod.local
INFO: Listening for 2.0 seconds...
DEBUG: Received 312 bytes from ('239.251.200.193', 5006)
DEBUG: Discovered channel: SSRC=14074000, freq=14.074 MHz, rate=12000 Hz, preset=usb
DEBUG: Received 298 bytes from ('239.251.200.193', 5006)
DEBUG: Discovered channel: SSRC=7040000, freq=7.040 MHz, rate=12000 Hz, preset=lsb
INFO: Discovered 2 channels from 47 packets
```

## Compatibility

### Backwards Compatible
- Default `discover_channels()` behavior unchanged
- Old code continues to work without modification
- Control utility fallback ensures reliability

### New Features Available
- `discover_channels_native()` for pure Python
- `discover_channels_via_control()` explicitly named
- `use_native` parameter for method selection
- `listen_duration` parameter for tuning

## Testing

Run the discovery example:

```bash
python examples/discover_example.py
```

This demonstrates all three methods:
1. Automatic discovery (native with fallback)
2. Native Python only
3. Control utility only

## Troubleshooting

### No Channels Found

**Possible causes:**
- radiod not running
- radiod not broadcasting to expected multicast address
- Network firewall blocking multicast
- Listen duration too short

**Solutions:**
```python
# Try longer listen duration
channels = discover_channels("radiod.local", listen_duration=5.0)

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
channels = discover_channels("radiod.local")
```

### Multicast Not Working

**Check:**
1. Multicast routing enabled on network interfaces
2. Firewall allows multicast traffic
3. Correct multicast address for your radiod instance

**Test with control utility:**
```bash
control -v radiod.local
```

If control works but native doesn't, please file an issue.

## Future Enhancements

Potential improvements:
1. Async/await version using `asyncio`
2. Streaming discovery (continuous updates)
3. Channel change notifications
4. Better multicast interface selection
5. IPv6 support

## References

- `ka9q/discovery.py` - Implementation
- `ka9q/control.py` - TLV decoder used for status packets
- `examples/discover_example.py` - Usage examples
- `README.md` - User documentation
