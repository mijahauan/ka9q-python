# Architecture - ka9q-python

This document describes the internal architecture, design decisions, and protocol implementation of ka9q-python.

---

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Protocol Implementation](#protocol-implementation)
4. [Threading Model](#threading-model)
5. [Error Handling Strategy](#error-handling-strategy)
6. [Network Operations](#network-operations)
7. [Resource Management](#resource-management)
8. [Design Principles](#design-principles)

---

## Overview

ka9q-python is a pure Python library for controlling ka9q-radio channels using radiod's TLV (Type-Length-Value) command protocol. The library is designed to be:

- **General-purpose**: No application-specific assumptions
- **Robust**: Comprehensive error handling and validation
- **Thread-safe**: Safe for multi-threaded applications
- **Cross-platform**: Works on Linux, macOS, and Windows
- **Production-ready**: Suitable for long-running applications

---

## Module Structure

```
ka9q/
├── __init__.py       # Package exports and version
├── control.py        # RadiodControl class and TLV encoding
├── discovery.py      # Channel discovery functions
├── types.py          # Protocol constants (StatusType, Encoding)
├── exceptions.py     # Custom exception classes
└── utils.py          # Shared utilities (mDNS resolution)
```

### Module Responsibilities

#### `control.py` - Command and Control
- **Purpose**: Send TLV commands to radiod, manage connections
- **Key Classes**: `RadiodControl`
- **Key Functions**: 
  - TLV encoding: `encode_int64()`, `encode_double()`, `encode_float()`, `encode_string()`
  - TLV decoding: `decode_int()`, `decode_double()`, `decode_float()`, `decode_string()`
  - Validation: `_validate_ssrc()`, `_validate_frequency()`, etc.
- **Network**: UDP multicast for sending commands and receiving status

#### `discovery.py` - Service Discovery
- **Purpose**: Discover active channels and radiod services
- **Key Functions**:
  - `discover_channels()` - Automatic discovery (native + fallback)
  - `discover_channels_native()` - Pure Python discovery
  - `discover_channels_via_control()` - Use ka9q-radio's `control` utility
  - `discover_radiod_services()` - Find radiod instances via mDNS
- **Network**: Listens to multicast status stream

#### `types.py` - Protocol Constants
- **Purpose**: Define all StatusType enum values and encoding constants
- **Source**: Mirrors ka9q-radio/src/status.h exactly
- **Contains**: 110+ StatusType constants, Encoding types

#### `exceptions.py` - Error Handling
- **Purpose**: Define custom exception hierarchy
- **Exceptions**:
  - `Ka9qError` (base)
  - `ConnectionError` (network/connection issues)
  - `CommandError` (command sending failures)
  - `ValidationError` (invalid parameters)
  - `DiscoveryError` (discovery failures)

#### `utils.py` - Shared Utilities
- **Purpose**: Common functions used across modules
- **Key Functions**:
  - `resolve_multicast_address()` - Cross-platform mDNS resolution
  - `create_multicast_socket()` - Configure multicast UDP sockets
  - `validate_multicast_address()` - Validate multicast IP ranges

---

## Protocol Implementation

### TLV (Type-Length-Value) Format

All communication with radiod uses TLV encoding:

```
[Type: 1 byte][Length: 1-2 bytes][Value: variable]
```

#### Type Byte
- Identifies the parameter (e.g., `StatusType.RADIO_FREQUENCY = 33`)
- Defined in `types.py`, must match ka9q-radio/status.h

#### Length Encoding
- **Single-byte** (length < 128): Length value directly
- **Multi-byte** (length >= 128): `0x80 | high_byte`, then `low_byte`
- **Zero length**: Used for zero values (compressed encoding)

#### Value Encoding

**Integers (64-bit)**:
- Big-endian encoding
- Leading zeros stripped (compressed)
- Example: `12345` → `[type][2][0x30, 0x39]`

**Floats (IEEE 754)**:
- **float32**: 4 bytes, big-endian
- **float64**: 8 bytes, big-endian
- Encoded as integers after packing to IEEE 754 format

**Strings (UTF-8)**:
- UTF-8 encoded bytes
- Length-prefixed
- Example: `"usb"` → `[type][3][0x75, 0x73, 0x62]`

**EOL Marker**:
- Every command packet ends with `StatusType.EOL = 0`
- Signals end of parameter list

### Command Packet Structure

```
[CMD_TYPE: 1][param1_type][param1_len][param1_data]...[EOL]
```

Example command to set frequency:
```python
cmdbuffer = bytearray()
cmdbuffer.append(CMD)  # Command packet type = 1
encode_double(cmdbuffer, StatusType.RADIO_FREQUENCY, 14.074e6)
encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, 14074000)
encode_int(cmdbuffer, StatusType.COMMAND_TAG, 12345)
encode_eol(cmdbuffer)
# Send via UDP multicast
```

### Status Response Structure

```
[STATUS_TYPE: 0][param1_type][param1_len][param1_data]...[EOL]
```

Radiod sends status responses:
- As multicast UDP packets
- Periodically (every few seconds)
- In response to commands (matched by COMMAND_TAG)

---

## Threading Model

### Thread Safety Guarantees

**RadiodControl** is thread-safe for:
- ✅ All public methods (`create_channel()`, `set_frequency()`, `tune()`, etc.)
- ✅ Sending commands (protected by `_socket_lock`)
- ✅ Status listening (protected by `_status_sock_lock`)
- ✅ Resource cleanup (`close()`)

### Lock Hierarchy

```
_socket_lock (RLock)
└── Protects: self.socket, send operations

_status_sock_lock (RLock)  
└── Protects: self._status_sock, tune() operations
```

**Lock Type**: `threading.RLock()` (reentrant)
- Allows same thread to acquire lock multiple times
- Prevents deadlocks in recursive calls

### Concurrent Usage Pattern

```python
control = RadiodControl("radiod.local")

def worker(frequency):
    # Safe from multiple threads
    control.set_frequency(ssrc=10000, frequency_hz=frequency)

threads = [Thread(target=worker, args=(f,)) for f in frequencies]
for t in threads:
    t.start()
for t in threads:
    t.join()

control.close()
```

---

## Error Handling Strategy

### Validation Philosophy

**Fail Fast**: Validate inputs at public API boundaries before any network operations.

```python
def create_channel(self, ssrc, frequency_hz, ...):
    # Validate ALL inputs first
    _validate_ssrc(ssrc)
    _validate_frequency(frequency_hz)
    # ... then proceed with operations
```

### Exception Hierarchy

```
Exception
└── Ka9qError (base for all ka9q errors)
    ├── ConnectionError (network/connection)
    ├── CommandError (sending failures)
    ├── ValidationError (invalid parameters)
    └── DiscoveryError (discovery failures)
```

### Exception Chaining

Always preserve original exceptions:

```python
except socket.error as e:
    raise CommandError(f"Socket error: {e}") from e
    # ^^^ 'from e' preserves stack trace
```

### Error Recovery

**Retry Logic** (for transient failures):
- Network operations retry up to 3 times by default
- Exponential backoff: 0.1s → 0.2s → 0.4s
- Configurable via `send_command(max_retries=N)`

**Resource Cleanup** (always safe):
- `close()` method handles all cleanup errors
- Safe to call multiple times
- Context manager ensures cleanup even on exceptions

---

## Network Operations

### Multicast UDP

**Protocol**: UDP (connectionless)
**Multicast Group**: 239.x.x.x (configurable per radiod instance)
**Port**: 5006 (standard radiod control/status port)

### Address Resolution

**Cross-platform mDNS**:
1. Check if already IP address (no resolution needed)
2. Try `avahi-resolve` (Linux)
3. Try `dns-sd` (macOS)
4. Fallback to `getaddrinfo()` (works everywhere)

**Timeout**: 5 seconds default, configurable

### Socket Configuration

**Control Socket** (for sending commands):
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, inet_aton('0.0.0.0'))
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
```

**Status Socket** (for receiving responses):
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # if available
sock.bind(('0.0.0.0', 5006))  # CRITICAL: must bind to multicast port
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
sock.settimeout(0.1)  # For polling
```

### Performance Optimizations

**Socket Reuse**:
- Status listener socket cached in `tune()` method
- Avoids create/destroy overhead (~20-30ms saved per call)
- Prevents socket exhaustion in loops

**Exponential Backoff**:
- Command retries use exponential backoff
- Reduces network spam
- Improves reliability on congested networks

---

## Resource Management

### Lifecycle

```
RadiodControl("radiod.local")
    ↓
__init__() → _connect() → socket created
    ↓
send commands... (multiple operations)
    ↓
close() or __exit__() → sockets closed
```

### Context Manager Pattern

**Recommended Usage**:
```python
with RadiodControl("radiod.local") as control:
    control.create_channel(...)
# Automatic cleanup, guaranteed
```

**Implementation**:
```python
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()
    return False  # Don't suppress exceptions
```

### Socket Cleanup

**Robust close()** method:
- Handles errors during cleanup
- Safe to call multiple times
- Sets sockets to None in finally blocks
- Logs warnings for any failures

```python
def close(self):
    errors = []
    
    if self.socket:
        try:
            self.socket.close()
        except Exception as e:
            errors.append(f"control: {e}")
        finally:
            self.socket = None
    
    # Similar for _status_sock...
    
    if errors:
        logger.warning(f"Cleanup errors: {'; '.join(errors)}")
```

---

## Design Principles

### 1. **No Application Assumptions**

The library makes **zero** assumptions about:
- What you're recording
- Where you're storing data
- What sample rates you need
- What frequencies you monitor
- Your data format or encoding

**Example**: Unlike application-specific libraries, we don't have a "record FT8" function. Instead, we provide primitives:
```python
control.create_channel(ssrc=14074000, frequency_hz=14.074e6, preset="usb")
# YOU decide what to do with the RTP stream
```

### 2. **Defensive Programming**

- **Validate early**: Check parameters before network operations
- **Fail fast**: Raise clear errors immediately
- **Preserve context**: Use exception chaining
- **Guard resources**: Always cleanup, even on errors

### 3. **Composability**

Functions are designed to be composed:
```python
# Discover channels
channels = discover_channels("radiod.local")

# Create control instance
with RadiodControl("radiod.local") as control:
    # Tune to specific frequency
    status = control.tune(ssrc=10000, frequency_hz=14.074e6)
    
    # Adjust based on status
    if status['snr'] < 10:
        control.set_gain(ssrc=10000, gain_db=20)
```

### 4. **Explicit is Better Than Implicit**

- Method names are clear: `create_channel()`, not `setup()`
- Parameters are explicit: `frequency_hz`, not `freq`
- Errors are specific: `ValidationError`, not generic `Exception`
- Return values are documented: `Dict[int, ChannelInfo]`

### 5. **Production-First**

Designed for production use from day 1:
- Thread-safe by default
- Robust error handling
- Resource leak prevention
- Network retry logic
- Comprehensive logging
- Context manager support

---

## Protocol Compatibility

### ka9q-radio Version

**Based on**: ka9q-radio status.h protocol
**Compatible with**: ka9q-radio v1.x and v2.x
**Constants**: All 110+ StatusType values match status.h exactly

### Future Compatibility

**Adding new parameters**:
1. Update `types.py` with new StatusType constants
2. Add encode/decode if needed (rare)
3. Add setter method if convenient

**Protocol changes**:
- TLV format is stable and unlikely to change
- New StatusType values are backward compatible
- Deprecated values remain for compatibility

---

## Performance Characteristics

### Typical Operation Times

| Operation | Time | Notes |
|-----------|------|-------|
| `create_channel()` | 1-2 ms | Single UDP packet |
| `set_frequency()` | 1-2 ms | Single UDP packet |
| `tune()` | 50-500 ms | Waits for status response |
| `discover_channels()` | 2-5 sec | Listens for status packets |
| `resolve_multicast_address()` | 10-100 ms | Varies by method |

### Memory Footprint

- **RadiodControl instance**: ~2 KB
- **Per command buffer**: ~100 bytes
- **Per status response**: ~1-8 KB
- **Socket overhead**: ~8 KB per socket

### Network Bandwidth

- **Command packet**: 20-100 bytes
- **Status packet**: 500-4000 bytes
- **Frequency**: Commands as needed, status every 1-5 seconds

---

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### View Hex Dumps

```python
# control.py logs hex dumps of all sent commands
# DEBUG: Sending 23 bytes: 01 21 08 41 4c 40 00 00 00 00 00 12 04 00 d6 f2 d0 ...
```

### Common Issues

**Problem**: "Failed to resolve address"
- Check mDNS is working: `avahi-resolve -n radiod.local`
- Try IP address directly instead of .local name

**Problem**: "Socket error: Permission denied"
- Multicast may require sudo on some systems
- Check firewall allows UDP port 5006

**Problem**: "ValidationError: Invalid SSRC"
- SSRC must be 0-4294967295 (32-bit unsigned)
- Convention: use frequency in Hz as SSRC

---

## Testing Strategy

### Unit Tests
- Mock network operations
- Test encoding/decoding
- Validate error handling

### Integration Tests
- Require live radiod instance
- Test actual channel creation
- Verify status responses

### Performance Tests
- Socket reuse efficiency
- Retry logic behavior
- Resource leak detection

---

## Version History

- **v1.0.0**: Initial release
- **v2.0.0**: Added tune() method, comprehensive testing
- **v2.1.0**: Input validation, thread safety, retry logic, context manager support

---

*For API documentation, see [API_REFERENCE.md](API_REFERENCE.md)*  
*For user guide, see [README.md](README.md)*
