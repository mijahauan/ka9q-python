# RTP Timing Support

## Overview

`ka9q-python` decodes the `GPS_TIME` and `RTP_TIMESNAP` fields that radiod publishes in its status stream. Together they let you convert any RTP timestamp in a packet header into a sample-accurate Unix wallclock time — the same calculation `pcmrecord.c` uses in ka9q-radio.

The helper `rtp_to_wallclock()` is exported from the top-level `ka9q` package; you rarely need to implement the formula yourself.

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

Use the exported `rtp_to_wallclock()` helper:

```python
import time
from ka9q import discover_channels, parse_rtp_header, rtp_to_wallclock

channels = discover_channels("radiod.local")
channel = channels[14074000]

data = receive_rtp_packet()                  # your socket read
hdr  = parse_rtp_header(data)

wall = rtp_to_wallclock(hdr.timestamp, channel)
print(f"Packet received at: {time.ctime(wall)}")
```

`RTPRecorder` passes this wallclock value into its `on_packet` callback automatically, so most users never call the helper directly:

```python
from ka9q import RTPRecorder

def handle(hdr, payload, wallclock):
    ...

recorder = RTPRecorder(channel=channel, on_packet=handle)
```

### Typed status

When you want to read the timing fields out of a status packet directly (rather than at discovery time), use `decode_status_packet()`:

```python
from ka9q import decode_status_packet

status = decode_status_packet(raw_bytes)   # raw_bytes from the status multicast
print(status.ssrc, status.frequency, status.sample_rate)
# gps_time / rtp_timesnap are also available as typed fields on ChannelStatus
```

See [API_REFERENCE.md](API_REFERENCE.md) for the full `ChannelStatus` field list.

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

