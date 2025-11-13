# ka9q-python

**General-purpose Python library for controlling [ka9q-radio](https://github.com/ka9q/ka9q-radio)**

Control radiod channels for any application: AM/FM/SSB radio, WSPR monitoring, SuperDARN radar, CODAR oceanography, HF fax, satellite downlinks, and more.

## Features

✅ **Zero assumptions** - Works for any SDR application  
✅ **Complete API** - All 85+ radiod parameters exposed  
✅ **Channel control** - Create, configure, discover channels  
✅ **Pure Python** - No compiled dependencies  
✅ **Well tested** - Comprehensive test coverage  
✅ **Documented** - Comprehensive examples included  

## Installation

```bash
pip install ka9q
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

## Examples

See `examples/` directory for complete applications:

- **`discover_example.py`** - Channel discovery methods (native Python and control utility)
- **`tune.py`** - Interactive channel tuning utility (Python implementation of ka9q-radio's tune)
- **`tune_example.py`** - Programmatic examples of using the tune() method
- **`simple_am_radio.py`** - Minimal AM broadcast listener
- **`superdarn_recorder.py`** - Ionospheric radar monitoring
- **`codar_oceanography.py`** - Ocean current radar
- **`hf_band_scanner.py`** - Dynamic frequency scanner
- **`wspr_monitor.py`** - Weak signal propagation reporter

## API Reference

### RadiodControl

Main class for controlling radiod:

```python
from ka9q import RadiodControl

control = RadiodControl("radiod-status.local")
```

#### create_channel()

Create and configure a channel:

```python
control.create_channel(
    ssrc=12345678,           # Unique identifier
    frequency_hz=14.074e6,   # Frequency in Hz
    preset="usb",            # Mode: iq, am, fm, usb, lsb, cw
    sample_rate=48000        # Sample rate in Hz
)
```

#### remove_channel()

Remove a channel when done (important for cleanup):

```python
control.remove_channel(ssrc=12345678)
```

**⚠️ Important**: Always remove channels when your application is done with them. Radiod doesn't automatically clean up unused channels, so long-running applications should explicitly remove temporary channels to prevent accumulation.

**Note**: Removal is not instantaneous. Setting frequency to 0 marks the channel for removal, and radiod periodically polls to remove marked channels. The channel may still appear in discovery for a brief time after calling `remove_channel()`.

**Best Practice** - Use context manager or try/finally:

```python
# Pattern 1: Context manager (automatic cleanup)
with RadiodControl("radiod.local") as control:
    control.create_channel(ssrc=14074000, frequency_hz=14.074e6, preset="usb")
    # ... use channel ...
    control.remove_channel(ssrc=14074000)

# Pattern 2: Try/finally (manual cleanup)
control = RadiodControl("radiod.local")
try:
    control.create_channel(ssrc=14074000, frequency_hz=14.074e6, preset="usb")
    # ... use channel ...
finally:
    control.remove_channel(ssrc=14074000)
    control.close()
```

#### Granular Setters

Fine-tune individual parameters:

```python
# Set frequency
control.set_frequency(ssrc=12345678, frequency_hz=14.095e6)

# Set AGC
control.set_agc(ssrc=12345678, enable=True, hangtime=1.5, headroom=10.0)

# Set filter
control.set_filter(ssrc=12345678, low_edge=-2400, high_edge=2400)

# Set gain
control.set_gain(ssrc=12345678, gain_db=20.0)

# Set frequency shift (CW offset)
control.set_shift_frequency(ssrc=12345678, shift_hz=800)
```

#### tune()

Tune a channel and retrieve its status (like the tune utility in ka9q-radio):

```python
# Tune a channel and get immediate status feedback
status = control.tune(
    ssrc=12345678,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    timeout=5.0
)

print(f"Frequency: {status['frequency']/1e6:.3f} MHz")
print(f"SNR: {status['snr']:.1f} dB")
```

This method sends commands to radiod and waits for a status response, providing immediate confirmation of the channel state. Useful for:
- Verifying channel configuration
- Getting real-time signal quality metrics (SNR, power levels)
- Interactive tuning applications
- Debugging channel issues

#### verify_channel()

Check if channel exists:

```python
if control.verify_channel(ssrc=12345678, expected_freq=14.074e6):
    print("Channel OK!")
```

### Discovery Functions

#### discover_channels()

Query existing channels using native Python (no external dependencies):

```python
from ka9q import discover_channels

# Native Python discovery (default, listens for 2 seconds)
channels = discover_channels("radiod.local")
# Returns: {ssrc: ChannelInfo(...), ...}

# Customize listen duration
channels = discover_channels("radiod.local", listen_duration=5.0)

# Force use of 'control' utility (requires ka9q-radio installed)
channels = discover_channels("radiod.local", use_native=False)
```

The native discovery method listens directly to radiod's status multicast stream and requires no external executables. It will automatically fall back to the `control` utility if native discovery fails or finds no channels.

#### discover_radiod_services()

Find all radiod instances on network:

```python
from ka9q import discover_radiod_services

services = discover_radiod_services()
# Returns: [{'name': 'radiod@hf', 'address': '239.1.2.3:5006'}, ...]
```

### StatusType

All radiod parameters (85+ constants):

```python
from ka9q import StatusType

# Commonly used:
StatusType.RADIO_FREQUENCY       # 33
StatusType.PRESET                # 85
StatusType.OUTPUT_SAMPRATE       # 20
StatusType.AGC_ENABLE            # 61
StatusType.GAIN                  # 66
StatusType.LOW_EDGE              # 39
StatusType.HIGH_EDGE             # 40
# ... and 78 more
```

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

## Architecture

### No Application-Specific Defaults

The API doesn't assume you're:
- Recording data
- Using any specific sample rate
- Monitoring any specific frequencies
- Storing anything
- Using any particular data format

**You specify everything.** This makes it reusable for any project.

### Modular Design

```
ka9q/
├── control.py      # RadiodControl class (TLV commands)
├── discovery.py    # Channel & service discovery
├── types.py        # StatusType enum (protocol constants)
└── exceptions.py   # Ka9qError, ConnectionError, etc.
```

Each module is independent and can be used separately.

## Requirements

### Core Requirements
- Python 3.9+
- Running `radiod` instance on network

### Optional Requirements (for enhanced functionality)
- **mDNS tools** (for .local hostname resolution):
  - Linux: `avahi-utils` package provides `avahi-resolve` and `avahi-browse`
  - macOS: `dns-sd` (built-in) for hostname resolution
  - Fallback: Python's `getaddrinfo` works everywhere
- **ka9q-radio tools** (optional fallback):
  - `control` utility for channel discovery (falls back to native Python)

**Note**: The package works cross-platform without any external tools! They just provide optimization for mDNS resolution.

## Security Considerations

⚠️ **IMPORTANT**: ka9q-radio uses an **unauthenticated UDP multicast protocol** for control commands.

### Threat Model

The ka9q-radio protocol does NOT include:
- ❌ Authentication - Anyone on the network can send commands
- ❌ Encryption - All traffic is plaintext
- ❌ Authorization - No access control lists
- ❌ Audit logging - No built-in command tracking

### Possible Attacks

If radiod is exposed to untrusted networks, attackers can:
- **Command Injection**: Send arbitrary commands to your radiod instance
- **Denial of Service**: Flood with commands, delete channels, cause crashes
- **Eavesdropping**: Monitor what frequencies you're tuning to
- **Frequency Hijacking**: Force channels to unintended frequencies

### Recommended Deployment

✅ **Suitable Environments**:
- Private LANs behind firewalls (home networks, labs)
- Isolated network segments (VLANs, Docker networks)
- VPN-only access for remote users
- Amateur radio operations on trusted networks

❌ **NOT Suitable For**:
- Public internet exposure
- Multi-tenant cloud environments
- Untrusted networks (public WiFi, university networks, etc.)
- Security-critical or compliance-regulated applications

### Security Checklist

Before deploying in production:

- [ ] **Network Isolation**: Radiod is on isolated network segment
- [ ] **Firewall Rules**: Block UDP port 5006 from untrusted sources
- [ ] **No Public Exposure**: Radiod NOT accessible from internet
- [ ] **VPN for Remote Access**: Use WireGuard/OpenVPN, not port forwarding
- [ ] **Monitoring**: Log unusual command patterns
- [ ] **Physical Security**: Control access to network infrastructure

### Secure Deployment Patterns

**Pattern 1: Isolated Home Network** (Recommended for Amateur Radio)
```
[Internet] <-> [Router/Firewall] <-> [Private 192.168.x.x Network]
                                       └─ radiod (no internet access)
                                       └─ Control applications
```

**Pattern 2: VPN Access** (For Remote Operation)
```
[Remote User] -> [VPN Tunnel] -> [Private Network with radiod]
```

**Pattern 3: Docker Isolation** (For Development/Testing)
```bash
# Run radiod in isolated Docker network
docker network create --internal radiod-net
docker run --network=radiod-net radiod
```

### What ka9q-python Does for Security

✅ **Input Validation**: All parameters validated before transmission
- SSRC range checking (0-4294967295)
- Frequency validation (prevents invalid values)
- String sanitization (rejects control characters, null bytes)
- Parameter bounds checking

✅ **Rate Limiting**: Prevents command flooding (default: 100 commands/sec)

✅ **Secure Random**: Uses `secrets` module for command tags (prevents prediction)

✅ **Error Handling**: Comprehensive validation prevents malformed packets

### For FCC-Regulated / Commercial Use

If you're using this for:
- **FCC-licensed operations**: Ensure unauthorized frequency changes are prevented via network isolation
- **Research/Government**: Authentication may be required by policy (not provided by protocol)
- **Commercial Products**: Network-level security (VPN, IPsec) required

### Future Security Enhancements

The ka9q-radio protocol would need updates to support:
- HMAC-based message authentication
- TLS/DTLS encryption for command transport
- Role-based access control
- Command auditing and logging

These are protocol-level changes that would require updates to both radiod (C code) and ka9q-python.

---

## Development

```bash
# Clone
git clone https://github.com/mijahauan/ka9q-python.git
cd ka9q-python

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run examples
python examples/simple_am_radio.py
```

## Integration with Other Projects

This library is designed to be used as a dependency:

```toml
# pyproject.toml
[project]
dependencies = [
    "ka9q>=1.0.0",
]
```

```python
# requirements.txt
ka9q>=1.0.0
```

Then in your code:

```python
from ka9q import RadiodControl

# Your application code here
```

### Example: Application-Specific Wrapper

You can create application-specific wrappers with your own defaults:

```python
from ka9q import RadiodControl

# Application-specific wrapper with custom defaults
class MyChannelManager:
    def __init__(self, radiod_address):
        self.control = RadiodControl(radiod_address)
    
    def create_my_channel(self, frequency_mhz, sample_rate=16000):
        # Your application's defaults
        self.control.create_channel(
            ssrc=int(frequency_mhz * 1e6),
            frequency_hz=frequency_mhz * 1e6,
            preset="iq",
            sample_rate=sample_rate,
            agc_enable=0,
            gain=0.0
        )
```

## Contributing

Contributions welcome! Please:

1. Add tests for new features
2. Follow existing code style
3. Add examples for new use cases
4. Update documentation

## License

MIT License - see LICENSE file

## Credits

- Based on [ka9q-radio](https://github.com/ka9q/ka9q-radio) by Phil Karn KA9Q
- Developed by Michael J. Hauan AC0G

## Documentation

- **[API Reference](API_REFERENCE.md)** - Complete API documentation with all parameters and examples
- **[Architecture](ARCHITECTURE.md)** - Internal design, protocol details, threading model
- **[Installation Guide](INSTALLATION.md)** - Detailed installation instructions

## See Also

- [ka9q-radio](https://github.com/ka9q/ka9q-radio) - The SDR software this controls
- [SuperDARN](http://vt.superdarn.org/) - Ionospheric radar network
- [CODAR](https://codaros.com/) - Ocean current radar systems
