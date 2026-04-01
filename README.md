# ka9q-python

[![PyPI version](https://badge.fury.io/py/ka9q-python.svg)](https://badge.fury.io/py/ka9q-python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**General-purpose Python library for controlling [ka9q-radio](https://github.com/ka9q/ka9q-radio)**

Control radiod channels for any application: AM/FM/SSB radio, WSPR monitoring, SuperDARN radar, CODAR oceanography, HF fax, satellite downlinks, and more.

**Note:** Package name is `ka9q-python` out of respect for KA9Q (Phil Karn's callsign). Import as `import ka9q`.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Getting Started](docs/GETTING_STARTED.md)
- [Quick Start](#quick-start)
- [ka9q-radio Compatibility](#ka9q-radio-compatibility)
- [Documentation](#documentation)
- [Examples](#examples)
- [Use Cases](#use-cases)
- [License](#license)

## Features

✅ **Zero assumptions** - Works for any SDR application  
✅ **Complete API** - All 85+ radiod parameters exposed  
✅ **Channel control** - Create, configure, discover channels  
✅ **RTP recording** - Generic recorder with timing support and state machine  
✅ **Precise timing** - GPS_TIME/RTP_TIMESNAP for accurate timestamps  
✅ **Multi-homed support** - Works on systems with multiple network interfaces  
✅ **Pure Python** - No compiled dependencies  
✅ **Well tested** - Comprehensive test coverage  
✅ **Documented** - Comprehensive examples and API reference included  

## Installation

```bash
pip install ka9q-python
```

Or install from source:

```bash
git clone https://github.com/mijahauan/ka9q-python.git
cd ka9q-python
pip install -e .
```

## Quick Start

> **Host selection:** All examples reference `bee1-hf-status.local`, which is the default integration test radiod in this repo. Replace it with your own radiod host or set `RADIOD_HOST`, `RADIOD_ADDRESS`, or the `--radiod-host` pytest option when running in other environments.

### Listen to AM Broadcast

```python
from ka9q import RadiodControl

# Connect to radiod (default test host: bee1-hf-status.local)
control = RadiodControl("bee1-hf-status.local")

# Create AM channel on 10 MHz WWV
control.create_channel(
    ssrc=10000000,
    frequency_hz=10.0e6,
    preset="am",
    sample_rate=12000
)

# RTP stream now available with SSRC 10000000
```

### Request Specific Output Encoding

```python
from ka9q import RadiodControl, Encoding

control = RadiodControl("bee1-hf-status.local")

# Create a channel with 32-bit float output (highest quality)
control.ensure_channel(
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    encoding=Encoding.F32
)
```

### Monitor WSPR Bands

```python
from ka9q import RadiodControl

control = RadiodControl("bee1-hf-status.local")

wspr_bands = [
    (1.8366e6, "160m"),
    (3.5686e6, "80m"),
    (7.0386e6, "40m"),
    (10.1387e6, "30m"),
    (14.0956e6, "20m"),
]

for freq, band in wspr_bands:
    control.create_channel(
        ssrc=int(freq),
        frequency_hz=freq,
        preset="usb",
        sample_rate=12000
    )
    print(f"{band} WSPR channel created")
```

### Discover Existing Channels

```python
from ka9q import discover_channels

channels = discover_channels("bee1-hf-status.local")
for ssrc, info in channels.items():
    print(f"{ssrc}: {info.frequency/1e6:.3f} MHz, {info.preset}, {info.sample_rate} Hz")
```

### Record RTP Stream with Precise Timing

```python
from ka9q import discover_channels, RTPRecorder
import time

# Get channel with timing info
channels = discover_channels("bee1-hf-status.local")
channel = channels[14074000]

# Define packet handler
def handle_packet(header, payload, wallclock):
    print(f"Packet at {wallclock}: {len(payload)} bytes")

# Create and start recorder
recorder = RTPRecorder(channel=channel, on_packet=handle_packet)
recorder.start()
recorder.start_recording()
time.sleep(60)  # Record for 60 seconds
recorder.stop_recording()
recorder.stop()
```

### Multi-Homed Systems

For systems with multiple network interfaces, specify which interface to use:

```python
from ka9q import RadiodControl, discover_channels

# Specify your interface IP address
my_interface = "192.168.1.100"

# Create control with specific interface
control = RadiodControl("bee1-hf-status.local", interface=my_interface)

# Discovery on specific interface
channels = discover_channels("bee1-hf-status.local", interface=my_interface)
```

### Automatic Channel Recovery

ensure your channels survive radiod restarts:

```python
from ka9q import RadiodControl, ChannelMonitor

control = RadiodControl("bee1-hf-status.local")
monitor = ChannelMonitor(control)
monitor.start()

# This channel will be automatically re-created if it disappears
monitor.monitor_channel(
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000
)

### Channel Cleanup (frequency = 0)

`radiod` removes channels by polling for streams whose frequency is set to `0 Hz`. Always call `remove_channel(ssrc)` (or explicitly set `set_frequency(ssrc, 0.0)` if you build TLVs yourself) when tearing down a stream so the background poller can reclaim it:

```python
with RadiodControl("bee1-hf-status.local") as control:
    info = control.ensure_channel(
        frequency_hz=10e6,
        preset="iq",
        sample_rate=16000
    )

    # ... use channel ...

    control.remove_channel(info.ssrc)  # marks frequency=0
```

> Note: `remove_channel()` finishes instantly on the client; radiod’s poller typically purges the channel within the next second.

## ka9q-radio Compatibility

`ka9q-python` tracks a specific git commit of [ka9q-radio](https://github.com/ka9q/ka9q-radio) to ensure its protocol definitions (`StatusType`, `Encoding`) match the C headers exactly. This prevents subtle bugs from protocol drift between the two projects.

### How It Works

| File | Role |
|------|------|
| `ka9q_radio_compat` | Plain-text pin recording the validated ka9q-radio commit hash |
| `ka9q/compat.py` | Importable `KA9Q_RADIO_COMMIT` constant for deployment tooling |
| `ka9q/types.py` | Auto-generated from ka9q-radio's `status.h` and `rtp.h` |
| `scripts/sync_types.py` | The tool that parses C headers and regenerates `types.py` |
| `tests/test_protocol_compat.py` | Drift test (runs automatically if `../ka9q-radio` exists) |

### Checking for Drift

If you have the ka9q-radio source tree at `../ka9q-radio`:

```bash
python scripts/sync_types.py --check    # CI mode: exits non-zero on drift
python scripts/sync_types.py --diff     # Preview changes without modifying anything
```

### Syncing After ka9q-radio Updates

```bash
python scripts/sync_types.py --apply    # Regenerates types.py, updates pins
git diff ka9q/types.py                  # Review the changes
python -m pytest tests/                 # Verify nothing broke
```

The `--apply` mode updates three files atomically:
1. `ka9q/types.py` — regenerated from the C headers
2. `ka9q_radio_compat` — updated with the new commit hash
3. `ka9q/compat.py` — updated with the new commit hash (importable)

### For Deployment Tooling

`ka9q-update` (or any deployment tool) can read the pinned commit to ensure the correct `radiod` version is running:

```python
from ka9q.compat import KA9Q_RADIO_COMMIT

print(f"This ka9q-python requires ka9q-radio at {KA9Q_RADIO_COMMIT[:12]}")
```

### Running the Drift Test

The pytest drift test runs automatically as part of the test suite:

```bash
python -m pytest tests/test_protocol_compat.py -v
```

It auto-skips if `../ka9q-radio` is not present, so CI environments without the C source tree are unaffected.

## Documentation

For detailed information, please refer to the documentation in the `docs/` directory:

- **[API Reference](docs/API_REFERENCE.md)**: Full details on all classes, methods, and functions.
- **[RTP Timing Support](docs/RTP_TIMING_SUPPORT.md)**: Guide to RTP timing and synchronization.
- **[Architecture](docs/ARCHITECTURE.md)**: Overview of the library's design and structure.
- **[Installation Guide](docs/INSTALLATION.md)**: Detailed installation instructions.
- **[Testing Guide](docs/TESTING_GUIDE.md)**: Information on how to run the test suite.
- **[Security Considerations](docs/SECURITY.md)**: Important security information regarding the ka9q-radio protocol.
- **[Changelog](docs/CHANGELOG.md)**: A log of all changes for each version.
- **[Release Notes](docs/releases/)**: Release-specific notes and instructions.

## Examples

See the `examples/` directory for complete applications:

- **High-Level API**: `ensure_channel()` handles the complexity of checking existing channels, creating new ones only when necessary, and verifying configurations.
- **Destination-Aware Channels**: Support for unique per-application multicast destinations and deterministic IP generation.
- **Stream Sharing**: Deterministic SSRC allocation allows multiple independent applications to share `radiod` streams efficiently.
- **`discover_example.py`** - Channel discovery methods (native Python and control utility)
- **`tune.py`** - Interactive channel tuning utility (Python implementation of ka9q-radio's tune)
- **`tune_example.py`** - Programmatic examples of using the tune() method
- **`rtp_recorder_example.py`** - Complete RTP recorder with timing and state machine
- **`test_timing_fields.py`** - Verify GPS_TIME/RTP_TIMESNAP timing fields
- **`simple_am_radio.py`** - Minimal AM broadcast listener
- **`superdarn_recorder.py`** - Ionospheric radar monitoring
- **`codar_oceanography.py`** - Ocean current radar
- **`hf_band_scanner.py`** - Dynamic frequency scanner
- **`wspr_monitor.py`** - Weak signal propagation reporter

## Use Cases

### AM/FM/SSB Radio
- Broadcast monitoring
- Ham radio operation  
- Shortwave listening

### Scientific Research
- WSPR propagation studies
- SuperDARN ionospheric radar
- CODAR ocean current mapping
- Meteor scatter
- EME (moonbounce)

### Digital Modes
- FT8/FT4 monitoring
- RTTY/PSK decoding
- DRM digital radio
- HF fax reception

### Satellite Operations
- Downlink reception
- Doppler tracking
- Multi-frequency monitoring

### Custom Applications
**No assumptions!** Use for anything SDR-related.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
