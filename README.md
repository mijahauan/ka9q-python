# ka9q-python

[![PyPI version](https://badge.fury.io/py/ka9q-python.svg)](https://badge.fury.io/py/ka9q-python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**General-purpose Python library for controlling [ka9q-radio](https://github.com/ka9q/ka9q-radio)**

Control radiod channels for any application: AM/FM/SSB radio, WSPR monitoring, SuperDARN radar, CODAR oceanography, HF fax, satellite downlinks, and more.

**Note:** Package name is `ka9q-python` out of respect for KA9Q (Phil Karn's callsign). Import as `import ka9q`.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
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

### Listen to AM Broadcast

```python
from ka9q import RadiodControl

# Connect to radiod
control = RadiodControl("radiod.local")

# Create AM channel on 10 MHz WWV
control.create_channel(
    ssrc=10000000,
    frequency_hz=10.0e6,
    preset="am",
    sample_rate=12000
)

# RTP stream now available with SSRC 10000000
```

### Monitor WSPR Bands

```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")

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

channels = discover_channels("radiod.local")
for ssrc, info in channels.items():
    print(f"{ssrc}: {info.frequency/1e6:.3f} MHz, {info.preset}, {info.sample_rate} Hz")
```

### Record RTP Stream with Precise Timing

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
control = RadiodControl("radiod.local", interface=my_interface)

# Discovery on specific interface
channels = discover_channels("radiod.local", interface=my_interface)
```

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
