# Code Review Recommendations - ka9q-python

## Priority 1: Critical Fixes (Do Immediately)

### 1. Fix Documentation-Code Mismatch

**Current Problem:** README documents `create_channel()` but code implements `create_and_configure_channel()`

**Solution Options:**
1. Rename method to `create_channel()` (simpler API)
2. Keep current name and update all documentation
3. Add alias: `create_channel = create_and_configure_channel`

**Recommended:** Option 1 - Rename to `create_channel()` for simplicity and user expectations.

### 2. Add Input Validation

Add validation wrapper functions:

```python
def _validate_frequency(freq_hz: float) -> None:
    """Validate frequency is within reasonable SDR range"""
    if not (0 < freq_hz < 10e12):  # 10 THz max
        raise ValidationError(f"Invalid frequency: {freq_hz} Hz")

def _validate_sample_rate(rate: int) -> None:
    """Validate sample rate is positive and reasonable"""
    if not (1 <= rate <= 100e6):  # 100 MHz max
        raise ValidationError(f"Invalid sample rate: {rate} Hz")

def _validate_ssrc(ssrc: int) -> None:
    """Validate SSRC fits in 32-bit unsigned integer"""
    if not (0 <= ssrc <= 0xFFFFFFFF):
        raise ValidationError(f"Invalid SSRC: {ssrc} (must be 0-4294967295)")

def _validate_timeout(timeout: float) -> None:
    """Validate timeout is positive"""
    if timeout <= 0:
        raise ValidationError(f"Timeout must be positive, got {timeout}")
```

Apply these in all public methods that accept these parameters.

### 3. Improve Exception Handling

Replace generic exception handlers:

```python
# BEFORE (control.py line 355-357)
except Exception as e:
    logger.error(f"Failed to connect to radiod: {e}")
    raise

# AFTER
except socket.error as e:
    logger.error(f"Socket error connecting to radiod: {e}")
    raise ConnectionError(f"Failed to connect to radiod: {e}") from e
except subprocess.TimeoutExpired as e:
    logger.error(f"Timeout resolving address: {e}")
    raise ConnectionError(f"Address resolution timeout: {e}") from e
except Exception as e:
    logger.error(f"Unexpected error connecting to radiod: {e}", exc_info=True)
    raise ConnectionError(f"Failed to connect to radiod: {e}") from e
```

### 4. Add Context Manager Support

```python
class RadiodControl:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except Exception as e:
            logger.warning(f"Error closing RadiodControl: {e}")
        return False  # Don't suppress exceptions

# Usage:
# with RadiodControl("radiod.local") as control:
#     control.create_channel(...)
# # Automatically closed
```

## Priority 2: Reliability Improvements

### 5. Robust Socket Cleanup

```python
def close(self):
    """Close all sockets (control and status listener)"""
    errors = []
    
    if self.socket:
        try:
            self.socket.close()
        except Exception as e:
            errors.append(f"Control socket: {e}")
        finally:
            self.socket = None
    
    if self._status_sock:
        try:
            logger.debug("Closing cached status listener socket")
            self._status_sock.close()
        except Exception as e:
            errors.append(f"Status socket: {e}")
        finally:
            self._status_sock = None
    
    if errors:
        logger.warning(f"Errors during close: {'; '.join(errors)}")
```

### 6. Bounded Integer Encoding

```python
def encode_int64(buf: bytearray, type_val: int, x: int) -> int:
    """
    Encode a 64-bit integer in TLV format
    
    Args:
        buf: Buffer to write to
        type_val: TLV type identifier
        x: Integer value (must be 0 <= x <= 2^64-1)
        
    Raises:
        ValidationError: If x is negative or too large
    """
    if x < 0:
        raise ValidationError(f"Cannot encode negative integer: {x}")
    if x >= 2**64:
        raise ValidationError(f"Integer too large for 64-bit encoding: {x}")
    
    buf.append(type_val)
    
    if x == 0:
        buf.append(0)
        return 2
    
    # Rest of encoding...
```

### 7. Retry Logic for Network Operations

