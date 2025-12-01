# ka9q-python v3.2.0 Release Notes

## 🌊 RadiodStream API - Continuous Sample Delivery with Quality Tracking

This release adds a high-level streaming API that delivers continuous sample streams with comprehensive quality metadata. Designed for applications like GRAPE, WSPR, CODAR, and SuperDARN that need reliable data capture with gap detection and quality metrics.

## Installation

```bash
pip install ka9q-python
# or
pip install git+https://github.com/mijahauan/ka9q-python.git
```

## What's New

### RadiodStream - High-Level Streaming

```python
from ka9q import RadiodStream, StreamQuality, discover_channels

def on_samples(samples, quality: StreamQuality):
    print(f"Got {len(samples)} samples, {quality.completeness_pct:.1f}% complete")

channels = discover_channels('radiod.local')
stream = RadiodStream(channel=channels[10000000], on_samples=on_samples)
stream.start()
# ... your application runs ...
final_quality = stream.stop()
```

### StreamQuality - Comprehensive Metrics

Every callback receives quality metadata:

| Metric | Description |
|--------|-------------|
| `completeness_pct` | Percentage of expected samples received |
| `total_gap_events` | Number of distinct gaps detected |
| `total_gaps_filled` | Total zero-fill samples inserted |
| `rtp_packets_received` | Packets received from multicast |
| `rtp_packets_lost` | Packets never received (sequence gaps) |
| `rtp_packets_resequenced` | Out-of-order packets that were resequenced |
| `first_rtp_timestamp` | RTP timestamp of first packet (for precise timing) |

### GapEvent - Gap Classification

```python
for gap in quality.batch_gaps:
    print(f"Gap at sample {gap.position_samples}")
    print(f"  Type: {gap.source.value}")  # network_loss, resequence_timeout, etc.
    print(f"  Duration: {gap.duration_samples} samples")
```

### PacketResequencer - Reliable Delivery

- Circular buffer handles network jitter (configurable, default 64 packets)
- KA9Q-style signed 32-bit timestamp arithmetic for wrap handling
- Zero-fills gaps to maintain sample count integrity
- Detects and logs out-of-order and lost packets

## Architecture

```
radiod → Multicast → RadiodStream → PacketResequencer → App Callback
                          ↓
                    StreamQuality (per batch + cumulative)
```

**Core (ka9q-python) delivers:**
- Continuous sample stream (gaps zero-filled)
- Quality metadata with every callback
- RTP timestamps for precise timing

**Applications handle:**
- Segmentation (1-minute NPZ, 2-minute WAV, etc.)
- Format conversion
- App-specific gap classification

## Examples

Two new examples demonstrate the API:

- `examples/stream_example.py` - Basic streaming with quality reporting
- `examples/grape_integration_example.py` - Two-phase recording (startup buffer → recording)

## New Exports

```python
from ka9q import (
    # Stream API (NEW)
    RadiodStream,
    StreamQuality,
    GapSource,
    GapEvent,
    PacketResequencer,
    RTPPacket,
    ResequencerStats,
    
    # Existing
    RadiodControl,
    discover_channels,
    ChannelInfo,
    # ...
)
```

## Compatibility

- Python 3.8+
- Linux, macOS, Windows (multicast support)
- Works with ka9q-radio (radiod)

## Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete release history.
