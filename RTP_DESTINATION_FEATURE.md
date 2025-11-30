# RTP Destination Control Feature

## Overview

This feature enables ka9q-python clients to specify custom RTP multicast destinations for individual radiod channels. Previously, channels used the default destination from radiod's configuration file. Now you can direct each channel's audio stream to a specific multicast address.

## Implementation

### New Functions

#### `encode_socket(buf, type_val, address, port=5004)`

Encodes IPv4 socket addresses in radiod's TLV format:
- **Format**: `address(4 bytes) + port(2 bytes)` = 6 bytes total
- **Parameters**:
  - `buf`: bytearray to write to
  - `type_val`: TLV type (e.g., `StatusType.OUTPUT_DATA_DEST_SOCKET`)
  - `address`: IP address as string (e.g., `"239.1.2.3"`)
  - `port`: Port number (default: 5004)
- **Returns**: Number of bytes written (8 = type + length + data)

#### `_validate_multicast_address(address)`

Validates multicast address format (IP address or hostname).

### Updated Methods

#### `create_channel(..., destination=None)`

Added optional `destination` parameter:

```python
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    destination="239.192.1.100:5004"  # NEW: Custom RTP destination
)
```

**Destination formats**:
- IP address only: `"239.1.2.3"` (uses default port 5004)
- IP with port: `"239.1.2.3:6789"`
- Hostname: `"wspr.local"` (radiod resolves or hashes to multicast address)

#### `tune(..., destination=None)`

Added optional `destination` parameter to dynamically change a channel's output:

```python
control.tune(
    ssrc=14074000,
    destination="ft8-new.local"  # Redirect existing channel
)
```

## Usage Examples

### Example 1: Create Channels with Isolated Streams

```python
from ka9q.control import RadiodControl

control = RadiodControl("radiod.local")

# WSPR on 20m → dedicated stream
control.create_channel(
    ssrc=14095600,
    frequency_hz=14.0956e6,
    preset="usb",
    sample_rate=12000,
    destination="wspr-20m.local:5004"
)

# FT8 on 20m → different stream
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    destination="ft8-20m.local:5004"
)
```

### Example 2: Dynamic Stream Switching

```python
# Start with default destination
control.create_channel(
    ssrc=7074000,
    frequency_hz=7.074e6,
    preset="usb",
    sample_rate=12000
)

# Later, redirect to a different stream
control.tune(
    ssrc=7074000,
    destination="239.192.1.50:5004"
)
```

### Example 3: Multiple Channels, One Stream (Default Behavior)

```python
# Create multiple channels without destination parameter
# They all use radiod's default stream from config file
# Demultiplexed by SSRC in RTP headers

for freq in [14.074e6, 7.074e6, 3.573e6]:
    control.create_channel(
        ssrc=int(freq),
        frequency_hz=freq,
        preset="usb",
        sample_rate=12000
        # No destination = use radiod default
    )
```

## Architecture

### Radiod's Two RTP Models

1. **Shared Stream (Config File Default)**:
   - Multiple channels → one multicast group
   - Channels differentiated by RTP SSRC
   - Example: All WSPR channels → `wspr.local`

2. **Per-Channel Streams (New Feature)**:
   - Each channel → unique multicast group
   - Full isolation between channels
   - Example: Each band → dedicated stream

### How radiod Handles Destinations

From `radio_status.c:526-533`:
```c
case OUTPUT_DATA_DEST_SOCKET:
  {
    // Actually sets both data and status, overriding port numbers
    decode_socket(&chan->output.dest_socket,cp,optlen);
    setport(&chan->output.dest_socket,DEFAULT_RTP_PORT);
    chan->status.dest_socket = chan->output.dest_socket;
    setport(&chan->status.dest_socket,DEFAULT_STAT_PORT);
  }
  break;
```

**Effect**: Setting `OUTPUT_DATA_DEST_SOCKET` updates:
- RTP data stream destination (port 5004)
- Status stream destination (port 5006, same IP)

## Socket Encoding Format

Based on radiod's `encode_socket()` and `decode_socket()` in `status.c`:

### IPv4 (6 bytes)
```
[address: 4 bytes (network order)] [port: 2 bytes (big-endian)]
```

Example for `239.1.2.3:5004`:
```
0xEF 0x01 0x02 0x03  0x13 0x8C
│                    │
└─ address           └─ port (5004 = 0x138C)
```

### Complete TLV Packet
```
[type: 1] [length: 1] [address: 4] [port: 2]
    17         6        (IP addr)    (port)
```

## Testing

Run the included test:
```bash
python3 test_socket_encoding_manual.py
```

Expected output:
```
Testing encode_socket()...

1. Testing basic IPv4 encoding with default port...
   ✓ Encoded 239.1.2.3:5004 correctly (6-byte format)

2. Testing custom port...
   ✓ Custom port 6789 encoded correctly

3. Testing roundtrip (encode -> decode)...
   ✓ Roundtrip successful: 239.192.1.100:5006

...

All tests passed! ✓
```

## Limitations

- **IPv4 only**: IPv6 not yet implemented (radiod supports it via 10-byte format)
- **No DNS resolution**: Library passes address to radiod as-is; radiod handles DNS
- **Port override**: radiod always uses RTP port 5004 and status port 5006, ignoring the encoded port for those specific streams

## Files Modified

- `ka9q/control.py`:
  - Added `encode_socket()` function
  - Added `_validate_multicast_address()` function
  - Updated `create_channel()` to accept `destination` parameter
  - Updated `tune()` to properly encode `destination` parameter

- `tests/test_encode_socket.py`: Comprehensive pytest test suite
- `test_socket_encoding_manual.py`: Standalone verification script

## Comparison: Config File vs Client Control

| Feature | Config File | Client Control (ka9q-python) |
|---------|-------------|------------------------------|
| **Batch frequency list** | ✅ `freq = "14.074 7.074 3.573"` | ❌ Loop required |
| **Per-channel destination** | ⚠️ Section-level only | ✅ Fully supported |
| **Dynamic changes** | ❌ Requires restart | ✅ Runtime via `tune()` |
| **Multiple channels, one stream** | ✅ Default behavior | ✅ Don't specify destination |
| **Multiple channels, separate streams** | ⚠️ Multiple sections | ✅ Set destination per channel |

## Summary

This implementation completes ka9q-python's support for the `OUTPUT_DATA_DEST_SOCKET` TLV command, enabling full control over where each channel's RTP stream is sent. This is critical for:

- Isolating channels to separate multicast groups
- Directing specific frequencies to dedicated decoders
- Building complex multi-channel SDR applications
- Dynamic stream routing based on propagation conditions

The feature matches radiod's protocol specification and has been tested with roundtrip encode/decode verification.