```python
def send_command(self, cmdbuffer: bytearray, max_retries: int = 3):
    """Send a command packet to radiod with retry logic"""
    if not self.socket:
        raise RuntimeError("Not connected to radiod")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            hex_dump = ' '.join(f'{b:02x}' for b in cmdbuffer)
            logger.debug(f"Sending {len(cmdbuffer)} bytes to {self.dest_addr}: {hex_dump}")
            
            sent = self.socket.sendto(bytes(cmdbuffer), self.dest_addr)
            logger.debug(f"Sent {sent} bytes to radiod")
            return sent
        except socket.error as e:
            last_error = e
            logger.warning(f"Send attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
    
    logger.error(f"Failed to send command after {max_retries} attempts")
    raise CommandError(f"Failed to send command: {last_error}") from last_error
```

### 8. Thread-Safe Operations

```python
import threading

class RadiodControl:
    def __init__(self, status_address: str):
        self.status_address = status_address
        self.socket = None
        self._status_sock = None
        self._status_sock_lock = threading.RLock()  # Reentrant lock
        self._socket_lock = threading.RLock()  # Protect control socket
        self._connect()
    
    def send_command(self, cmdbuffer: bytearray):
        """Thread-safe command sending"""
        with self._socket_lock:
            if not self.socket:
                raise RuntimeError("Not connected to radiod")
            # ... send logic ...
```

## Priority 3: Code Quality Improvements

### 9. Refactor Shared Code

Create `ka9q/utils.py`:

```python
"""Shared utility functions"""

import socket
import subprocess
import re
import logging

logger = logging.getLogger(__name__)

def resolve_multicast_address(address: str, timeout: float = 5.0) -> str:
    """
    Resolve hostname/mDNS address to IP (shared by control and discovery)
    
    Args:
        address: Hostname, .local name, or IP address
        timeout: Resolution timeout in seconds
        
    Returns:
        Resolved IP address string
        
    Raises:
        ConnectionError: If resolution fails
    """
    # Check if already IP
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', address):
        return address
    
    # Try avahi-resolve (Linux)
    try:
        result = subprocess.run(
            ['avahi-resolve', '-n', address],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                logger.debug(f"Resolved via avahi: {address} -> {parts[1]}")
                return parts[1]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try dns-sd (macOS)
    try:
        result = subprocess.run(
            ['dns-sd', '-G', 'v4', address],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match and address in line:
                    logger.debug(f"Resolved via dns-sd: {address} -> {match.group(1)}")
                    return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback to getaddrinfo
    try:
        addr_info = socket.getaddrinfo(address, None, socket.AF_INET, socket.SOCK_DGRAM)
        resolved = addr_info[0][4][0]
        logger.debug(f"Resolved via getaddrinfo: {address} -> {resolved}")
        return resolved
    except Exception as e:
        raise ConnectionError(f"Failed to resolve {address}: {e}") from e
```

### 10. Improve Documentation

Add comprehensive docstrings:

```python
def create_channel(self, ssrc: int, frequency_hz: float, 
                   preset: str = "iq", sample_rate: Optional[int] = None,
                   agc_enable: int = 0, gain: float = 0.0):
    """
    Create and configure a new radiod channel
    
    This sends all parameters in a single packet to radiod, which creates
    the channel when it receives the first command for a new SSRC.
    
    Args:
        ssrc: Channel identifier (0 to 4294967295). Convention is to use
              frequency in Hz as SSRC (e.g., 14074000 for 14.074 MHz)
        frequency_hz: RF frequency in Hz (typically 0 to 6 GHz for HF/VHF/UHF,
                     depends on your SDR hardware)
        preset: Demodulation mode (default: "iq" for linear/IQ mode)
                Common values: "iq", "usb", "lsb", "am", "fm", "cw"
        sample_rate: Output sample rate in Hz (optional, radiod uses default if None)
                    Typical values: 12000, 48000, 16000
        agc_enable: Automatic Gain Control (0=disabled/manual gain, 1=enabled)
                   Default: 0 (manual gain mode)
        gain: Manual gain in dB, used when agc_enable=0 (default: 0.0)
              Typical range: -60 to +60 dB
    
    Raises:
        ValidationError: If parameters are out of valid ranges
        CommandError: If command fails to send
        RuntimeError: If not connected to radiod
    
    Example:
        >>> control = RadiodControl("radiod.local")
        >>> control.create_channel(
        ...     ssrc=14074000,
        ...     frequency_hz=14.074e6,
        ...     preset="usb",
        ...     sample_rate=12000
        ... )
    """
```

