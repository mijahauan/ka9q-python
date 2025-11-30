# GitHub Release for v2.5.0

## Release Summary

**Tag:** v2.5.0  
**Title:** Release v2.5.0: RTP Recorder External Resequencing Support  
**Date:** November 30, 2025

### Key Feature

**RTP Recorder Pass-All-Packets Mode**
- New `pass_all_packets` parameter in `RTPRecorder`
- Bypass internal packet resequencing for external handlers
- Metrics continue tracking errors for monitoring
- Designed for applications with custom packet resequencers

### Statistics

- **1 file changed** (`ka9q/rtp_recorder.py`)
- **~40 lines modified**
- Full backward compatibility maintained

---

## Release Description (for GitHub UI)

If editing the release on GitHub, use this description:

---

# Release v2.5.0: RTP Recorder External Resequencing Support

**Release Date:** November 30, 2025  
**Type:** Feature Enhancement  
**Compatibility:** Fully backward compatible with v2.4.0

---

## 🎯 What's New

### External Resequencing Support

The `RTPRecorder` class now supports external packet resequencing through the new `pass_all_packets` parameter:

```python
from ka9q import RTPRecorder, discover_channels

channels = discover_channels("radiod.local")
channel = channels[14074000]

# Create recorder with external resequencing mode
recorder = RTPRecorder(
    channel=channel,
    on_packet=my_packet_handler,
    pass_all_packets=True  # NEW: Pass all packets to callback
)

# Now ALL packets are delivered to callback, regardless of sequence gaps
# Your application handles packet ordering and buffering
```

**Key Benefits:**
- 🔄 Delegate packet ordering to specialized external resequencers
- 📊 Metrics still track sequence errors, drops, and timestamp jumps
- ⚡ No internal resync state transitions
- 🎯 Perfect for applications like signal-recorder with custom buffering

**How It Works:**
- When `pass_all_packets=True`:
  - All packets (except wrong SSRC) are passed to `on_packet` callback
  - No resync state transitions on sequence gaps
  - `max_packet_gap` parameter is ignored
  - Metrics continue tracking errors for monitoring
  - Stays in RECORDING state continuously

- When `pass_all_packets=False` (default):
  - Original behavior preserved
  - Internal packet validation and resequencing
  - Automatic resync on large sequence gaps

---

## 📦 Installation

```bash
pip install git+https://github.com/mijahauan/ka9q-python.git@v2.5.0
```

Or upgrade existing installation:

```bash
pip install --upgrade git+https://github.com/mijahauan/ka9q-python.git@v2.5.0
```

---

## 🚀 Quick Start

### Basic Usage (Default Behavior)

```python
from ka9q import RTPRecorder, discover_channels

channels = discover_channels("radiod.local")
channel = channels[14074000]

def handle_packet(header, payload, wallclock):
    print(f"Packet {header.sequence}: {len(payload)} bytes")

# Default mode - internal resequencing and validation
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
recorder.start()
recorder.start_recording()
```

### External Resequencing Mode

```python
from ka9q import RTPRecorder, discover_channels

channels = discover_channels("radiod.local")
channel = channels[14074000]

class MyResequencer:
    def add_packet(self, header, payload, wallclock):
        # Your custom packet buffering and reordering logic
        self.buffer[header.sequence] = (payload, wallclock)
        self.process_buffer()

resequencer = MyResequencer()

# Pass all packets to external resequencer
recorder = RTPRecorder(
    channel=channel,
    on_packet=resequencer.add_packet,
    pass_all_packets=True  # Bypass internal resequencing
)

recorder.start()
recorder.start_recording()

# Monitor metrics while resequencer handles ordering
metrics = recorder.get_metrics()
print(f"Sequence errors: {metrics['sequence_errors']}")
print(f"Packets dropped: {metrics['packets_dropped']}")
```

---

## 🔧 Implementation Details

### Code Changes

**File Modified:** `ka9q/rtp_recorder.py`

**Changes to `__init__`:**
- Added `pass_all_packets: bool = False` parameter
- Updated docstring with usage guidance
- Stored `self.pass_all_packets` instance variable

**Changes to `_validate_packet`:**
- Added conditional resync triggering based on `pass_all_packets` flag
- Early return when `pass_all_packets=True` to bypass resync state handling
- Metrics tracking preserved in all modes
- Comments clarified for pass-all behavior

### Behavior Comparison

| Feature | `pass_all_packets=False` (Default) | `pass_all_packets=True` |
|---------|-----------------------------------|-------------------------|
| Packet delivery | Only in-sequence packets | All packets (except wrong SSRC) |
| Resync on gaps | Yes, triggers RESYNC state | No, stays in RECORDING |
| Metrics tracking | Yes | Yes |
| Use case | General-purpose recording | External resequencing |

---

## 📝 Documentation

**Updated Documentation:**
- [API Reference](../API_REFERENCE.md) - Added `pass_all_packets` parameter
- [CHANGELOG.md](../../CHANGELOG.md) - Complete v2.5.0 changelog
- [RTP Timing Support](../RTP_TIMING_SUPPORT.md) - Usage patterns

---

## 🎯 Use Cases

### External Resequencing
- Custom packet buffering strategies
- Specialized jitter handling
- Multi-stream synchronization
- Research applications with custom ordering logic

### Signal Recorder Integration
- Works seamlessly with signal-recorder's `PacketResequencer`
- Allows application-level packet ordering
- Enables custom buffer management
- Supports multi-channel recording scenarios

---

## 🔄 Backward Compatibility

**100% backward compatible** - All existing code continues to work:

```python
# v2.4.0 code works identically in v2.5.0
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
```

The new `pass_all_packets` parameter defaults to `False`, preserving the original internal resequencing behavior.

---

## 🧪 Testing

Tested with:
- ✅ Default mode (internal resequencing)
- ✅ Pass-all mode with external resequencer
- ✅ Metrics tracking in both modes
- ✅ State transitions with pass_all_packets=True
- ✅ Backward compatibility with existing code
- ✅ Integration with signal-recorder

---

## 🔗 Resources

- **Changelog:** [CHANGELOG.md](../../CHANGELOG.md)
- **API Reference:** [API_REFERENCE.md](../API_REFERENCE.md)
- **Issues:** https://github.com/mijahauan/ka9q-python/issues
- **ka9q-radio:** https://github.com/ka9q/ka9q-radio

---

**Full Changelog:** https://github.com/mijahauan/ka9q-python/blob/main/CHANGELOG.md

---

**Thank you for using ka9q-python!** 📻✨
