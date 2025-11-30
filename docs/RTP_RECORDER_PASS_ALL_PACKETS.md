# RTP Recorder Pass-All-Packets Mode

**Feature:** External packet resequencing support in `RTPRecorder`  
**Version:** v2.5.0  
**Date:** November 30, 2025

---

## Overview

The `RTPRecorder` class now supports external packet resequencing through the `pass_all_packets` parameter. This allows applications with specialized packet buffering and ordering requirements to receive all RTP packets directly, bypassing the built-in resequencing logic.

### Key Capabilities

✅ **Pass all packets** to callback (except wrong SSRC)  
✅ **Bypass resync state** - stay in RECORDING continuously  
✅ **Track metrics** - sequence errors, drops, timestamp jumps still recorded  
✅ **Backward compatible** - defaults to original behavior  
✅ **Application control** - delegate ordering to external resequencers

---

## Motivation

### Problem Statement

The original `RTPRecorder` includes built-in packet validation and resequencing:
- Drops packets during RESYNC state
- Triggers RESYNC on large sequence gaps
- May not match specialized application buffering needs

Some applications need:
- Custom packet buffering strategies
- External resequencing with jitter handling
- Multi-stream synchronization
- Research-specific ordering requirements

### Solution

Add `pass_all_packets` parameter to bypass internal resequencing while preserving metrics tracking:

```python
recorder = RTPRecorder(
    channel=channel,
    on_packet=external_resequencer.add_packet,
    pass_all_packets=True  # NEW
)
```

---

## API Reference

### Constructor Parameter

```python
RTPRecorder(
    channel: ChannelInfo,
    on_packet: Optional[Callable[[RTPHeader, bytes, float], None]] = None,
    on_state_change: Optional[Callable[[RecorderState, RecorderState], None]] = None,
    on_recording_start: Optional[Callable[[], None]] = None,
    on_recording_stop: Optional[Callable[[RecordingMetrics], None]] = None,
    max_packet_gap: int = 10,
    resync_threshold: int = 5,
    pass_all_packets: bool = False  # NEW
)
```

**Parameter: `pass_all_packets`**

| Attribute | Value |
|-----------|-------|
| Type | `bool` |
| Default | `False` |
| Purpose | Pass ALL packets to callback regardless of sequence errors |

**Behavior:**
- `False` (default): Original behavior with internal resequencing
- `True`: Pass all packets to callback, bypass resync state machine

**When `pass_all_packets=True`:**
- All packets delivered to `on_packet` callback (except wrong SSRC)
- No RESYNC state transitions on sequence gaps
- `max_packet_gap` parameter ignored
- Metrics continue tracking errors
- Stays in RECORDING state continuously

**When `pass_all_packets=False`:**
- Original behavior preserved
- Internal validation and resequencing
- RESYNC state on large gaps
- `max_packet_gap` enforced

---

## Usage Examples

### Example 1: Default Mode (Internal Resequencing)

```python
from ka9q import RTPRecorder, discover_channels

channels = discover_channels("radiod.local")
channel = channels[14074000]

def handle_packet(header, payload, wallclock):
    print(f"Sequence {header.sequence}: {len(payload)} bytes")

# Default: internal resequencing
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
recorder.start()
recorder.start_recording()

# Packets are validated and resequenced internally
# Large sequence gaps trigger RESYNC state
# Packets dropped during RESYNC
```

### Example 2: External Resequencer

```python
from ka9q import RTPRecorder, discover_channels
import time

class PacketResequencer:
    """Custom packet resequencer with buffering"""
    
    def __init__(self, buffer_size=100):
        self.buffer = {}
        self.buffer_size = buffer_size
        self.next_sequence = None
    
    def add_packet(self, header, payload, wallclock):
        """Called for EVERY packet"""
        # Store in buffer
        self.buffer[header.sequence] = (payload, wallclock)
        
        # Initialize next expected sequence
        if self.next_sequence is None:
            self.next_sequence = header.sequence
        
        # Process sequential packets
        while self.next_sequence in self.buffer:
            payload, wallclock = self.buffer.pop(self.next_sequence)
            self.process_packet(self.next_sequence, payload, wallclock)
            self.next_sequence = (self.next_sequence + 1) & 0xFFFF
        
        # Limit buffer size (handle persistent gaps)
        if len(self.buffer) > self.buffer_size:
            # Skip to newest packet
            self.next_sequence = max(self.buffer.keys())
    
    def process_packet(self, sequence, payload, wallclock):
        """Process ordered packet"""
        print(f"Processing sequence {sequence}: {len(payload)} bytes")

# Create resequencer
resequencer = PacketResequencer()

channels = discover_channels("radiod.local")
channel = channels[14074000]

# Pass all packets to external resequencer
recorder = RTPRecorder(
    channel=channel,
    on_packet=resequencer.add_packet,
    pass_all_packets=True  # ALL packets delivered
)

recorder.start()
recorder.start_recording()
time.sleep(60)

# Check metrics (still tracked!)
metrics = recorder.get_metrics()
print(f"Sequence errors: {metrics['sequence_errors']}")
print(f"Packets dropped: {metrics['packets_dropped']}")
```