### 11. Add Examples of Error Handling

Create `examples/error_handling.py`:

```python
#!/usr/bin/env python3
"""
Demonstrate proper error handling with ka9q-python
"""

from ka9q import RadiodControl, ValidationError, ConnectionError, CommandError
import logging

logging.basicConfig(level=logging.INFO)

def main():
    try:
        # Use context manager for automatic cleanup
        with RadiodControl("radiod.local") as control:
            
            # Validate parameters before using
            ssrc = 14074000
            freq = 14.074e6
            
            # Create channel with error handling
            try:
                control.create_channel(
                    ssrc=ssrc,
                    frequency_hz=freq,
                    preset="usb",
                    sample_rate=12000
                )
                print(f"✓ Channel {ssrc} created successfully")
            except ValidationError as e:
                print(f"✗ Invalid parameters: {e}")
                return 1
            except CommandError as e:
                print(f"✗ Command failed: {e}")
                return 1
            
            # Tune with timeout
            try:
                status = control.tune(ssrc, frequency_hz=freq, timeout=10.0)
                print(f"✓ Channel tuned: {status['frequency']/1e6:.3f} MHz")
            except TimeoutError:
                print(f"✗ Tune timeout - radiod may not be responding")
                return 1
                
    except ConnectionError as e:
        print(f"✗ Connection failed: {e}")
        print("  Check that radiod is running and address is correct")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
```

## Testing Recommendations

### Unit Tests to Add

1. **Input validation tests** - test all boundary conditions
2. **Network error simulation** - mock socket failures
3. **Thread safety tests** - concurrent access patterns
4. **Resource cleanup tests** - verify no leaks
5. **Encoding edge cases** - test max values, zero, boundary conditions

### Integration Tests to Add

1. **Retry logic verification** - ensure retries work correctly
2. **Timeout handling** - verify all timeout paths
3. **Context manager usage** - verify cleanup in all scenarios
4. **Error recovery** - test recovery from transient failures

## Documentation Updates Required

1. **README.md**
   - Change all `create_channel()` to match actual method name
   - Add error handling examples
   - Document valid parameter ranges
   - Add threading considerations section

2. **INSTALLATION.md**  
   - Fix method name references
   - Add troubleshooting for common errors

3. **New file: ARCHITECTURE.md**
   - Document protocol details
   - Explain threading model
   - Document error handling strategy

4. **New file: API_REFERENCE.md**
   - Complete API documentation with all parameters
   - Valid ranges for all parameters
   - Error conditions for each method
   - Thread safety guarantees

## Performance Considerations

1. **Socket reuse** - Already implemented well in `tune()` method
2. **Batch operations** - Consider adding bulk channel creation
3. **Async support** - Consider adding asyncio version for high-performance apps
4. **Connection pooling** - For apps managing many radiod instances

## Backward Compatibility

If renaming `create_and_configure_channel()` to `create_channel()`:

```python
# Add deprecation warning for old name
def create_and_configure_channel(self, *args, **kwargs):
    """Deprecated: Use create_channel() instead"""
    import warnings
    warnings.warn(
        "create_and_configure_channel() is deprecated, use create_channel()",
        DeprecationWarning,
        stacklevel=2
    )
    return self.create_channel(*args, **kwargs)
```

## Summary Priority Matrix

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| P1 | Fix method name in docs | High | Low |
| P1 | Add input validation | High | Medium |
| P1 | Improve exception handling | High | Medium |
| P1 | Add context manager | Medium | Low |
| P2 | Robust socket cleanup | Medium | Low |
| P2 | Bounded integer encoding | Medium | Low |
| P2 | Retry logic | Medium | Medium |
| P2 | Thread safety | Medium | Medium |
| P3 | Refactor shared code | Low | High |
| P3 | Improve documentation | Low | High |

Total estimated effort: ~2-3 days for P1+P2 items
