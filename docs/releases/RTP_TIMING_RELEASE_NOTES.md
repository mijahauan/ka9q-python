# RTP Timing & Generic Recorder - Release Notes

**Date:** November 30, 2025  
**Commit:** 090f98c  
**Status:** ✅ Complete and Pushed

---

## Summary

Added comprehensive RTP timing support and a generic RTP recorder to ka9q-python, enabling precise timestamp synchronization and robust packet recording with automatic error recovery.

---

## What Was Added

### 1. RTP Timing Support

**GPS_TIME and RTP_TIMESNAP Parsing:**
- `decode_int64()` - Decode 64-bit GPS timestamps
- Extended `_decode_status_response()` to capture timing fields
- Added to `ChannelInfo` as optional fields

**Files Modified:**
- `ka9q/control.py` - Added GPS_TIME/RTP_TIMESNAP decoding
- `ka9q/discovery.py` - Extended ChannelInfo dataclass

### 2. Generic RTP Recorder

**New File:** `ka9q/rtp_recorder.py` (440 lines)

**Features:**
- ✅ State machine (IDLE → ARMED → RECORDING → RESYNC)
- ✅ RTP header parsing (RFC 3550)
- ✅ Sequence number validation
- ✅ Automatic resynchronization
- ✅ Comprehensive metrics tracking
- ✅ Callback architecture
- ✅ Precise timing conversion

**Key Components:**
- `RTPRecorder` class - Main recorder with state machine
- `parse_rtp_header()` - Parse RTP packets
- `rtp_to_wallclock()` - Convert RTP timestamps to Unix time
- `RecorderState` enum - State machine states
- `RTPHeader` named tuple - Parsed packet header
- `RecordingMetrics` dataclass - Session metrics

### 3. Examples

**New Files:**
- `examples/test_timing_fields.py` - Verify timing field capture
- `examples/rtp_recorder_example.py` - Complete recorder demo

### 4. Documentation

**New Files:**
- `docs/RTP_TIMING_SUPPORT.md` - User guide with examples
- `docs/RTP_TIMING_IMPLEMENTATION.md` - Technical details

**Updated Files:**
- `docs/API_REFERENCE.md` - Added complete RTP Recording section
- `README.md` - Added recorder examples and features
- `IMPLEMENTATION_STATUS.md` - Added v2.4.0 features
- `ka9q/__init__.py` - Exported new classes and functions

---

## API Changes

### New Exports

```python
from ka9q import (
    RTPRecorder,       # Generic recorder class
    RecorderState,     # State machine enum
    RTPHeader,         # Parsed RTP header
    RecordingMetrics,  # Recording statistics
    parse_rtp_header,  # Parse RTP packets
    rtp_to_wallclock   # Timestamp conversion
)
```

### Extended ChannelInfo

```python
@dataclass
class ChannelInfo:
    # ... existing fields ...
    gps_time: Optional[int] = None        # GPS nanoseconds
    rtp_timesnap: Optional[int] = None    # RTP timestamp at GPS_TIME
```

---

## Usage Example

```python
from ka9q import discover_channels, RTPRecorder
import time

# Get channel with timing info
channels = discover_channels("radiod.local")
channel = channels[14074000]

# Define packet handler
def handle_packet(header, payload, wallclock):
    print(f"Packet at {wallclock}: {len(payload)} bytes")

# Create and start recorder
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
recorder.start()
recorder.start_recording()
time.sleep(60)
recorder.stop_recording()
recorder.stop()

# Get metrics
metrics = recorder.get_metrics()
print(f"Packets received: {metrics['packets_received']}")
```

---

## Backward Compatibility

✅ **100% backward compatible**

- Timing fields are optional in `ChannelInfo`
- All existing code continues to work unchanged
- New functionality is opt-in

---

## Files Changed

### Core Library (6 files modified, 1 new)
- `ka9q/__init__.py` - Exported new classes
- `ka9q/control.py` - Added timing decoders
- `ka9q/discovery.py` - Extended ChannelInfo
- `ka9q/rtp_recorder.py` - **NEW** Generic recorder