### Example 3: Signal-Recorder Integration

```python
from ka9q import RTPRecorder, discover_channels

class SignalRecorder:
    """Application with external PacketResequencer"""
    
    def __init__(self):
        self.packet_resequencer = PacketResequencer()
    
    def setup_rtp_recorder(self, channel):
        """Setup RTPRecorder with pass-all mode"""
        self.rtp_recorder = RTPRecorder(
            channel=channel,
            on_packet=self._handle_packet,
            pass_all_packets=True  # Let PacketResequencer handle ordering
        )
    
    def _handle_packet(self, header, payload, wallclock):
        """Receive ALL packets from RTPRecorder"""
        # Pass to external resequencer
        self.packet_resequencer.add_packet(header, payload, wallclock)
    
    def start(self):
        self.rtp_recorder.start()
        self.rtp_recorder.start_recording()

# Usage
recorder = SignalRecorder()
channels = discover_channels("radiod.local")
recorder.setup_rtp_recorder(channels[14074000])
recorder.start()
```

---

## Implementation Details

### Code Changes

#### File: `ka9q/rtp_recorder.py`

**Change 1: Constructor**

```python
def __init__(
    self,
    channel: ChannelInfo,
    on_packet: Optional[Callable[[RTPHeader, bytes, float], None]] = None,
    on_state_change: Optional[Callable[[RecorderState, RecorderState], None]] = None,
    on_recording_start: Optional[Callable[[], None]] = None,
    on_recording_stop: Optional[Callable[[RecordingMetrics], None]] = None,
    max_packet_gap: int = 10,
    resync_threshold: int = 5,
    pass_all_packets: bool = False  # NEW parameter
):
    # ... existing code ...
    
    self.max_packet_gap = max_packet_gap
    self.resync_threshold = resync_threshold
    self.pass_all_packets = pass_all_packets  # Store flag
```

**Change 2: Validation Logic**

```python
def _validate_packet(self, header: RTPHeader) -> bool:
    """
    Validate RTP packet and update state
    
    Returns:
        True if packet should be processed, False if dropped
    """
    # Check SSRC - always filter wrong SSRC
    if header.ssrc != self.channel.ssrc:
        return False
    
    # ... sequence and timestamp validation (metrics tracked) ...
    
    # In pass_all mode, don't trigger resync - just log and continue
    if seq_gap > self.max_packet_gap:
        self.metrics.sequence_errors += 1
        if not self.pass_all_packets:
            # Trigger resync if recording
            if self.state == RecorderState.RECORDING:
                self._change_state(RecorderState.RESYNC)
                return False
    
    # In pass_all mode, skip resync state handling - always deliver
    if self.pass_all_packets:
        return True
    
    # Handle resync state (original behavior)
    if self.state == RecorderState.RESYNC:
        # ... resync logic ...
```

### State Machine Behavior

#### Default Mode (`pass_all_packets=False`)

```
IDLE → ARMED → RECORDING → RESYNC → RECORDING
                    ↓
                  ARMED → IDLE
```

**RESYNC triggered on:**
- Sequence gap > `max_packet_gap`
- Packets dropped during RESYNC
- Returns to RECORDING after `resync_threshold` good packets

#### Pass-All Mode (`pass_all_packets=True`)

```
IDLE → ARMED → RECORDING
                    ↓
                  ARMED → IDLE
```

**No RESYNC state:**
- Sequence gaps logged but don't trigger state change
- All packets delivered continuously
- Application handles ordering

---

## Metrics Tracking

Metrics are tracked **in both modes**:

```python
# Get metrics
metrics = recorder.get_metrics()

# Available metrics (tracked regardless of pass_all_packets):
{
    'packets_received': 12000,
    'packets_dropped': 5,        # Based on sequence gaps
    'packets_out_of_order': 0,
    'bytes_received': 3840000,
    'sequence_errors': 2,        # Large gaps detected
    'timestamp_jumps': 0,
    'state_changes': 2,
    'recording_duration': 60.0
}
```

