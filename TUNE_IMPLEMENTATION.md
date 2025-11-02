# Tune Functionality Implementation

This document describes the implementation of the `tune` functionality from ka9q-radio in the ka9q-python package.

## Overview

The tune functionality allows you to send commands to radiod and immediately receive status responses, similar to the `tune` utility in ka9q-radio. This provides:
- Immediate confirmation of channel configuration
- Real-time signal quality metrics (SNR, power levels, etc.)
- Interactive channel control
- Debugging capabilities

## Implementation Details

### 1. Updated StatusType Constants (`ka9q/types.py`)

Updated all StatusType enum values to match the official ka9q-radio repository at `/Users/mjh/Sync/GitHub/ka9q-radio/src/status.h`. Key additions include:

- `RF_GAIN` (98) - RF front-end gain in dB
- `RF_ATTEN` (97) - RF front-end attenuation in dB
- `RF_AGC` (99) - RF AGC enable/disable
- `OUTPUT_ENCODING` (107) - Output encoding type
- `PRESET` (85) - Mode/preset name
- Plus many other fields up to `RF_LEVEL_CAL` (110)

Also added `Encoding` class for output encoding types:
- `NO_ENCODING` (0)
- `S16BE` (1) - Signed 16-bit big-endian
- `S16LE` (2) - Signed 16-bit little-endian
- `F32` (3) - 32-bit float
- `F16` (4) - 16-bit float
- `OPUS` (5) - Opus codec

### 2. Decode Functions (`ka9q/control.py`)

Added TLV response decoding functions to parse status packets from radiod:

- `decode_int(data, length)` - Decode variable-length integers
- `decode_int32(data, length)` - Decode 32-bit integers
- `decode_float(data, length)` - Decode 32-bit floats
- `decode_double(data, length)` - Decode 64-bit doubles
- `decode_bool(data, length)` - Decode boolean values
- `decode_string(data, length)` - Decode UTF-8 strings
- `decode_socket(data, length)` - Decode socket addresses

### 3. RadiodControl.tune() Method (`ka9q/control.py`)

Added the main `tune()` method to the `RadiodControl` class:

```python
def tune(self, ssrc: int, frequency_hz: Optional[float] = None, 
         preset: Optional[str] = None, sample_rate: Optional[int] = None,
         low_edge: Optional[float] = None, high_edge: Optional[float] = None,
         gain: Optional[float] = None, agc_enable: Optional[bool] = None,
         rf_gain: Optional[float] = None, rf_atten: Optional[float] = None,
         encoding: Optional[int] = None, destination: Optional[str] = None,
         timeout: float = 5.0) -> dict:
```

**Features:**
- Sends TLV-encoded command packet with specified parameters
- Listens for status response packets on multicast socket
- Matches responses by SSRC and command tag
- Returns dictionary with decoded status fields
- Calculates SNR from noise density and signal power
- Raises `TimeoutError` if no response within timeout period

**Returned Status Fields:**
- `ssrc` - Channel SSRC
- `frequency` - Radio frequency in Hz
- `preset` - Mode/preset name
- `sample_rate` - Sample rate in Hz
- `agc_enable` - AGC enabled status
- `gain` - Current gain in dB
- `rf_gain` - RF gain in dB
- `rf_atten` - RF attenuation in dB
- `rf_agc` - RF AGC status
- `low_edge` - Low filter edge in Hz
- `high_edge` - High filter edge in Hz
- `noise_density` - Noise density in dB/Hz
- `baseband_power` - Baseband power in dB
- `encoding` - Output encoding type
- `destination` - Destination socket address
- `snr` - Signal-to-noise ratio in dB (calculated)

### 4. Helper Methods

**`_setup_status_listener()`** - Creates and configures a UDP socket to listen for status responses on the multicast group.

**`_decode_status_response(buffer)`** - Parses a complete status response packet and returns a dictionary of decoded fields.

### 5. CLI Tool (`examples/tune.py`)

Created a command-line interface that replicates the functionality of `tune.c` from ka9q-radio:

```bash
# Create USB channel on 14.074 MHz
./examples/tune.py -r radiod.local -s 12345678 -f 14.074M -m usb

# Create IQ channel with custom sample rate
./examples/tune.py -r radiod.local -s 10000000 -f 10M -m iq -R 48000

# Set manual gain (disables AGC)
./examples/tune.py -r radiod.local -s 12345678 -f 7.040M -m lsb -g 20

# Enable AGC
./examples/tune.py -r radiod.local -s 12345678 -a
```

