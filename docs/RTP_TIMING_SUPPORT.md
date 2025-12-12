# RTP Timing Support

## Overview

ka9q-python v2.4.0+ now decodes and exposes the timing fields `GPS_TIME` and `RTP_TIMESNAP` from radiod status packets, enabling precise RTP timestamp-to-wall-clock synchronization.

## Background

### The Problem

RTP packets contain timestamps that increment based on the sample rate (e.g., for 48 kHz audio, the timestamp increments by 48,000 per second). However, these timestamps don't directly correspond to wall-clock time—they're just relative counters.

To record RTP streams with accurate timestamps, you need to know:
1. What wall-clock time corresponds to a specific RTP timestamp
2. The sample rate to convert between RTP timestamps and time

### How radiod Solves This

radiod periodically sends two timing fields in its status packets:

- **`GPS_TIME`** (type 3): GPS nanoseconds since GPS epoch when the snapshot was taken
- **`RTP_TIMESNAP`** (type 8): The RTP timestamp value at that exact GPS time

This is the same mechanism used by radiod's `pcmrecord.c` utility.

## Using the Timing Fields

### Discovery

The timing fields are automatically captured during channel discovery:

```python
from ka9q import discover_channels

channels = discover_channels("radiod.local")

for ssrc, channel in channels.items():
    print(f"Channel {ssrc}:")
    print(f"  GPS Time:     {channel.gps_time} ns")
    print(f"  RTP Timesnap: {channel.rtp_timesnap}")
    print(f"  Sample Rate:  {channel.sample_rate} Hz")
```

### Converting RTP Timestamp to Wall Clock

Use this formula (from `pcmrecord.c`):

```python
import time

def rtp_to_wallclock(rtp_timestamp, channel):
    """
    Convert RTP timestamp to Unix wall-clock time
    
    Args:
        rtp_timestamp: RTP timestamp from packet header
        channel: ChannelInfo with gps_time, rtp_timesnap, sample_rate
    
    Returns:
        Unix timestamp (seconds since 1970-01-01 00:00:00 UTC)
    """
    # Constants from radiod
    GPS_UTC_OFFSET = 315964800  # GPS epoch (1980-01-06) - Unix epoch (1970-01-01)
    UNIX_EPOCH = 2208988800     # Unix epoch in NTP seconds
    BILLION = 1_000_000_000
    
    # Convert GPS nanoseconds to Unix time
    sender_time = channel.gps_time + BILLION * GPS_UTC_OFFSET
    
    # Add offset from RTP timestamp difference
    rtp_delta = int(rtp_timestamp) - int(channel.rtp_timesnap)
    time_offset = BILLION * rtp_delta // channel.sample_rate
    
    wall_time_ns = sender_time + time_offset
    
    # Convert to Unix seconds
    return wall_time_ns / BILLION


# Example usage with RTP packet
from ka9q.rtp import parse_rtp_header

data = receive_rtp_packet()
rtp_header = parse_rtp_header(data)

timestamp = rtp_to_wallclock(rtp_header.timestamp, channel)
print(f"Packet received at: {time.ctime(timestamp)}")
```

### Status Decoder

The timing fields are also available when listening to status packets directly:

```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")

# Poll for status
status = control.poll_status(ssrc=14074000)

if 'gps_time' in status and 'rtp_timesnap' in status:
    print(f"GPS Time: {status['gps_time']} ns")
    print(f"RTP Timesnap: {status['rtp_timesnap']}")
    print(f"Sample Rate: {status['sample_rate']} Hz")
else:
    print("Timing fields not available")
```

## Implementation Details

### Status Packet Decoding

The `_decode_status_response()` method in `RadiodControl` now handles:

```python
elif type_val == StatusType.GPS_TIME:
    status['gps_time'] = decode_int64(data, optlen)
elif type_val == StatusType.RTP_TIMESNAP:
    status['rtp_timesnap'] = decode_int32(data, optlen)
```

### ChannelInfo

The `ChannelInfo` dataclass includes optional timing fields:

```python
@dataclass
class ChannelInfo:
    ssrc: int
    preset: str
    sample_rate: int
    frequency: float
    snr: float
    multicast_address: str
    port: int
    gps_time: Optional[int] = None        # GPS nanoseconds
    rtp_timesnap: Optional[int] = None    # RTP timestamp at GPS_TIME
```

## Example: Recording with Timestamps

See `examples/test_timing_fields.py` for a complete example of capturing and displaying timing information.

## References

### radiod Sources

- `ka9q-radio/radio.h` - GPS_TIME field (type 3)
- `ka9q-radio/status.h` - RTP_TIMESNAP field (type 8)
- `ka9q-radio/pcmrecord.c` - Reference implementation of RTP timing
- `ka9q-radio/radiod.c` - Status packet generation

### Formula from pcmrecord.c

```c
// Compute wall time for any RTP packet:
int64_t sender_time = sp->chan.clocktime + (int64_t)BILLION * (UNIX_EPOCH - GPS_UTC_OFFSET);
sender_time += (int64_t)BILLION * (int32_t)(rtp.timestamp - sp->chan.output.time_snap) / sp->samprate;
```

Where:
- `clocktime` = GPS_TIME (GPS nanoseconds)
- `time_snap` = RTP_TIMESNAP (RTP timestamp when GPS_TIME was captured)
- `samprate` = OUTPUT_SAMPRATE (channel sample rate)

## Version History

- **v2.4.0** - Added GPS_TIME and RTP_TIMESNAP decoding
  - `decode_int64()` function for 64-bit GPS time
  - Status decoder updated to capture both fields
  - `ChannelInfo` extended with optional timing fields
  - Example test script added