**In pass-all mode:**
- `sequence_errors`: Number of large gaps (> `max_packet_gap`)
- `packets_dropped`: Estimated from sequence gaps
- `timestamp_jumps`: Timestamp discontinuities detected
- All metrics available for monitoring health

---

## Design Rationale

### Why This Approach?

1. **Separation of concerns**: RTPRecorder handles network I/O, application handles ordering
2. **Flexibility**: Applications can implement custom buffering strategies
3. **Observability**: Metrics still tracked for monitoring
4. **Backward compatibility**: Default behavior unchanged
5. **Simplicity**: Single boolean flag, clear semantics

### Alternatives Considered

❌ **Subclassing**: More complex, harder to maintain  
❌ **Separate class**: Duplicates network/timing logic  
❌ **Callback filtering**: Less clear, more complex API  
✅ **Boolean flag**: Simple, clear, backward compatible

---

## Testing

### Test Cases

```python
import unittest
from ka9q import RTPRecorder, ChannelInfo, RTPHeader

class TestPassAllPackets(unittest.TestCase):
    
    def test_default_mode_drops_during_resync(self):
        """Default mode: packets dropped in RESYNC state"""
        # Create recorder with default settings
        recorder = RTPRecorder(channel=channel)
        # Simulate large gap → RESYNC → drops packets
        # ...
    
    def test_pass_all_mode_delivers_all_packets(self):
        """Pass-all mode: all packets delivered"""
        packets_received = []
        
        def callback(header, payload, wallclock):
            packets_received.append(header.sequence)
        
        recorder = RTPRecorder(
            channel=channel,
            on_packet=callback,
            pass_all_packets=True
        )
        
        # Simulate packets with gaps
        # Assert all packets delivered to callback
        # ...
    
    def test_metrics_tracked_in_pass_all_mode(self):
        """Metrics tracked even in pass-all mode"""
        recorder = RTPRecorder(
            channel=channel,
            pass_all_packets=True
        )
        
        # Simulate sequence gaps
        metrics = recorder.get_metrics()
        assert metrics['sequence_errors'] > 0
        assert metrics['packets_dropped'] > 0
```

---

## Migration Guide

### Existing Code (No Changes Needed)

```python
# This code continues to work identically in v2.5.0
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
```

### Adopting External Resequencing

```python
# Before (v2.4.0 and earlier)
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
# Packets may be dropped during RESYNC

# After (v2.5.0+) - with external resequencer
recorder = RTPRecorder(
    channel=channel,
    on_packet=my_resequencer.add_packet,
    pass_all_packets=True
)
# All packets delivered, resequencer handles ordering
```

---

## Performance Considerations

### Pass-All Mode Benefits
- **Lower latency**: No RESYNC delays
- **Simpler state machine**: Fewer transitions
- **Predictable**: All packets delivered

### Pass-All Mode Costs
- **Application complexity**: Must implement resequencing
- **Memory**: External buffer required
- **CPU**: Application handles ordering logic

**Recommendation:** Use pass-all mode only when you have specific resequencing requirements. Default mode works well for most use cases.

---

## Best Practices

### When to Use Pass-All Mode

✅ **Use when:**
- You have a specialized packet resequencer
- Custom jitter handling is required
- Multi-stream synchronization needed
- Research applications with specific ordering requirements

❌ **Don't use when:**
- Simple recording is sufficient
- You don't want to handle packet ordering
- Memory/CPU constraints exist

### Example Best Practice

```python
class RobustRecorder:
    """Recorder with external resequencing and overflow handling"""
    
    def __init__(self, channel, max_buffer_size=1000):
        self.buffer = {}
        self.max_buffer_size = max_buffer_size
        self.overflow_count = 0
        
        self.recorder = RTPRecorder(
            channel=channel,
            on_packet=self.add_packet,
            pass_all_packets=True
        )
    
    def add_packet(self, header, payload, wallclock):
        # Check buffer overflow
        if len(self.buffer) >= self.max_buffer_size:
            self.overflow_count += 1
            self.handle_overflow()
        
        # Add to buffer
        self.buffer[header.sequence] = (payload, wallclock)
        self.process_buffer()
    
    def handle_overflow(self):
        """Handle buffer overflow gracefully"""
        # Skip to most recent packet
        if self.buffer:
            newest = max(self.buffer.keys())
            self.buffer.clear()
            logging.warning(f"Buffer overflow, skipping to {newest}")
```

---

## See Also

- [API Reference](API_REFERENCE.md) - Complete API documentation
- [RTP Timing Support](RTP_TIMING_SUPPORT.md) - Timing and synchronization
- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [Architecture](ARCHITECTURE.md) - Library design

---

**Version:** v2.5.0  
**Author:** ka9q-python contributors  
**License:** MIT