### Examples (2 new)
- `examples/test_timing_fields.py` - **NEW**
- `examples/rtp_recorder_example.py` - **NEW**

### Documentation (2 new, 3 updated)
- `docs/RTP_TIMING_SUPPORT.md` - **NEW** User guide
- `docs/RTP_TIMING_IMPLEMENTATION.md` - **NEW** Technical details
- `docs/API_REFERENCE.md` - Added RTP Recording section
- `README.md` - Added recorder examples
- `IMPLEMENTATION_STATUS.md` - Added v2.4.0 features

**Total:** 11 files changed, 1,803 insertions(+), 15 deletions(-)

---

## Testing

### Verify Timing Fields
```bash
python examples/test_timing_fields.py radiod.local
```

### Test RTP Recorder
```bash
python examples/rtp_recorder_example.py radiod.local 14074000 30
```

---

## Technical Details

### Timing Formula

Based on `ka9q-radio/pcmrecord.c`:

```python
wall_time = gps_time + (rtp_timestamp - rtp_timesnap) / sample_rate
```

Where:
- `gps_time` - GPS nanoseconds when RTP_TIMESNAP was captured
- `rtp_timesnap` - RTP timestamp at that moment
- `rtp_timestamp` - Current packet's RTP timestamp
- `sample_rate` - Channel sample rate

### State Machine

```
        start()           start_recording()
IDLE ──────────> ARMED ──────────────────> RECORDING
  ^                ^                            │
  │                │                            │ (gap > threshold)
  │                │                            v
  └── stop() ──────┴────── stop_recording() ─ RESYNC
                                                 │
                                                 │ (N good packets)
                                                 └──────> RECORDING
```

### Constants from radiod

```c
GPS_UTC_OFFSET = 315964800  // GPS epoch - Unix epoch
UNIX_EPOCH = 2208988800     // Unix epoch in NTP seconds
```

---

## References

### ka9q-radio Sources
- `ka9q-radio/radio.h` - GPS_TIME definition (type 3)
- `ka9q-radio/status.h` - RTP_TIMESNAP definition (type 8)
- `ka9q-radio/pcmrecord.c` - Reference timing implementation
- `ka9q-radio/radiod.c` - Status packet generation

### Standards
- RFC 3550 - RTP: A Transport Protocol for Real-Time Applications

---

## Next Steps

This implementation provides the foundation for:

1. **WSPR Recorder** - 2-minute interval recording
2. **FT8 Recorder** - 15-second interval recording
3. **General Audio Recorder** - Continuous recording
4. **Signal Analysis Tools** - Real-time processing

All can use the same `RTPRecorder` base with application-specific callbacks.

---

## Commit Message

```
Add RTP timing support and generic recorder

Features:
- GPS_TIME and RTP_TIMESNAP parsing from radiod status packets
- decode_int64() for 64-bit GPS timestamps
- Extended ChannelInfo with optional timing fields

Generic RTP Recorder:
- RTPRecorder class with callback architecture
- State machine: IDLE → ARMED → RECORDING → RESYNC
- Automatic resynchronization on packet loss
- Comprehensive metrics tracking
- RTP header parsing (RFC 3550)
- Sequence number validation
- Timestamp jump detection
- parse_rtp_header() and rtp_to_wallclock() utilities

Examples:
- test_timing_fields.py - Verify timing field capture
- rtp_recorder_example.py - Complete recorder demonstration

Documentation:
- RTP_TIMING_SUPPORT.md - User guide with examples
- RTP_TIMING_IMPLEMENTATION.md - Technical details
- Updated API_REFERENCE.md with full RTP section
- Updated README.md with recorder examples
- Updated IMPLEMENTATION_STATUS.md with new features

Based on timing mechanism from ka9q-radio/pcmrecord.c
Fully backward compatible - timing fields are optional
```

---

## Status

✅ **Complete and Pushed**

- Commit: 090f98c
- Branch: main
- Remote: origin/main
- All files committed and pushed successfully