**Supported Options:**
- `-r/--radio` - Radiod address (required)
- `-s/--ssrc` - SSRC identifier (required)
- `-f/--frequency` - Radio frequency (supports k/M/G suffixes)
- `-m/--mode/--preset` - Preset/mode name
- `-R/--samprate` - Sample rate in Hz
- `-L/--low` - Low filter edge
- `-H/--high` - High filter edge
- `-g/--gain` - Manual gain in dB
- `-a/--agc` - Enable AGC
- `-G/--rfgain` - RF front-end gain
- `-A/--rfatten` - RF front-end attenuation
- `-e/--encoding` - Output encoding
- `-D/--destination` - Destination multicast address
- `-q/--quiet` - Suppress status output
- `-v/--verbose` - Verbose mode
- `-t/--timeout` - Response timeout

### 6. Programmatic Example (`examples/tune_example.py`)

Created examples showing how to use the `tune()` method in Python code:

```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")

# Tune a USB channel
status = control.tune(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    timeout=5.0
)

print(f"Frequency: {status['frequency']/1e6:.6f} MHz")
print(f"SNR: {status['snr']:.1f} dB")
```

### 7. Updated Exports (`ka9q/__init__.py`)

Added `Encoding` to the exported classes:

```python
from .types import StatusType, Encoding

__all__ = [
    'RadiodControl',
    'discover_channels',
    'discover_radiod_services',
    'ChannelInfo',
    'StatusType',
    'Encoding',
    'Ka9qError',
    'ConnectionError',
    'CommandError',
]
```

### 8. Documentation (`README.md`)

Added documentation for:
- The `tune()` method in the API Reference section
- Examples of tune.py and tune_example.py in the Examples section
- Use cases for the tune functionality

## Usage Examples

### Command Line

```bash
# Tune to WWV on 10 MHz
./examples/tune.py -r radiod.local -s 10000000 -f 10M -m am

# Create FT8 channel
./examples/tune.py -r radiod.local -s 14074000 -f 14.074M -m usb -R 12000

# Adjust gain on existing channel
./examples/tune.py -r radiod.local -s 14074000 -g 15

# Get channel status (no changes)
./examples/tune.py -r radiod.local -s 14074000
```

### Python API

```python
from ka9q import RadiodControl, Encoding

control = RadiodControl("radiod.local")

# Create and configure channel
status = control.tune(
    ssrc=10000000,
    frequency_hz=10.0e6,
    preset="iq",
    sample_rate=48000,
    low_edge=-24000,
    high_edge=24000,
    agc_enable=False,
    timeout=5.0
)

# Display status
print(f"Frequency: {status['frequency']/1e6:.6f} MHz")
print(f"Sample Rate: {status['sample_rate']} Hz")
print(f"Passband: {status['low_edge']:.0f} to {status['high_edge']:.0f} Hz")
if 'snr' in status:
    print(f"SNR: {status['snr']:.1f} dB")

control.close()
```

## Technical Notes

### Protocol Compatibility

All StatusType values have been verified against the official ka9q-radio repository at:
- Repository: https://github.com/ka9q/ka9q-radio
- File: `/Users/mjh/Sync/GitHub/ka9q-radio/src/status.h`

The enum values match exactly with the C implementation.

### Socket Configuration

The tune implementation uses the same multicast socket configuration as the existing ka9q-python code:
- Loopback interface with proper `ip_mreqn` structure
- Multicast group membership on 127.0.0.1
- TTL=2, loopback enabled

### Response Matching

Responses are matched by both SSRC and command tag to ensure we receive the correct status packet for our command, even when multiple clients are communicating with radiod.

### Error Handling

- `TimeoutError` - Raised if no matching response received within timeout
- `ConnectionError` - Raised if unable to connect to radiod
- `CommandError` - Raised if command encoding fails

## Testing

To test the implementation:

1. Ensure radiod is running and accessible
2. Run the CLI tool:
   ```bash
   ./examples/tune.py -r radiod.local -s 10000000 -f 10M -m am -v
   ```
3. Run the programmatic example:
   ```bash
   python examples/tune_example.py
   ```

## Files Modified/Created

**Modified:**
- `ka9q/types.py` - Updated StatusType constants, added Encoding class
- `ka9q/control.py` - Added decode functions, tune() method, helper methods
- `ka9q/__init__.py` - Exported Encoding class
- `README.md` - Added documentation for tune functionality

**Created:**
- `examples/tune.py` - CLI tool (Python implementation of ka9q-radio's tune.c)
- `examples/tune_example.py` - Programmatic usage examples
- `TUNE_IMPLEMENTATION.md` - This documentation file

## Future Enhancements

Potential improvements:
1. Full socket address encoding/decoding for destination parameter
2. Additional status fields as radiod protocol evolves
3. Async/await version of tune() method
4. Batch tuning of multiple channels
5. Status streaming (continuous updates)

## References

- ka9q-radio official repository: https://github.com/ka9q/ka9q-radio
- tune.c source: `/Users/mjh/Sync/GitHub/ka9q-radio/src/tune.c`
- status.h source: `/Users/mjh/Sync/GitHub/ka9q-radio/src/status.h`
