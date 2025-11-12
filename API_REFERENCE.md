# API Reference - ka9q-python

Complete reference for all public APIs, parameters, and constants.

---

## Table of Contents

1. [RadiodControl Class](#radiodcontrol-class)
2. [Discovery Functions](#discovery-functions)
3. [Constants](#constants)
4. [Exceptions](#exceptions)
5. [Utility Functions](#utility-functions)

---

## RadiodControl Class

Main class for controlling radiod channels.

### Constructor

```python
RadiodControl(status_address: str)
```

**Parameters:**
- `status_address` (str): mDNS name (e.g., "radiod.local") or IP address of radiod status stream

**Raises:**
- `ConnectionError`: If unable to connect to radiod

**Example:**
```python
control = RadiodControl("bee1-hf-status.local")
# or
control = RadiodControl("239.251.200.193")
```

---

### Context Manager Support

`RadiodControl` supports the context manager protocol:

```python
with RadiodControl("radiod.local") as control:
    control.create_channel(...)
# Automatic cleanup
```

**Methods:**
- `__enter__()` → `RadiodControl`: Returns self
- `__exit__(exc_type, exc_val, exc_tb)` → `bool`: Calls `close()`, returns False

---

### Channel Creation

#### `create_channel()`

Create and configure a new radiod channel with all parameters in a single packet.

```python
create_channel(ssrc: int, 
               frequency_hz: float,
               preset: str = "iq",
               sample_rate: Optional[int] = None,
               agc_enable: int = 0,
               gain: float = 0.0) → None
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ssrc` | int | Yes | - | Channel identifier (0-4294967295). Convention: use frequency in Hz |
| `frequency_hz` | float | Yes | - | RF frequency in Hz (typically 0-10 GHz) |
| `preset` | str | No | "iq" | Demodulation mode: "iq", "usb", "lsb", "am", "fm", "cw" |
| `sample_rate` | int | No | None | Output sample rate in Hz (e.g., 12000, 48000, 16000) |
| `agc_enable` | int | No | 0 | AGC: 0=disabled/manual, 1=enabled |
| `gain` | float | No | 0.0 | Manual gain in dB (-60 to +60) when agc_enable=0 |

**Raises:**
- `ValidationError`: If parameters are out of valid ranges
- `CommandError`: If command fails to send
- `RuntimeError`: If not connected to radiod

**Example:**
```python
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    agc_enable=0,
    gain=0.0
)
```

**Notes:**
- All parameters sent in a single packet (atomic operation)
- Radiod creates channel on first command for new SSRC
- RTP stream becomes available at destination multicast address

---

### Channel Configuration

#### `set_frequency()`

Set the frequency of an existing channel.

```python
set_frequency(ssrc: int, frequency_hz: float) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel (0-4294967295)
- `frequency_hz` (float): Frequency in Hz (0-10 THz)

**Raises:**
- `ValidationError`: If parameters are invalid
- `CommandError`: If command fails to send

**Example:**
```python
control.set_frequency(ssrc=14074000, frequency_hz=14.095e6)
```

---

#### `set_preset()`

Set the preset (demodulation mode) of a channel.

```python
set_preset(ssrc: int, preset: str) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `preset` (str): Preset name ("iq", "usb", "lsb", "am", "fm", "cw")

**Example:**
```python
control.set_preset(ssrc=14074000, preset="usb")
```

---

#### `set_sample_rate()`

Set the output sample rate of a channel.

```python
set_sample_rate(ssrc: int, sample_rate: int) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `sample_rate` (int): Sample rate in Hz (1-100000000)

**Raises:**
- `ValidationError`: If parameters are invalid

**Example:**
```python
control.set_sample_rate(ssrc=14074000, sample_rate=48000)
```

---

#### `set_gain()`

Set manual gain for a channel (linear modes only).

```python
set_gain(ssrc: int, gain_db: float) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `gain_db` (float): Gain in dB (-100 to +100)

**Raises:**
- `ValidationError`: If parameters are invalid

**Example:**
```python
control.set_gain(ssrc=14074000, gain_db=20.0)
```

---

#### `set_agc()`

Configure AGC (Automatic Gain Control) for a channel.

```python
set_agc(ssrc: int,
        enable: bool,
        hangtime: Optional[float] = None,
        headroom: Optional[float] = None,
        recovery_rate: Optional[float] = None,
        attack_rate: Optional[float] = None) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `enable` (bool): True=AGC enabled, False=manual gain
- `hangtime` (float, optional): AGC hang time in seconds
- `headroom` (float, optional): Target headroom in dB
- `recovery_rate` (float, optional): AGC recovery rate
- `attack_rate` (float, optional): AGC attack rate

**Example:**
```python
control.set_agc(
    ssrc=14074000,
    enable=True,
    hangtime=1.5,
    headroom=10.0
)
```

---

#### `set_filter()`

Configure filter parameters for a channel.

```python
set_filter(ssrc: int,
           low_edge: Optional[float] = None,
           high_edge: Optional[float] = None,
           kaiser_beta: Optional[float] = None) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `low_edge` (float, optional): Low frequency edge in Hz
- `high_edge` (float, optional): High frequency edge in Hz
- `kaiser_beta` (float, optional): Kaiser window beta parameter

**Example:**
```python
control.set_filter(
    ssrc=14074000,
    low_edge=-2400,
    high_edge=2400
)
```

---

#### `set_shift_frequency()`

Set post-detection frequency shift (for CW offset, etc.).

```python
set_shift_frequency(ssrc: int, shift_hz: float) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `shift_hz` (float): Frequency shift in Hz

**Example:**
```python
control.set_shift_frequency(ssrc=14074000, shift_hz=800)
```

---

#### `set_output_level()`

Set output level for a channel.

```python
set_output_level(ssrc: int, level: float) → None
```

**Parameters:**
- `ssrc` (int): SSRC of the channel
- `level` (float): Output level (range depends on mode)

---

### Tuning and Status

#### `tune()`

Tune a channel and retrieve its status (like tune.c in ka9q-radio).

```python
tune(ssrc: int,
     frequency_hz: Optional[float] = None,
     preset: Optional[str] = None,
     sample_rate: Optional[int] = None,
     low_edge: Optional[float] = None,
     high_edge: Optional[float] = None,
     gain: Optional[float] = None,
     agc_enable: Optional[bool] = None,
     rf_gain: Optional[float] = None,
     rf_atten: Optional[float] = None,
     encoding: Optional[int] = None,
     destination: Optional[str] = None,
     timeout: float = 5.0) → dict
```

**Parameters:**
- `ssrc` (int): SSRC of the channel to tune
- `frequency_hz` (float, optional): Frequency in Hz
- `preset` (str, optional): Preset/mode name
- `sample_rate` (int, optional): Sample rate in Hz
- `low_edge` (float, optional): Low filter edge in Hz
- `high_edge` (float, optional): High filter edge in Hz
- `gain` (float, optional): Manual gain in dB (disables AGC)
- `agc_enable` (bool, optional): Enable AGC
- `rf_gain` (float, optional): RF front-end gain in dB
- `rf_atten` (float, optional): RF front-end attenuation in dB
- `encoding` (int, optional): Output encoding type (use `Encoding` constants)
- `destination` (str, optional): Destination multicast address
- `timeout` (float): Maximum time to wait for response (default: 5.0s)

**Returns:**

Dictionary containing channel status with keys:

| Key | Type | Description |
|-----|------|-------------|
| `ssrc` | int | Channel SSRC |
| `frequency` | float | Radio frequency in Hz |
| `preset` | str | Mode/preset name |
| `sample_rate` | int | Sample rate in Hz |
| `agc_enable` | bool | AGC enabled status |
| `gain` | float | Current gain in dB |
| `rf_gain` | float | RF gain in dB |
| `rf_atten` | float | RF attenuation in dB |
| `rf_agc` | int | RF AGC status |
| `low_edge` | float | Low filter edge in Hz |
| `high_edge` | float | High filter edge in Hz |
| `noise_density` | float | Noise density in dB/Hz |
| `baseband_power` | float | Baseband power in dB |
| `encoding` | int | Output encoding type |
| `destination` | dict | Destination socket address |
| `snr` | float | Signal-to-noise ratio in dB (calculated) |

**Raises:**
- `ValidationError`: If parameters are invalid
- `TimeoutError`: If no matching response received within timeout

**Example:**
```python
status = control.tune(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    timeout=10.0
)

print(f"Frequency: {status['frequency']/1e6:.3f} MHz")
print(f"SNR: {status['snr']:.1f} dB")
print(f"Preset: {status['preset']}")
```

**Notes:**
- Sends commands and waits for status response
- Matches responses by COMMAND_TAG
- Useful for verifying channel configuration
- Provides real-time signal quality metrics

---

#### `verify_channel()`

Verify that a channel exists and is configured correctly.

```python
verify_channel(ssrc: int, expected_freq: Optional[float] = None) → bool
```

**Parameters:**
- `ssrc` (int): SSRC to verify
- `expected_freq` (float, optional): Expected frequency in Hz

**Returns:**
- `bool`: True if channel exists and matches expectations, False otherwise

**Example:**
```python
if control.verify_channel(ssrc=14074000, expected_freq=14.074e6):
    print("Channel OK!")
```

---

### Connection Management

#### `close()`

Close all sockets and cleanup resources.

```python
close() → None
```

**Notes:**
- Safe to call multiple times
- Handles errors during cleanup gracefully
- Automatically called by context manager

**Example:**
```python
control = RadiodControl("radiod.local")
try:
    control.create_channel(...)
finally:
    control.close()
```

---

### Low-Level Operations

#### `send_command()`

Send a raw TLV command packet to radiod (advanced usage).

```python
send_command(cmdbuffer: bytearray,
             max_retries: int = 3,
             retry_delay: float = 0.1) → int
```

**Parameters:**
- `cmdbuffer` (bytearray): Command buffer to send
- `max_retries` (int): Maximum number of retry attempts (default: 3)
- `retry_delay` (float): Initial delay between retries in seconds (default: 0.1)

**Returns:**
- `int`: Number of bytes sent

**Raises:**
- `RuntimeError`: If not connected to radiod
- `CommandError`: If sending fails after all retries

**Notes:**
- Uses exponential backoff for retries (0.1s → 0.2s → 0.4s)
- Thread-safe with `_socket_lock`
- Most users should use higher-level methods instead

---

## Discovery Functions

Functions for discovering active channels and radiod services.

### `discover_channels()`

Discover channels using the best available method.

```python
discover_channels(status_address: str,
                  listen_duration: float = 2.0,
                  use_native: bool = True) → Dict[int, ChannelInfo]
```

**Parameters:**
- `status_address` (str): Status multicast address (e.g., "radiod.local")
- `listen_duration` (float): Duration to listen for native discovery (default: 2.0s)
- `use_native` (bool): If True, use native Python listener; if False, use control utility

**Returns:**
- `Dict[int, ChannelInfo]`: Dictionary mapping SSRC to ChannelInfo

**Example:**
```python
channels = discover_channels("radiod.local")
for ssrc, info in channels.items():
    print(f"SSRC {ssrc}: {info.frequency/1e6:.3f} MHz, {info.preset}")
```

**Notes:**
- By default, tries native Python discovery first
- Falls back to `control` utility if native finds no channels
- Native discovery requires no external dependencies

---

### `discover_channels_native()`

Discover channels by listening to radiod status multicast (pure Python).

```python
discover_channels_native(status_address: str,
                         listen_duration: float = 2.0) → Dict[int, ChannelInfo]
```

**Parameters:**
- `status_address` (str): Status multicast address
- `listen_duration` (float): How long to listen for status packets (default: 2.0s)

**Returns:**
- `Dict[int, ChannelInfo]`: Dictionary mapping SSRC to ChannelInfo

**Example:**
```python
channels = discover_channels_native("radiod.local", listen_duration=5.0)
```

---

### `discover_channels_via_control()`

Discover channels using the 'control' utility from ka9q-radio.

```python
discover_channels_via_control(status_address: str,
                               timeout: float = 30.0) → Dict[int, ChannelInfo]
```

**Parameters:**
- `status_address` (str): Status multicast address
- `timeout` (float): Timeout for control command (default: 30.0s)

**Returns:**
- `Dict[int, ChannelInfo]`: Dictionary mapping SSRC to ChannelInfo

**Requirements:**
- Requires `control` executable from ka9q-radio to be installed

---

### `discover_radiod_services()`

Find all radiod instances on the network via mDNS.

```python
discover_radiod_services() → List[dict]
```

**Returns:**
- `List[dict]`: List of dictionaries with "name" and "address" keys

**Example:**
```python
services = discover_radiod_services()
for service in services:
    print(f"{service['name']}: {service['address']}")
```

**Requirements:**
- Requires `avahi-browse` (Linux) for mDNS discovery

---

### ChannelInfo Dataclass

```python
@dataclass
class ChannelInfo:
    ssrc: int                   # Channel SSRC
    preset: str                 # Mode/preset name
    sample_rate: int            # Sample rate in Hz
    frequency: float            # Frequency in Hz
    snr: float                  # Signal-to-noise ratio in dB
    multicast_address: str      # Destination multicast address
    port: int                   # Destination port
```

---

## Constants

### StatusType

All radiod protocol type identifiers (110+ constants).

**Common Constants:**

```python
from ka9q import StatusType

StatusType.EOL = 0                    # End of list marker
StatusType.COMMAND_TAG = 1            # Command tag for matching responses
StatusType.OUTPUT_SSRC = 18           # Channel SSRC
StatusType.OUTPUT_SAMPRATE = 20       # Sample rate
StatusType.RADIO_FREQUENCY = 33       # RF frequency
StatusType.LOW_EDGE = 39              # Low filter edge
StatusType.HIGH_EDGE = 40             # High filter edge
StatusType.BASEBAND_POWER = 46        # Baseband power
StatusType.NOISE_DENSITY = 47         # Noise density
StatusType.DEMOD_TYPE = 48            # Demodulation type (0=linear, 1=FM)
StatusType.AGC_ENABLE = 62            # AGC enable/disable
StatusType.GAIN = 68                  # Manual gain
StatusType.PRESET = 85                # Mode/preset name
StatusType.RF_ATTEN = 97              # RF attenuation
StatusType.RF_GAIN = 98               # RF gain
StatusType.RF_AGC = 99                # RF AGC status
StatusType.OUTPUT_ENCODING = 107      # Output encoding type
```

**See**: `ka9q/types.py` for complete list

---

### Encoding

Output encoding type constants.

```python
from ka9q import Encoding

Encoding.NO_ENCODING = 0
Encoding.S16BE = 1          # Signed 16-bit big-endian
Encoding.S16LE = 2          # Signed 16-bit little-endian
Encoding.F32 = 3            # 32-bit float
Encoding.F16 = 4            # 16-bit float
Encoding.OPUS = 5           # Opus codec
```

**Example:**
```python
status = control.tune(ssrc=10000, encoding=Encoding.F32)
```

---

## Exceptions

### Ka9qError

Base exception for all ka9q-python errors.

```python
class Ka9qError(Exception):
    """Base exception for all ka9q errors"""
```

---

### ConnectionError

Failed to connect to radiod.

```python
class ConnectionError(Ka9qError):
    """Failed to connect to radiod"""
```

**Causes:**
- Cannot resolve address
- Network unreachable
- Socket creation failure
- Multicast join failure

---

### CommandError

Failed to send command to radiod.

```python
class CommandError(Ka9qError):
    """Failed to send command to radiod"""
```

**Causes:**
- Socket error during send
- Network failure
- All retries exhausted

---

### ValidationError

Invalid parameter or configuration.

```python
class ValidationError(Ka9qError):
    """Invalid parameter or configuration"""
```

**Causes:**
- SSRC out of range (must be 0-4294967295)
- Frequency out of range
- Sample rate invalid (must be positive)
- Gain out of range
- Timeout not positive

---

### DiscoveryError

Failed to discover radiod services or channels.

```python
class DiscoveryError(Ka9qError):
    """Failed to discover radiod services or channels"""
```

---

## Utility Functions

### resolve_multicast_address()

Resolve hostname or mDNS address to IP for multicast operations.

```python
from ka9q.utils import resolve_multicast_address

resolve_multicast_address(address: str, timeout: float = 5.0) → str
```

**Parameters:**
- `address` (str): Hostname, .local mDNS name, or IP address
- `timeout` (float): Resolution timeout in seconds (default: 5.0)

**Returns:**
- `str`: Resolved IP address

**Raises:**
- `Exception`: If resolution fails after trying all methods

**Example:**
```python
ip = resolve_multicast_address("radiod.local")
print(ip)  # "239.251.200.193"
```

---

### validate_multicast_address()

Validate that an address is a valid multicast address.

```python
from ka9q.utils import validate_multicast_address

validate_multicast_address(address: str) → bool
```

**Parameters:**
- `address` (str): IP address string to validate

**Returns:**
- `bool`: True if valid multicast address (224.0.0.0 to 239.255.255.255)

**Example:**
```python
is_mcast = validate_multicast_address("239.251.200.193")
print(is_mcast)  # True
```

---

## Parameter Ranges and Limits

### Valid Ranges

| Parameter | Type | Min | Max | Notes |
|-----------|------|-----|-----|-------|
| `ssrc` | int | 0 | 4294967295 | 32-bit unsigned integer |
| `frequency_hz` | float | 0 | 10e12 | 10 THz practical limit |
| `sample_rate` | int | 1 | 100e6 | 100 MHz practical limit |
| `gain_db` | float | -100 | +100 | Typical SDR range |
| `timeout` | float | >0 | unlimited | Seconds |

### Conventions

**SSRC Selection:**
- **Recommended**: Use frequency in Hz as SSRC
- Example: For 14.074 MHz, use SSRC = 14074000
- Must be unique per channel

**Frequency Units:**
- Always in Hz (not MHz or kHz)
- Example: 14.074 MHz = 14.074e6 Hz = 14074000 Hz

**Sample Rate Values:**
- Typical: 12000, 16000, 24000, 48000
- Must match your application's needs
- Higher rates = more CPU/bandwidth

**Preset/Mode Names:**
- "iq" - I/Q linear mode (wideband)
- "usb" - Upper sideband
- "lsb" - Lower sideband
- "am" - Amplitude modulation
- "fm" - Frequency modulation (narrowband)
- "cw" - Continuous wave (Morse code)

---

## Thread Safety

**Thread-Safe Methods:**
- ✅ All `RadiodControl` public methods
- ✅ `send_command()`
- ✅ `tune()`
- ✅ `close()`

**Not Thread-Safe:**
- Discovery functions (call from single thread or synchronize externally)

**Example Multi-Threaded Usage:**
```python
control = RadiodControl("radiod.local")

def worker(freq):
    control.set_frequency(ssrc=10000, frequency_hz=freq)

from threading import Thread
threads = [Thread(target=worker, args=(f,)) for f in [14.074e6, 14.095e6]]
for t in threads:
    t.start()
for t in threads:
    t.join()

control.close()
```

---

## Error Handling Best Practices

### Always Catch Specific Exceptions

```python
from ka9q import RadiodControl, ValidationError, ConnectionError, CommandError

try:
    with RadiodControl("radiod.local") as control:
        control.create_channel(ssrc=10000, frequency_hz=14.074e6)
except ValidationError as e:
    print(f"Invalid parameters: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except CommandError as e:
    print(f"Command failed: {e}")
```

### Use Context Manager

```python
# GOOD: Automatic cleanup
with RadiodControl("radiod.local") as control:
    control.create_channel(...)

# AVOID: Manual cleanup
control = RadiodControl("radiod.local")
try:
    control.create_channel(...)
finally:
    control.close()
```

### Validate Before Sending

```python
# Input validation happens automatically
control.create_channel(ssrc=-1, ...)  # Raises ValidationError immediately
```

---

## Version Information

```python
import ka9q
print(ka9q.__version__)  # "2.1.0"
print(ka9q.__author__)   # "Michael J. Hauan"
```

---

*For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)*  
*For user guide, see [README.md](README.md)*  
*For installation, see [INSTALLATION.md](INSTALLATION.md)*
